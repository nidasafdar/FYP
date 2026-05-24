import os
import time
from datetime import datetime

try:
    from backend.config import DEEPSORT_MAX_AGE, LINE_ORIENTATION, MODEL_PATH
except Exception:
    from config import DEEPSORT_MAX_AGE, LINE_ORIENTATION, MODEL_PATH


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(BACKEND_DIR, "frames")


def get_crossing_direction(previous_center, current_center, line_position):
    if previous_center < line_position <= current_center:
        return "IN"
    if previous_center > line_position >= current_center:
        return "OUT"
    return None


def _status(status_queue, **payload):
    try:
        status_queue.put(payload)
    except Exception:
        pass


def run_stream_worker(camera_id, source_id, stream_url, stop_event, status_queue):
    """Read one stream URL, detect people crossings, and persist events to live_logs."""
    session_id = f"LIVE_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    started_at = datetime.now().astimezone().isoformat()

    try:
        import cv2
        try:
            from backend.db_handler import DBHandler
        except Exception:
            from db_handler import DBHandler
        from deep_sort_realtime.deepsort_tracker import DeepSort
        from ultralytics import YOLO
    except Exception as exc:
        _status(
            status_queue,
            camera_id=camera_id,
            source_id=source_id,
            stream_url=stream_url,
            session_id=session_id,
            started_at=started_at,
            ok=False,
            state="dependency_error",
            error=f"Stream dependencies unavailable: {exc}",
            last_frame_at=None,
            inserted_rows=0,
        )
        return

    os.makedirs(FRAMES_DIR, exist_ok=True)
    frame_path = os.path.join(FRAMES_DIR, f"{camera_id}.jpg")
    line_type = LINE_ORIENTATION
    line_position = None
    track_history = {}
    frame_count = 0
    inserted_rows = 0

    model = tracker = db = cap = None
    try:
        model = YOLO(MODEL_PATH)
        tracker = DeepSort(max_age=DEEPSORT_MAX_AGE)
        db = DBHandler(camera_id=camera_id)
        
        is_youtube = "youtube.com" in stream_url.lower() or "youtu.be" in stream_url.lower()
        if is_youtube:
            try:
                import yt_dlp
                ydl_opts = {
                    'format': 'best[ext=mp4]/best',
                    'quiet': True,
                    'no_warnings': True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(stream_url, download=False)
                    actual_url = info.get('url') or stream_url
            except Exception as e:
                print(f"[ERROR] Failed to extract YouTube stream in stream_worker: {e}")
                actual_url = stream_url
        else:
            actual_url = stream_url
            
        cap = cv2.VideoCapture(actual_url)

        if not cap.isOpened():
            _status(
                status_queue,
                camera_id=camera_id,
                source_id=source_id,
                stream_url=stream_url,
                session_id=session_id,
                started_at=started_at,
                ok=False,
                state="open_failed",
                error=f"Unable to open stream URL: {stream_url}",
                last_frame_at=None,
                inserted_rows=0,
            )
            return

        _status(
            status_queue,
            camera_id=camera_id,
            source_id=source_id,
            stream_url=stream_url,
            session_id=session_id,
            started_at=started_at,
            ok=True,
            state="running",
            error=None,
            last_frame_at=None,
            inserted_rows=0,
        )

        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                _status(
                    status_queue,
                    camera_id=camera_id,
                    source_id=source_id,
                    stream_url=stream_url,
                    session_id=session_id,
                    started_at=started_at,
                    ok=False,
                    state="read_failed",
                    error="Stream frame read failed or stream ended.",
                    last_frame_at=None,
                    inserted_rows=inserted_rows,
                )
                break

            frame_count += 1
            h, w, _ = frame.shape
            if line_position is None:
                line_position = h // 2 if line_type == "horizontal" else w // 2

            if line_type == "horizontal":
                cv2.line(frame, (0, line_position), (w, line_position), (0, 255, 255), 2)
            else:
                cv2.line(frame, (line_position, 0), (line_position, h), (0, 255, 255), 2)

            detections = []
            results = model(frame, verbose=False)
            for result in results:
                for box in result.boxes:
                    if int(box.cls[0]) == 0:
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        detections.append(([x1, y1, x2 - x1, y2 - y1], confidence, "person"))

            tracks = tracker.update_tracks(detections, frame=frame)
            for track in tracks:
                if not track.is_confirmed():
                    continue

                track_id = track.track_id
                l, t, r, b = map(int, track.to_ltrb())
                center = (t + b) // 2 if line_type == "horizontal" else (l + r) // 2
                direction = None

                if track_id in track_history:
                    direction = get_crossing_direction(track_history[track_id], center, line_position)

                track_history[track_id] = center

                if direction:
                    db.insert_detection(
                        track_id=track_id,
                        obj_class="person",
                        confidence=1.0,
                        bbox=(l, t, r, b),
                        frame_number=frame_count,
                        direction=direction,
                        session_id=session_id,
                        table="live_logs",
                    )
                    inserted_rows += 1

                cv2.rectangle(frame, (l, t), (r, b), (255, 0, 0), 2)
                cv2.putText(frame, f"ID:{track_id}", (l, t - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            last_frame_at = datetime.now().astimezone().isoformat()
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 60])

            _status(
                status_queue,
                camera_id=camera_id,
                source_id=source_id,
                stream_url=stream_url,
                session_id=session_id,
                started_at=started_at,
                ok=True,
                state="running",
                error=None,
                last_frame_at=last_frame_at,
                inserted_rows=inserted_rows,
                frame_count=frame_count,
            )

            time.sleep(0.001)

    except Exception as exc:
        _status(
            status_queue,
            camera_id=camera_id,
            source_id=source_id,
            stream_url=stream_url,
            session_id=session_id,
            started_at=started_at,
            ok=False,
            state="error",
            error=str(exc),
            last_frame_at=None,
            inserted_rows=inserted_rows,
            frame_count=frame_count,
        )
    finally:
        if cap is not None:
            cap.release()
        if db is not None:
            db.close()
