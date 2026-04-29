# Architecture

## Layers

```
┌──────────────────────────────────────────────────┐
│ Browser (vanilla JS — no build step)            │
├──────────────────────────────────────────────────┤
│ Flask blueprint: /jobs, /jobs/<id>/{run,stream,diff}│
├──────────────────────────────────────────────────┤
│ Runner — orchestrates Steps with a Simulator hook│
├──────────────────────────────────────────────────┤
│ Store (Protocol) — InMemoryStore for tests,     │
│                    SQLAlchemy adapter in prod   │
└──────────────────────────────────────────────────┘
```

## Why no React build step

The dashboard is intentionally a single static HTML document with
inline CSS and a 20-line `<script>` that calls `/jobs` and renders
the list. EDA teams ship the launcher into long-lived production
environments where rebuilding a Node toolchain every six months is
its own maintenance burden.

If you'd rather ship a React app, drop the SPA bundle into
`edalauncher/static/` and replace `INDEX_HTML` with a `send_file`
call. The REST surface is unchanged.

## Why a Simulator seam

`Runner` accepts a `Simulator` callable: `Step → (logs, metrics)`.
In tests we pass `_stub_simulator`. In production it's
`shell_simulator(step) → invokes the EDA tool, captures stdout/stderr,
parses the report file`. The Runner contract doesn't change.

This keeps tests hermetic — nobody needs Synopsys or Cadence licenses
to run pytest — while preserving an exact behavior model for the real
flow.

## Streaming run (v2)

`Runner.stream(job_id)` is a generator that yields SSE frames:

- `start`: job_id + step count
- `step`: name, tool, log lines, metrics produced
- `done`: aggregated metrics across the whole run

The Flask handler returns it directly to the browser:

```python
return Response(r.stream(job_id), mimetype="text/event-stream")
```

## Regression diff (v3)

`diff_runs(old, new)` returns a `RunDiff` carrying:

- `new_metrics` / `removed_metrics` — additions and deletions
- `deltas` — per-shared-metric absolute + relative change

We don't decide what's a regression — that's a project's QoR policy.
The diff gives reviewers the change-set; gating is layered on top
(e.g., a CI step that fails when `wns` worsens by more than X ns).

## ValidationError serialization

Pydantic v2's `ValidationError.errors()` includes Python exception
objects (e.g. `ValueError` from custom validators) in the `ctx`
field. Those aren't JSON-serializable. We pass `include_context=False`
to the `errors()` call so JSON serialization works without
needing a custom encoder.
