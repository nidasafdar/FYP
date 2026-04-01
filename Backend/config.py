# config.py
import os

# -------------------------------
# Base Directories
# -------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------------
# Database Configuration (Cloud Ready)
# -------------------------------
import streamlit as st

# In local: uses the fallback hardcoded DB. 
# In Cloud: uses the 'DB_URL' you paste in the secrets box.
DB_URL = st.secrets.get("DB_URL", "postgresql://postgres:n1d@n1d@@localhost:5432/FYP_Tracking")

# Extract components from URL if needed by older parts of your system
DB_CONFIG = {
    "dsn": DB_URL
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
# Runtime Behavior (Nonstop & Backend Optimization)
# -------------------------------
LOOP_VIDEO = False     # Automatically restart video for continuous analytics (Set to False for uploads)
SHOW_PREVIEW = True    # Set to False for 'headless' background processing (faster/saves memory)
LINE_ORIENTATION = "horizontal"  # Options: "horizontal" or "vertical"
DEEPSORT_MAX_AGE = 30
