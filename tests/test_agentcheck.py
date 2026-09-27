"""Offline tests: no API key needed (LLM calls are stubbed)."""

import pytest

from agentcheck import config, gatekeeper, similarity
from agentcheck.models import (
    AgentRequest,
    CandidateJudgement,
    CandidateScore,
    Decomposition,
    JudgeResult,
    SubtaskJudgement,
    Verdict,
)
from agentcheck.registry import Registry
from agentcheck.scenarios import SCENARIOS


def judgement(agent_id, statuses, domain=True, io=True):
    return CandidateJudgement(
        agent_id=agent_id,
        domain_compatible=domain,
        io_compatible=io,
        subtasks=[SubtaskJudgement(subtask=f"task {i}", status=s, reason="") for i, s in enumerate(statuses)],
        summary="",
    )


def score(agent_id, statuses, **kw):
    j = judgement(agent_id, statuses, **kw)
    return CandidateScore(agent_id=agent_id, agent_name=agent_id, similarity=0.5, coverage=gatekeeper.coverage_of(j), judgement=j)


@pytest.fixture
def registry(tmp_path):
    return Registry(agents_dir=tmp_path / "agents", seed_dir=config.SEED_DIR)


# ---------- scoring ----------


def test_coverage_formula():
    assert gatekeeper.coverage_of(judgement("a", ["covered"] * 4 + ["not_covered"])) == 80.0
    assert gatekeeper.coverage_of(judgement("a", ["covered", "partial"])) == 75.0


def test_domain_mismatch_caps_coverage():
    j = judgement("email", ["covered", "covered", "partial"], domain=False)
    assert gatekeeper.coverage_of(j) == gatekeeper.DOMAIN_MISMATCH_CAP


def test_verdict_thresholds():
    assert gatekeeper.decide(score("a", ["covered"] * 10), None)[0] == Verdict.DUPLICATE
    assert gatekeeper.decide(score("a", ["covered"] * 4 + ["not_covered"]), None)[0] == Verdict.HIGH_OVERLAP
    assert gatekeeper.decide(score("a", ["covered", "not_covered"]), None)[0] == Verdict.PARTIAL
    assert gatekeeper.decide(score("a", ["not_covered"] * 3), None)[0] == Verdict.UNIQUE
    assert gatekeeper.decide(None, None)[0] == Verdict.UNIQUE


def test_combo_detects_complementary_agents():
    translator = score("translator", ["covered", "not_covered"])
    sentiment = score("sentiment", ["not_covered", "covered"])
    combo = gatekeeper.best_combo([sentiment, translator])
    assert combo.coverage == 100.0
    assert combo.agent_ids == ["translator", "sentiment"]  # translate first, then score
    verdict, _, chosen = gatekeeper.decide(translator, combo)
    assert verdict == Verdict.PARTIAL and chosen is combo


def test_combo_ignores_incompatible_domain():
    a = score("a", ["covered", "not_covered"])
    b = score("b", ["not_covered", "covered"], domain=False)
    assert gatekeeper.best_combo([a, b]) is None


# ---------- registry ----------


def test_registry_seeds_and_registers(registry):
    assert len(registry.list()) == 8
    req = SCENARIOS[5]["request"]
    agent = registry.register(req, ["build sprint report"])
    assert registry.get(agent.id).name == req.name
    assert len(registry.list()) == 9
    registry.reset()
    assert len(registry.list()) == 8


def test_registry_extend_bumps_version(registry):
    agent = registry.extend("invoice_extractor", ["push invoice data to SAP"])
    assert agent.version == 2
    assert "push invoice data to SAP" in agent.capabilities
    assert "push invoice data to SAP" in agent.system_prompt


def test_unique_ids(registry):
    req = AgentRequest(name="Translator", description="x")
    assert registry.register(req, []).id == "translator_2"


# ---------- similarity ----------


@pytest.mark.parametrize(
    "scenario_idx, expected_id",
    [(0, "email_summarizer"), (1, "email_summarizer"), (2, "invoice_extractor"), (3, "translator"), (3, "sentiment_analyzer"), (4, "clinical_note_summarizer")],
)
def test_shortlist_contains_expected_agent(registry, scenario_idx, expected_id):
    req = SCENARIOS[scenario_idx]["request"]
    ids = gatekeeper.shortlist(req, [], registry.list(), config.TOP_K_CANDIDATES)
    assert expected_id in ids


def test_rank_orders_best_first():
    ranked = similarity.rank("translate spanish text", ["summarize emails", "translate text between languages"])
    assert ranked[0][0] == 1


# ---------- end-to-end with stubbed LLM ----------


def test_check_end_to_end_with_stub(registry, monkeypatch):
    def fake_structured(system, user, fmt):
        if fmt is Decomposition:
            return Decomposition(subtasks=["read invoice", "extract fields", "push to SAP"])
        ids = [line.split(": ", 1)[1] for line in user.splitlines() if line.startswith("agent_id: ")]
        return JudgeResult(
            candidates=[
                judgement(i, ["covered", "covered", "not_covered"] if i == "invoice_extractor" else ["not_covered"] * 3)
                for i in ids
            ]
            + [judgement("made_up_agent", ["covered"] * 3)]  # hallucinated id must be ignored
        )

    monkeypatch.setattr(gatekeeper.llm, "structured", fake_structured)
    result = gatekeeper.check(SCENARIOS[2]["request"], registry)
    assert result.best.agent_id == "invoice_extractor"
    assert result.best.coverage == pytest.approx(66.7)
    assert result.best.missing == ["task 2"]
    assert all(c.agent_id != "made_up_agent" for c in result.candidates)
    assert result.verdict == Verdict.PARTIAL
