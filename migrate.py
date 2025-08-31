#!/usr/bin/env python3
"""
Production migration runner for iScan backend
Runs database migrations safely with logging and rollback support
"""
import os
import sys
import logging
import subprocess
from typing import Optional


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('migration.log', mode='a')
        ]
    )


def run_command(cmd: list, description: str) -> bool:
    """Run a shell command and log the result"""
    logger = logging.getLogger(__name__)
    logger.info(f"Running: {description}")
    logger.info(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"✅ {description} completed successfully")
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"❌ {description} failed with code {result.returncode}")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {description} timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"❌ {description} failed with exception: {str(e)}")
        return False


def check_database_connection() -> bool:
    """Check if database is accessible"""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Checking database connection...")
    
    # Try to connect to database
    cmd = [
        'python', '-c',
        'from app.core.database import SessionLocal; '
        'db = SessionLocal(); '
        'db.execute("SELECT 1"); '
        'db.close(); '
        'print("Database connection successful")'
    ]
    
    return run_command(cmd, "Database connection check")


def get_current_migration_version() -> Optional[str]:
    """Get the current migration version from database"""
    logger = logging.getLogger(__name__)
    
    try:
        cmd = [
            'python', '-c',
            'from alembic.config import Config; '
            'from alembic import command; '
            'from alembic.runtime.migration import MigrationContext; '
            'from sqlalchemy import create_engine; '
            'import os; '
            'engine = create_engine(os.getenv("DATABASE_URL")); '
            'with engine.connect() as connection: '
            '    context = MigrationContext.configure(connection); '
            '    print(context.get_current_revision() or "None")'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            version = result.stdout.strip()
            logger.info(f"📍 Current migration version: {version}")
            return version if version != "None" else None
        else:
            logger.warning("Could not determine current migration version")
            return None
            
    except Exception as e:
        logger.warning(f"Could not determine current migration version: {str(e)}")
        return None


def run_migrations() -> bool:
    """Run database migrations"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting database migrations...")
    
    # First check current version
    current_version = get_current_migration_version()
    
    # Run migrations
    cmd = ['alembic', 'upgrade', 'head']
    success = run_command(cmd, "Database migration")
    
    if success:
        new_version = get_current_migration_version()
        if new_version != current_version:
            logger.info(f"📈 Migration completed: {current_version or 'None'} -> {new_version}")
        else:
            logger.info("📋 Database already up to date")
    
    return success


def main():
    """Main migration runner"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("🔧 iScan Database Migration Runner")
    logger.info("=" * 60)
    
    # Check environment
    if not os.getenv("DATABASE_URL"):
        logger.error("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Check database connection
    if not check_database_connection():
        logger.error("❌ Database connection failed - aborting migrations")
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        logger.error("❌ Migration failed - check logs for details")
        sys.exit(1)
    
    logger.info("✅ Migration completed successfully")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()