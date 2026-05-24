import json
import os
import threading
import time
from dataclasses import dataclass
from multiprocessing import Event, Process, Queue

try:
    from source_repository import SourceRepository
except Exception:
    try:
        from backend.source_repository import SourceRepository
    except Exception:
        SourceRepository = None

try:
    from RandomDataGen.worker import run_worker
except Exception:
    from backend.RandomDataGen.worker import run_worker


@dataclass
class WorkerState:
    process: Process
    stop_event: Event
    source_id: str
    camera_id: str
    managed: bool
    started_at: float
    restart_count: int = 0


class SimulatorSupervisor:
    def __init__(self, api_base_url="http://127.0.0.1:8000", refresh_seconds=15, worker_interval_seconds=5, max_restarts=5):
        self.api_base_url = api_base_url
        self.refresh_seconds = refresh_seconds
        self.worker_interval_seconds = worker_interval_seconds
        self.max_restarts = max_restarts

        self.status_queue = Queue()
        self._workers = {}
        self._last_status = {}

        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        self.backend_dir = os.path.dirname(os.path.abspath(__file__))
        self.sources_file = os.path.join(self.backend_dir, "sources.json")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        with self._lock:
            for camera_id in list(self._workers.keys()):
                self._stop_worker_locked(camera_id)

    def list_workers(self):
        self._drain_status_queue()
        with self._lock:
            out = []
            for camera_id, state in self._workers.items():
                status = self._last_status.get(camera_id, {})
                out.append({
                    "camera_id": camera_id,
                    "source_id": state.source_id,
                    "pid": state.process.pid,
                    "alive": state.process.is_alive(),
                    "managed": state.managed,
                    "restart_count": state.restart_count,
                    "started_at": state.started_at,
                    "last_status": status,
                })
            return out

    def start_worker(self, camera_id, source_id=None, managed=False):
        with self._lock:
            if camera_id in self._workers and self._workers[camera_id].process.is_alive():
                return {"status": "already_running", "camera_id": camera_id}
            return self._start_worker_locked(camera_id, source_id or camera_id, managed)

    def stop_worker(self, camera_id):
        with self._lock:
            if camera_id not in self._workers:
                return {"status": "not_found", "camera_id": camera_id}
            self._stop_worker_locked(camera_id)
            return {"status": "stopped", "camera_id": camera_id}

    def restart_worker(self, camera_id):
        with self._lock:
            state = self._workers.get(camera_id)
            if not state:
                return {"status": "not_found", "camera_id": camera_id}
            source_id = state.source_id
            managed = state.managed
            self._stop_worker_locked(camera_id)
            return self._start_worker_locked(camera_id, source_id, managed)

    def _loop(self):
        while self._running:
            self._drain_status_queue()
            self._reconcile_sources()
            self._heal_workers()
            time.sleep(self.refresh_seconds)

    def _drain_status_queue(self):
        while True:
            try:
                msg = self.status_queue.get_nowait()
                camera_id = msg.get("camera_id")
                if camera_id:
                    self._last_status[camera_id] = msg
            except Exception:
                break

    def _load_generated_sources(self):
        sources = self._from_source_repository()
        if not sources:
            sources = self._from_sources_json()
        return {s["camera_id"]: s for s in sources if s.get("camera_id")}

    def _from_source_repository(self):
        if SourceRepository is None:
            return []
        try:
            repo = SourceRepository()
            data = repo.list_sources()
            return [
                {
                    "source_id": str(s.get("id")),
                    "camera_id": s.get("camera_id"),
                }
                for s in data
                if (s.get("mode") == "generate" or s.get("source_type") == "generate") and s.get("camera_id")
            ]
        except Exception:
            return []

    def _from_sources_json(self):
        if not os.path.exists(self.sources_file):
            return []
        try:
            with open(self.sources_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [
                {
                    "source_id": str(s.get("id") or s.get("camera_id")),
                    "camera_id": s.get("camera_id"),
                }
                for s in data
                if s.get("camera_id") and (s.get("mode") == "generate" or s.get("source_type") == "generate" or str(s.get("stream_url", "")).startswith("sim://"))
            ]
        except Exception:
            return []

    def _reconcile_sources(self):
        desired = self._load_generated_sources()
        with self._lock:
            current = set(self._workers.keys())
            wanted = set(desired.keys())

            for camera_id in wanted - current:
                src = desired[camera_id]
                self._start_worker_locked(camera_id, src.get("source_id", camera_id), managed=True)

            for camera_id in current - wanted:
                state = self._workers.get(camera_id)
                if state and state.managed:
                    self._stop_worker_locked(camera_id)

    def _heal_workers(self):
        with self._lock:
            for camera_id, state in list(self._workers.items()):
                if state.process.is_alive():
                    continue

                if state.restart_count >= self.max_restarts:
                    continue

                state.restart_count += 1
                self._start_worker_locked(
                    camera_id=camera_id,
                    source_id=state.source_id,
                    managed=state.managed,
                    restart_count=state.restart_count,
                )

    def _start_worker_locked(self, camera_id, source_id, managed, restart_count=0):
        stop_event = Event()
        process = Process(
            target=run_worker,
            args=(camera_id, source_id, stop_event, self.status_queue, self.api_base_url, self.worker_interval_seconds),
            daemon=True,
        )
        process.start()
        self._workers[camera_id] = WorkerState(
            process=process,
            stop_event=stop_event,
            source_id=source_id,
            camera_id=camera_id,
            managed=managed,
            started_at=time.time(),
            restart_count=restart_count,
        )
        return {"status": "started", "camera_id": camera_id, "pid": process.pid}

    def _stop_worker_locked(self, camera_id):
        state = self._workers.pop(camera_id, None)
        if not state:
            return
        state.stop_event.set()
        state.process.join(timeout=3)
        if state.process.is_alive():
            state.process.terminate()
            state.process.join(timeout=2)
