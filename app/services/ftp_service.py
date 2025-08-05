import ftplib
import io
import os
import logging
from typing import Optional, BinaryIO
from contextlib import contextmanager
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FTPService:
    def __init__(self):
        self.host = settings.ftp_host
        self.port = settings.ftp_port
        self.username = settings.ftp_user
        self.password = settings.ftp_password
        self.base_path = settings.ftp_base_path
        self.files_path = settings.ftp_files_path
        self.csv_path = settings.ftp_csv_path
    
    @contextmanager
    def get_connection(self):
        ftp = ftplib.FTP()
        try:
            logger.info(f"Connecting to FTP server: {self.host}:{self.port}")
            ftp.connect(self.host, self.port)
            logger.info(f"Logging in with user: {self.username}")
            ftp.login(self.username, self.password)
            logger.info("FTP connection successful")
            yield ftp
        except ftplib.error_perm as e:
            logger.error(f"FTP permission error: {e}")
            raise
        except ftplib.error_temp as e:
            logger.error(f"FTP temporary error: {e}")
            raise
        except Exception as e:
            logger.error(f"FTP connection error: {e}")
            raise
        finally:
            try:
                ftp.quit()
                logger.info("FTP connection closed")
            except:
                ftp.close()
                logger.info("FTP connection forcibly closed")
    
    def upload_file(self, file_content: bytes, remote_path: str) -> bool:
        try:
            logger.info(f"Starting upload to: {remote_path}")
            with self.get_connection() as ftp:
                directory = os.path.dirname(remote_path)
                if directory:
                    logger.info(f"Ensuring directory exists: {directory}")
                    self._ensure_directory_exists(ftp, directory)
                
                logger.info(f"Uploading file ({len(file_content)} bytes)")
                bio = io.BytesIO(file_content)
                ftp.storbinary(f'STOR {remote_path}', bio)
                logger.info(f"Upload successful: {remote_path}")
                return True
        except Exception as e:
            logger.error(f"FTP upload error for {remote_path}: {e}")
            return False
    
    def download_file(self, remote_path: str) -> Optional[bytes]:
        try:
            with self.get_connection() as ftp:
                bio = io.BytesIO()
                ftp.retrbinary(f'RETR {remote_path}', bio.write)
                return bio.getvalue()
        except Exception as e:
            print(f"FTP download error: {e}")
            return None
    
    def delete_file(self, remote_path: str) -> bool:
        try:
            with self.get_connection() as ftp:
                ftp.delete(remote_path)
                return True
        except Exception as e:
            print(f"FTP delete error: {e}")
            return False
    
    def file_exists(self, remote_path: str) -> bool:
        try:
            with self.get_connection() as ftp:
                ftp.size(remote_path)
                return True
        except:
            return False
    
    def upload_pdf_file(self, file_content: bytes, filename: str) -> Optional[str]:
        """Upload PDF file to the files directory"""
        try:
            remote_path = f"{self.files_path}/{filename}"
            logger.info(f"Uploading PDF: {filename} to {remote_path}")
            if self.upload_file(file_content, remote_path):
                return remote_path
            logger.error(f"PDF upload failed for: {filename}")
            return None
        except Exception as e:
            logger.error(f"PDF upload error for {filename}: {e}")
            return None
    
    def upload_csv_file(self, csv_content: bytes, filename: str) -> Optional[str]:
        """Upload CSV file to the csv directory"""
        try:
            remote_path = f"{self.csv_path}/{filename}"
            if self.upload_file(csv_content, remote_path):
                return remote_path
            return None
        except Exception as e:
            print(f"CSV upload error: {e}")
            return None
    
    def upload_json_file(self, json_content: bytes, filename: str) -> Optional[str]:
        """Upload JSON file to the csv directory (reusing same directory)"""
        try:
            remote_path = f"{self.csv_path}/{filename}"
            logger.info(f"Uploading JSON: {filename} to {remote_path}")
            if self.upload_file(json_content, remote_path):
                logger.info(f"JSON upload successful: {remote_path}")
                return remote_path
            logger.error(f"JSON upload failed for: {filename}")
            return None
        except Exception as e:
            logger.error(f"JSON upload error for {filename}: {e}")
            return None
    
    def ensure_base_directories(self) -> bool:
        """Ensure the base directories exist on FTP server"""
        try:
            with self.get_connection() as ftp:
                self._ensure_directory_exists(ftp, self.base_path)
                self._ensure_directory_exists(ftp, self.files_path)
                self._ensure_directory_exists(ftp, self.csv_path)
                return True
        except Exception as e:
            print(f"Directory creation error: {e}")
            return False
    
    def _ensure_directory_exists(self, ftp: ftplib.FTP, directory: str):
        parts = directory.split('/')
        current_path = ''
        
        for part in parts:
            if not part:
                continue
            
            current_path += f'/{part}' if current_path else part
            
            try:
                ftp.cwd(current_path)
            except ftplib.error_perm:
                try:
                    ftp.mkd(current_path)
                    ftp.cwd(current_path)
                except ftplib.error_perm:
                    pass
        
        ftp.cwd('/')

ftp_service = FTPService()