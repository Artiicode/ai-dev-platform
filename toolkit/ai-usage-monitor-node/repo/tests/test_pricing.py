import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_usage_monitor.pricing import estimate_cost, get_price  # noqa: E402


def test_model_matching_longest_wins():
    # "sonnet" should match, not the default.
    p = get_price("claude-sonnet-4-6")
    assert p.output == 15.0
    p2 = get_price("claude-4.6-opus-high-thinking")
    assert p2.output == 75.0


def test_unknown_model_uses_default():
    p = get_price("some-random-model")
    assert p.output == 15.0  # default sonnet-like


def test_estimate_cost_math():
    # 1M output tokens of sonnet = $15
    cost = estimate_cost("claude-sonnet-4-6", output_tokens=1_000_000)
    assert abs(cost - 15.0) < 1e-6
    # cache reads are cheap
    cost2 = estimate_cost("claude-sonnet-4-6", cache_read_tokens=1_000_000)
    assert abs(cost2 - 0.30) < 1e-6


def test_estimate_zero():
    assert estimate_cost("anything") == 0.0
