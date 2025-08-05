from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Batch, ProcessingResult
from app.models.batch import BatchStatus
from app.services.queue_service import queue_service

router = APIRouter()

class BatchResponse(BaseModel):
    id: int
    name: str
    status: str
    created_at: str
    completed_at: Optional[str] = None

class BatchCreate(BaseModel):
    name: str

@router.get("/", response_model=List[BatchResponse])
def get_batches(db: Session = Depends(get_db)):
    batches = db.query(Batch).all()
    return [
        BatchResponse(
            id=b.id,
            name=b.name,
            status=b.status.value,
            created_at=b.created_at.isoformat(),
            completed_at=b.completed_at.isoformat() if b.completed_at else None
        )
        for b in batches
    ]

@router.post("/", response_model=BatchResponse)
def create_batch(batch: BatchCreate, db: Session = Depends(get_db)):
    db_batch = Batch(name=batch.name)
    db.add(db_batch)
    db.commit()
    db.refresh(db_batch)
    
    return BatchResponse(
        id=db_batch.id,
        name=db_batch.name,
        status=db_batch.status.value,
        created_at=db_batch.created_at.isoformat()
    )

@router.get("/{batch_id}/results")
def get_batch_results(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    results = db.query(ProcessingResult).filter(ProcessingResult.batch_id == batch_id).all()
    
    return {
        "batch_id": batch_id,
        "batch_name": batch.name,
        "results": [
            {
                "id": r.id,
                "file_id": r.file_id,
                "result_data": r.result_data,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat()
            }
            for r in results
        ]
    }

@router.post("/{batch_id}/export-json")
def export_batch_json(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Check if batch has results
    results_count = db.query(ProcessingResult).filter(ProcessingResult.batch_id == batch_id).count()
    if results_count == 0:
        raise HTTPException(status_code=400, detail="Batch has no results to export")
    
    # Queue JSON export task
    from app.celery_app import celery_app
    task = celery_app.send_task("app.tasks.export_batch_to_json", args=[batch_id])
    
    return {
        "message": "JSON export started",
        "task_id": task.id,
        "batch_id": batch_id
    }