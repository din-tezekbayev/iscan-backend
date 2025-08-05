from fastapi import APIRouter
from app.services.queue_service import queue_service

router = APIRouter()

@router.get("/{task_id}/status")
def get_task_status(task_id: str):
    return queue_service.get_task_status(task_id)

@router.delete("/{task_id}")
def cancel_task(task_id: str):
    success = queue_service.cancel_task(task_id)
    return {"success": success, "message": "Task cancelled" if success else "Failed to cancel task"}

@router.get("/queue/length")
def get_queue_length():
    length = queue_service.get_queue_length()
    return {"queue_length": length}