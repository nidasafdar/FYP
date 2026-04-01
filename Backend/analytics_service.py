# analytics_service.py
import psycopg2
from config import DB_CONFIG, DEFAULT_CAMERA_ID, DB_URL

class AnalyticsService:

    def __init__(self, db_config=None):
        self.config = db_config if db_config else DB_CONFIG
        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self):
        try:
            # Handle both local (dict) and cloud (DSN string) formats
            dsn = self.config.get("dsn", DB_URL)
            self.conn = psycopg2.connect(dsn)
            self.cursor = self.conn.cursor()
            print("[SUCCESS] AnalyticsService Cloud-Connected")
        except Exception as e:
            print(f"[ERROR] AnalyticsService connection error: {e}")
            self.conn = None
            self.cursor = None
            # Do NOT raise here if we want the dashboard to load even without DB

    def get_latest_session_id(self):
        """Helper to identify which video session was last active."""
        if not self.cursor: return None
        try:
            self.cursor.execute("SELECT session_id FROM detections ORDER BY timestamp DESC LIMIT 1")
            res = self.cursor.fetchone()
            return res[0] if res else None
        except:
            return None

    # --- Core Metric: Occupancy ---

    def get_current_occupancy_by_in_out(self, camera_id=DEFAULT_CAMERA_ID, session_id=None, date_filter=None, hour_range=None):
        """Calculates occupancy with optional date and time range filtering."""
        if not self.cursor: return 0
        try:
            query = """
                SELECT 
                    COUNT(*) FILTER (WHERE direction = 'IN') - 
                    COUNT(*) FILTER (WHERE direction = 'OUT')
                FROM detections
                WHERE camera_id = %s
            """
            params = [camera_id]
            
            if session_id:
                query += " AND session_id = %s"
                params.append(session_id)
            if date_filter:
                query += " AND timestamp::date = %s"
                params.append(date_filter)
            if hour_range:
                query += " AND EXTRACT(HOUR FROM timestamp) BETWEEN %s AND %s"
                params.extend(hour_range)

            self.cursor.execute(query, tuple(params))
            result = self.cursor.fetchone()[0]
            return result if result is not None else 0
        except Exception as e:
            print("[ERROR] Filtered occupancy error:", e)
            return 0

    def get_total_visitors(self, camera_id=DEFAULT_CAMERA_ID, session_id=None, direction='IN', date_filter=None, hour_range=None):
        """Returns total headcount with date and timing filters."""
        if not self.cursor: return 0
        try:
            query = "SELECT COUNT(*) FROM detections WHERE camera_id = %s AND direction = %s"
            params = [camera_id, direction]
            
            if session_id:
                query += " AND session_id = %s"
                params.append(session_id)
            if date_filter:
                query += " AND timestamp::date = %s"
                params.append(date_filter)
            if hour_range:
                query += " AND EXTRACT(HOUR FROM timestamp) BETWEEN %s AND %s"
                params.extend(hour_range)
                
            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchone()[0] or 0
        except Exception as e:
            print("[ERROR] Total visitors error:", e)
            return 0

    # --- Trends ---

    def get_hourly_trend(self, camera_id=DEFAULT_CAMERA_ID, session_id=None, date_filter=None):
        """Returns hourly trend filtered by date for fine-grained analysis."""
        if not self.cursor: return []
        try:
            query = """
                SELECT 
                    EXTRACT(HOUR FROM timestamp) AS hour,
                    COUNT(*) AS people
                FROM detections
                WHERE camera_id = %s AND direction = 'IN'
            """
            params = [camera_id]
            
            if session_id:
                query += " AND session_id = %s"
                params.append(session_id)
            if date_filter:
                query += " AND timestamp::date = %s"
                params.append(date_filter)
            
            query += " GROUP BY hour ORDER BY hour"
            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except Exception as e:
            print("[ERROR] Hourly trend error:", e)
            return []

    def get_peak_hours(self, camera_id=DEFAULT_CAMERA_ID, session_id=None):
        if not self.cursor: return []
        try:
            query = """
                SELECT 
                    EXTRACT(HOUR FROM timestamp) AS hour,
                    COUNT(*) AS people
                FROM detections
                WHERE camera_id = %s
            """
            params = [camera_id]
            if session_id:
                query += " AND session_id = %s"
                params.append(session_id)
                
            query += " GROUP BY hour ORDER BY people DESC"
            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except Exception as e:
            print("[ERROR] Peak hour analysis error:", e)
            return []

    # --- Flow Analysis ---

    def get_average_occupancy(self, camera_id=DEFAULT_CAMERA_ID):
        """Calculates average occupancy across all historical data."""
        if not self.cursor: return 0
        try:
            self.cursor.execute("""
                SELECT AVG(occupancy)
                FROM (
                    SELECT 
                        timestamp,
                        COUNT(*) FILTER (WHERE direction = 'IN') OVER (ORDER BY timestamp) - 
                        COUNT(*) FILTER (WHERE direction = 'OUT') OVER (ORDER BY timestamp) as occupancy
                    FROM detections
                    WHERE camera_id = %s
                ) as sub
            """, (camera_id,))
            result = self.cursor.fetchone()[0]
            return int(result) if result is not None else 0
        except Exception as e:
            print("[ERROR] Average occupancy error:", e)
            return 0

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("[SUCCESS] AnalyticsService connection closed")
