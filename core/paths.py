import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
HISTORY_DIR = DATA_DIR / "history"

MODULES_FILE = DATA_DIR / "modules.json"
PROGRAMS_FILE = DATA_DIR / "programs.json"
VAULT_FILE = DATA_DIR / "vault.json"

CONFIG_PATH = BASE_DIR / "config.json"