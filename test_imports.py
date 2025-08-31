#!/usr/bin/env python3
"""Test script to check if all imports work correctly"""

def test_imports():
    print("Testing imports...")
    
    try:
        print("1. Testing basic imports...")
        import asyncio
        from celery import current_task
        from sqlalchemy.orm import Session
        print("   ✓ Basic imports OK")
        
        print("2. Testing app core imports...")
        from app.core.database import SessionLocal
        from app.core.config import settings
        print("   ✓ Core imports OK")
        
        print("3. Testing model imports...")
        from app.models import File, FileType, ProcessingResult, Batch
        from app.models.file import FileStatus
        print("   ✓ Model imports OK")
        
        print("4. Testing service imports...")
        from app.services.ftp_service import ftp_service
        print("   ✓ Service imports OK")
        
        print("5. Testing processor imports...")
        from app.process_services.invoice_processor import InvoiceProcessor
        from app.process_services.huawei_processor import HuaweiProcessor
        print("   ✓ Processor imports OK")
        
        print("6. Testing LangGraph imports...")
        import pymupdf
        from langgraph.graph import StateGraph, END
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
        print("   ✓ LangGraph imports OK")
        
        print("7. Testing document processor...")
        from app.langgraph.document_processor import process_document
        print("   ✓ Document processor import OK")
        
        print("8. Testing Celery app...")
        from app.celery_app import celery_app
        print("   ✓ Celery app import OK")
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_imports()