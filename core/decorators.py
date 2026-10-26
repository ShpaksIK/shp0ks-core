import functools

from core.registry import registry
from core.services.vault import VaultLockedError


def require_module(name: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not registry.is_enabled(name):
                return {"success": False, "error": "модуль выключен"}
            return func(*args, **kwargs)
        return wrapper
    return decorator


def handle_vault_locked(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except VaultLockedError as e:
            return {"success": False, "error": str(e), "locked": True}
    return wrapper