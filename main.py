import cv2
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

tracker = DeepSort(max_age=30)  # Keep tracks for 30 frames

model = YOLO("yolov8n.pt")  # lightweight model for edge

cap = cv2.VideoCapture("videos/footage1.mp4")
if not cap.isOpened():
    print("Error opening video")
    exit()

cv2.namedWindow("Detection", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Detection", 1280, 720)

frame_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Video finished or cannot read frame")
        break

    frame_count += 1

    if frame_count % 2 == 0:
        results = model(frame)

        detections = []  # Reset per frame

        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                if cls == 0:  # person class
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)

                    # Prepare for DeepSORT: [x, y, w, h], confidence, class
                    detections.append(([x1, y1, x2-x1, y2-y1], conf, 'person'))

        tracks = tracker.update_tracks(detections, frame=frame)

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            l, t, r, b = track.to_ltrb()  # left, top, right, bottom

            # Draw tracked object
            cv2.rectangle(frame, (int(l), int(t)), (int(r), int(b)), (255,0,0), 2)
            cv2.putText(frame, f"ID: {track_id}", (int(l), int(t-10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)

    h, w = frame.shape[:2]
    scale = min(1280 / w, 720 / h)  # Max width=1280, height=720
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized_frame = cv2.resize(frame, (new_w, new_h))

    # Display
    cv2.imshow("Detection", resized_frame)

    key = cv2.waitKey(30) & 0xFF
    if key == 27 or key == ord('q'):
        print("Stopped by user")
        break

cap.release()
cv2.destroyAllWindows()
print("Video processing ended safely")