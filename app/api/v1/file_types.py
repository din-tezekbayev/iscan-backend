from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import FileType

router = APIRouter()

class FileTypeResponse(BaseModel):
    id: int
    name: str
    description: str

class FileTypeDetailResponse(BaseModel):
    id: int
    name: str
    description: str
    processing_prompts: dict
    created_at: str
    updated_at: str

class FileTypeCreate(BaseModel):
    name: str
    description: str
    processing_prompts: dict

class FileTypeUpdate(BaseModel):
    name: str
    description: str
    processing_prompts: dict

class PromptsUpdate(BaseModel):
    processing_prompts: dict

@router.get("/", response_model=List[FileTypeResponse])
def get_file_types(db: Session = Depends(get_db)):
    file_types = db.query(FileType).all()
    return [
        FileTypeResponse(
            id=ft.id,
            name=ft.name,
            description=ft.description or ""
        )
        for ft in file_types
    ]

@router.post("/", response_model=FileTypeResponse)
def create_file_type(file_type: FileTypeCreate, db: Session = Depends(get_db)):
    existing = db.query(FileType).filter(FileType.name == file_type.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="File type with this name already exists")
    
    db_file_type = FileType(
        name=file_type.name,
        description=file_type.description,
        processing_prompts=file_type.processing_prompts
    )
    
    db.add(db_file_type)
    db.commit()
    db.refresh(db_file_type)
    
    return FileTypeResponse(
        id=db_file_type.id,
        name=db_file_type.name,
        description=db_file_type.description or ""
    )

@router.get("/{file_type_id}", response_model=FileTypeDetailResponse)
def get_file_type(file_type_id: int, db: Session = Depends(get_db)):
    file_type = db.query(FileType).filter(FileType.id == file_type_id).first()
    if not file_type:
        raise HTTPException(status_code=404, detail="File type not found")
    
    return FileTypeDetailResponse(
        id=file_type.id,
        name=file_type.name,
        description=file_type.description or "",
        processing_prompts=file_type.processing_prompts,
        created_at=file_type.created_at.isoformat() if file_type.created_at else "",
        updated_at=file_type.updated_at.isoformat() if file_type.updated_at else ""
    )

@router.put("/{file_type_id}", response_model=FileTypeDetailResponse)
def update_file_type(file_type_id: int, file_type_data: FileTypeUpdate, db: Session = Depends(get_db)):
    file_type = db.query(FileType).filter(FileType.id == file_type_id).first()
    if not file_type:
        raise HTTPException(status_code=404, detail="File type not found")
    
    # Check if name is being changed and if it conflicts with existing
    if file_type_data.name != file_type.name:
        existing = db.query(FileType).filter(
            FileType.name == file_type_data.name,
            FileType.id != file_type_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="File type with this name already exists")
    
    file_type.name = file_type_data.name
    file_type.description = file_type_data.description
    file_type.processing_prompts = file_type_data.processing_prompts
    
    db.commit()
    db.refresh(file_type)
    
    return FileTypeDetailResponse(
        id=file_type.id,
        name=file_type.name,
        description=file_type.description or "",
        processing_prompts=file_type.processing_prompts,
        created_at=file_type.created_at.isoformat() if file_type.created_at else "",
        updated_at=file_type.updated_at.isoformat() if file_type.updated_at else ""
    )

@router.put("/{file_type_id}/prompts", response_model=FileTypeDetailResponse)
def update_file_type_prompts(file_type_id: int, prompts_data: PromptsUpdate, db: Session = Depends(get_db)):
    file_type = db.query(FileType).filter(FileType.id == file_type_id).first()
    if not file_type:
        raise HTTPException(status_code=404, detail="File type not found")
    
    file_type.processing_prompts = prompts_data.processing_prompts
    
    db.commit()
    db.refresh(file_type)
    
    return FileTypeDetailResponse(
        id=file_type.id,
        name=file_type.name,
        description=file_type.description or "",
        processing_prompts=file_type.processing_prompts,
        created_at=file_type.created_at.isoformat() if file_type.created_at else "",
        updated_at=file_type.updated_at.isoformat() if file_type.updated_at else ""
    )

@router.delete("/{file_type_id}")
def delete_file_type(file_type_id: int, db: Session = Depends(get_db)):
    from app.models import File
    
    file_type = db.query(FileType).filter(FileType.id == file_type_id).first()
    if not file_type:
        raise HTTPException(status_code=404, detail="File type not found")
    
    # Check if any files are using this file type
    files_count = db.query(File).filter(File.file_type_id == file_type_id).count()
    if files_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete file type. {files_count} files are using this file type."
        )
    
    db.delete(file_type)
    db.commit()
    
    return {"message": "File type deleted successfully"}