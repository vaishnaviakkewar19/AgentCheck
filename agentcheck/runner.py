"""Runs a worker agent: its system prompt + the user's input, one Claude call."""

from __future__ import annotations

import io

from agentcheck import llm
from agentcheck.models import AgentManifest


def pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def run(agent: AgentManifest, user_input: str) -> str:
    if not user_input.strip():
        raise ValueError("Please provide some input for the agent.")
    return llm.text(agent.system_prompt, user_input)
