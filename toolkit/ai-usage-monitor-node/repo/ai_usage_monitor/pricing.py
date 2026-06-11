"""Local model pricing table (USD per 1M tokens).

Used to estimate cost from token counts when an authoritative dollar figure is
not available (notably Claude Pro/Max local JSONL data). Prices are list API
prices and are approximate; update as providers change pricing.

Source: provider public API pricing pages (per million tokens).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    input: float  # per 1M input tokens
    output: float  # per 1M output tokens
    cache_read: float  # per 1M cache-read tokens
    cache_write: float  # per 1M cache-creation tokens


# Keys are matched by substring (lowercased) against the model id, longest
# match wins. This keeps the table resilient to date suffixes / variants such as
# "claude-sonnet-4-6", "claude-4.6-sonnet-medium-thinking", etc.
_PRICES: dict[str, ModelPrice] = {
    # --- Anthropic Claude ---
    "opus": ModelPrice(input=15.0, output=75.0, cache_read=1.5, cache_write=18.75),
    "sonnet": ModelPrice(input=3.0, output=15.0, cache_read=0.30, cache_write=3.75),
    "haiku": ModelPrice(input=0.80, output=4.0, cache_read=0.08, cache_write=1.0),
    # --- Cursor in-house models (approx, hidden/utility) ---
    "composer": ModelPrice(input=1.25, output=10.0, cache_read=0.125, cache_write=1.25),
    # --- generic fallbacks for other providers Cursor may route to ---
    "gpt-4": ModelPrice(input=2.5, output=10.0, cache_read=0.25, cache_write=3.0),
    "gemini": ModelPrice(input=1.25, output=10.0, cache_read=0.125, cache_write=1.5),
}

_DEFAULT = ModelPrice(input=3.0, output=15.0, cache_read=0.30, cache_write=3.75)


def get_price(model: str) -> ModelPrice:
    """Return the best-matching price entry for a model id."""
    if not model:
        return _DEFAULT
    m = model.lower()
    best_key = ""
    for key in _PRICES:
        if key in m and len(key) > len(best_key):
            best_key = key
    return _PRICES[best_key] if best_key else _DEFAULT


def estimate_cost(
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """Estimate USD cost from token counts using the local price table."""
    p = get_price(model)
    return (
        input_tokens * p.input
        + output_tokens * p.output
        + cache_read_tokens * p.cache_read
        + cache_creation_tokens * p.cache_write
    ) / 1_000_000.0
