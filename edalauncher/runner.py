"""Job runner — drives the steps of a Job to completion and produces
metrics. The real runner shells out to Cadence / Synopsys binaries;
this in-process version executes a per-step `simulator` callable so
tests can plug in any behavior.

A simulator is `Callable[[Step], tuple[list[str], list[Metric]]]` —
returns log lines + metrics for that step.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from edalauncher.schema import Job, JobRequest, JobStatus, Metric, Step
from edalauncher.store import Store

Simulator = Callable[[Step], tuple[list[str], list[Metric]]]


def _stub_simulator(step: Step) -> tuple[list[str], list[Metric]]:
    """Default simulator: produce a few canned log lines per step
    and a synthetic metric that varies by tool name. Used by tests
    and the smoke server.
    """

    log = [f"[{step.tool}] {line}" for line in (
        f"start {step.name}",
        f"args: {' '.join(step.args)}",
        f"finished {step.name}",
    )]
    metrics: list[Metric] = []
    if step.tool == "synopsys-dc":
        metrics.append(Metric(name="wns", value=-0.012, unit="ns"))
        metrics.append(Metric(name="area_um2", value=12_500.0, unit="um^2"))
    elif step.tool == "cadence-innovus":
        metrics.append(Metric(name="tns", value=-1.4, unit="ns"))
    return log, metrics


@dataclass
class Runner:
    store: Store
    simulator: Simulator = _stub_simulator

    def submit(self, req: JobRequest) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, request=req, steps=list(req.steps))
        self.store.put(job)
        return job

    def run(self, job_id: str) -> Job | None:
        """Synchronous run: process every step in order, capture logs
        + metrics, persist."""
        job = self.store.get(job_id)
        if job is None or job.status != JobStatus.QUEUED:
            return job
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        self.store.put(job)
        for step in job.steps:
            step.status = JobStatus.RUNNING
            log, metrics = self.simulator(step)
            step.log_lines.extend(log)
            job.metrics.extend(metrics)
            step.status = JobStatus.SUCCEEDED
            self.store.put(job)
        job.status = JobStatus.SUCCEEDED
        job.finished_at = time.time()
        self.store.put(job)
        return job

    # v2: streaming run — yields one SSE frame per step + a final
    # 'done' frame.
    def stream(self, job_id: str) -> Iterator[str]:

        job = self.store.get(job_id)
        if job is None:
            yield self._frame("error", {"reason": "not found"})
            return
        if job.status != JobStatus.QUEUED:
            yield self._frame("error", {"reason": f"job is {job.status}"})
            return

        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        self.store.put(job)
        yield self._frame("start", {"job_id": job.id, "n_steps": len(job.steps)})

        for step in job.steps:
            step.status = JobStatus.RUNNING
            log, metrics = self.simulator(step)
            step.log_lines.extend(log)
            job.metrics.extend(metrics)
            step.status = JobStatus.SUCCEEDED
            self.store.put(job)
            yield self._frame(
                "step",
                {
                    "name": step.name,
                    "tool": step.tool,
                    "log": log,
                    "metrics": [m.model_dump() for m in metrics],
                },
            )

        job.status = JobStatus.SUCCEEDED
        job.finished_at = time.time()
        self.store.put(job)
        yield self._frame(
            "done",
            {"job_id": job.id, "metrics": [m.model_dump() for m in job.metrics]},
        )

    @staticmethod
    def _frame(event: str, data: dict) -> str:
        import json

        return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"
