# db_handler.py
import psycopg2
from datetime import datetime
try:
    from config import DB_CONFIG, DEFAULT_CAMERA_ID
except ImportError:
    # Fallback for systems where config.py isn't available
    DB_CONFIG = {
        "dbname": "FYP_Tracking",
        "user": "postgres",
        "password": "yourpassword",
        "host": "localhost",
        "port": 5432
    }
    DEFAULT_CAMERA_ID = "gate1"

class DBHandler:

    def __init__(self, db_config=None, camera_id=DEFAULT_CAMERA_ID):
        # Use provided config or fallback to global DB_CONFIG
        self.config = db_config if db_config else DB_CONFIG
        self.camera_id = camera_id
        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self):
        try:
            self.conn = psycopg2.connect(**self.config)
            self.cursor = self.conn.cursor()
            print(f"✅ DBHandler connected to {self.config['dbname']}")
        except Exception as e:
            print(f"❌ DBHandler Connection Error: {e}")
            raise

    def insert_detection(self, track_id, obj_class, confidence, bbox, frame_number, direction=None):
        l, t, r, b = bbox
        try:
            self.cursor.execute("""
                INSERT INTO detections (
                    track_id,
                    object_class,
                    confidence,
                    bbox_x1,
                    bbox_y1,
                    bbox_x2,
                    bbox_y2,
                    frame_number,
                    timestamp,
                    camera_id,
                    direction
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s,%s)
            """,
            (
                int(track_id),
                obj_class,
                float(confidence),
                int(l),
                int(t),
                int(r),
                int(b),
                int(frame_number),
                self.camera_id,
                direction
            ))

            self.conn.commit()
            print("✅ Insert successful")

        except Exception as e:
            print("❌ DB INSERT ERROR:", e)
            self.conn.rollback()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ Database connection closed")