import json
import queue
import threading
import time
import pyperclip

from pathlib import Path
import sounddevice as sd
from vosk import Model, KaldiRecognizer

from core.services.tts import tts
from core.registry import registry
from core.paths import DATA_DIR, CONFIG_PATH, VOICE_COMMANDS_FILE
from core.services.launcher import launcher
from core.services.script_runner import script_runner
from core.services.vault import vault, VaultLockedError

def _load_voice_config() -> dict:
    """Чтение настроек из config.json."""
    defaults = {
        "model_path": str(DATA_DIR / "models" / "vosk-model-small-ru-0.22"),
        "sample_rate": 16000,
        "block_size": 8000,
        "wake_words": ["джарвис", "дарвис", "джарвиз", "шпакс", "шпокс"],
        "default_commands": {}
    }
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            voice_cfg = config.get("voice", {})
            
            defaults.update({
                "model_path": voice_cfg.get("model_path", defaults["model_path"]),
                "sample_rate": voice_cfg.get("sample_rate", defaults["sample_rate"]),
                "block_size": voice_cfg.get("block_size", defaults["block_size"]),
                "wake_words": voice_cfg.get("wake_words", defaults["wake_words"]),
                "default_commands": voice_cfg.get("default_commands", defaults["default_commands"]),
            })
    except (json.JSONDecodeError, OSError):
        pass
        
    return defaults

class Voice:
    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._model: Model | None = None
        self._commands: dict = {}
        self._commands_mtime: float = 0.0

        self._config = _load_voice_config()

        p = Path(self._config["model_path"])
        self._model_path = p if p.is_absolute() else CONFIG_PATH.parent / p

        self._sample_rate = self._config["sample_rate"]
        self._block_size = self._config["block_size"]
        self._wake_words = self._config["wake_words"]
        self._default_commands = self._config["default_commands"]

        self._load_commands(force=True)

    def _load_commands(self, force: bool = False) -> None:
        """Читает файл команд, если он изменился (или force=True)."""
        if not VOICE_COMMANDS_FILE.exists():
            VOICE_COMMANDS_FILE.parent.mkdir(parents=True, exist_ok=True)
            VOICE_COMMANDS_FILE.write_text(
                json.dumps(self._default_commands, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._commands = dict(self._default_commands)
            self._commands_mtime = VOICE_COMMANDS_FILE.stat().st_mtime
            return

        mtime = VOICE_COMMANDS_FILE.stat().st_mtime
        if not force and mtime == self._commands_mtime:
            return

        try:
            with open(VOICE_COMMANDS_FILE, "r", encoding="utf-8") as f:
                self._commands = json.load(f)
            self._commands_mtime = mtime
        except (json.JSONDecodeError, OSError):
            pass

    def _save_commands(self) -> None:
        with open(VOICE_COMMANDS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._commands, f, ensure_ascii=False, indent=2)
        self._commands_mtime = VOICE_COMMANDS_FILE.stat().st_mtime

    def list_commands(self) -> dict:
        self._load_commands()
        return {"success": True, "commands": self._commands}

    def add_command(self, phrase: str, action: str, arg: str | None, as_admin: bool = False) -> dict:
        phrase = phrase.strip().lower()
        if not phrase or not action:
            return {"success": False, "error": "требуются фраза и действие"}

        self._load_commands()
        if phrase in self._commands:
            return {"success": False, "error": f"фраза '{phrase}' уже существует"}

        # Сохраняем as_admin в словарь команды
        self._commands[phrase] = {"action": action, "arg": arg, "as_admin": as_admin}
        self._save_commands()
        return {"success": True, "phrase": phrase}

    def update_command(self, phrase: str, action: str, arg: str | None, as_admin: bool = False) -> dict:
        phrase = phrase.strip().lower()
        self._load_commands()
        if phrase not in self._commands:
            return {"success": False, "error": f"фраза '{phrase}' не найдена"}

        self._commands[phrase] = {"action": action, "arg": arg, "as_admin": as_admin}
        self._save_commands()
        return {"success": True, "phrase": phrase}

    def delete_command(self, phrase: str) -> dict:
        phrase = phrase.strip().lower()
        self._load_commands()
        if phrase not in self._commands:
            return {"success": False, "error": f"фраза '{phrase}' не найдена"}

        del self._commands[phrase]
        self._save_commands()
        return {"success": True, "deleted": phrase}

    def start(self) -> dict:
        if self._running:
            return {"success": False, "error": "голосовой режим уже запущен"}
        if not self._model_path.exists():
            return {"success": False, "error": f"модель не найдена: {self._model_path}"}

        try:
            self._model = Model(str(self._model_path))
        except Exception as e:
            return {"success": False, "error": f"не удалось загрузить модель: {e}"}

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        return {"success": True, "message": "началось прослушивание голоса"}

    def stop(self) -> dict:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        return {"success": True, "message": "прослушивание голоса остановлено"}

    def status(self) -> dict:
        return {"success": True, "running": self._running}

    def _listen_loop(self) -> None:
        audio_queue: queue.Queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            audio_queue.put(bytes(indata))

        try:
            with sd.RawInputStream(
                samplerate=self._sample_rate,
                blocksize=self._block_size,
                dtype="int16",
                channels=1,
                callback=callback,
            ):
                rec = KaldiRecognizer(self._model, self._sample_rate)
                rec.SetWords(True)

                while self._running:
                    if not registry.is_enabled("voice"):
                        time.sleep(1)
                        continue

                    data = audio_queue.get()
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").strip().lower()
                        if text:
                            self._handle_command(text)
        except Exception:
            self._running = False

    def _handle_command(self, text: str) -> None:
        self._load_commands()

        found_wake_word = None
        for w in self._wake_words:
            if w in text:
                found_wake_word = w
                break

        if not found_wake_word:
            return

        clean_text = text.replace(found_wake_word, "").strip(" ,.!?")

        if not clean_text:
            tts.say("Слушаю")
            return

        action = None
        arg = None
        sorted_commands = sorted(self._commands.items(), key=lambda x: len(x[0]), reverse=True)
        
        for phrase, cmd in sorted_commands:
            if phrase in clean_text:
                action = cmd.get("action")
                arg = cmd.get("arg")
                as_admin = cmd.get("as_admin", False)
                break

        if action is None:
            tts.say("Команда не распознана")
            return

        if action == "launcher_open":
            res = launcher.open(arg)
            if res.get("success"):
                tts.say(f"Открываю {arg}")
            else:
                tts.say(f"Не удалось открыть {arg}")

        elif action == "vault_get":
            try:
                res = vault.get(arg)
                if res.get("success"):
                    password = res['password']
                    pyperclip.copy(password)
                    tts.say(f"Пароль скопирован")
                else:
                    tts.say("Не удалось получить пароль")
            except VaultLockedError:
                tts.say("Хранилище заблокировано. Откройте его через интерфейс.")

        elif action == "vault_lock":
            vault.lock()
            tts.say("Хранилище заблокировано")

        elif action == "script_run":
            # Если в JSON arg указан явно (например, "arg": "test.bat"), используем его
            # Если arg = null, значит мы должны взять остаток текста после фразы-триггера
            alias_to_run = arg

            if not alias_to_run:
                # Убираем из текста саму фразу-триггер и лишние знаки
                alias_to_run = clean_text.replace(phrase, "").strip(" ,.!?")

            if not alias_to_run:
                tts.say("Какой скрипт запустить?")
                return
            
            res = script_runner.run_by_alias(alias_to_run, as_admin=as_admin)
            if res.get("success"):
                tts.say(f"Запускаю скрипт {alias_to_run}")
            else:
                tts.say(f"Ошибка: {res.get('error')}")


voice = Voice()