from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..core.database import get_db
from ..models.models import Workflow, WorkflowNode
from ..schemas.schemas import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowNodeCreate,
    WorkflowNodeResponse
)

router = APIRouter()

@router.get("/", response_model=List[WorkflowResponse])
def get_workflows(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    workflows = db.query(Workflow).offset(skip).limit(limit).all()
    return workflows

@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(workflow: WorkflowCreate, db: Session = Depends(get_db)):
    db_workflow = Workflow(**workflow.model_dump())
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow

@router.get("/{workflow_id}/nodes", response_model=List[WorkflowNodeResponse])
def get_workflow_nodes(workflow_id: int, db: Session = Depends(get_db)):
    nodes = db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow_id).all()
    return nodes

@router.post("/nodes", response_model=WorkflowNodeResponse, status_code=status.HTTP_201_CREATED)
def create_workflow_node(node: WorkflowNodeCreate, db: Session = Depends(get_db)):
    db_node = WorkflowNode(**node.model_dump())
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node

@router.patch("/{workflow_id}/status")
def update_workflow_status(workflow_id: int, status: str, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow.status = status
    db.commit()
    return {"message": "Status updated successfully"}
