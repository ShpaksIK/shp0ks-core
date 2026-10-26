from fastapi import APIRouter
from core.decorators import require_module
from core.services.monitor import monitor

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/snapshot")
@require_module("monitor")
def snapshot():
    return monitor.get_snapshot()


@router.post("/save")
@require_module("monitor")
def save_snapshot():
    return monitor.save_snapshot()


@router.get("/history")
@require_module("monitor")
def history(days: int = 1):
    if days < 1 or days > 30:
        return {"success": False, "error": "количество дней должно быть от 1 до 30"}
    return monitor.get_history(days)


@router.post("/cleanup")
@require_module("monitor")
def cleanup():
    return monitor.cleanup_history()