from fastapi import APIRouter
from pydantic import BaseModel

from core.decorators import require_module, handle_vault_locked
from core.services.vault import vault, VaultLockedError

router = APIRouter(prefix="/vault", tags=["vault"])


class UnlockIn(BaseModel):
    master_password: str


class SetIn(BaseModel):
    key: str
    password: str


@router.post("/unlock")
@require_module("vault")
def unlock(payload: UnlockIn):
    return vault.unlock(payload.master_password)


@router.post("/lock")
@require_module("vault")
def lock():
    return vault.lock()


@router.get("/list")
@require_module("vault")
@handle_vault_locked
def list_keys():
    return vault.list_keys()


@router.post("/set")
@require_module("vault")
@handle_vault_locked
def set_password(payload: SetIn):
    return vault.set(payload.key, payload.password)


@router.get("/get/{key}")
@require_module("vault")
@handle_vault_locked
def get_password(key: str):
    return vault.get(key)


@router.delete("/delete/{key}")
@require_module("vault")
@handle_vault_locked
def delete_key(key: str):
    return vault.delete(key)