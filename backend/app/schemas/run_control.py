from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RunPlanRequest(BaseModel):
    start: str = Field(..., description="YYYYMMDDHH or YYYYMMDD")
    end: str = Field(..., description="YYYYMMDDHH or YYYYMMDD")
    period: Literal["spring", "summer", "autumn"]
    run_id: Optional[str] = None
    domain: str = "neimeng"
    variant: str = "official"
    met_provider: str = "FNL"
    commands_file: Optional[str] = None


class RunSubmitRequest(BaseModel):
    dry_run: bool = False
    allow_noop: bool = False


class RetryRequest(BaseModel):
    node: str
    dry_run: bool = False


class CancelRunRequest(BaseModel):
    dry_run: bool = True


class FnlVerifyRequest(BaseModel):
    run_id: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None


class FnlRepairRequest(FnlVerifyRequest):
    pass


class AgentTickRequest(BaseModel):
    run_id: Optional[str] = None
    start: str
    end: str
    period: Literal["spring", "summer", "autumn"]
    domain: str = "neimeng"
    variant: str = "official"
    met_provider: str = "FNL"
    commands_file: Optional[str] = None
    repair_fnl: bool = True
    dry_run_submit: bool = True
    allow_noop: bool = False


class FlowResponse(BaseModel):
    ok: bool = True
    data: dict[str, Any]


class LogsResponse(BaseModel):
    run_id: str
    node: Optional[str] = None
    logs: str
