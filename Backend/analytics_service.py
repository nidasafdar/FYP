# analytics_service.py
import psycopg2
from config import DB_CONFIG, DEFAULT_CAMERA_ID

class AnalyticsService:

    def __init__(self, db_config=None):
        self.config = db_config if db_config else DB_CONFIG
        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self):
        try:
            self.conn = psycopg2.connect(**self.config)
            self.cursor = self.conn.cursor()
            print(f"[SUCCESS] AnalyticsService connected to {self.config['dbname']}")
        except Exception as e:
            print(f"[ERROR] AnalyticsService connection error:", e)
            raise

    # --- Core Metric: Occupancy ---

    def get_current_occupancy_by_in_out(self, camera_id=DEFAULT_CAMERA_ID):
        """Calculates current occupancy as Total IN - Total OUT."""
        try:
            self.cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE direction = 'IN') - 
                    COUNT(*) FILTER (WHERE direction = 'OUT')
                FROM detections
                WHERE camera_id = %s
            """, (camera_id,))
            result = self.cursor.fetchone()[0]
            return result if result is not None else 0
        except Exception as e:
            print("[ERROR] Occupancy (In-Out) error:", e)
            return 0

    def get_total_unique_visitors(self, camera_id=DEFAULT_CAMERA_ID):
        """Returns total number of unique track_ids observed."""
        try:
            self.cursor.execute("""
                SELECT COUNT(DISTINCT track_id)
                FROM detections
                WHERE camera_id = %s
            """, (camera_id,))
            return self.cursor.fetchone()[0] or 0
        except Exception as e:
            print("[ERROR] Unique visitors error:", e)
            return 0

    # --- Trends ---

    def get_hourly_trend(self, camera_id=DEFAULT_CAMERA_ID):
        try:
            self.cursor.execute("""
                SELECT 
                    EXTRACT(HOUR FROM timestamp) AS hour,
                    COUNT(*) AS people
                FROM detections
                WHERE camera_id = %s AND direction = 'IN'
                GROUP BY hour
                ORDER BY hour
            """, (camera_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print("[ERROR] Hourly trend error:", e)
            return []

    def get_peak_hours(self, camera_id=DEFAULT_CAMERA_ID):
        try:
            self.cursor.execute("""
                SELECT 
                    EXTRACT(HOUR FROM timestamp) AS hour,
                    COUNT(*) AS people
                FROM detections
                WHERE camera_id = %s
                GROUP BY hour
                ORDER BY people DESC
            """, (camera_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print("[ERROR] Peak hour analysis error:", e)
            return []

    # --- Flow Analysis ---

    def get_average_flow(self, camera_id=DEFAULT_CAMERA_ID):
        """Calculates people per minute."""
        try:
            self.cursor.execute("""
                SELECT
                    COUNT(*) /
                    NULLIF(EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))), 0) * 60
                FROM detections
                WHERE camera_id = %s
            """, (camera_id,))
            result = self.cursor.fetchone()[0]
            return round(result, 2) if result else 0
        except Exception as e:
            print("[ERROR] Average flow error:", e)
            return 0

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("[SUCCESS] AnalyticsService connection closed")
