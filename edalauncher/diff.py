"""v3: regression diff between EDA runs on the same target.

Surface metric drift so reviewers can spot timing regressions, area
bloat, etc. The diff returns absolute + relative deltas per metric;
we don't decide what's a regression — that's the project's QoR
policy. We just expose the change-set.
"""

from __future__ import annotations

from dataclasses import dataclass

from edalauncher.schema import Job, Metric


@dataclass(frozen=True, slots=True)
class MetricDelta:
    name: str
    old: float
    new: float
    delta: float
    pct: float  # relative change ((new - old) / old) * 100; nan if old==0


@dataclass(frozen=True, slots=True)
class RunDiff:
    new_metrics: tuple[str, ...]
    removed_metrics: tuple[str, ...]
    deltas: tuple[MetricDelta, ...]


def diff_runs(old: Job, new: Job) -> RunDiff:
    old_idx = {m.name: m for m in old.metrics}
    new_idx = {m.name: m for m in new.metrics}

    deltas: list[MetricDelta] = []
    for name, m_new in new_idx.items():
        m_old = old_idx.get(name)
        if m_old is None:
            continue
        deltas.append(_make_delta(m_old, m_new))

    return RunDiff(
        new_metrics=tuple(sorted(set(new_idx) - set(old_idx))),
        removed_metrics=tuple(sorted(set(old_idx) - set(new_idx))),
        deltas=tuple(sorted(deltas, key=lambda d: d.name)),
    )


def _make_delta(old: Metric, new: Metric) -> MetricDelta:
    delta = new.value - old.value
    pct = (delta / old.value) * 100.0 if old.value != 0 else float("nan")
    return MetricDelta(name=new.name, old=old.value, new=new.value, delta=delta, pct=pct)
