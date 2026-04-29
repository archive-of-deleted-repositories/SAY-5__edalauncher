# edalauncher

Browser-based launcher and dashboard for EDA tool flows (Cadence,
Synopsys, etc). Flask backend with a typed Pydantic core, vanilla-JS
frontend (no build step), live SSE streaming of run logs, and
regression diffing across runs on the same target.

```
browser ──HTTP──▶ Flask  ─create/cancel─▶ Store (in-memory + SQLAlchemy seam)
              │
              └──SSE────▶ live log stream
```

## Versions

| Version | Capability | Status |
|---|---|---|
| v1 | Flask API + Pydantic Job model + in-memory store + a no-JS frontend | shipped |
| v2 | SSE streaming of run logs as steps complete | shipped |
| v3 | Regression diff between runs on the same target — metric drift surfacing | shipped |

## Quickstart

```bash
pip install -e ".[dev]"
edalauncher serve  # http://127.0.0.1:5000
pytest             # 12 tests
```
