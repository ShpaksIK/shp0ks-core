import psutil
import time
import json
from datetime import datetime, date
from pathlib import Path

from core.paths import HISTORY_DIR


class Monitor:
    def __init__(self, history_dir: Path, history_retention_days: int = 7):
        self._last_net = None
        self._last_net_time = None
        self._history_dir = history_dir
        self._history_retention_days = history_retention_days
        self._history_dir.mkdir(parents=True, exist_ok=True)

        psutil.cpu_percent(interval=None)

    def _net_snapshot(self):
        now = time.monotonic()
        counters = psutil.net_io_counters()
        result = {
            "bytes_sent": counters.bytes_sent,
            "bytes_recv": counters.bytes_recv,
            "errin": counters.errin,
            "errout": counters.errout,
            "dropin": counters.dropin,
            "dropout": counters.dropout,
            "bytes_total_per_sec": None,
        }
        if self._last_net is not None and self._last_net_time is not None:
            elapsed = now - self._last_net_time
            if elapsed > 0:
                sent_delta = counters.bytes_sent - self._last_net.bytes_sent
                recv_delta = counters.bytes_recv - self._last_net.bytes_recv
                result["bytes_total_per_sec"] = round((sent_delta + recv_delta) / elapsed, 2)
        self._last_net = counters
        self._last_net_time = now
        return result

    def _top_processes(self, n=3):
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_percent"]):
            try:
                info = p.info
                # cpu_percent без interval может быть 0.0, но при повторных вызовах стабилизируется
                cpu = p.cpu_percent(interval=None)
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": round(cpu, 2),
                    "memory_percent": round(info["memory_percent"] or 0.0, 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        top_cpu = sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:n]
        top_mem = sorted(procs, key=lambda x: x["memory_percent"], reverse=True)[:n]
        return {"top_cpu": top_cpu, "top_mem": top_mem}

    def get_snapshot(self) -> dict:
        cpu_times = psutil.cpu_times()
        freq = psutil.cpu_freq()

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        disk = psutil.disk_usage("C:\\")

        net = self._net_snapshot()

        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": psutil.cpu_percent(interval=None),
                "cores_logical": psutil.cpu_count(logical=True),
                "cores_physical": psutil.cpu_count(logical=False),
                "freq_mhz": round(freq.current, 0) if freq and freq.current else None,
                "queue_length": None,  # TODO: PDH System\Processor Queue Length
                "times": {
                    "user": round(cpu_times.user, 2),
                    "system": round(cpu_times.system, 2),
                    "idle": round(cpu_times.idle, 2),
                },
            },
            "memory": {
                "total_gb": round(memory.total / (1024 ** 3), 2),
                "available_gb": round(memory.available / (1024 ** 3), 2),
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "percent": memory.percent,
                # "committed" и "cache" на Windows через psutil недоступны напрямую
                "committed_gb": None,  # TODO: PDH Memory\Committed Bytes
                "cache_gb": None,      # TODO: PDH Memory\Cache Bytes
                "pages_per_sec": None, # TODO: PDH Memory\Pages/sec
                "swap": {
                    "total_gb": round(swap.total / (1024 ** 3), 2),
                    "used_gb": round(swap.used / (1024 ** 3), 2),
                    "percent": swap.percent,
                },
            },
            "disk": {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "percent": disk.percent,
                # latency и queue length через psutil на Windows не получить
                "avg_read_latency_ms": None,   # TODO: PDH PhysicalDisk\Avg. Disk sec/Read
                "avg_write_latency_ms": None,  # TODO: PDH PhysicalDisk\Avg. Disk sec/Write
                "queue_length": None,          # TODO: PDH PhysicalDisk\Current Disk Queue Length
            },
            "network": net,
            "processes": self._top_processes(3),
        }

    def _history_path(self, day: date = None) -> Path:
        day = day or date.today()
        return self._history_dir / f"metrics_{day.isoformat()}.json"

    def save_snapshot(self) -> dict:
        """Сохраняет текущий снимок в файл за сегодня."""
        snapshot = self.get_snapshot()
        path = self._history_path()

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, OSError):
                history = []
        else:
            history = []

        history.append(snapshot)

        max_per_file = 1000
        if len(history) > max_per_file:
            history = history[-max_per_file:]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        return {"success": True, "saved": path.name, "count": len(history)}

    def get_history(self, days: int = 1) -> dict:
        """Возвращает снимки за последние N дней (включая сегодня)."""
        result = []
        today = date.today()

        for offset in range(days):
            day = date.fromordinal(today.toordinal() - offset)
            path = self._history_path(day)
            if not path.exists():
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    result.extend(json.load(f))
            except (json.JSONDecodeError, OSError):
                continue

        result.sort(key=lambda x: x.get("timestamp", ""))
        return {"success": True, "count": len(result), "snapshots": result}

    def cleanup_history(self) -> dict:
        """Удаляет файлы истории старше retention_days."""
        removed = []
        cutoff = date.today().toordinal() - self._history_retention_days

        for path in self._history_dir.glob("metrics_*.json"):
            try:
                day_str = path.stem.replace("metrics_", "")
                day = date.fromisoformat(day_str)
                if day.toordinal() < cutoff:
                    path.unlink()
                    removed.append(path.name)
            except (ValueError, OSError):
                continue

        return {"success": True, "removed": removed}


monitor = Monitor(HISTORY_DIR)