from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from .core.database import SessionLocal, engine
from .core.config import settings
from .core.migrations import run_migrations
from .core.seeds import seed_operational_defaults
from .core.security import require_admin
from .api import workflows, tasks, products, dashboard, runs, fnl, agent, system, auth

run_migrations(engine)
with SessionLocal() as seed_db:
    seed_operational_defaults(seed_db)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

admin_dependencies = [Depends(require_admin)]

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(workflows.router, prefix=f"{settings.API_V1_STR}/workflows", tags=["workflows"], dependencies=admin_dependencies)
app.include_router(tasks.router, prefix=f"{settings.API_V1_STR}/tasks", tags=["tasks"], dependencies=admin_dependencies)
app.include_router(products.router, prefix=f"{settings.API_V1_STR}/products", tags=["products"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"], dependencies=admin_dependencies)
app.include_router(runs.router, prefix=f"{settings.API_V1_STR}/runs", tags=["runs"], dependencies=admin_dependencies)
app.include_router(fnl.router, prefix=f"{settings.API_V1_STR}/fnl", tags=["fnl"], dependencies=admin_dependencies)
app.include_router(agent.router, prefix=f"{settings.API_V1_STR}/agent", tags=["agent"], dependencies=admin_dependencies)
app.include_router(system.router, prefix=f"{settings.API_V1_STR}/system", tags=["system"], dependencies=admin_dependencies)

@app.get("/")
def root():
    return {
        "message": "China Pollen Forecast System API",
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
