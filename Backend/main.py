import cv2
import os
import sys
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from db_handler import DBHandler
from config import MODEL_PATH, DEFAULT_VIDEO_PATH, DEEPSORT_MAX_AGE, LINE_ORIENTATION, LOOP_VIDEO, SHOW_PREVIEW

# -------------------------------
# Paths (From Config)
# -------------------------------
print("Model Path:", MODEL_PATH)
print("Video Path:", DEFAULT_VIDEO_PATH)

# -------------------------------
# Load Model & Tracker
# -------------------------------
model = YOLO(MODEL_PATH)
tracker = DeepSort(max_age=DEEPSORT_MAX_AGE)

# Track history for direction detection
track_history = {}

# -------------------------------
# Database
# -------------------------------
db = DBHandler() # Default config from config.py
print("📊 Database initialized. Historical data preserved.")

# -------------------------------
# Video Capture
# -------------------------------
# Check if a custom video path was passed via command line (for uploads)
video_source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VIDEO_PATH
print(f"📌 Using Video Source: {video_source}")

cap = cv2.VideoCapture(video_source)
if not cap.isOpened():
    print(f"❌ ERROR: Cannot open video at {video_source}")
    # Small sleep so the user can see the error in the terminal before it closes
    import time
    time.sleep(10)
    exit()

print("✅ Video opened successfully")

if SHOW_PREVIEW:
    cv2.namedWindow("Detection", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Detection", 1280, 720)

frame_count = 0

# -------------------------------
# Configure line orientation
# -------------------------------
line_type = LINE_ORIENTATION

# Will be calculated based on frame size
line_position = None

# -------------------------------
# Main Loop
# -------------------------------
STOP_SIGNAL = os.path.join(os.path.dirname(__file__), "stop_signal.txt")
if os.path.exists(STOP_SIGNAL): os.remove(STOP_SIGNAL)

while True:
    # Check for stop signal from frontend
    if os.path.exists(STOP_SIGNAL):
        print("🛑 STOP SIGNAL RECEIVED. Terminating...")
        break

    ret, frame = cap.read()
    if not ret:
        print("✅ Video finished (Reached last frame)")
        break

    frame_count += 1
    height, width, _ = frame.shape

    # Determine line position if not yet set
    if line_position is None:
        if line_type == "horizontal":
            line_position = height // 2
        else:  # vertical
            line_position = width // 2

    # Draw virtual gate line
    if line_type == "horizontal":
        cv2.line(frame, (0, line_position), (width, line_position), (0,255,255), 2)
    else:
        cv2.line(frame, (line_position, 0), (line_position, height), (0,255,255), 2)

    # -------------------------------
    # YOLO Detection
    # -------------------------------
    results = model(frame, verbose=False)
    detections = []

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])

            if cls == 0:  # person
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
                detections.append(([x1, y1, x2-x1, y2-y1], conf, 'person'))

    # -------------------------------
    # DeepSORT Tracking
    # -------------------------------
    tracks = tracker.update_tracks(detections, frame=frame)

    processed_tracks = 0
    confirmed_tracks_list = [] # Temporarily store confirmed tracks to count them first
    for track in tracks:
        if not track.is_confirmed():
            continue
        confirmed_tracks_list.append(track)
        
    processed_tracks = len(confirmed_tracks_list)
    print(f"Active Tracks: {processed_tracks}")

    for track in confirmed_tracks_list: # Iterate over the confirmed tracks
        track_id = track.track_id
        l, t, r, b = map(int, track.to_ltrb())

        # Calculate center based on line orientation
        if line_type == "horizontal":
            center = (t + b) // 2
        else:
            center = (l + r) // 2

        direction = None

        # -------------------------------
        # Direction Detection (Crossing Logic)
        # -------------------------------
        if track_id in track_history:
            previous_center = track_history[track_id]

            # Crossing from Top to Bottom (IN) or Bottom to Top (OUT)
            if previous_center < line_position and center >= line_position:
                direction = "IN"
            elif previous_center > line_position and center <= line_position:
                direction = "OUT"

        # Update tracking memory
        track_history[track_id] = center

        # -------------------------------
        # Visuals: Box and ID
        # -------------------------------
        cv2.rectangle(frame, (l, t), (r, b), (255, 0, 0), 2)
        cv2.putText(frame, f"ID:{track_id}", (l, t - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        if direction:
            cv2.putText(frame,
                        direction,
                        (l, b+20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0,255,255),
                        2)
            
            print(f"✅ Track {track_id} moved {direction} - Saving to DB")

            # -------------------------------
            # Store in PostgreSQL (Only on Crossing)
            # -------------------------------
            # Use filename as session_id to allow multi-file tracking without deletion
            session_label = os.path.basename(video_source)
            db.insert_detection(
                track_id,
                "person",
                1.0,  # Constant confidence for tracked objects
                (l, t, r, b),
                frame_count,
                direction,
                session_id=session_label
            )

    if SHOW_PREVIEW:
        # Resize for screen
        frame_vis = cv2.resize(frame, (1280,720))
        cv2.imshow("Detection", frame_vis)

        key = cv2.waitKey(1)
        if key == 27 or key == ord("q"):
            break
    else:
        # Prevent CPU spike in headless mode if processing too fast
        pass

    # --- LIVE PREVIEW (Save to disk for Streamlit) ---
    try:
        temp_path = os.path.join(os.path.dirname(__file__), "temp_frame.jpg")
        final_path = os.path.join(os.path.dirname(__file__), "current_frame.jpg")
        # Save a reasonably compressed JPG
        cv2.imwrite(temp_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        if os.path.exists(final_path):
            os.remove(final_path)
        os.rename(temp_path, final_path)
    except Exception as e:
        pass # Silently fail to not break the engine if disk is busy

# -------------------------------
# Cleanup
# -------------------------------
cap.release()
db.close()
cv2.destroyAllWindows()
print("✅ Program finished safely")