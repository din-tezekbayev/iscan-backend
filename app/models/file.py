from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class FileStatus(enum.Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    original_name = Column(String(255), nullable=False)
    unique_name = Column(String(255), nullable=False, unique=True, index=True)
    file_type_id = Column(Integer, ForeignKey("file_types.id"), nullable=False)
    ftp_path = Column(String(500), nullable=False)
    status = Column(Enum(FileStatus), default=FileStatus.UPLOADED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    file_type = relationship("FileType", backref="files")
    processing_results = relationship("ProcessingResult", back_populates="file")