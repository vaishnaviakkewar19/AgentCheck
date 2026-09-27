"""The Gatekeeper: decides whether a proposed agent duplicates an existing one.

Layer 1  LLM splits the request into atomic sub-tasks.
Layer 2  Similarity search shortlists the most similar registry agents.
Layer 3  LLM judges, per candidate and per sub-task: covered / partial / not covered.
Scoring  Deterministic Python: coverage %, two-agent combinations, verdict.
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Optional, Sequence

from agentcheck import config, llm, similarity
from agentcheck.models import (
    AgentManifest,
    AgentRequest,
    CandidateJudgement,
    CandidateScore,
    CheckResult,
    ComboScore,
    Decomposition,
    JudgeResult,
    Verdict,
)
from agentcheck.registry import Registry

_STATUS_POINTS = {"covered": 1.0, "partial": 0.5, "not_covered": 0.0}

# Coverage caps when the judge says the agent works on a different kind of data.
DOMAIN_MISMATCH_CAP = 30.0
IO_MISMATCH_CAP = 60.0

DECOMPOSE_SYSTEM = """You analyse proposed AI agents for an internal agent registry.
Break the proposed agent into 3-6 atomic sub-tasks: the distinct pieces of work it must do.

Rules:
- Each sub-task is a short verb phrase (e.g. "extract line items from invoice").
- Keep the domain and data type in each sub-task ("summarize clinical discharge notes",
  not just "summarize") so it can be compared fairly with other agents.
- Include integrations or delivery steps as their own sub-tasks (e.g. "push data to SAP").
- Do not invent work the description does not ask for.

Also return 5-10 search_keywords: plain, standard terms for the data and actions involved,
including common synonyms (e.g. "inbox digest" -> "email", "summary", "summarize")."""

JUDGE_SYSTEM = """You are the Gatekeeper of an internal AI agent registry. Someone wants to build a
new agent. Decide how much of its work each EXISTING candidate agent already does.

For every candidate, judge every sub-task (same order, same wording as given):
- "covered": the existing agent, as described, already does this with no changes.
- "partial": it does a closely related, narrower, or more generic version, or only part of it.
- "not_covered": it does not do this.

Also set:
- domain_compatible: false if the candidate is built for materially different data or a
  different domain (e.g. email threads vs clinical records), unless its capability is
  genuinely domain-agnostic (e.g. translation). Sharing a verb like "summarize" is NOT enough.
- io_compatible: false if the candidate's inputs/outputs clearly cannot serve the request.
- summary: one sentence a non-technical user would understand.

Be strict and honest. Judge only from the manifests given."""


# ---------------------------------------------------------------------------
# Scoring (pure functions, unit-tested)
# ---------------------------------------------------------------------------


def coverage_of(judgement: CandidateJudgement) -> float:
    if not judgement.subtasks:
        return 0.0
    points = sum(_STATUS_POINTS[s.status] for s in judgement.subtasks)
    score = 100.0 * points / len(judgement.subtasks)
    if not judgement.domain_compatible:
        score = min(score, DOMAIN_MISMATCH_CAP)
    if not judgement.io_compatible:
        score = min(score, IO_MISMATCH_CAP)
    return round(score, 1)


def best_combo(candidates: Sequence[CandidateScore]) -> Optional[ComboScore]:
    """Best pair of agents whose combined sub-task coverage beats either alone."""
    usable = [c for c in candidates if c.judgement.domain_compatible and c.judgement.io_compatible]
    best: Optional[ComboScore] = None
    for a, b in combinations(usable, 2):
        sa, sb = a.judgement.subtasks, b.judgement.subtasks
        if len(sa) != len(sb) or not sa:
            continue
        points = sum(max(_STATUS_POINTS[x.status], _STATUS_POINTS[y.status]) for x, y in zip(sa, sb))
        cov = round(100.0 * points / len(sa), 1)
        if best is None or cov > best.coverage:
            # Chain order follows the sub-task order: whoever handles the earliest step runs first.
            first, second = sorted((a, b), key=_first_useful_step)
            best = ComboScore(
                agent_ids=[first.agent_id, second.agent_id], agent_names=[first.agent_name, second.agent_name], coverage=cov
            )
    return best


def _first_useful_step(c: CandidateScore) -> int:
    return next((i for i, s in enumerate(c.judgement.subtasks) if s.status != "not_covered"), len(c.judgement.subtasks))


def decide(best: Optional[CandidateScore], combo: Optional[ComboScore]) -> tuple[Verdict, str, Optional[ComboScore]]:
    top = best.coverage if best else 0.0
    if best and top >= config.DUPLICATE_THRESHOLD:
        return Verdict.DUPLICATE, f'"{best.agent_name}" already does this ({top:.0f}% coverage). Use it instead?', None
    if best and top >= config.HIGH_OVERLAP_THRESHOLD:
        return (
            Verdict.HIGH_OVERLAP,
            f'"{best.agent_name}" already does {top:.0f}% of this. Extend it with the missing parts instead of building a new agent?',
            None,
        )
    if combo and combo.coverage >= config.HIGH_OVERLAP_THRESHOLD and combo.coverage - top >= config.COMBO_MIN_GAIN:
        names = " + ".join(f'"{n}"' for n in combo.agent_names)
        return Verdict.PARTIAL, f"{names} together cover {combo.coverage:.0f}% of this. Consider combining them.", combo
    if best and top >= config.PARTIAL_THRESHOLD:
        return Verdict.PARTIAL, f'"{best.agent_name}" covers part of this ({top:.0f}%). You may be able to reuse it.', None
    return Verdict.UNIQUE, "No existing agent does this. It is safe to create a new one.", None


# ---------------------------------------------------------------------------
# The three layers
# ---------------------------------------------------------------------------


def _request_text(req: AgentRequest) -> str:
    return (
        f"Name: {req.name}\nDescription: {req.description}\n"
        f"Inputs: {', '.join(req.input_types) or 'unspecified'}\n"
        f"Outputs: {', '.join(req.output_types) or 'unspecified'}\n"
        f"Domain: {req.domain}"
    )


def _manifest_text(a: AgentManifest) -> str:
    return (
        f"agent_id: {a.id}\nName: {a.name}\nDescription: {a.description}\n"
        f"Capabilities: {'; '.join(a.capabilities)}\n"
        f"Inputs: {', '.join(a.input_types)}\nOutputs: {', '.join(a.output_types)}\nDomain: {a.domain}"
    )


def decompose(req: AgentRequest) -> Decomposition:
    result = llm.structured(DECOMPOSE_SYSTEM, _request_text(req), Decomposition)
    result.subtasks = [s.strip() for s in result.subtasks if s.strip()]
    return result


def shortlist(req: AgentRequest, terms: List[str], agents: List[AgentManifest], k: int) -> Dict[str, float]:
    query = " ".join([req.name, req.description, req.domain, *req.input_types, *req.output_types, *terms])
    ranked = similarity.rank(query, [a.profile_text() for a in agents])
    return {agents[i].id: round(score, 3) for i, score in ranked[:k]}


def judge(req: AgentRequest, subtasks: List[str], candidates: List[AgentManifest]) -> JudgeResult:
    numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(subtasks))
    manifests = "\n\n".join(_manifest_text(a) for a in candidates)
    user = (
        f"PROPOSED AGENT\n{_request_text(req)}\n\nSUB-TASKS\n{numbered}\n\n"
        f"EXISTING CANDIDATE AGENTS\n{manifests}\n\n"
        f"Return one judgement per candidate (use the exact agent_id)."
    )
    return llm.structured(JUDGE_SYSTEM, user, JudgeResult)


def check(req: AgentRequest, registry: Registry) -> CheckResult:
    agents = registry.list()
    decomposition = decompose(req)
    subtasks = decomposition.subtasks
    sims = shortlist(req, subtasks + decomposition.search_keywords, agents, config.TOP_K_CANDIDATES)
    by_id = {a.id: a for a in agents}
    candidates = [by_id[i] for i in sims]

    scores: List[CandidateScore] = []
    if candidates:
        for j in judge(req, subtasks, candidates).candidates:
            if j.agent_id not in by_id:
                continue  # ignore hallucinated ids
            scores.append(
                CandidateScore(
                    agent_id=j.agent_id,
                    agent_name=by_id[j.agent_id].name,
                    similarity=sims.get(j.agent_id, 0.0),
                    coverage=coverage_of(j),
                    judgement=j,
                )
            )
    scores.sort(key=lambda c: c.coverage, reverse=True)
    best = scores[0] if scores else None
    verdict, message, combo = decide(best, best_combo(scores))
    return CheckResult(
        request=req, subtasks=subtasks, candidates=scores, best=best, combo=combo, verdict=verdict, message=message
    )
