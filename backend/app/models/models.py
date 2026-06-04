from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, Enum
from sqlalchemy.sql import func
from ..core.database import Base
import enum

class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"

class TaskStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"

class ProductStatus(str, enum.Enum):
    READY = "ready"
    ARCHIVED = "archived"
    ERROR = "error"

class ForecastRunStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text)
    template_type = Column(String)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.PENDING)
    region = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, index=True)
    node_name = Column(String)
    node_type = Column(String)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.PENDING)
    progress = Column(Float, default=0.0)
    cpu_cores = Column(Integer)
    memory_gb = Column(Integer)
    slurm_queue = Column(String)
    walltime = Column(String)
    slurm_job_id = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    name = Column(String)
    status = Column(Enum(TaskStatus), default=TaskStatus.ACTIVE)
    cron_expression = Column(String)
    region = Column(String)
    template = Column(String)
    workflow_id = Column(Integer, nullable=True)
    last_run = Column(DateTime(timezone=True), nullable=True)
    last_result = Column(String, nullable=True)
    last_duration = Column(Float, nullable=True)
    success_rate = Column(Float, default=100.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ForecastProduct(Base):
    __tablename__ = "forecast_products"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, unique=True, index=True)
    product_type = Column(String)
    status = Column(Enum(ProductStatus), default=ProductStatus.READY)
    region = Column(String)
    pollen_type = Column(String)
    resolution = Column(String)
    workflow_node = Column(String)
    workflow_version = Column(String)
    file_path = Column(String)
    thumbnail_path = Column(String, nullable=True)
    is_published = Column(Boolean, default=False)
    release_time = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String)
    message = Column(Text)
    source = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True)
    start_time = Column(String, index=True)
    end_time = Column(String, index=True)
    period = Column(String, index=True)
    domain = Column(String, default="neimeng")
    variant = Column(String, default="official")
    met_provider = Column(String, default="FNL")
    status = Column(Enum(ForecastRunStatus), default=ForecastRunStatus.PENDING)
    progress = Column(Float, default=0.0)
    server_run_dir = Column(String, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ForecastRunNode(Base):
    __tablename__ = "forecast_run_nodes"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, index=True)
    node_name = Column(String, index=True)
    status = Column(String, default="pending")
    progress = Column(Float, default=0.0)
    attempt = Column(Integer, default=0)
    slurm_job_id = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class FnlFileRecord(Base):
    __tablename__ = "fnl_file_records"

    id = Column(Integer, primary_key=True, index=True)
    valid_time = Column(String, index=True)
    file_name = Column(String, index=True)
    status = Column(String, index=True)
    source = Column(String, nullable=True)
    server_path = Column(String, nullable=True)
    local_path = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    valid_grib = Column(Boolean, default=False)
    uploaded = Column(Boolean, default=False)
    repair_attempt = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    checked_at = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AgentAction(Base):
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, index=True, nullable=True)
    action_type = Column(String, index=True)
    reason = Column(Text, nullable=True)
    status = Column(String, index=True)
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
