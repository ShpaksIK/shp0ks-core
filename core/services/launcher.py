import json
import subprocess
from pathlib import Path

from core.paths import PROGRAMS_FILE


class Launcher:
    def __init__(self, data_path: Path):
        self._data_path = data_path
        self._programs: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self._data_path.exists():
            self._data_path.parent.mkdir(parents=True, exist_ok=True)
            self._programs = {}
            self._save()
            return

        with open(self._data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._programs = data.get("programs", {})

    def _save(self) -> None:
        with open(self._data_path, "w", encoding="utf-8") as f:
            json.dump({"programs": self._programs}, f, ensure_ascii=False, indent=2)

    def list(self) -> dict:
        return {"success": True, "programs": dict(self._programs)}

    def add(self, name: str, path: str) -> dict:
        name = name.strip().lower()
        path = path.strip()

        if not name or not path:
            return {"success": False, "error": "необходимо указать имя и путь"}

        if name in self._programs:
            return {"success": False, "error": f"программа '{name}' уже существует"}

        if not Path(path).exists():
            return {"success": False, "error": f"путь не найден: {path}"}

        self._programs[name] = path
        self._save()
        return {"success": True, "program": name, "path": path}

    def remove(self, name: str) -> dict:
        name = name.strip().lower()
        if name not in self._programs:
            return {"success": False, "error": f"программа '{name}' не найдена"}

        del self._programs[name]
        self._save()
        return {"success": True, "removed": name}

    def open(self, name: str) -> dict:
        name = name.strip().lower()
        if name not in self._programs:
            return {"success": False, "error": f"программа '{name}' не найдена"}

        path = self._programs[name]
        try:
            subprocess.Popen(path, shell=False)
            return {"success": True, "program": name}
        except FileNotFoundError:
            del self._programs[name]
            self._save()
            return {
                "success": False,
                "error": f"исполняемый файл не найден: {path}",
                "removed": name,
            }
        except OSError as e:
            del self._programs[name]
            self._save()
            return {
                "success": False,
                "error": f"не удалось запустить: {e}",
                "removed": name,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


launcher = Launcher(PROGRAMS_FILE)