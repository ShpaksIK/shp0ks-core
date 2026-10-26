import json
import os
from pathlib import Path
import subprocess
import getpass
import time

from core.paths import VAULT_FILE

from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultLockedError(Exception):
    pass


class Vault:
    def __init__(self, data_path: Path, auto_lock_seconds: int = 180):
        self._data_path = data_path
        self._entries: dict[str, dict] = {}
        self._key: bytes | None = None
        self._load_file()
        self._auto_lock_seconds = auto_lock_seconds
        self._last_activity: float = 0.0

    def _touch(self) -> None:
        self._last_activity = time.monotonic()

    def _load_file(self) -> None:
        if not self._data_path.exists():
            self._data_path.parent.mkdir(parents=True, exist_ok=True)
            self._entries = {}
            self._save_file()
            return

        with open(self._data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._entries = data.get("entries", {})

    def _restrict_permissions(self) -> None:
        if not self._data_path.exists():
            return
        username = getpass.getuser()
        try:
            subprocess.run(
                ["icacls", str(self._data_path), "/inheritance:r"],
                check=False, capture_output=True,
            )
            subprocess.run(
                ["icacls", str(self._data_path), "/grant:r", f"{username}:(F)"],
                check=False, capture_output=True,
            )
            subprocess.run(
                ["icacls", str(self._data_path), "/grant:r", "SYSTEM:(F)"],
                check=False, capture_output=True,
            )
        except Exception:
            pass

    def _save_file(self) -> None:
        with open(self._data_path, "w", encoding="utf-8") as f:
            json.dump({"entries": self._entries}, f, ensure_ascii=False, indent=2)
        self._restrict_permissions()

    def _derive_key(self, master_password: str, salt: bytes) -> bytes:
        return hash_secret_raw(
            secret=master_password.encode("utf-8"),
            salt=salt,
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            type=Type.ID,
        )

    def unlock(self, master_password: str) -> dict:
        if not self._entries:
            self._master_password = master_password
            self._key = None
            self._touch()
            return {"success": True, "unlocked": True, "empty": True}

        first_key = next(iter(self._entries))
        entry = self._entries[first_key]
        if not isinstance(entry, dict):
            return {"success": False, "error": "vault.json имеет устаревший формат; удалите его, чтобы выполнить повторную инициализацию."}

        salt = bytes.fromhex(entry["salt"])
        key = self._derive_key(master_password, salt)
        try:
            aes = AESGCM(key)
            aes.decrypt(
                bytes.fromhex(entry["nonce"]),
                bytes.fromhex(entry["ciphertext"]),
                None,
            )
        except Exception:
            return {"success": False, "error": "неверный мастер-пароль"}

        self._master_password = master_password
        self._key = key
        self._touch()
        return {"success": True, "unlocked": True}

    def lock(self) -> dict:
        self._key = None
        if hasattr(self, "_master_password"):
            del self._master_password
        return {"success": True, "locked": True}

    def _require_unlocked(self) -> None:
        if not hasattr(self, "_master_password"):
            raise VaultLockedError("хранилище заблокировано; сначала вызовите функцию разблокировки")
        if time.monotonic() - self._last_activity > self._auto_lock_seconds:
            self.lock()
            raise VaultLockedError("хранилище автоматически заблокировано из-за бездействия")

    def list_keys(self) -> dict:
        self._require_unlocked()
        self._touch()
        return {"success": True, "keys": sorted(self._entries.keys())}

    def set(self, key: str, password: str) -> dict:
        self._require_unlocked()
        self._touch()
        key = key.strip().lower()
        if not key or not password:
            return {"success": False, "error": "требуются ключ и пароль"}

        salt = os.urandom(16)
        nonce = os.urandom(12)
        derived = self._derive_key(self._master_password, salt)
        aes = AESGCM(derived)
        ciphertext = aes.encrypt(nonce, password.encode("utf-8"), None)

        self._entries[key] = {
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
        }
        self._save_file()
        return {"success": True, "key": key}

    def get(self, key: str) -> dict:
        self._require_unlocked()
        self._touch()
        key = key.strip().lower()
        if key not in self._entries:
            return {"success": False, "error": f"ключ '{key}' не найден"}

        entry = self._entries[key]
        salt = bytes.fromhex(entry["salt"])
        nonce = bytes.fromhex(entry["nonce"])
        ciphertext = bytes.fromhex(entry["ciphertext"])

        derived = self._derive_key(self._master_password, salt)
        aes = AESGCM(derived)
        try:
            plaintext = aes.decrypt(nonce, ciphertext, None)
        except Exception:
            return {"success": False, "error": "расшифровка не удалась (повреждённые данные?)"}

        return {"success": True, "key": key, "password": plaintext.decode("utf-8")}

    def delete(self, key: str) -> dict:
        self._require_unlocked()
        self._touch()
        key = key.strip().lower()
        if key not in self._entries:
            return {"success": False, "error": f"ключ '{key}' не найден"}

        del self._entries[key]
        self._save_file()
        return {"success": True, "deleted": key}


vault = Vault(VAULT_FILE)