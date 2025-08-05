from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    app_name: str = "iScan Document Processing"
    debug: bool = False
    
    database_url: str
    redis_url: str
    
    # FTP settings - optional for Railway deployment
    ftp_host: Optional[str] = None
    ftp_user: Optional[str] = None
    ftp_password: Optional[str] = None
    ftp_port: int = 21
    ftp_base_path: str = "/Marketplace/scan_ai"
    ftp_files_path: str = "/Marketplace/scan_ai/files"
    ftp_csv_path: str = "/Marketplace/scan_ai/csvs"
    
    openai_api_key: str
    
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    
    # Railway deployment settings
    port: int = 8000
    host: str = "0.0.0.0"
    
    class Config:
        env_file = ".env"
    
    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url
    
    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

settings = Settings()