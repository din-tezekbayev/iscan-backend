import uuid
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import File, FileType, Batch, ProcessingResult
from app.models.file import FileStatus
from app.services.ftp_service import ftp_service
from app.services.queue_service import queue_service

router = APIRouter()

class FileResponse(BaseModel):
    id: int
    original_name: str
    unique_name: str
    file_type_id: int
    status: str
    created_at: str
    batch_id: Optional[int] = None
    batch_name: Optional[str] = None

class FileUploadResponse(BaseModel):
    file_id: int
    message: str
    task_id: Optional[str] = None

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    file_type_id: int = 1,
    batch_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_type = db.query(FileType).filter(FileType.id == file_type_id).first()
    if not file_type:
        raise HTTPException(status_code=404, detail="File type not found")
    
    # Create a batch if not provided (for single file uploads)
    if batch_id is None:
        batch = Batch(
            name=f"Single file batch - {file.filename}"
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        batch_id = batch.id
    
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    
    file_content = await file.read()
    
    # Ensure FTP directories exist
    try:
        ftp_service.ensure_base_directories()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to setup FTP directories: {str(e)}")
    
    # Upload to the specific files directory
    try:
        ftp_path = ftp_service.upload_pdf_file(file_content, unique_name)
        if not ftp_path:
            raise HTTPException(status_code=500, detail="Failed to upload file to FTP server - check server logs for details")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FTP upload error: {str(e)}")
    
    db_file = File(
        original_name=file.filename,
        unique_name=unique_name,
        file_type_id=file_type_id,
        ftp_path=ftp_path,
        status=FileStatus.UPLOADED
    )
    
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    task_id = queue_service.enqueue_file_processing(db_file.id, file_type_id, batch_id)
    
    db_file.status = FileStatus.QUEUED
    db.commit()
    
    return FileUploadResponse(
        file_id=db_file.id,
        message="File uploaded successfully and queued for processing",
        task_id=task_id
    )

@router.get("/", response_model=List[FileResponse])
def get_files(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # Query files with their associated batch information through processing_results
    query = db.query(File, Batch.id.label('batch_id'), Batch.name.label('batch_name')).outerjoin(
        ProcessingResult, File.id == ProcessingResult.file_id
    ).outerjoin(
        Batch, ProcessingResult.batch_id == Batch.id
    )
    
    if status:
        try:
            file_status = FileStatus(status)
            query = query.filter(File.status == file_status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")
    
    # Order by file ID descending
    query = query.order_by(File.id.desc())
    files_with_batch = query.offset(skip).limit(limit).all()
    
    return [
        FileResponse(
            id=f.File.id,
            original_name=f.File.original_name,
            unique_name=f.File.unique_name,
            file_type_id=f.File.file_type_id,
            status=f.File.status.value,
            created_at=f.File.created_at.isoformat(),
            batch_id=f.batch_id,
            batch_name=f.batch_name
        )
        for f in files_with_batch
    ]

@router.get("/{file_id}")
def get_file(file_id: int, db: Session = Depends(get_db)):
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        id=file.id,
        original_name=file.original_name,
        unique_name=file.unique_name,
        file_type_id=file.file_type_id,
        status=file.status.value,
        created_at=file.created_at.isoformat()
    )

@router.get("/test-ftp")
def test_ftp_connection():
    """Test FTP connectivity for diagnostics"""
    import ftplib
    from app.core.config import settings
    
    try:
        ftp = ftplib.FTP()
        ftp.connect(settings.ftp_host, settings.ftp_port)
        ftp.login(settings.ftp_user, settings.ftp_password)
        
        # Try to list directories
        files = ftp.nlst()
        
        # Test directory access
        base_accessible = False
        try:
            ftp.cwd(settings.ftp_base_path)
            base_accessible = True
        except:
            pass
        
        ftp.quit()
        
        return {
            "status": "success",
            "message": "FTP connection successful",
            "host": settings.ftp_host,
            "port": settings.ftp_port,
            "base_path": settings.ftp_base_path,
            "base_accessible": base_accessible,
            "root_files_count": len(files)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"FTP connection failed: {str(e)}",
            "host": settings.ftp_host,
            "port": settings.ftp_port,
            "base_path": settings.ftp_base_path
        }

@router.get("/{file_id}/results")
def get_file_results(file_id: int, db: Session = Depends(get_db)):
    """Get processing results for a specific file"""
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    result = db.query(ProcessingResult).filter(ProcessingResult.file_id == file_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="No results found for this file")
    
    return {
        "file_id": file_id,
        "file_name": file.original_name,
        "result_data": result.result_data,
        "error_message": result.error_message,
        "created_at": result.created_at.isoformat(),
        "batch_id": result.batch_id
    }

@router.post("/{file_id}/export-json")
def export_file_json(file_id: int, db: Session = Depends(get_db)):
    """Export individual file results as JSON"""
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    result = db.query(ProcessingResult).filter(ProcessingResult.file_id == file_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="No results found for this file")
    
    # Get the batch for this file
    if result.batch_id:
        # Queue JSON export task for the batch containing this file
        from app.celery_app import celery_app
        task = celery_app.send_task("app.tasks.export_batch_to_json", args=[result.batch_id])
        
        return {
            "message": "JSON export started for file",
            "task_id": task.id,
            "file_id": file_id,
            "batch_id": result.batch_id
        }
    else:
        raise HTTPException(status_code=400, detail="File has no associated batch for export")