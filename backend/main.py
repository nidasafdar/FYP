import cv2
import os
import sys
import json
from datetime import datetime
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from db_handler import DBHandler
from config import MODEL_PATH, DEFAULT_VIDEO_PATH, DEEPSORT_MAX_AGE, LINE_ORIENTATION

# Core Components
model = YOLO(MODEL_PATH)
tracker = DeepSort(max_age=DEEPSORT_MAX_AGE)
db = DBHandler()

# Global State
track_history = {}
frame_count = 0
line_type = LINE_ORIENTATION
line_position = None

# Hardware/Source Discovery
video_source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VIDEO_PATH
cap = cv2.VideoCapture(video_source)

if not cap.isOpened():
    print(f"Critical Error: Source {video_source} unavailable.")
    sys.exit(1)

print(f"Analysis Started: {video_source}")

# Generate a unique Session ID for this run to keep data isolated
ACTIVE_SESSION_ID = f"{os.path.basename(video_source)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Signals
STOP_SIGNAL = os.path.join(os.path.dirname(__file__), "stop_signal.txt")
if os.path.exists(STOP_SIGNAL): os.remove(STOP_SIGNAL)

while True:
    if os.path.exists(STOP_SIGNAL):
        print("Interrupt signal received. Cleaning up...")
        break

    ret, frame = cap.read()
    if not ret:
        print("Source stream consumed.")
        break

    frame_count += 1
    h, w, _ = frame.shape
    if line_position is None:
        line_position = h // 2 if line_type == "horizontal" else w // 2

    # Visual Line Overlay
    if line_type == "horizontal": cv2.line(frame, (0, line_position), (w, line_position), (0, 255, 255), 2)
    else: cv2.line(frame, (line_position, 0), (line_position, h), (0, 255, 255), 2)

    # YOLO Inference
    results = model(frame, verbose=False)
    detections = []
    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0: # person
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append(([x1, y1, x2-x1, y2-y1], conf, 'person'))

    # Tracking Updates
    tracks = tracker.update_tracks(detections, frame=frame)
    for track in tracks:
        if not track.is_confirmed(): continue
        
        tid = track.track_id
        l, t, r, b = map(int, track.to_ltrb())
        center = (t + b) // 2 if line_type == "horizontal" else (l + r) // 2
        
        # Crossing logic
        direction = None
        if tid in track_history:
            prev = track_history[tid]
            if prev < line_position and center >= line_position: direction = "IN"
            elif prev > line_position and center <= line_position: direction = "OUT"
        
        track_history[tid] = center

        # Database Logging & Visuals
        if direction:
            session_label = ACTIVE_SESSION_ID
            # Route to separate table: audit_logs for recorded videos, live_logs for camera streams
            target_table = "audit_logs" if os.path.isfile(video_source) else "live_logs"
            db.insert_detection(tid, "person", 1.0, (l, t, r, b), frame_count, direction, 
                                session_id=session_label, table=target_table)
            print(f"Crossing Detected [{target_table}]: ID {tid} -> {direction}")

        cv2.rectangle(frame, (l, t), (r, b), (255, 0, 0), 2)
        cv2.putText(frame, f"ID:{tid}", (l, t-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # Frame Export for Dashboard
    try:
        current_frame_path = os.path.join(os.path.dirname(__file__), "current_frame.jpg")
        cv2.imwrite(current_frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    except: pass

# Post-Session Summary
print("--- Finalizing Audit Session ---")
cap.release()

session_ref = ACTIVE_SESSION_ID
target_table = "audit_logs" if os.path.isfile(video_source) else "live_logs"
final_in = db.get_total_visitors(session_id=session_ref, direction='IN', table=target_table)
final_out = db.get_total_visitors(session_id=session_ref, direction='OUT', table=target_table)

audit_summary = {
    "session": session_ref,
    "total_in": final_in,
    "total_out": final_out,
    "total_flow": final_in + final_out,
    "status": "SUCCESS",
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

sum_path = os.path.join(os.path.dirname(__file__), "audit_summary.json")
comp_path = os.path.join(os.path.dirname(__file__), "audit_complete.txt")

with open(sum_path, "w") as f: json.dump(audit_summary, f)
with open(comp_path, "w") as f: f.write("DONE")

db.close()
cv2.destroyAllWindows()
print("Audit processing completed successfully.")