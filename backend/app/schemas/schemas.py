from pydantic import BaseModel
from datetime import datetime
from typing import Any, Literal, Optional, List
from ..models.models import WorkflowStatus, TaskStatus, ProductStatus

class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    template_type: str
    region: str

class WorkflowCreate(WorkflowBase):
    pass

class WorkflowResponse(WorkflowBase):
    id: int
    status: WorkflowStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorkflowNodeBase(BaseModel):
    node_name: str
    node_type: str
    cpu_cores: int = 128
    memory_gb: int = 512
    slurm_queue: str = "compute-high-priority"
    walltime: str = "04:00:00"

class WorkflowNodeCreate(WorkflowNodeBase):
    workflow_id: int

class WorkflowNodeResponse(WorkflowNodeBase):
    id: int
    workflow_id: int
    status: WorkflowStatus
    progress: float
    slurm_job_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ScheduledTaskBase(BaseModel):
    name: str
    cron_expression: str
    region: str
    template: str

class ScheduledTaskCreate(ScheduledTaskBase):
    pass

class ScheduledTaskStatusUpdate(BaseModel):
    status: TaskStatus

class ScheduledTaskRunRequest(BaseModel):
    run_id: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    period: Optional[Literal["spring", "summer", "autumn"]] = None
    domain: Optional[str] = None
    variant: Optional[str] = None
    met_provider: Optional[str] = None
    commands_file: Optional[str] = None
    repair_fnl: Optional[bool] = None
    dry_run_submit: Optional[bool] = None
    allow_noop: Optional[bool] = None
    template_overrides: dict[str, Any] = {}

class ScheduledTaskResponse(ScheduledTaskBase):
    id: int
    task_id: str
    status: TaskStatus
    workflow_id: Optional[int] = None
    last_run: Optional[datetime] = None
    last_result: Optional[str] = None
    last_duration: Optional[float] = None
    success_rate: float
    created_at: datetime

    class Config:
        from_attributes = True

class ForecastProductBase(BaseModel):
    product_name: str
    product_type: str
    region: str
    pollen_type: str
    resolution: str
    workflow_node: str
    workflow_version: str
    file_path: str
    subtype: Optional[str] = None
    variable: Optional[str] = None
    unit: Optional[str] = None
    bounds: Optional[dict[str, float]] = None
    bounds_json: Optional[str] = None
    lead_time: Optional[str] = None
    source_run_id: Optional[str] = None
    capability_status: Optional[str] = None

class ForecastProductCreate(ForecastProductBase):
    pass

class ForecastProductPublishRequest(BaseModel):
    is_published: bool

class ForecastProductResponse(ForecastProductBase):
    id: int
    status: ProductStatus
    thumbnail_path: Optional[str] = None
    is_published: bool
    release_time: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class SystemLogResponse(BaseModel):
    id: int
    level: str
    message: str
    source: str
    timestamp: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    active_schedulers: int
    slurm_jobs_queued: int
    system_health: float
    total_workflows: int
    running_workflows: int
    failed_workflows: int
