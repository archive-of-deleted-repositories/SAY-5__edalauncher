"""v3 tests: regression diff between two runs on the same target."""

from __future__ import annotations

from edalauncher import Job, JobRequest, Metric, Step, diff_runs


def _job(metrics: list[Metric]) -> Job:
    req = JobRequest(target="cpu", flow="syn", steps=[Step(name="syn", tool="synopsys-dc")])
    return Job(id="x", request=req, metrics=metrics)


def test_diff_classifies_new_removed_and_changed() -> None:
    old = _job([Metric(name="wns", value=-0.10), Metric(name="dropped", value=1.0)])
    new = _job([Metric(name="wns", value=-0.20), Metric(name="added", value=2.0)])
    d = diff_runs(old, new)
    assert d.new_metrics == ("added",)
    assert d.removed_metrics == ("dropped",)
    assert len(d.deltas) == 1
    delta = d.deltas[0]
    assert delta.name == "wns"
    assert delta.delta == -0.10
    assert abs(delta.pct - 100.0) < 0.01


def test_diff_handles_zero_old_value() -> None:
    old = _job([Metric(name="m", value=0.0)])
    new = _job([Metric(name="m", value=5.0)])
    d = diff_runs(old, new)
    # NaN pct on zero-old; we just verify the delta exists.
    assert d.deltas[0].name == "m"
    assert d.deltas[0].delta == 5.0
    assert d.deltas[0].pct != d.deltas[0].pct  # NaN
