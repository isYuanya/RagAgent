from typing import Literal

from pydantic import BaseModel, Field


ServiceHealthStatus = Literal["ok", "degraded", "down"]


class DependencyStatus(BaseModel):
    name: str = Field(description="Dependency display name.")
    required: bool = Field(description="Whether this dependency blocks core workflows.")
    status: ServiceHealthStatus = Field(description="Current dependency status.")
    latency_ms: int | None = Field(default=None, ge=0, description="Check latency in milliseconds.")
    endpoint: str | None = Field(default=None, description="Safe endpoint summary without secrets.")
    message: str = Field(description="Human-readable status message.")


class SystemStatusResponse(BaseModel):
    status: ServiceHealthStatus = Field(description="Overall system status.")
    services: list[DependencyStatus] = Field(description="Dependency status list.")
