# # config.py
# print("📡 Backend: Loading latest Database Configuration (DSN format)...")
# import os

# # -------------------------------
# # Base Directories
# # -------------------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # -------------------------------
# # Database Configuration (Local Ready)
# # -------------------------------
# # Using the local hardcoded DB. 
# # libpq format: Safe for passwords with special characters like '@'
# DB_URL = "host=localhost dbname=FYP_Tracking user=postgres password=n1d@n1d@ port=5432"

# # Extract components from URL if needed by older parts of your system
# DB_CONFIG = {
#     "dsn": DB_URL
# }


# # -------------------------------
# # Camera Configuration
# # -------------------------------
# DEFAULT_CAMERA_ID = "Camera_01"

# # -------------------------------
# # File Paths
# # -------------------------------
# MODEL_PATH = os.path.join(BASE_DIR, "yolov8n.pt")
# VIDEO_FOLDER = os.path.join(BASE_DIR, "videos")
# DEFAULT_VIDEO_PATH = os.path.join(VIDEO_FOLDER, "footage1.mp4")

# # -------------------------------
# # Runtime Behavior (Nonstop & Backend Optimization)
# # -------------------------------
# LOOP_VIDEO = False     # Automatically restart video for continuous analytics (Set to False for uploads)
# SHOW_PREVIEW = True    # Set to False for 'headless' background processing (faster/saves memory)
# LINE_ORIENTATION = "horizontal"  # Options: "horizontal" or "vertical"
# DEEPSORT_MAX_AGE = 30



import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv():
        return None

load_dotenv()

DATABASE_URL     = os.getenv("DATABASE_URL", "host=db.ukmegcuexricbwewumnx.supabase.co dbname=postgres user=postgres password=XKCwg9uP7rAgUoZO port=5432 sslmode=require")
DEFAULT_CAMERA_ID = os.getenv("DEFAULT_CAMERA_ID", "Camera_01")

# Keep these for any file that imports them directly
DB_URL    = DATABASE_URL
DB_CONFIG = {"dsn": DATABASE_URL}

MODEL_PATH         = "yolov8n.pt"
DEFAULT_VIDEO_PATH = "videos/sample.mp4"
DEEPSORT_MAX_AGE   = 30
LINE_ORIENTATION   = "vertical"
