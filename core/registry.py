import json
from pathlib import Path


_DEFAULT_STATE = {
    "monitor": True,
    "launcher": True,
    "voice": False,
    "vault": False,
}


class ModuleRegistry:
    def __init__(self, data_path: Path):
        self._data_path = data_path
        self._state: dict[str, bool] = dict(_DEFAULT_STATE)
        self._load()

    def _load(self) -> None:
        if not self._data_path.exists():
            self._data_path.parent.mkdir(parents=True, exist_ok=True)
            self._save()
            return

        try:
            with open(self._data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._state = dict(_DEFAULT_STATE)
            self._save()
            return

        saved = data.get("modules", {})
        for name, default in _DEFAULT_STATE.items():
            value = saved.get(name, default)
            self._state[name] = bool(value)

        if set(saved.keys()) - set(_DEFAULT_STATE.keys()):
            self._save()

    def _save(self) -> None:
        with open(self._data_path, "w", encoding="utf-8") as f:
            json.dump({"modules": self._state}, f, ensure_ascii=False, indent=2)

    def is_enabled(self, name: str) -> bool:
        return self._state.get(name, False)

    def set_enabled(self, name: str, enabled: bool) -> dict:
        if name not in self._state:
            return {"success": False, "error": f"неизвестный модуль: {name}"}
        self._state[name] = bool(enabled)
        self._save()
        return {"success": True, "module": name, "enabled": self._state[name]}

    def all(self) -> dict:
        return dict(self._state)


_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "modules.json"
registry = ModuleRegistry(_DATA_PATH)