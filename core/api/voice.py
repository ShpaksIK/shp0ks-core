from fastapi import APIRouter
from pydantic import BaseModel

from core.decorators import require_module
from core.services.voice import voice
from core.services.tts import tts

router = APIRouter(prefix="/voice", tags=["voice"])


class CommandIn(BaseModel):
    phrase: str
    action: str
    arg: str | None = None
    as_admin: bool = False


class SayIn(BaseModel):
    text: str

@router.post("/say")
@require_module("voice")
def say_text(payload: SayIn):
    tts.say(payload.text)
    return {"success": True, "message": "текст поставлен в очередь на озвучивание"}


@router.post("/start")
@require_module("voice")
def start_listening():
    return voice.start()


@router.post("/stop")
@require_module("voice")
def stop_listening():
    return voice.stop()


@router.get("/status")
@require_module("voice")
def voice_status():
    return voice.status()


@router.get("/commands")
@require_module("voice")
def list_commands():
    return voice.list_commands()


@router.post("/commands")
@require_module("voice")
def add_command(payload: CommandIn):
    return voice.add_command(payload.phrase, payload.action, payload.arg, payload.as_admin)


@router.put("/commands/{phrase}")
@require_module("voice")
def update_command(phrase: str, payload: CommandIn):
    return voice.update_command(phrase, payload.action, payload.arg, payload.as_admin)


@router.delete("/commands/{phrase}")
@require_module("voice")
def delete_command(phrase: str):
    return voice.delete_command(phrase)