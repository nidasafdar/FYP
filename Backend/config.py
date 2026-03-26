# config.py
import os

# -------------------------------
# Base Directories
# -------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------------
# Database Configuration
# -------------------------------
DB_CONFIG = {
    "dbname": "FYP_Tracking",
    "user": "postgres",
    "password": "n1d@n1d@",
    "host": "localhost",
    "port": 5432
}

# -------------------------------
# Camera Configuration
# -------------------------------
DEFAULT_CAMERA_ID = "gate1"

# -------------------------------
# File Paths
# -------------------------------
MODEL_PATH = os.path.join(BASE_DIR, "yolov8n.pt")
VIDEO_FOLDER = os.path.join(BASE_DIR, "videos")
DEFAULT_VIDEO_PATH = os.path.join(VIDEO_FOLDER, "footage1.mp4")

# -------------------------------
# Detection Logic
# -------------------------------
LINE_ORIENTATION = "horizontal"  # Options: "horizontal" or "vertical"
DEEPSORT_MAX_AGE = 30
