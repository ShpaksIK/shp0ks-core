import ctypes
import subprocess
import uuid
from pathlib import Path
from core.paths import DATA_DIR

SCRIPTS_DIR = DATA_DIR / "scripts"
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

class ScriptRunner:
    async def save_upload(self, file) -> dict:
        """Сохраняет файл и возвращает путь. Не выполняет."""
        original_name = Path(file.filename).name
        file_path = SCRIPTS_DIR / original_name
        
        if file_path.exists():
            safe_name = f"{uuid.uuid4().hex[:8]}_{original_name}"
            file_path = SCRIPTS_DIR / safe_name

        with file_path.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
                
        return {"success": True, "filename": file_path.name}

    def list_scripts(self) -> dict:
        """Возвращает список загруженных скриптов."""
        scripts = []
        for path in SCRIPTS_DIR.glob("*.*"):
            if path.is_file() and path.suffix.lower() in ('.bat', '.cmd', '.ps1', '.py'):
                scripts.append({
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "modified": path.stat().st_mtime
                })

        scripts.sort(key=lambda x: x["modified"], reverse=True)
        return {"success": True, "scripts": scripts}

    def run_existing(self, name: str, as_admin: bool = False) -> dict:
        """Запускает уже загруженный скрипт по имени."""
        file_path = (SCRIPTS_DIR / name).resolve()
        if not file_path.is_file() or SCRIPTS_DIR.resolve() not in file_path.parents:
            return {"success": False, "error": "Скрипт не найден"}
        
        return self._execute(file_path, as_admin)

    def delete_script(self, name: str) -> dict:
        """Удаляет скрипт по имени."""
        file_path = (SCRIPTS_DIR / name).resolve()
        if not file_path.is_file() or SCRIPTS_DIR.resolve() not in file_path.parents:
            return {"success": False, "error": "Скрипт не найден"}
            
        try:
            file_path.unlink()
            return {"success": True, "deleted": name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def clear_scripts(self) -> dict:
        """Удаляет все файлы скриптов из папки."""
        deleted_count = 0
        errors = []
        
        for path in SCRIPTS_DIR.iterdir():
            if path.is_file():
                try:
                    path.unlink()
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"{path.name}: {e}")
                    
        if errors:
            return {"success": False, "deleted_count": deleted_count, "errors": errors}
            
        return {"success": True, "deleted_count": deleted_count}

    def _execute(self, file_path: Path, as_admin: bool) -> dict:
        """Внутренний метод для запуска (обычный или от админа)."""
        if as_admin:
            return self._run_as_admin(file_path)
        return self._run_normal(file_path)

    def _run_as_admin(self, file_path: Path):
        """Запускает скрипт от имени администратора через UAC."""
        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                "cmd.exe",
                f'/c "{file_path}"',
                str(file_path.parent),
                1
            )
            success = result > 32
            if success:
                return {
                    "success": True,
                    "message": "Скрипт запущен от имени администратора (возможно, появлялся запрос UAC). Вывод не перехватывается."
                }
            else:
                return {"success": False, "error": f"Не удалось повысить права. Код ошибки: {result}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_normal(self, file_path: Path):
        try:
            result = subprocess.run(
                [str(file_path)],
                capture_output=True,
                text=True,
                shell=True,
                timeout=30,
                stdin=subprocess.DEVNULL,
                encoding='utf-8',
                errors='replace'
            )
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Время выполнения скрипта истекло"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        

script_runner = ScriptRunner()