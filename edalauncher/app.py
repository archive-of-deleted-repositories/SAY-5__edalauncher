"""Flask app factory. Endpoints:

POST   /jobs                — submit a JobRequest, returns Job
GET    /jobs                — list all jobs
GET    /jobs/<id>           — fetch a job
POST   /jobs/<id>/run       — run synchronously
GET    /jobs/<id>/stream    — SSE stream of run progress (v2)
GET    /jobs/<id>/diff/<other_id> — metric diff between two runs (v3)
GET    /                    — distinctive vanilla-JS dashboard
"""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, jsonify, request
from pydantic import ValidationError

from edalauncher.diff import diff_runs
from edalauncher.runner import Runner
from edalauncher.schema import JobRequest
from edalauncher.store import InMemoryStore, Store

INDEX_HTML = """\
<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>edalauncher</title>
<style>
  :root {
    --bg:#0f1115; --panel:#181b22; --line:#2a2e36;
    --ink:#dde2ea; --muted:#7d848f;
    --good:#8be78b; --warn:#f0c674; --bad:#f29ea0;
  }
  body { margin:0; font:14px/1.5 'IBM Plex Mono', monospace;
    background:var(--bg); color:var(--ink); }
  header { padding:1.4rem 2rem; border-bottom:1px solid var(--line);
    letter-spacing:0.02em; }
  h1 { margin:0; font-size:1.05rem; font-weight:500; }
  h1 b { color:var(--warn); }
  main { display:grid; grid-template-columns: 320px 1fr; min-height:calc(100vh - 60px); }
  aside { border-right:1px solid var(--line); padding:1rem; overflow-y:auto; }
  section { padding:1rem 2rem; }
  .job { padding:0.6rem; border:1px solid var(--line); margin-bottom:0.5rem;
    cursor:pointer; }
  .job:hover { border-color:var(--warn); }
  .stat { font-size:0.75rem; color:var(--muted); }
  .stat.succeeded { color:var(--good); }
  .stat.failed { color:var(--bad); }
  pre { background:var(--panel); padding:0.8rem; border:1px solid var(--line);
    overflow-x:auto; font-size:0.8rem; }
</style></head><body>
<header><h1>edalauncher <b>·</b> EDA tool launcher</h1></header>
<main>
  <aside><h2 style="font-size:0.85rem;margin:0 0 .5rem;color:var(--muted)">RUNS</h2>
    <div id="jobs"></div>
  </aside>
  <section><h2 style="font-size:0.95rem">selected run</h2>
    <pre id="detail">select a run to view metrics + logs</pre>
  </section>
</main>
<script>
  async function refresh() {
    const r = await fetch('/jobs');
    const jobs = await r.json();
    document.getElementById('jobs').innerHTML = jobs.map(j =>
      `<div class="job" onclick="show('${j.id}')">
         <div>${j.request.target} · ${j.request.flow}</div>
         <div class="stat ${j.status}">${j.status}</div>
       </div>`).join('');
  }
  async function show(id) {
    const r = await fetch('/jobs/' + id);
    document.getElementById('detail').textContent = JSON.stringify(await r.json(), null, 2);
  }
  refresh();
</script></body></html>
"""


def create_app(store: Store | None = None, runner: Runner | None = None) -> Flask:
    s: Store = store or InMemoryStore()
    r = runner or Runner(s)
    app = Flask(__name__)

    @app.get("/")
    def index() -> Response:
        return Response(INDEX_HTML, mimetype="text/html")

    @app.post("/jobs")
    def post_job() -> Any:
        try:
            req = JobRequest.model_validate(request.get_json(force=True))
        except ValidationError as e:
            # include_context=False strips Python exception objects
            # (ValueError etc.) that aren't JSON-serializable.
            return jsonify({"errors": e.errors(include_context=False)}), 400
        job = r.submit(req)
        return jsonify(job.model_dump()), 201

    @app.get("/jobs")
    def list_jobs() -> Any:
        return jsonify([j.model_dump() for j in s.all()])

    @app.get("/jobs/<job_id>")
    def get_job(job_id: str) -> Any:
        j = s.get(job_id)
        if j is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(j.model_dump())

    @app.post("/jobs/<job_id>/run")
    def run_job(job_id: str) -> Any:
        j = r.run(job_id)
        if j is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(j.model_dump())

    @app.get("/jobs/<job_id>/stream")
    def stream_job(job_id: str) -> Response:
        return Response(r.stream(job_id), mimetype="text/event-stream")

    @app.get("/jobs/<job_id>/diff/<other_id>")
    def diff_jobs(job_id: str, other_id: str) -> Any:
        j_old = s.get(other_id)
        j_new = s.get(job_id)
        if not (j_old and j_new):
            return jsonify({"error": "not found"}), 404
        d = diff_runs(j_old, j_new)
        return jsonify(
            {
                "new_metrics": list(d.new_metrics),
                "removed_metrics": list(d.removed_metrics),
                "deltas": [
                    {
                        "name": x.name,
                        "old": x.old,
                        "new": x.new,
                        "delta": x.delta,
                        "pct": None if x.pct != x.pct else x.pct,  # NaN -> null
                    }
                    for x in d.deltas
                ],
            }
        )

    return app
