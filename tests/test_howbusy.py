import math

import howbusy

# Mirrors real vLLM /metrics output: every line carries a label block,
# even for metrics that aren't per-reason.
SAMPLE = """\
vllm:num_requests_running{engine="0",model_name="qwen3.8-flash-next-uncensored"} 3.0
vllm:kv_cache_usage_perc{engine="0",model_name="qwen3.8-flash-next-uncensored"} 5.3838943131268024e-01
vllm:num_requests_waiting_by_reason{engine="0",model_name="qwen3.8-flash-next-uncensored",reason="capacity"} 4.0
vllm:num_requests_waiting_by_reason{engine="0",model_name="qwen3.8-flash-next-uncensored",reason="deferred"} 1.0
vllm:foo{engine="0"} 1.5e+02
vllm:num_requests_running{engine="0",model_name="qwen3.8-flash-next-uncensored"} 5.0
"""


def test_metric_returns_last_value():
    assert howbusy.metric(SAMPLE, "num_requests_running") == 5.0


def test_metric_plain_float():
    assert howbusy.metric("vllm:bar{engine=\"0\"} 1.0\n", "bar") == 1.0


def test_metric_sci_negative_exponent_regression():
    # Prometheus prints small metrics in sci-notation (e.g. 5.38e-01). The
    # parser must NOT truncate at the '-' (this was the original crash bug).
    val = howbusy.metric(SAMPLE, "kv_cache_usage_perc")
    assert val is not None
    assert math.isclose(val, 0.5383894313126802, rel_tol=1e-9)


def test_metric_sci_positive_exponent():
    assert howbusy.metric(SAMPLE, "foo") == 150.0


def test_metric_filter_by_label():
    assert (
        howbusy.metric(
            SAMPLE, "num_requests_waiting_by_reason", label="reason", lval="capacity"
        )
        == 4.0
    )
    assert (
        howbusy.metric(
            SAMPLE, "num_requests_waiting_by_reason", label="reason", lval="deferred"
        )
        == 1.0
    )


def test_metric_filter_mismatch_returns_none():
    assert (
        howbusy.metric(
            SAMPLE, "num_requests_waiting_by_reason", label="reason", lval="other"
        )
        is None
    )


def test_metric_no_match_returns_none():
    assert howbusy.metric(SAMPLE, "nonexistent") is None


def test_last_line():
    assert howbusy.last_line("a\nbb\nccc\n", "bb") == "bb"
    assert howbusy.last_line("a\n", "zz") == ""
