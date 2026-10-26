from fastapi import APIRouter
from core.registry import registry

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("")
def list_modules():
    return registry.all()


@router.post("/{name}/enable")
def enable_module(name: str):
    return registry.set_enabled(name, True)


@router.post("/{name}/disable")
def disable_module(name: str):
    return registry.set_enabled(name, False)