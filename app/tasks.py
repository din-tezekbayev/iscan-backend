import asyncio
import logging
from celery import current_task
from sqlalchemy.orm import Session
from app.celery_app import celery_app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_processors():
    """Lazy load processors to avoid import issues on startup"""
    from app.process_services.invoice_processor import InvoiceProcessor
    from app.process_services.huawei_processor import HuaweiProcessor
    from app.models.enums import ProcessorType

    return {
        ProcessorType.INVOICE: InvoiceProcessor(),
        ProcessorType.HUAWEI_ACT: HuaweiProcessor(),
        ProcessorType.RECEIPT: InvoiceProcessor(),  # Using InvoiceProcessor for receipts for now
        ProcessorType.CONTRACT: InvoiceProcessor(),  # Using InvoiceProcessor for contracts for now
        ProcessorType.CUSTOM: InvoiceProcessor(),  # Default fallback
    }

@celery_app.task(bind=True)
def process_document_task(self, file_id: int, file_type_id: int, batch_id: int = None):
    # Import inside the task to avoid startup issues
    from app.core.database import SessionLocal
    from app.models import File, FileType, ProcessingResult
    from app.models.file import FileStatus
    from app.services.ftp_service import ftp_service
    from app.langgraph.document_processor import process_document

    db: Session = SessionLocal()

    try:
        file_record = db.query(File).filter(File.id == file_id).first()
        if not file_record:
            raise Exception(f"File with id {file_id} not found")

        file_type = db.query(FileType).filter(FileType.id == file_type_id).first()
        if not file_type:
            raise Exception(f"FileType with id {file_type_id} not found")

        file_record.status = FileStatus.PROCESSING
        db.commit()

        file_content = ftp_service.download_file(file_record.ftp_path)
        if not file_content:
            raise Exception(f"Could not download file from FTP: {file_record.ftp_path}")

        processors = get_processors()
        processor = processors.get(file_type.processor_type)
        prompts = file_type.processing_prompts
        
        logger.info(f"File type: {file_type.name}, Processor type: {file_type.processor_type}, Processing mode: {file_type.processing_mode}, Verification: {file_type.verification_enabled}")
        logger.info(f"Processor found: {type(processor).__name__ if processor else 'None'}")

        logger.info(f"File prompts: {prompts}")
        
        # Enhanced prompts with processing metadata
        enhanced_prompts = {
            **prompts,
            "processing_mode": file_type.processing_mode,
            "verification_enabled": file_type.verification_enabled
        }
        
        result = asyncio.run(process_document(file_content, enhanced_prompts))

        if "error" in result:
            file_record.status = FileStatus.FAILED
            processing_result = ProcessingResult(
                file_id=file_id,
                batch_id=batch_id,
                result_data={},
                error_message=result["error"]
            )
        else:
            if processor:
                result = processor.process_result(result)

            file_record.status = FileStatus.COMPLETED
            processing_result = ProcessingResult(
                file_id=file_id,
                batch_id=batch_id,
                result_data=result
            )

        db.add(processing_result)
        db.commit()

        return {"status": "completed", "result": result}

    except Exception as e:
        if 'file_record' in locals():
            file_record.status = FileStatus.FAILED
            db.commit()

        processing_result = ProcessingResult(
            file_id=file_id,
            batch_id=batch_id,
            result_data={},
            error_message=str(e)
        )
        db.add(processing_result)
        db.commit()

        raise e
    finally:
        db.close()

@celery_app.task(bind=True)
def export_batch_to_csv(self, batch_id: int):
    """Export batch processing results to CSV and upload to FTP"""
    # Import inside the task to avoid startup issues
    from app.core.database import SessionLocal
    from app.models import Batch, ProcessingResult
    from app.models.batch import BatchStatus
    from app.services.ftp_service import ftp_service

    db: Session = SessionLocal()

    try:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise Exception(f"Batch with id {batch_id} not found")

        # Get all processing results for this batch
        results = db.query(ProcessingResult).filter(ProcessingResult.batch_id == batch_id).all()

        if not results:
            raise Exception(f"No results found for batch {batch_id}")

        # Convert results to list of dictionaries for CSV
        csv_data = []
        for result in results:
            row = {
                'file_id': result.file_id,
                'file_name': result.file.original_name if result.file else 'Unknown',
                'processing_date': result.created_at.isoformat(),
                'status': 'success' if not result.error_message else 'failed',
                'error_message': result.error_message or '',
            }

            # Add result data fields
            if result.result_data:
                for key, value in result.result_data.items():
                    if isinstance(value, (str, int, float, bool)):
                        row[key] = value
                    else:
                        row[key] = str(value)

            csv_data.append(row)

        # Generate CSV
        import pandas as pd
        import io
        df = pd.DataFrame(csv_data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue().encode('utf-8')

        # Upload to FTP
        csv_filename = f"batch_{batch_id}_results_{batch.created_at.strftime('%Y%m%d_%H%M%S')}.csv"
        csv_path = ftp_service.upload_csv_file(csv_content, csv_filename)

        if csv_path:
            # Update batch with CSV path
            batch.status = BatchStatus.COMPLETED
            db.commit()
            return {"status": "completed", "csv_path": csv_path}
        else:
            raise Exception("Failed to upload CSV to FTP")

    except Exception as e:
        raise e
    finally:
        db.close()

@celery_app.task(bind=True)
def export_batch_to_json(self, batch_id: int):
    """Export batch processing results to JSON and upload to FTP"""
    # Import inside the task to avoid startup issues
    from app.core.database import SessionLocal
    from app.models import Batch, ProcessingResult
    from app.models.batch import BatchStatus
    from app.services.ftp_service import ftp_service
    import json

    db: Session = SessionLocal()

    try:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise Exception(f"Batch with id {batch_id} not found")

        # Get all processing results for this batch
        results = db.query(ProcessingResult).filter(ProcessingResult.batch_id == batch_id).all()

        if not results:
            raise Exception(f"No results found for batch {batch_id}")

        # Convert results to structured JSON
        json_data = {
            "batch_info": {
                "batch_id": batch_id,
                "batch_name": batch.name,
                "created_at": batch.created_at.isoformat(),
                "status": batch.status.value,
                "total_files": len(results)
            },
            "results": []
        }

        for result in results:
            result_entry = {
                "file_info": {
                    "file_id": result.file_id,
                    "file_name": result.file.original_name if result.file else "Unknown",
                    "processing_date": result.created_at.isoformat(),
                    "status": "success" if not result.error_message else "failed"
                },
                "extracted_data": result.result_data if result.result_data else {},
                "error_message": result.error_message
            }
            json_data["results"].append(result_entry)

        # Generate JSON content
        json_content = json.dumps(json_data, indent=2, ensure_ascii=False).encode('utf-8')

        # Upload to FTP
        json_filename = f"batch_{batch_id}_results_{batch.created_at.strftime('%Y%m%d_%H%M%S')}.json"
        json_path = ftp_service.upload_json_file(json_content, json_filename)

        if json_path:
            # Update batch with JSON path
            batch.status = BatchStatus.COMPLETED
            db.commit()
            return {"status": "completed", "json_path": json_path}
        else:
            raise Exception("Failed to upload JSON to FTP")

    except Exception as e:
        raise e
    finally:
        db.close()
