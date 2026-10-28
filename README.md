# Shpagra Core
Shpagra Core - это локальный ассистент для Windows, вдохновлённый Джарвисом. Он работает как фоновый сервер, который следит за состоянием компьютера, запускает программы и скрипты, хранит пароли и слушается голосовых команд - всё без интернета и облаков.

## Возможности
### 🖥️ Мониторинг системы
Отслеживание CPU, RAM, диска, сети. История метрик раз в 5 минут сохраняется в JSON.

### ⚡ Быстрый запуск
Добавляйте программы в список и открывайте их одной командой.

### 📜 Запуск скриптов
Загружайте .bat, .cmd, .ps1 файлы и выполняйте их (в том числе от имени администратора).

### 🔐 Менеджер паролей
Локальное хранилище с мастер-паролем. Шифрование AES-256-GCM + Argon2id. Копирование паролей в буфер обмена.

### 🎙️ Голосовое управление
Офлайн-распознавание речи (Vosk) и синтез (pyttsx3). Активация по кодовому слову («Джарвис»).

### 🌐 Поиск в браузере
Голосовая команда «найди в гугле...» открывает поисковый запрос.

### 🔧 Модульность
Каждый модуль можно включить или выключить на лету через API.

## Технологии
- Python 3.12+
- FastAPI + Uvicorn - HTTP/WebSocket сервер.
- Vosk - офлайн-распознавание речи.
- pyttsx3 - синтез речи (SAPI5).
- cryptography — шифрование паролей.
- psutil — мониторинг системы.
- pyperclip — буфер обмена.

## Установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/yourname/shpagra-core.git
cd shpagra-core
```
2. Создайте виртуальное окружение и установите зависимости:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
3. Скачайте модель Vosk:
Скачайте русскую модель (vosk-model-small-ru-0.22) с официального сайта
Распакуйте её в data/models/vosk-model-small-ru-0.22/.
Настройте config.json:
```json
{
  "monitor": {
    "history_interval_seconds": 300
  },
  "voice": {
    "model_path": "data/models/vosk-model-small-ru-0.22",
    "sample_rate": 16000,
    "block_size": 8000,
    "wake_words": ["джарвис", "дарвис", "шпакс"]
  }
}
```
4. Запустите сервер:
```bash
uvicorn main:app --host 127.0.0.1 --port 8765
```

## Быстрый старт
1. Включите модули:
```bash
curl -X POST http://127.0.0.1:8765/modules/monitor/enable
curl -X POST http://127.0.0.1:8765/modules/launcher/enable
curl -X POST http://127.0.0.1:8765/modules/vault/enable
curl -X POST http://127.0.0.1:8765/modules/voice/enable
curl -X POST http://127.0.0.1:8765/modules/scripts/enable
```
2. Добавьте программу:
```bash
curl -X POST http://127.0.0.1:8765/launcher/add \
  -H "Content-Type: application/json" \
  -d '{"name": "notepad", "path": "C:\\Windows\\notepad.exe"}'
```
3. Запустите прослушивание:
```bash
curl -X POST http://127.0.0.1:8765/voice/start
```
4. Скажите: «Джарвис, открой блокнот»

## Структура проекта
```text
shpagra-core/
├── main.py                    # Точка входа
├── config.json                # Настройки
├── requirements.txt
└── core/
    ├── paths.py               # Управление путями (работает и в .exe)
    ├── registry.py            # Состояние модулей (вкл/выкл)
    ├── decorators.py          # @require_module
    ├── api/                   # HTTP-эндпоинты
    │   ├── modules.py
    │   ├── monitor.py
    │   ├── launcher.py
    │   ├── vault.py
    │   ├── script_runner.py
    │   └── voice.py
    └── services/              # Бизнес-логика
        ├── monitor.py         # psutil + история
        ├── launcher.py        # Запуск программ
        ├── vault.py           # AES-GCM + Argon2id
        ├── script_runner.py   # Загрузка/запуск скриптов
        ├── voice.py           # Vosk + маршрутизация
        ├── voice_commands.py  # CRUD для голосовых команд
        ├── voice_actions.py   # @voice_action
        └── tts.py             # Синтез речи
```

## Документация API
После запуска ядра документация доступна по адресу: `http://127.0.0.1:8765/docs`

## Основные эндпоинты

| Метод | Путь | Описание |
| :--- | :--- | :--- |
| **GET** | `/modules` | Список модулей и их состояние |
| **POST** | `/modules/{name}/enable` | Включить модуль |
| **POST** | `/modules/{name}/disable` | Выключить модуль |
| **GET** | `/monitor/snapshot` | Текущий снимок метрик |
| **GET** | `/monitor/history?days=1` | История метрик |
| **GET** | `/monitor/stream` | WebSocket-поток метрик |
| **POST** | `/launcher/add` | Добавить программу |
| **POST** | `/launcher/open/{name}` | Открыть программу |
| **POST** | `/vault/unlock` | Разблокировать хранилище |
| **GET** | `/vault/get/{key}` | Получить пароль |
| **POST** | `/scripts/upload` | Загрузить скрипт |
| **POST** | `/scripts/run/{name}` | Запустить скрипт |
| **POST** | `/voice/start` | Начать прослушивание |
| **GET** | `/voice/commands` | Список голосовых команд |

## Безопасность
Пароли хранятся в зашифрованном виде (vault.json). Мастер-пароль вводится при разблокировке и живёт только в памяти.
Данные (пароли, история, скрипты) лежат в папке data/ и не должны попадать в git (см. .gitignore).
Сервер слушает только 127.0.0.1 и недоступен извне.

## Сборка в .exe
1. Установите PyInstaller:
```bash
pip install pyinstaller
```
2. Соберите проект:
```bash
pyinstaller --onefile --name shpagra-core main.py
```
3. Скопируйте dist/shpagra-core.exe в отдельную папку и положите рядом:
 - `config.json`
- папку `data/` (с моделями и файлами)
Благодаря `core/paths.py` программа будет искать данные рядом с .exe, а не внутри временной папки.

## Вклад
Проект создан для личного использования, но если у вас есть идеи - создавайте Issue или Pull Request.

## Лицензия
MIT. Делайте что хотите, но не забывайте о безопасности своих данных.
