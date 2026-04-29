"""v1 + v2 tests: synchronous Runner + SSE streaming."""

from __future__ import annotations

import json

from edalauncher import (
    InMemoryStore,
    JobRequest,
    JobStatus,
    Runner,
    Step,
)


def _request() -> JobRequest:
    return JobRequest(
        target="cpu_top",
        flow="syn",
        steps=[
            Step(name="syn", tool="synopsys-dc"),
            Step(name="report", tool="synopsys-dc", args=["-format", "json"]),
        ],
    )


def test_submit_and_run_succeeds() -> None:
    store = InMemoryStore()
    r = Runner(store)
    job = r.submit(_request())
    assert job.status == JobStatus.QUEUED
    final = r.run(job.id)
    assert final is not None
    assert final.status == JobStatus.SUCCEEDED
    assert all(s.status == JobStatus.SUCCEEDED for s in final.steps)
    assert any(m.name == "wns" for m in final.metrics)
    assert any(m.name == "area_um2" for m in final.metrics)


def test_run_unknown_id_returns_none() -> None:
    r = Runner(InMemoryStore())
    assert r.run("does-not-exist") is None


def test_stream_emits_start_step_done() -> None:
    r = Runner(InMemoryStore())
    job = r.submit(_request())
    frames = list(r.stream(job.id))
    assert frames[0].startswith("event: start\n")
    assert frames[-1].startswith("event: done\n")
    step_frames = [f for f in frames if f.startswith("event: step\n")]
    assert len(step_frames) == 2


def test_stream_done_carries_metrics() -> None:
    r = Runner(InMemoryStore())
    job = r.submit(_request())
    frames = list(r.stream(job.id))
    done_data = json.loads(frames[-1].split("data: ", 1)[1].strip())
    assert any(m["name"] == "wns" for m in done_data["metrics"])


def test_run_after_stream_is_a_noop_or_idempotent() -> None:
    # Streaming completes the job; running it again should be safe.
    r = Runner(InMemoryStore())
    job = r.submit(_request())
    list(r.stream(job.id))
    again = r.run(job.id)
    # `run` returns the existing succeeded job rather than re-running.
    assert again is not None
    assert again.status == JobStatus.SUCCEEDED
