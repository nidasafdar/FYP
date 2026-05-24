from datetime import timedelta, datetime
from .analytics_service import AnalyticsService

class RushDetection:

    def __init__(self, service=None, verbose=False):
        self.service = service if service else AnalyticsService()
        self.verbose = verbose
        print(f"[SUCCESS] RushDetection initialized (Shared: {service is not None})")


    # -------------------------------
    # 1. Current Traffic (Sliding Window)
    # -------------------------------
    def get_current_count(self, camera_id, minutes=10, table="simulated_logs"):
        return self.service.get_current_count(camera_id, minutes, table=table, direction=None)


    # -------------------------------
    # 2. Historical Mean & StdDev (Same Hour)
    # -------------------------------
    def get_hourly_stats(self, camera_id, table="simulated_logs", bucket_minutes=10):
        return self.service.get_hourly_stats(camera_id, table=table, bucket_minutes=bucket_minutes, direction=None)


    # -------------------------------
    # 3. Z-Score Calculation
    # -------------------------------
    def calculate_z_score(self, current, mean, std):
        if std == 0: return 0
        z = (current - mean) / std
        return z


    # -------------------------------
    # 4. Alert Level Decision
    # -------------------------------
    def get_alert_level(self, z, ratio):
        if ratio >= 2.0:
            return "RUSH ALERT"
        if z < 1:
            return "NORMAL"
        elif 1 <= z < 2:
            return "BUSY"
        else:
            return "RUSH ALERT"


    # -------------------------------
    # 5. Full Detection Pipeline
    # -------------------------------
    def detect_rush(self, camera_id, minutes=10, table="simulated_logs"):
        current = self.get_current_count(camera_id, minutes, table=table)
        mean, std = self.get_hourly_stats(camera_id, table=table, bucket_minutes=minutes)

        z = self.calculate_z_score(current, mean, std)
        ratio = current / mean if mean > 0 else 0

        # Baseline threshold prevents cold-start noise from becoming a rush alert.
        if current < 10:
            status = "NORMAL"
            z = 0.0
            ratio = 0
        else:
            status = self.get_alert_level(z, ratio)

        if self.verbose:
            print("\n--- RUSH ANALYSIS ---")
            print(f"Camera: {camera_id}")
            print(f"Window: Last {minutes} minutes")
            print(f"Current Count: {current}")
            print(f"Window Avg: {round(mean,2)}")
            print(f"Std Dev: {round(std,2)}")
            print(f"Z-Score: {round(z,2)}")
            print(f"Ratio: {round(ratio,2)}")
            print(f"Status: {status}")

        return {
            "current": current,
            "mean": mean,
            "std": std,
            "z": z,
            "ratio": ratio,
            "status": status,
            "window_minutes": minutes,
            "is_active": status == "RUSH ALERT",
        }


    def close(self):
        print("[SUCCESS] RushDetection Logic Disengaged")
