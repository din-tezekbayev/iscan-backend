#!/usr/bin/env python3
"""
Production migration script to safely add new FileType columns
This script will check if columns exist before creating them
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment"""
    return os.getenv("DATABASE_URL", "postgresql://iscan_user:iscan_password@postgres:5432/iscan_db")


def column_exists(engine, table_name, column_name):
    """Check if a column exists in the table"""
    try:
        query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table_name 
            AND column_name = :column_name
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"table_name": table_name, "column_name": column_name})
            return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking if column exists: {e}")
        return False


def enum_type_exists(engine, enum_name):
    """Check if enum type exists"""
    try:
        query = text("""
            SELECT typname 
            FROM pg_type 
            WHERE typname = :enum_name
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"enum_name": enum_name})
            return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking if enum exists: {e}")
        return False


def apply_migration():
    """Apply the migration safely"""
    database_url = get_database_url()
    logger.info(f"Connecting to database...")
    
    try:
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logger.info("✅ Database connection successful")
        
        # Create transaction for safe migration
        with engine.begin() as conn:
            logger.info("Starting migration transaction...")
            
            # Create enum types if they don't exist
            if not enum_type_exists(engine, 'processingmode'):
                logger.info("Creating processingmode enum...")
                conn.execute(text("CREATE TYPE processingmode AS ENUM ('IMAGE_OCR', 'TEXT_EXTRACTION');"))
                logger.info("✅ Created processingmode enum")
            else:
                logger.info("📋 processingmode enum already exists")
            
            if not enum_type_exists(engine, 'processortype'):
                logger.info("Creating processortype enum...")
                conn.execute(text("CREATE TYPE processortype AS ENUM ('HUAWEI_ACT', 'INVOICE', 'CONTRACT', 'RECEIPT', 'CUSTOM');"))
                logger.info("✅ Created processortype enum")
            else:
                logger.info("📋 processortype enum already exists")
            
            # Add columns if they don't exist
            columns_to_add = [
                {
                    'name': 'processor_type',
                    'definition': 'processortype NOT NULL DEFAULT \'CUSTOM\'::processortype'
                },
                {
                    'name': 'processing_mode', 
                    'definition': 'processingmode NOT NULL DEFAULT \'IMAGE_OCR\'::processingmode'
                },
                {
                    'name': 'verification_enabled',
                    'definition': 'boolean NOT NULL DEFAULT false'
                }
            ]
            
            for column in columns_to_add:
                if not column_exists(engine, 'file_types', column['name']):
                    logger.info(f"Adding column {column['name']}...")
                    conn.execute(text(f"ALTER TABLE file_types ADD COLUMN {column['name']} {column['definition']};"))
                    logger.info(f"✅ Added column {column['name']}")
                else:
                    logger.info(f"📋 Column {column['name']} already exists")
            
            # Update existing huawei record if it exists
            logger.info("Checking for existing huawei record...")
            result = conn.execute(text("SELECT id FROM file_types WHERE name = 'huawei'"))
            huawei_record = result.fetchone()
            
            if huawei_record:
                logger.info("Updating huawei record with correct values...")
                conn.execute(text("""
                    UPDATE file_types 
                    SET processor_type = 'HUAWEI_ACT', 
                        processing_mode = 'IMAGE_OCR', 
                        verification_enabled = true 
                    WHERE name = 'huawei'
                """))
                logger.info("✅ Updated huawei record")
            else:
                logger.info("📋 No huawei record found to update")
        
        logger.info("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔧 Production Database Migration")
    logger.info("=" * 60)
    
    success = apply_migration()
    
    if success:
        logger.info("✅ All migrations applied successfully")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed")
        sys.exit(1)