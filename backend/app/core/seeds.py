from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models.models import ScheduledTask, TaskStatus, Workflow, WorkflowNode, WorkflowStatus


FLOW_NODE_DEFAULTS = [
    ("fnl_verify", "input", WorkflowStatus.SUCCESS, 100.0, 4, 16, "00:30:00"),
    ("wps_geogrid", "wps", WorkflowStatus.SUCCESS, 100.0, 8, 32, "01:00:00"),
    ("wps_ungrib", "wps", WorkflowStatus.SUCCESS, 100.0, 8, 32, "01:00:00"),
    ("wps_metgrid", "wps", WorkflowStatus.SUCCESS, 100.0, 8, 32, "01:00:00"),
    ("wrf_setup", "setup", WorkflowStatus.SUCCESS, 100.0, 4, 16, "00:30:00"),
    ("real", "wrf", WorkflowStatus.SUCCESS, 100.0, 16, 64, "02:00:00"),
    ("compute_gdd", "pollen", WorkflowStatus.SUCCESS, 100.0, 8, 32, "01:00:00"),
    ("prep_pollen", "pollen", WorkflowStatus.SUCCESS, 100.0, 8, 32, "01:00:00"),
    ("wrf_run", "wrf", WorkflowStatus.RUNNING, 66.0, 64, 256, "24:00:00"),
    ("postprocess_eval", "postprocess", WorkflowStatus.PENDING, 0.0, 8, 32, "01:00:00"),
    ("product_extract", "products", WorkflowStatus.PENDING, 0.0, 8, 32, "01:00:00"),
    ("package_products", "products", WorkflowStatus.PENDING, 0.0, 4, 16, "00:30:00"),
]


def seed_operational_defaults(db: Session) -> None:
    """Create non-demo operational defaults for empty production databases."""
    seed_workflow(db)
    seed_scheduled_task(db)
    db.commit()


def seed_workflow(db: Session) -> None:
    workflow = db.query(Workflow).filter(Workflow.name == "auto_pollen_neimeng_official").first()
    if not workflow:
        workflow = Workflow(
            name="auto_pollen_neimeng_official",
            description="Operational WRF-Pollen DAG for the Neimeng official forecast cycle.",
            template_type="auto-pollen production",
            status=WorkflowStatus.RUNNING,
            region="neimeng",
        )
        db.add(workflow)
        db.flush()

    existing_nodes = {
        node.node_name
        for node in db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow.id).all()
    }
    for name, node_type, status, progress, cpu, memory, walltime in FLOW_NODE_DEFAULTS:
        if name in existing_nodes:
            continue
        db.add(
            WorkflowNode(
                workflow_id=workflow.id,
                node_name=name,
                node_type=node_type,
                status=status,
                progress=progress,
                cpu_cores=cpu,
                memory_gb=memory,
                slurm_queue="compute",
                walltime=walltime,
            )
        )


def seed_scheduled_task(db: Session) -> None:
    task = db.query(ScheduledTask).filter(ScheduledTask.task_id == "TASK-AUTO-POLLEN-NEIMENG").first()
    if task:
        return
    db.add(
        ScheduledTask(
            task_id="TASK-AUTO-POLLEN-NEIMENG",
            name="Auto Pollen Neimeng Official",
            status=TaskStatus.ACTIVE,
            cron_expression="0 4 * * *",
            region="neimeng",
            template=json.dumps(
                {
                    "period": "spring",
                    "domain": "neimeng",
                    "variant": "official",
                    "met_provider": "FNL",
                    "cycle_hour": 0,
                    "forecast_days": 7,
                    "server_owned": True,
                },
                ensure_ascii=False,
            ),
            workflow_id=None,
            last_result="Waiting for first scheduled tick",
            success_rate=100.0,
        )
    )

def parse_template(template: str | None) -> dict:
    if not template:
        return {}
    try:
        value = json.loads(template)
    except json.JSONDecodeError:
        return {"template_name": template}
    return value if isinstance(value, dict) else {}
