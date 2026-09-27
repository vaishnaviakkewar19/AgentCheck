"""Agent Registry: one JSON manifest per agent under data/agents/."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import List, Optional

from agentcheck import config
from agentcheck.models import AgentManifest, AgentRequest


class Registry:
    def __init__(self, agents_dir: Path = config.AGENTS_DIR, seed_dir: Path = config.SEED_DIR):
        self.agents_dir = agents_dir
        self.seed_dir = seed_dir
        if not self.agents_dir.exists() or not any(self.agents_dir.glob("*.json")):
            self.reset()

    # ---------- read ----------

    def list(self) -> List[AgentManifest]:
        agents = [self._load(p) for p in sorted(self.agents_dir.glob("*.json"))]
        return sorted(agents, key=lambda a: a.created_date)

    def get(self, agent_id: str) -> Optional[AgentManifest]:
        path = self._path(agent_id)
        return self._load(path) if path.exists() else None

    # ---------- write ----------

    def save(self, agent: AgentManifest) -> None:
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self._path(agent.id).write_text(agent.model_dump_json(indent=2), encoding="utf-8")

    def register(
        self, request: AgentRequest, capabilities: List[str], related_to: Optional[List[str]] = None
    ) -> AgentManifest:
        agent = AgentManifest(
            id=self._unique_id(request.name),
            name=request.name,
            description=request.description,
            capabilities=capabilities,
            input_types=request.input_types,
            output_types=request.output_types,
            domain=request.domain,
            owner=request.owner,
            related_to=related_to or [],
            system_prompt=build_system_prompt(request.name, request.description, capabilities, request.output_types),
        )
        self.save(agent)
        return agent

    def extend(self, agent_id: str, new_capabilities: List[str]) -> AgentManifest:
        agent = self.get(agent_id)
        if agent is None:
            raise KeyError(agent_id)
        added = [c for c in new_capabilities if c not in agent.capabilities]
        agent.capabilities.extend(added)
        agent.version += 1
        agent.system_prompt += "\n\nAdditional responsibilities (added in v{}):\n{}".format(
            agent.version, "\n".join(f"- {c}" for c in added)
        )
        self.save(agent)
        return agent

    def record_use(self, agent_id: str) -> None:
        agent = self.get(agent_id)
        if agent:
            agent.usage_count += 1
            self.save(agent)

    def reset(self) -> None:
        """Restore the registry to the seed agents.

        Replaces the files rather than deleting the folder: on Windows, antivirus or
        OneDrive often holds the folder open briefly, which makes rmtree fail.
        """
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        for path in self.agents_dir.glob("*.json"):
            path.unlink()
        for seed in self.seed_dir.glob("*.json"):
            shutil.copy2(seed, self.agents_dir / seed.name)

    # ---------- helpers ----------

    def _path(self, agent_id: str) -> Path:
        return self.agents_dir / f"{agent_id}.json"

    @staticmethod
    def _load(path: Path) -> AgentManifest:
        return AgentManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _unique_id(self, name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "agent"
        candidate, n = base, 2
        while self._path(candidate).exists():
            candidate, n = f"{base}_{n}", n + 1
        return candidate


def build_system_prompt(name: str, description: str, capabilities: List[str], output_types: List[str]) -> str:
    caps = "\n".join(f"- {c}" for c in capabilities)
    outputs = ", ".join(output_types) or "a clear, well-structured response"
    return (
        f"You are {name}. {description}\n\n"
        f"Your responsibilities:\n{caps}\n\n"
        f"Produce: {outputs}. Work only from the input provided; if something needed is missing, say so."
    )
