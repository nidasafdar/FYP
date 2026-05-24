from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from urllib.parse import urlparse
from datetime import datetime, timedelta
import os
import sys
import json
import threading
import random

# Ensure project root and Backend on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path: sys.path.append(ROOT)
if BACKEND_DIR not in sys.path: sys.path.append(BACKEND_DIR)

try:
    from backend.analytics_engine import AnalyticsEngine
except Exception:
    # fallback import if package context differs
    try:
        from analytics_engine import AnalyticsEngine
    except Exception as e:
        AnalyticsEngine = None

try:
    from backend.source_repository import SourceRepository, SourceRepositoryError
except Exception:
    try:
        from source_repository import SourceRepository, SourceRepositoryError
    except Exception:
        SourceRepository = None
        SourceRepositoryError = Exception

try:
    from backend.db_handler import DBHandler
except Exception:
    try:
        from db_handler import DBHandler
    except Exception:
        DBHandler = None

try:
    from backend.simulator_supervisor import SimulatorSupervisor
except Exception:
    try:
        from simulator_supervisor import SimulatorSupervisor
    except Exception:
        SimulatorSupervisor = None

try:
    from backend.stream_supervisor import StreamSupervisor
except Exception:
    try:
        from stream_supervisor import StreamSupervisor
    except Exception:
        StreamSupervisor = None

app = FastAPI(title="FYP Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SOURCES_FILE = os.path.join(BACKEND_DIR, "sources.json")
_engine = None
_engine_lock = threading.Lock()
_source_repository = None
_supervisor = None
_stream_supervisor = None

class SourceCreate(BaseModel):
    title: str
    description: str
    mode: str = "generate"
    streamUrl: Optional[str] = None
    stream_url: Optional[str] = None


class SimulatorIngest(BaseModel):
    source_id: Optional[str] = None
    camera_id: str
    timestamp: Optional[str] = None
    incoming_count: int = 0
    outgoing_count: int = 0
    session_id: Optional[str] = None


@app.on_event("startup")
def startup_event():
    global _engine, _source_repository, _supervisor, _stream_supervisor
    if AnalyticsEngine is None:
        print("[WARN] AnalyticsEngine import failed; API will still serve sources but analytics endpoints will return errors.")
    else:
        with _engine_lock:
            if _engine is None:
                _engine = AnalyticsEngine()

    if SourceRepository is None:
        print("[WARN] SourceRepository import failed; source endpoints will be unavailable.")
        return

    try:
        _source_repository = SourceRepository()
    except Exception as e:
        print(f"[WARN] SourceRepository initialization failed: {e}")

    if SimulatorSupervisor is None:
        print("[WARN] SimulatorSupervisor import failed; simulator control endpoints disabled.")
    else:
        try:
            _supervisor = SimulatorSupervisor()
            _supervisor.start()
            print("[SUCCESS] Simulator supervisor started")
        except Exception as e:
            print(f"[WARN] Failed to start simulator supervisor: {e}")

    if StreamSupervisor is None:
        print("[WARN] StreamSupervisor import failed; stream control endpoints disabled.")
    else:
        try:
            _stream_supervisor = StreamSupervisor()
            _stream_supervisor.start()
            print("[SUCCESS] Stream supervisor started")
        except Exception as e:
            print(f"[WARN] Failed to start stream supervisor: {e}")


@app.on_event("shutdown")
def shutdown_event():
    global _supervisor, _stream_supervisor
    if _supervisor is not None:
        try:
            _supervisor.stop()
            print("[SUCCESS] Simulator supervisor stopped")
        except Exception as e:
            print(f"[WARN] Failed to stop simulator supervisor cleanly: {e}")
    if _stream_supervisor is not None:
        try:
            _stream_supervisor.stop()
            print("[SUCCESS] Stream supervisor stopped")
        except Exception as e:
            print(f"[WARN] Failed to stop stream supervisor cleanly: {e}")


def read_sources():
    if not os.path.exists(SOURCES_FILE):
        return []
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def write_sources(sources):
    tmp = SOURCES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2)
    os.replace(tmp, SOURCES_FILE)


def get_source_repository():
    if _source_repository is None:
        raise HTTPException(status_code=503, detail="Supabase source repository unavailable")
    return _source_repository


def get_supervisor():
    if _supervisor is None:
        raise HTTPException(status_code=503, detail="Simulator supervisor unavailable")
    return _supervisor


def get_stream_supervisor():
    if _stream_supervisor is None:
        raise HTTPException(status_code=503, detail="Stream supervisor unavailable")
    return _stream_supervisor


def attach_stream_runtime(sources):
    if _stream_supervisor is None:
        return sources

    status_by_camera = _stream_supervisor.get_status_map()
    enriched = []
    for source in sources:
        item = dict(source)
        if item.get("mode") == "stream" or item.get("source_type") == "stream":
            worker = status_by_camera.get(item.get("camera_id")) or {}
            last_status = worker.get("last_status") or {}
            worker_alive = bool(worker.get("alive"))
            item.update({
                "worker_alive": worker_alive,
                "worker_status": last_status.get("state") or ("running" if worker_alive else "stopped"),
                "last_frame_at": last_status.get("last_frame_at"),
                "last_error": last_status.get("error"),
            })
        enriched.append(item)
    return enriched


def model_dump(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@app.get("/api/health")
def health():
    return {"status":"ok"}


@app.get("/api/sources")
def get_sources():
    try:
        return attach_stream_runtime(get_source_repository().list_sources())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sources")
def add_source(src: SourceCreate):
    payload = model_dump(src)
    title = payload.get("title", "").strip()
    description = payload.get("description", "").strip()
    mode = payload.get("mode", "generate")
    stream_url = payload.get("streamUrl") or payload.get("stream_url") or ""

    if not title:
        raise HTTPException(status_code=422, detail="Title is required")
    if not description:
        raise HTTPException(status_code=422, detail="Description is required")
    if mode not in ["generate", "stream"]:
        raise HTTPException(status_code=422, detail="Mode must be generate or stream")
    if mode == "stream" and not stream_url.strip():
        raise HTTPException(status_code=422, detail="Stream URL is required")
    if mode == "stream":
        parsed_url = urlparse(stream_url)
        if parsed_url.scheme not in ["http", "https", "rtsp"] or not parsed_url.netloc:
            raise HTTPException(status_code=422, detail="Stream URL must be http, https, or rtsp")

    try:
        source = get_source_repository().create_source(
            title=title,
            description=description,
            mode=mode,
            stream_url=stream_url,
        )
        return {"status":"created", "source": source}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard")
def dashboard(camera: str = None, mode: str = "simulation"):
    if _engine is None:
        raise HTTPException(status_code=503, detail="AnalyticsEngine unavailable")
    cam = camera.strip() if camera and camera.strip() else None
    try:
        data = _engine.get_dashboard_data(camera_id=cam, date_val=None, hour_range=None, mode=mode)
        if data is None:
            raise HTTPException(status_code=500, detail="Analytics engine returned no data")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/camera_comparison")
def camera_comparison(mode: str = "simulation"):
    if _engine is None:
        raise HTTPException(status_code=503, detail="AnalyticsEngine unavailable")
    try:
        return _engine.get_camera_comparison(mode=mode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/frame")
def frame(camera: Optional[str] = None):
    if camera and camera.strip():
        safe_camera = os.path.basename(camera.strip())
        frame_path = os.path.join(BACKEND_DIR, "frames", f"{safe_camera}.jpg")
        if os.path.exists(frame_path):
            return FileResponse(frame_path, media_type="image/jpeg")
        raise HTTPException(status_code=404, detail="Frame not available")

    frame_path = os.path.join(BACKEND_DIR, "current_frame.jpg")
    if os.path.exists(frame_path):
        return FileResponse(frame_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Frame not available")


@app.get("/api/camera/{camera_id}/occupancy")
def get_occupancy(camera_id: str, start_hour: int = 8, end_hour: int = 17, mode: str = "simulation"):
    """
    Get occupancy data for a camera within a time range.
    
    Args:
        camera_id: Camera ID to fetch data for
        start_hour: Start hour of the day (0-23, default 8 for 8am)
        end_hour: End hour of the day (0-23, default 17 for 5pm)
        mode: Data mode - 'simulation', 'simulated', 'live', or 'audit'
    
    Returns:
        {
            "camera_id": str,
            "incoming_count": int,
            "outgoing_count": int,
            "current_occupancy": int,
            "last_updated": str (ISO format),
            "mode": str
        }
    """
    if _engine is None:
        raise HTTPException(status_code=503, detail="AnalyticsEngine unavailable")
    
    if mode not in ["simulation", "simulated", "live", "audit"]:
        raise HTTPException(status_code=422, detail="Mode must be simulation, simulated, live, or audit")
    
    try:
        # Map mode to table name
        table_map = {
            "simulation": "simulated_logs",
            "simulated": "simulated_logs",
            "live": "live_logs",
            "audit": "audit_logs"
        }
        table = table_map[mode]
        
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Define time range (8am to 5pm today)
        hours_range = (start_hour, end_hour)
        
        # Use analytics service to get counts
        incoming = _engine.shared_service.get_total_visitors(
            camera_id=camera_id,
            direction='IN',
            date=today,
            hours=hours_range,
            table=table
        )
        
        outgoing = _engine.shared_service.get_total_visitors(
            camera_id=camera_id,
            direction='OUT',
            date=today,
            hours=hours_range,
            table=table
        )
        
        occupancy = max(0, incoming - outgoing)
        
        return {
            "camera_id": camera_id,
            "incoming_count": incoming,
            "outgoing_count": outgoing,
            "current_occupancy": occupancy,
            "last_updated": datetime.now().isoformat(),
            "mode": mode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulator/ingest")
def ingest_simulator_counts(payload: SimulatorIngest):
    if DBHandler is None:
        raise HTTPException(status_code=503, detail="DBHandler unavailable")

    camera_id = payload.camera_id.strip()
    if not camera_id:
        raise HTTPException(status_code=422, detail="camera_id is required")

    incoming = max(0, int(payload.incoming_count))
    outgoing = max(0, int(payload.outgoing_count))
    total = incoming + outgoing

    if total == 0:
        return {
            "status": "ok",
            "camera_id": camera_id,
            "inserted_rows": 0,
            "session_id": payload.session_id or "simulated",
        }

    frame_seed = int(datetime.now().timestamp())
    session_id = payload.session_id or f"SIM_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    db = DBHandler(camera_id=camera_id)
    try:
        inserted = 0
        for _ in range(incoming):
            tid = random.randint(100000, 999999)
            db.insert_detection(
                track_id=tid,
                obj_class="person",
                confidence=1.0,
                bbox=(0, 0, 1, 1),
                frame_number=frame_seed,
                direction="IN",
                session_id=session_id,
                table="simulated_logs",
            )
            inserted += 1

        for _ in range(outgoing):
            tid = random.randint(100000, 999999)
            db.insert_detection(
                track_id=tid,
                obj_class="person",
                confidence=1.0,
                bbox=(0, 0, 1, 1),
                frame_number=frame_seed,
                direction="OUT",
                session_id=session_id,
                table="simulated_logs",
            )
            inserted += 1

        return {
            "status": "ok",
            "camera_id": camera_id,
            "inserted_rows": inserted,
            "session_id": session_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/simulator/workers")
def simulator_workers():
    try:
        return {"workers": get_supervisor().list_workers()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulator/start/{camera_id}")
def simulator_start(camera_id: str):
    try:
        return get_supervisor().start_worker(camera_id=camera_id, source_id=camera_id, managed=False)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulator/stop/{camera_id}")
def simulator_stop(camera_id: str):
    try:
        return get_supervisor().stop_worker(camera_id=camera_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulator/restart/{camera_id}")
def simulator_restart(camera_id: str):
    try:
        return get_supervisor().restart_worker(camera_id=camera_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stream/workers")
def stream_workers():
    try:
        return {"workers": get_stream_supervisor().list_workers()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream/start/{camera_id}")
def stream_start(camera_id: str):
    try:
        return get_stream_supervisor().start_worker(camera_id=camera_id, managed=False)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream/stop/{camera_id}")
def stream_stop(camera_id: str):
    try:
        return get_stream_supervisor().stop_worker(camera_id=camera_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream/restart/{camera_id}")
def stream_restart(camera_id: str):
    try:
        return get_stream_supervisor().restart_worker(camera_id=camera_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
