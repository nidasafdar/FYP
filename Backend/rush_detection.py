from datetime import timedelta
from config import DB_CONFIG
from analytics_service import AnalyticsService

class RushDetection:

    def __init__(self, service=None, verbose=False):
        self.service = service if service else AnalyticsService()
        self.verbose = verbose
        print(f"[SUCCESS] RushDetection initialized (Shared: {service is not None})")


    # -------------------------------
    # 1. Current Traffic (Sliding Window)
    # -------------------------------
    def get_current_count(self, camera_id, minutes=5):

        self.service.cursor.execute(f"""
            SELECT COUNT(*)
            FROM detections
            WHERE camera_id = %s
            AND direction = 'IN'
            AND timestamp >= NOW() - INTERVAL '{minutes} minutes'
        """, (camera_id,))

        return self.service.cursor.fetchone()[0]


    # -------------------------------
    # 2. Historical Mean & StdDev (Same Hour)
    # -------------------------------
    def get_hourly_stats(self, camera_id):

        self.service.cursor.execute("""
            SELECT 
                AVG(count_per_minute),
                STDDEV(count_per_minute)
            FROM (
                SELECT COUNT(*) as count_per_minute
                FROM detections
                WHERE camera_id = %s
                AND direction = 'IN'
                AND EXTRACT(HOUR FROM timestamp) = EXTRACT(HOUR FROM NOW())
                GROUP BY DATE(timestamp), EXTRACT(MINUTE FROM timestamp)
            ) sub;
        """, (camera_id,))

        result = self.service.cursor.fetchone()

        mean = result[0] if result[0] else 0
        std = result[1] if result[1] else 1  # avoid division by zero

        return mean, std


    # -------------------------------
    # 3. Z-Score Calculation
    # -------------------------------
    def calculate_z_score(self, current, mean, std):

        z = (current - mean) / std
        return z


    # -------------------------------
    # 4. Alert Level Decision
    # -------------------------------
    def get_alert_level(self, z):

        if z < 1:
            return "NORMAL"
        elif 1 <= z < 2:
            return "BUSY"
        else:
            return "RUSH ALERT"


    # -------------------------------
    # 5. Full Detection Pipeline
    # -------------------------------
    def detect_rush(self, camera_id, minutes=5):

        current = self.get_current_count(camera_id, minutes)
        mean, std = self.get_hourly_stats(camera_id)

        z = self.calculate_z_score(current, mean, std)
        status = self.get_alert_level(z)

        if self.verbose:
            print("\n--- RUSH ANALYSIS ---")
            print(f"Camera: {camera_id}")
            print(f"Window: Last {minutes} minutes")
            print(f"Current Count: {current}")
            print(f"Hourly Avg: {round(mean,2)}")
            print(f"Std Dev: {round(std,2)}")
            print(f"Z-Score: {round(z,2)}")
            print(f"Status: {status}")

        return {
            "current": current,
            "mean": mean,
            "std": std,
            "z": z,
            "status": status
        }


    def close(self):
        # We don't close the service here anymore if shared
        print("[SUCCESS] RushDetection Logic Disengaged")