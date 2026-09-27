"""Thin wrapper around the Anthropic SDK used by the gatekeeper and worker agents."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional, Type, TypeVar

import anthropic
from pydantic import BaseModel

from agentcheck import config

T = TypeVar("T", bound=BaseModel)

# Models that support server-side refusal fallbacks: if Claude declines a request,
# the API transparently re-runs it on a fallback model in the same call.
_FALLBACK_MODELS = ("claude-opus-5", "claude-fable-5-1")
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _call(system: str, user: str, output_format: Optional[Type[BaseModel]] = None) -> Any:
    kwargs: dict = dict(
        model=config.CLAUDE_MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": config.CLAUDE_EFFORT},
    )
    if config.CLAUDE_MODEL in _FALLBACK_MODELS:
        kwargs.update(betas=[_FALLBACK_BETA], fallbacks="default")
    messages = client().beta.messages
    try:
        if output_format is not None:
            response = messages.parse(output_format=output_format, **kwargs)
        else:
            response = messages.create(**kwargs)
    except anthropic.AuthenticationError as e:
        raise LLMError("Invalid or missing ANTHROPIC_API_KEY. Check your .env file.") from e
    except anthropic.RateLimitError as e:
        raise LLMError("Rate limited by the Anthropic API. Wait a moment and try again.") from e
    except anthropic.APIConnectionError as e:
        raise LLMError("Could not reach the Anthropic API (network or proxy issue?).") from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"Anthropic API error {e.status_code}: {e.message}") from e

    if response.stop_reason == "refusal":
        raise LLMError("Claude declined this request (stop_reason=refusal).")
    if response.stop_reason == "max_tokens":
        raise LLMError("Response was cut off (max_tokens). Try a shorter input.")
    return response


def structured(system: str, user: str, output_format: Type[T]) -> T:
    """Call Claude and return a validated Pydantic object."""
    response = _call(system, user, output_format)
    if response.parsed_output is None:
        raise LLMError("Claude returned no parsable output.")
    return response.parsed_output


def text(system: str, user: str) -> str:
    """Call Claude and return plain text."""
    response = _call(system, user)
    return "".join(b.text for b in response.content if b.type == "text")
