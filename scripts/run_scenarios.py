"""Run all 8 demo scenarios against the real API and compare with the expected verdicts.

Uses a temporary registry, so your demo data is not touched.
Usage:  python scripts/run_scenarios.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentcheck import config, gatekeeper  # noqa: E402
from agentcheck.models import Verdict  # noqa: E402
from agentcheck.registry import Registry  # noqa: E402
from agentcheck.scenarios import SCENARIOS  # noqa: E402


def main() -> None:
    registry = Registry(agents_dir=Path(tempfile.mkdtemp()) / "agents", seed_dir=config.SEED_DIR)
    passed = 0
    for sc in SCENARIOS:
        result = gatekeeper.check(sc["request"], registry)
        ok = result.verdict == sc["expected"]
        passed += ok
        best = f"{result.best.agent_name} {result.best.coverage:.0f}%" if result.best else "-"
        combo = f" | combo {result.combo.coverage:.0f}%" if result.combo else ""
        print(f"{'PASS' if ok else 'FAIL'}  {sc['title']:<36} {result.verdict.value:<13} best: {best}{combo}")
        for c in result.candidates[:2]:
            marks = " ".join({"covered": "Y", "partial": "~", "not_covered": "-"}[s.status] for s in c.judgement.subtasks)
            print(f"        {c.agent_name:<28} {c.coverage:5.1f}%  [{marks}]")
        # Scenario 6 registers its agent so scenario 8 can find it.
        if result.verdict == Verdict.UNIQUE:
            registry.register(sc["request"], result.subtasks)
    print(f"\n{passed}/{len(SCENARIOS)} scenarios matched the expected verdict.")


if __name__ == "__main__":
    main()
