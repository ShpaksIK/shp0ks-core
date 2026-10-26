from fastapi import APIRouter
from pydantic import BaseModel

from core.decorators import require_module
from core.services.launcher import launcher

router = APIRouter(prefix="/launcher", tags=["launcher"])


class ProgramIn(BaseModel):
    name: str
    path: str


@router.get("/list")
@require_module("launcher")
def list_programs():
    return launcher.list()


@router.post("/add")
@require_module("launcher")
def add_program(payload: ProgramIn):
    return launcher.add(payload.name, payload.path)


@router.delete("/remove/{name}")
@require_module("launcher")
def remove_program(name: str):
    return launcher.remove(name)


@router.post("/open/{name}")
@require_module("launcher")
def open_program(name: str):
    return launcher.open(name)