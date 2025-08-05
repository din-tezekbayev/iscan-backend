from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import files, file_types, batches, tasks
from app.core.config import settings
from app.core.database import engine
from app.models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.railway.app",
        "https://*.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(file_types.router, prefix="/api/v1/file-types", tags=["file-types"])
app.include_router(batches.router, prefix="/api/v1/batches", tags=["batches"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])

@app.get("/")
def read_root():
    return {"message": "iScan Document Processing API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}