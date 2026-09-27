"""AgentCheck demo UI.  Run with:  streamlit run app.py"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from agentcheck import audit, config, gatekeeper, runner, similarity
from agentcheck.llm import LLMError
from agentcheck.models import AgentRequest, CheckResult, Verdict
from agentcheck.registry import Registry
from agentcheck.samples import SAMPLES
from agentcheck.scenarios import SCENARIOS

st.set_page_config(page_title="AgentCheck", page_icon="🛡️", layout="wide")

PAGES = ["📚 Registry", "➕ Create Agent", "▶️ Run Agent", "📜 Audit Log"]
STATUS_ICON = {"covered": "✅ Covered", "partial": "🟡 Partial", "not_covered": "❌ Not covered"}
VERDICT_STYLE = {
    Verdict.DUPLICATE: ("🔴 Duplicate", st.error),
    Verdict.HIGH_OVERLAP: ("🟠 High overlap", st.warning),
    Verdict.PARTIAL: ("🟡 Partial overlap", st.info),
    Verdict.UNIQUE: ("🟢 Unique", st.success),
}


@st.cache_resource
def get_registry() -> Registry:
    return Registry()


registry = get_registry()
ss = st.session_state
ss.setdefault("page", PAGES[0])
ss.setdefault("check", None)
ss.setdefault("flash", None)


def split_list(text: str) -> list[str]:
    return [p.strip() for p in text.split(",") if p.strip()]


# ---------------------------------------------------------------------------
# Callbacks (run before the page re-renders, so they may change widget state)
# ---------------------------------------------------------------------------


def load_scenario() -> None:
    title = ss.get("scenario_pick")
    sc = next((s for s in SCENARIOS if s["title"] == title), None)
    if not sc:
        return
    r: AgentRequest = sc["request"]
    ss.f_name, ss.f_desc, ss.f_domain = r.name, r.description, r.domain
    ss.f_inputs, ss.f_outputs = ", ".join(r.input_types), ", ".join(r.output_types)
    ss.check = None


def go_run(agent_id: str, chain_id: str | None = None) -> None:
    ss.page = PAGES[2]
    ss.run_agent = agent_id
    ss.chain_agent = chain_id or "(none)"
    ss.run_input = SAMPLES.get(agent_id, "")
    ss.run_output = None


def use_existing(result: CheckResult) -> None:
    b = result.best
    audit.log(result.request.name, result.verdict.value, b.coverage, b.agent_id, "use_existing")
    registry.record_use(b.agent_id)
    ss.flash = f'Great choice! Reusing "{b.agent_name}" instead of building a new agent.'
    ss.check = None
    go_run(b.agent_id)


def combine_existing(result: CheckResult) -> None:
    c = result.combo
    audit.log(result.request.name, result.verdict.value, c.coverage, " + ".join(c.agent_ids), "combine_existing")
    for aid in c.agent_ids:
        registry.record_use(aid)
    ss.flash = f"Chaining {' → '.join(c.agent_names)} instead of building a new agent."
    ss.check = None
    go_run(c.agent_ids[0], c.agent_ids[1])


def extend_existing(result: CheckResult) -> None:
    b = result.best
    agent = registry.extend(b.agent_id, b.missing)
    audit.log(result.request.name, result.verdict.value, b.coverage, b.agent_id, "extend_existing")
    ss.flash = f'Extended "{agent.name}" to v{agent.version} with {len(b.missing)} new capabilities.'
    ss.check = None
    ss.page = PAGES[0]


def create_agent(result: CheckResult, override: bool) -> None:
    related = [result.best.agent_id] if (override and result.best) else []
    agent = registry.register(result.request, result.subtasks, related_to=related)
    audit.log(
        result.request.name,
        result.verdict.value,
        result.best.coverage if result.best else None,
        result.best.agent_id if result.best else None,
        "create_anyway" if override else "create_new",
        ss.get("justification", "") if override else "",
    )
    ss.flash = f'Registered new agent "{agent.name}".' + (" (Override logged.)" if override else "")
    ss.check = None
    ss.page = PAGES[0]


def reset_demo() -> None:
    registry.reset()
    audit.clear()
    for k in ("check", "run_output"):
        ss[k] = None
    ss.flash = "Demo reset: registry restored to the 8 seed agents, audit log cleared."
    ss.page = PAGES[0]


def load_sample() -> None:
    ss.run_input = SAMPLES.get(ss.run_agent, "")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🛡️ AgentCheck")
    st.caption("Stop building agents that already exist.")
    st.radio("Go to", PAGES, key="page", label_visibility="collapsed")
    st.divider()
    s = audit.stats()
    c1, c2 = st.columns(2)
    c1.metric("Duplicates prevented", s["prevented"])
    c2.metric("Hours saved (est.)", s["hours_saved"])
    st.divider()
    has_key = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
    st.caption(f"Model: `{config.CLAUDE_MODEL}` · effort `{config.CLAUDE_EFFORT}`")
    st.caption(f"Candidate search: {similarity.method_name()}")
    if not has_key:
        st.warning("No ANTHROPIC_API_KEY found. Add it to the .env file.")
    st.button("🔄 Reset demo", on_click=reset_demo, width="stretch")

if ss.flash:
    st.success(ss.flash)
    ss.flash = None


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def page_registry() -> None:
    agents = registry.list()
    st.header(f"Agent Registry · {len(agents)} agents")
    cols = st.columns(3)
    for i, a in enumerate(agents):
        with cols[i % 3].container(border=True):
            st.subheader(a.name)
            st.caption(f"{a.domain} · v{a.version} · owner: {a.owner} · used {a.usage_count}×")
            st.write(a.description)
            with st.expander("Capabilities"):
                for c in a.capabilities:
                    st.markdown(f"- {c}")
                st.markdown(f"**Inputs:** {', '.join(a.input_types)}  \n**Outputs:** {', '.join(a.output_types)}")
                if a.related_to:
                    st.markdown(f"**Related to:** {', '.join(a.related_to)}")
            st.button("▶️ Run", key=f"run_{a.id}", on_click=go_run, args=(a.id,))


def render_result(result: CheckResult) -> None:
    label, box = VERDICT_STYLE[result.verdict]
    box(f"### {label}\n{result.message}")

    st.markdown("#### 1 · What the new agent needs to do")
    st.markdown("\n".join(f"{i + 1}. {s}" for i, s in enumerate(result.subtasks)))

    if result.candidates:
        st.markdown("#### 2 · Closest existing agents")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Agent": c.agent_name,
                        "Coverage %": c.coverage,
                        "Search similarity": c.similarity,
                        "Same domain": "✅" if c.judgement.domain_compatible else "❌",
                        "Compatible I/O": "✅" if c.judgement.io_compatible else "❌",
                        "Gatekeeper says": c.judgement.summary,
                    }
                    for c in result.candidates
                ]
            ),
            hide_index=True,
            width="stretch",
            column_config={"Coverage %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%")},
        )

        st.markdown("#### 3 · Sub-task breakdown")
        for c in result.candidates:
            with st.expander(f"{c.agent_name} · {c.coverage:.0f}%", expanded=(c is result.best)):
                st.dataframe(
                    pd.DataFrame(
                        [{"Sub-task": s.subtask, "Status": STATUS_ICON[s.status], "Why": s.reason} for s in c.judgement.subtasks]
                    ),
                    hide_index=True,
                    width="stretch",
                )

    if result.combo:
        st.info(f"🧩 **Combination:** {' + '.join(result.combo.agent_names)} → {result.combo.coverage:.0f}% combined coverage")

    st.markdown("#### 4 · Your decision")
    b = result.best
    if result.verdict == Verdict.UNIQUE:
        st.button("✅ Register new agent", type="primary", on_click=create_agent, args=(result, False))
        return

    cols = st.columns(3)
    if result.combo:
        cols[0].button(
            f"🧩 Chain {' → '.join(result.combo.agent_names)}", type="primary", on_click=combine_existing, args=(result,)
        )
    else:
        cols[0].button(f'♻️ Use "{b.agent_name}"', type="primary", on_click=use_existing, args=(result,))
    if b.missing and result.verdict in (Verdict.HIGH_OVERLAP, Verdict.PARTIAL):
        with cols[1]:
            st.button(f'🔧 Extend "{b.agent_name}"', on_click=extend_existing, args=(result,))
            st.caption("Adds: " + "; ".join(b.missing))
    with cols[2]:
        just = st.text_input("Reason for creating anyway", key="justification", placeholder="e.g. needs Outlook-only integration")
        st.button("⚠️ Create anyway", disabled=not just.strip(), on_click=create_agent, args=(result, True))


def page_create() -> None:
    st.header("Create a new agent")
    st.caption("Before your agent is registered, the Gatekeeper checks whether an existing one already does the job.")

    st.selectbox(
        "Load a demo scenario",
        ["(type your own)"] + [s["title"] for s in SCENARIOS],
        key="scenario_pick",
        on_change=load_scenario,
    )
    sc = next((s for s in SCENARIOS if s["title"] == ss.get("scenario_pick")), None)
    if sc:
        st.caption(f"**Shows:** {sc['shows']} · **Expected:** {VERDICT_STYLE[sc['expected']][0]}")

    with st.form("create"):
        st.text_input("Agent name", key="f_name")
        st.text_area("What should it do?", key="f_desc", height=100)
        c1, c2, c3 = st.columns(3)
        c1.text_input("Inputs (comma-separated)", key="f_inputs")
        c2.text_input("Outputs (comma-separated)", key="f_outputs")
        c3.text_input("Domain", key="f_domain")
        submitted = st.form_submit_button("🛡️ Check with Gatekeeper", type="primary")

    if submitted:
        if not ss.get("f_name", "").strip() or not ss.get("f_desc", "").strip():
            st.error("Please give the agent a name and a description.")
        else:
            req = AgentRequest(
                name=ss.f_name.strip(),
                description=ss.f_desc.strip(),
                input_types=split_list(ss.get("f_inputs", "")),
                output_types=split_list(ss.get("f_outputs", "")),
                domain=ss.get("f_domain", "").strip() or "general",
            )
            with st.status("Gatekeeper is checking the registry…", expanded=True) as status:
                try:
                    st.write("Layer 1 · breaking the request into sub-tasks")
                    st.write("Layer 2 · shortlisting similar agents")
                    st.write("Layer 3 · judging coverage for each sub-task")
                    ss.check = gatekeeper.check(req, registry)
                    status.update(label="Check complete", state="complete", expanded=False)
                except LLMError as e:
                    status.update(label="Check failed", state="error")
                    st.error(str(e))

    if ss.check:
        render_result(ss.check)


def page_run() -> None:
    st.header("Run an agent")
    agents = {a.id: a for a in registry.list()}
    ids = list(agents)
    if ss.get("run_agent") not in agents:
        ss.run_agent = ids[0]
    c1, c2 = st.columns(2)
    c1.selectbox("Agent", ids, key="run_agent", format_func=lambda i: agents[i].name)
    c2.selectbox(
        "Then pass the output to (optional)",
        ["(none)"] + ids,
        key="chain_agent",
        format_func=lambda i: i if i == "(none)" else agents[i].name,
    )
    agent = agents[ss.run_agent]
    st.caption(agent.description)

    upload = st.file_uploader("Upload a PDF or text file (optional)", type=["pdf", "txt"])
    st.text_area("Input", key="run_input", height=220)
    b1, b2 = st.columns([1, 5])
    b1.button("Load sample", on_click=load_sample, disabled=ss.run_agent not in SAMPLES)
    run_clicked = b2.button("▶️ Run", type="primary")

    if run_clicked:
        text = ss.get("run_input", "")
        if upload is not None:
            data = upload.getvalue()
            text = (runner.pdf_to_text(data) if upload.name.lower().endswith(".pdf") else data.decode("utf-8", "ignore")) + "\n" + text
        try:
            with st.spinner(f"{agent.name} is working…"):
                out = runner.run(agent, text)
            registry.record_use(agent.id)
            steps = [(agent.name, out)]
            if ss.chain_agent != "(none)":
                nxt = agents[ss.chain_agent]
                with st.spinner(f"{nxt.name} is working…"):
                    steps.append((nxt.name, runner.run(nxt, out)))
                registry.record_use(nxt.id)
            ss.run_output = steps
        except (LLMError, ValueError) as e:
            st.error(str(e))

    for name, out in ss.get("run_output") or []:
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.markdown(out)


def page_audit() -> None:
    st.header("Audit log")
    s = audit.stats()
    c = st.columns(4)
    c[0].metric("Gatekeeper checks", s["checks"])
    c[1].metric("Duplicates prevented", s["prevented"])
    c[2].metric("New agents created", s["created"])
    c[3].metric("Overrides", s["overrides"])
    rows = audit.history()
    if rows:
        st.dataframe(pd.DataFrame(rows).drop(columns=["id"]), hide_index=True, width="stretch")
    else:
        st.caption("No decisions yet. Try a scenario on the Create Agent page.")


{PAGES[0]: page_registry, PAGES[1]: page_create, PAGES[2]: page_run, PAGES[3]: page_audit}[ss.page]()
