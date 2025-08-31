from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, Enum
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import ProcessingMode, ProcessorType


class FileType(Base):
    __tablename__ = "file_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    processing_prompts = Column(JSON, nullable=False)
    
    # New fields for flexible processing
    processor_type = Column(Enum(ProcessorType), nullable=False, default=ProcessorType.CUSTOM)
    processing_mode = Column(Enum(ProcessingMode), nullable=False, default=ProcessingMode.IMAGE_OCR)
    verification_enabled = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())