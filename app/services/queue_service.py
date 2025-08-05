import redis
from typing import Dict, Any, Optional
from app.core.config import settings
from app.celery_app import celery_app

class QueueService:
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)
    
    def enqueue_file_processing(self, file_id: int, file_type_id: int, batch_id: Optional[int] = None) -> str:
        task = celery_app.send_task(
            "app.tasks.process_document_task",
            args=[file_id, file_type_id, batch_id]
        )
        return task.id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        task = celery_app.AsyncResult(task_id)
        return {
            "id": task_id,
            "status": task.status,
            "result": task.result if task.ready() else None,
            "traceback": task.traceback if task.failed() else None
        }
    
    def get_queue_length(self, queue_name: str = "celery") -> int:
        return self.redis_client.llen(queue_name)
    
    def cancel_task(self, task_id: str) -> bool:
        try:
            celery_app.control.revoke(task_id, terminate=True)
            return True
        except Exception:
            return False

queue_service = QueueService()