import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
HISTORY_DIR = DATA_DIR / "history"
SCRIPTS_DIR = DATA_DIR / "scripts"
MODELS_DIR = DATA_DIR / "models"

MODULES_FILE = DATA_DIR / "modules.json"
PROGRAMS_FILE = DATA_DIR / "programs.json"
VAULT_FILE = DATA_DIR / "vault.json"
VOICE_COMMANDS_FILE = DATA_DIR / "voice_commands.json"
SCRIPTS_REGISTRY_FILE = DATA_DIR / "scripts_registry.json"

CONFIG_PATH = BASE_DIR / "config.json"

for _dir in (DATA_DIR, HISTORY_DIR, SCRIPTS_DIR, MODELS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)