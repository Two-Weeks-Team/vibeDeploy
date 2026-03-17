"""Provider-level pricing specs for the 7 canonical doc-17 models."""

from __future__ import annotations

from typing import TypedDict


class PricingSpec(TypedDict):
    input_per_million: float
    output_per_million: float
    cached_input_per_million: float
    long_context_input_multiplier: float
    long_context_threshold_tokens: int


PRICING: dict[str, PricingSpec] = {
    "gpt-5.4": {
        "input_per_million": 2.50,
        "output_per_million": 15.00,
        "cached_input_per_million": 1.25,
        "long_context_input_multiplier": 1.0,
        "long_context_threshold_tokens": 128000,
    },
    "gpt-5.3-codex": {
        "input_per_million": 1.75,
        "output_per_million": 14.00,
        "cached_input_per_million": 0.875,
        "long_context_input_multiplier": 1.0,
        "long_context_threshold_tokens": 128000,
    },
    "gpt-5.2": {
        "input_per_million": 1.75,
        "output_per_million": 14.00,
        "cached_input_per_million": 0.875,
        "long_context_input_multiplier": 1.0,
        "long_context_threshold_tokens": 128000,
    },
    "claude-sonnet-4-6": {
        "input_per_million": 3.00,
        "output_per_million": 15.00,
        "cached_input_per_million": 0.30,
        "long_context_input_multiplier": 1.0,
        "long_context_threshold_tokens": 200000,
    },
    "claude-opus-4-6": {
        "input_per_million": 5.00,
        "output_per_million": 25.00,
        "cached_input_per_million": 0.50,
        "long_context_input_multiplier": 1.0,
        "long_context_threshold_tokens": 200000,
    },
    "gemini-3.1-pro-preview": {
        "input_per_million": 2.00,
        "output_per_million": 12.00,
        "cached_input_per_million": 0.50,
        "long_context_input_multiplier": 2.0,
        "long_context_threshold_tokens": 128000,
    },
    "gemini-3.1-flash-lite-preview": {
        "input_per_million": 0.25,
        "output_per_million": 1.50,
        "cached_input_per_million": 0.025,
        "long_context_input_multiplier": 1.0,
        "long_context_threshold_tokens": 1000000,
    },
}


def calculate_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Calculate USD cost with surcharge awareness for long-context and cached tokens.

    Args:
        model_id: Canonical model ID (must exist in PRICING).
        input_tokens: Non-cached input token count.
        output_tokens: Output token count.
        cached_input_tokens: Tokens served from cache (billed at cached_input_per_million).

    Returns:
        Estimated cost in USD, rounded to 6 decimal places.
    """
    spec = PRICING.get(model_id)
    if spec is None:
        return 0.0

    total_input = input_tokens + cached_input_tokens
    multiplier = spec["long_context_input_multiplier"] if total_input > spec["long_context_threshold_tokens"] else 1.0

    input_cost = (input_tokens * spec["input_per_million"] * multiplier) / 1_000_000
    cached_cost = (cached_input_tokens * spec["cached_input_per_million"]) / 1_000_000
    output_cost = (output_tokens * spec["output_per_million"]) / 1_000_000

    return round(input_cost + cached_cost + output_cost, 6)
