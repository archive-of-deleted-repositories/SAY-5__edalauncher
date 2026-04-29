"""Domain models. Pydantic for validation; the REST layer parses
JSON straight into these.

We model an EDA run as a Job with a sequence of Steps. Each Step
represents an invocation of an EDA tool (e.g. `synthesis`, `place`,
`route`, `drc`). Metrics are produced as Steps complete and are the
primary thing reviewers compare across runs.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class Step(BaseModel):
    model_config = {"extra": "forbid"}
    name: str
    tool: str  # e.g. 'synopsys-dc', 'cadence-innovus'
    args: list[str] = Field(default_factory=list)
    status: JobStatus = JobStatus.QUEUED
    log_lines: list[str] = Field(default_factory=list)


class Metric(BaseModel):
    model_config = {"extra": "forbid"}
    name: str  # 'wns', 'tns', 'area_um2', 'power_mw', etc.
    value: float
    unit: str = ""


class JobRequest(BaseModel):
    """Inbound shape for POST /jobs."""

    model_config = {"extra": "forbid"}
    target: str  # design or block name
    flow: str  # 'syn', 'pnr', 'sta', etc.
    steps: list[Step] = Field(min_length=1)

    @field_validator("target")
    @classmethod
    def _no_spaces(cls, v: str) -> str:
        if not v or " " in v:
            raise ValueError("target must be non-empty and space-free")
        return v


class Job(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    request: JobRequest
    status: JobStatus = JobStatus.QUEUED
    steps: list[Step] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    started_at: float = 0.0
    finished_at: float = 0.0
