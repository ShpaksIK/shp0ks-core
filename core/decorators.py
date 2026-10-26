import functools
import inspect

from core.registry import registry
from core.services.vault import VaultLockedError


def require_module(name: str):
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not registry.is_enabled(name):
                    return {"success": False, "error": "модуль отключен"}
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not registry.is_enabled(name):
                    return {"success": False, "error": "модуль отключен"}
                return func(*args, **kwargs)
            return sync_wrapper
    return decorator


def handle_vault_locked(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except VaultLockedError as e:
            return {"success": False, "error": str(e), "locked": True}
    return wrapper