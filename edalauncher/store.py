"""Job store. In-memory implementation for tests and local runs;
SQLAlchemy adapter is the production seam (omitted here to keep the
test surface hermetic — the contract is the `Store` Protocol).
"""

from __future__ import annotations

from threading import Lock
from typing import Protocol

from edalauncher.schema import Job


class Store(Protocol):
    def put(self, job: Job) -> None: ...
    def get(self, job_id: str) -> Job | None: ...
    def list_for_target(self, target: str) -> list[Job]: ...
    def all(self) -> list[Job]: ...


class InMemoryStore:
    """Thread-safe dict-backed store. Returns deep copies via
    Pydantic's `.model_copy(deep=True)` so callers can't mutate
    stored state through their references.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, Job] = {}

    def put(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job.model_copy(deep=True)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            j = self._jobs.get(job_id)
            return j.model_copy(deep=True) if j else None

    def list_for_target(self, target: str) -> list[Job]:
        with self._lock:
            return [
                j.model_copy(deep=True)
                for j in self._jobs.values()
                if j.request.target == target
            ]

    def all(self) -> list[Job]:
        with self._lock:
            return [j.model_copy(deep=True) for j in self._jobs.values()]
