"""v1 + v3 tests: REST endpoints + diff endpoint."""

from __future__ import annotations

from edalauncher import create_app


def _payload() -> dict:
    return {
        "target": "cpu_top",
        "flow": "syn",
        "steps": [
            {"name": "syn", "tool": "synopsys-dc"},
            {"name": "report", "tool": "synopsys-dc"},
        ],
    }


def test_post_jobs_creates_and_returns_job() -> None:
    app = create_app()
    client = app.test_client()
    r = client.post("/jobs", json=_payload())
    assert r.status_code == 201
    body = r.get_json()
    assert body["status"] == "queued"
    assert body["request"]["target"] == "cpu_top"


def test_post_jobs_rejects_invalid_payload() -> None:
    app = create_app()
    client = app.test_client()
    r = client.post("/jobs", json={"target": "with spaces", "flow": "syn", "steps": []})
    assert r.status_code == 400


def test_index_serves_dashboard_html() -> None:
    app = create_app()
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    assert b"edalauncher" in r.data


def test_run_endpoint_completes_job() -> None:
    app = create_app()
    client = app.test_client()
    r = client.post("/jobs", json=_payload())
    job_id = r.get_json()["id"]
    r = client.post(f"/jobs/{job_id}/run")
    assert r.status_code == 200
    assert r.get_json()["status"] == "succeeded"


def test_diff_endpoint_returns_metric_deltas() -> None:
    app = create_app()
    client = app.test_client()
    j_old = client.post("/jobs", json=_payload()).get_json()["id"]
    client.post(f"/jobs/{j_old}/run")
    j_new = client.post("/jobs", json=_payload()).get_json()["id"]
    client.post(f"/jobs/{j_new}/run")
    r = client.get(f"/jobs/{j_new}/diff/{j_old}")
    assert r.status_code == 200
    body = r.get_json()
    # Same simulator → metrics identical → all deltas zero.
    assert all(d["delta"] == 0 for d in body["deltas"])
    assert any(d["name"] == "wns" for d in body["deltas"])


def test_stream_endpoint_returns_sse() -> None:
    app = create_app()
    client = app.test_client()
    job_id = client.post("/jobs", json=_payload()).get_json()["id"]
    r = client.get(f"/jobs/{job_id}/stream")
    assert r.status_code == 200
    body = b"".join(r.response).decode()
    assert "event: start\n" in body
    assert "event: done\n" in body
