from sqlalchemy.orm import Session
from .core.database import SessionLocal, engine, Base
from .models.models import (
    Workflow, WorkflowNode, ScheduledTask, ForecastProduct, SystemLog,
    WorkflowStatus, TaskStatus, ProductStatus
)
from datetime import datetime, timedelta
import json

def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        if db.query(Workflow).count() == 0:
            workflows = [
                Workflow(
                    name="National_Daily_0924",
                    description="Full-scale atmospheric dispersion model for nationwide coverage",
                    template_type="National Daily",
                    status=WorkflowStatus.RUNNING,
                    region="National Wide"
                ),
                Workflow(
                    name="d02_Fine_Scale_Beijing",
                    description="High-resolution nested domain targeting urban hotspots",
                    template_type="d02 Fine-scale",
                    status=WorkflowStatus.SUCCESS,
                    region="Beijing-Tianjin-Hebei"
                )
            ]
            db.add_all(workflows)
            db.commit()

            nodes = [
                WorkflowNode(
                    workflow_id=1,
                    node_name="geogrid",
                    node_type="preprocessing",
                    status=WorkflowStatus.SUCCESS,
                    progress=100.0,
                    cpu_cores=64,
                    memory_gb=256,
                    slurm_queue="compute-high-priority",
                    walltime="02:00:00",
                    slurm_job_id="SL-2023-9821"
                ),
                WorkflowNode(
                    workflow_id=1,
                    node_name="ungrib",
                    node_type="preprocessing",
                    status=WorkflowStatus.SUCCESS,
                    progress=100.0,
                    cpu_cores=64,
                    memory_gb=256,
                    slurm_queue="compute-high-priority",
                    walltime="02:00:00"
                ),
                WorkflowNode(
                    workflow_id=1,
                    node_name="metgrid",
                    node_type="preprocessing",
                    status=WorkflowStatus.SUCCESS,
                    progress=100.0,
                    cpu_cores=64,
                    memory_gb=256,
                    slurm_queue="compute-high-priority",
                    walltime="02:00:00"
                ),
                WorkflowNode(
                    workflow_id=1,
                    node_name="WPS -> Interpolation",
                    node_type="processing",
                    status=WorkflowStatus.RUNNING,
                    progress=65.0,
                    cpu_cores=128,
                    memory_gb=512,
                    slurm_queue="compute-high-priority",
                    walltime="04:00:00"
                ),
                WorkflowNode(
                    workflow_id=1,
                    node_name="WRF Forecast",
                    node_type="processing",
                    status=WorkflowStatus.PENDING,
                    progress=0.0,
                    cpu_cores=256,
                    memory_gb=1024,
                    slurm_queue="compute-high-priority",
                    walltime="08:00:00"
                ),
                WorkflowNode(
                    workflow_id=1,
                    node_name="Post-processing",
                    node_type="postprocessing",
                    status=WorkflowStatus.FAILED,
                    progress=100.0,
                    cpu_cores=64,
                    memory_gb=256,
                    slurm_queue="compute-high-priority",
                    walltime="02:00:00",
                    error_message="Exit Code: 1 (OOM)"
                )
            ]
            db.add_all(nodes)
            db.commit()

        if db.query(ScheduledTask).count() == 0:
            tasks = [
                ScheduledTask(
                    task_id="TASK-8821",
                    name="Morning_Pollen_Aggregator",
                    status=TaskStatus.ACTIVE,
                    cron_expression="0 4 * * *",
                    region="East China Grid",
                    template=json.dumps(
                        {
                            "period": "spring",
                            "domain": "neimeng",
                            "variant": "official",
                            "met_provider": "FNL",
                            "cycle_hour": 0,
                            "forecast_days": 7,
                            "dry_run_submit": True,
                        },
                        ensure_ascii=False,
                    ),
                    last_run=datetime.now() - timedelta(hours=2),
                    last_result="Success",
                    last_duration=1.2,
                    success_rate=99.2
                ),
                ScheduledTask(
                    task_id="TASK-9902",
                    name="Sat_Imagery_PreProcess",
                    status=TaskStatus.ACTIVE,
                    cron_expression="*/15 * * * *",
                    region="National Wide",
                    template="Spectral_Filter",
                    last_run=datetime.now() - timedelta(minutes=15),
                    last_result="Success",
                    last_duration=8.4,
                    success_rate=98.8
                ),
                ScheduledTask(
                    task_id="TASK-1022",
                    name="Deep_Learning_Model_Retrain",
                    status=TaskStatus.INACTIVE,
                    cron_expression="0 0 1 * *",
                    region="Training Set Alpha",
                    template="CNN_LSTM_Core",
                    last_run=datetime.now() - timedelta(days=24),
                    last_result="Success",
                    last_duration=3600.0,
                    success_rate=100.0
                ),
                ScheduledTask(
                    task_id="TASK-4410",
                    name="Alert_Dispatcher_Regional",
                    status=TaskStatus.FAILED,
                    cron_expression="*/5 * * * *",
                    region="Guangdong / Pearl Delta",
                    template="SMS_PUSH_TPL",
                    last_run=datetime.now() - timedelta(minutes=5),
                    last_result="API Timeout (408)",
                    last_duration=30.0,
                    success_rate=85.5
                )
            ]
            db.add_all(tasks)
            db.commit()

        if db.query(ForecastProduct).count() == 0:
            products = [
                ForecastProduct(
                    product_name="NORTH_CHINA_PLN_ARTEMISIA_24H",
                    product_type="Map (GeoJSON)",
                    status=ProductStatus.READY,
                    region="North China Plain",
                    pollen_type="Artemisia (Mugwort)",
                    resolution="High Res",
                    workflow_node="WRF-CHEM-NCP-01",
                    workflow_version="V4.2 STABLE",
                    file_path="/data/products/north_china_artemisia_24h.geojson",
                    is_published=True,
                    release_time=datetime.now() - timedelta(hours=2)
                ),
                ForecastProduct(
                    product_name="YANGTZE_RV_CONC_PINUS_48H",
                    product_type="Chart (PDF)",
                    status=ProductStatus.ARCHIVED,
                    region="Yangtze River Basin",
                    pollen_type="Pinus (Pine)",
                    resolution="Standard",
                    workflow_node="HYSPLIT-YANGTZE-B",
                    workflow_version="BATCH PROCESSOR",
                    file_path="/data/products/yangtze_pinus_48h.pdf",
                    is_published=False,
                    release_time=datetime.now() - timedelta(hours=3)
                ),
                ForecastProduct(
                    product_name="TIBET_PLAT_DUST_MIX_72H",
                    product_type="Map (GeoTIFF)",
                    status=ProductStatus.ERROR,
                    region="Tibetan Plateau",
                    pollen_type="Mixed Species",
                    resolution="Standard",
                    workflow_node="CMA-GLOBAL-09",
                    workflow_version="TIMEOUT EXCEPTION",
                    file_path="/data/products/tibet_dust_72h.tif",
                    is_published=False,
                    release_time=datetime.now() - timedelta(hours=4)
                ),
                ForecastProduct(
                    product_name="S_CHINA_TROPIC_POLLEN_24H",
                    product_type="Map (GeoTIFF)",
                    status=ProductStatus.READY,
                    region="South China",
                    pollen_type="Tropical Species",
                    resolution="High Res",
                    workflow_node="WRF-CHEM-SC-14",
                    workflow_version="V4.2 STABLE",
                    file_path="/data/products/south_china_tropic_24h.tif",
                    is_published=True,
                    release_time=datetime.now() - timedelta(hours=5)
                )
            ]
            db.add_all(products)
            db.commit()

        if db.query(SystemLog).count() == 0:
            logs = [
                SystemLog(
                    level="INFO",
                    message="geogrid.exe completed successfully.",
                    source="WRF-Preprocessing",
                    timestamp=datetime.now() - timedelta(minutes=30)
                ),
                SystemLog(
                    level="INFO",
                    message="ungrib.exe successfully extracted 24 meteorological fields.",
                    source="WRF-Preprocessing",
                    timestamp=datetime.now() - timedelta(minutes=25)
                ),
                SystemLog(
                    level="INFO",
                    message="metgrid.exe vertical interpolation complete.",
                    source="WRF-Preprocessing",
                    timestamp=datetime.now() - timedelta(minutes=20)
                ),
                SystemLog(
                    level="INFO",
                    message="Starting WPS -> Interpolation on 128 cores...",
                    source="Workflow-Manager",
                    timestamp=datetime.now() - timedelta(minutes=15)
                ),
                SystemLog(
                    level="ERROR",
                    message="Post-processing node failed at step 4/12.",
                    source="Post-Processing",
                    timestamp=datetime.now() - timedelta(minutes=5)
                ),
                SystemLog(
                    level="ERROR",
                    message="OutOfMemoryError in Slurm partition 'compute-high-priority'. Process 4209 killed by signal 9.",
                    source="Slurm-Monitor",
                    timestamp=datetime.now() - timedelta(minutes=4)
                )
            ]
            db.add_all(logs)
            db.commit()

        print("Database initialized successfully with sample data!")

    finally:
        db.close()

if __name__ == "__main__":
    init_db()
