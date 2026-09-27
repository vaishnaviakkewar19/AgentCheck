"""Data models shared across AgentCheck."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AgentManifest(BaseModel):
    """Everything the registry knows about one agent."""

    id: str
    name: str
    description: str
    capabilities: List[str] = Field(default_factory=list)
    input_types: List[str] = Field(default_factory=list)
    output_types: List[str] = Field(default_factory=list)
    domain: str = "general"
    tools_used: List[str] = Field(default_factory=list)
    owner: str = "demo-team"
    created_date: str = Field(default_factory=lambda: date.today().isoformat())
    version: int = 1
    usage_count: int = 0
    related_to: List[str] = Field(default_factory=list)
    system_prompt: str

    def profile_text(self) -> str:
        """Text used for similarity search."""
        return " ".join(
            [
                self.name,
                self.description,
                " ".join(self.capabilities),
                " ".join(self.input_types),
                " ".join(self.output_types),
                self.domain,
            ]
        )


class AgentRequest(BaseModel):
    """What a user fills in when proposing a new agent."""

    name: str
    description: str
    input_types: List[str] = Field(default_factory=list)
    output_types: List[str] = Field(default_factory=list)
    domain: str = "general"
    owner: str = "demo-user"


# ---------- LLM structured outputs ----------


class Decomposition(BaseModel):
    """Layer 1: the new agent broken into atomic sub-tasks."""

    subtasks: List[str]
    search_keywords: List[str] = Field(default_factory=list)


SubtaskStatus = Literal["covered", "partial", "not_covered"]


class SubtaskJudgement(BaseModel):
    subtask: str
    status: SubtaskStatus
    reason: str


class CandidateJudgement(BaseModel):
    agent_id: str
    domain_compatible: bool
    io_compatible: bool
    subtasks: List[SubtaskJudgement]
    summary: str


class JudgeResult(BaseModel):
    """Layer 3: per-candidate, per-sub-task coverage verdicts."""

    candidates: List[CandidateJudgement]


# ---------- Gatekeeper output ----------


class Verdict(str, Enum):
    DUPLICATE = "duplicate"
    HIGH_OVERLAP = "high_overlap"
    PARTIAL = "partial"
    UNIQUE = "unique"


class CandidateScore(BaseModel):
    agent_id: str
    agent_name: str
    similarity: float  # Layer 2 retrieval score, 0..1
    coverage: float  # Layer 3 coverage %, 0..100
    judgement: CandidateJudgement

    @property
    def missing(self) -> List[str]:
        return [s.subtask for s in self.judgement.subtasks if s.status != "covered"]


class ComboScore(BaseModel):
    agent_ids: List[str]
    agent_names: List[str]
    coverage: float


class CheckResult(BaseModel):
    request: AgentRequest
    subtasks: List[str]
    candidates: List[CandidateScore]
    best: Optional[CandidateScore] = None
    combo: Optional[ComboScore] = None
    verdict: Verdict
    message: str
