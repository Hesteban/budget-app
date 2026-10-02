"""
Shared LLM configuration for all agents: OpenCode Zen backend + cost logging.

Importing this module points the OpenAI Agents SDK at Zen's Responses API
(https://opencode.ai/zen/v1) instead of api.openai.com. Zen bills pure
pay-as-you-go (auto-reload $20 when balance < $5) — no expiring prepaid credits.

Set OPENAI_BASE_URL / OPENAI_API_KEY in the environment to override.
"""
from __future__ import annotations

import os

from agents import set_tracing_disabled

os.environ.setdefault("OPENAI_BASE_URL", "https://opencode.ai/zen/v1")
set_tracing_disabled(True)  # traces would go to OpenAI's platform, which we no longer use

MODEL = "gpt-5.4-nano"

# Zen prices for gpt-5.4-nano, $ per 1M tokens — https://opencode.ai/docs/zen
# ponytail: cached-token discount ($0.02/1M) ignored, cost is an estimate
PRICE_INPUT = 0.20
PRICE_OUTPUT = 1.25


def log_cost(result, label: str) -> None:
    """Print token usage and estimated $ cost for a finished Runner result."""
    u = result.context_wrapper.usage
    cost = (u.input_tokens * PRICE_INPUT + u.output_tokens * PRICE_OUTPUT) / 1_000_000
    print(f"[llm-cost] {label}: {u.input_tokens} in / {u.output_tokens} out -> ${cost:.5f}")
