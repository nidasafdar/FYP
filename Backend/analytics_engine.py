from analytics_reports import AnalyticsReports
from analytics_trend import AnalyticsTrend
from rush_detection import RushDetection
from config import DEFAULT_CAMERA_ID

class AnalyticsEngine:

    def __init__(self):
        self.reports = AnalyticsReports()
        self.trend = AnalyticsTrend()
        self.rush = RushDetection()
        print("[SUCCESS] Central Analytics Engine Ready")

    def get_dashboard_data(self, camera_id=DEFAULT_CAMERA_ID):
        """ONE FUNCTION -> ALL ANALYTICS OUTPUT"""
        try:
            entries = self.reports.get_total_entries(camera_id)
            exits = self.reports.get_total_exits(camera_id)
            occupancy = self.reports.get_current_occupancy(camera_id)

            peak_list = self.reports.get_peak_hour(camera_id)
            # Peak hour is result[0] if exists
            peak_hour = int(peak_list[0]) if peak_list else 0

            rush_data = self.rush.detect_rush(camera_id)

            hourly = self.trend.get_hourly_trend(camera_id)
            daily = self.trend.get_daily_trend(camera_id)

            # Simple congestion logic
            if occupancy < 50:
                congestion = "LOW"
            elif occupancy < 150:
                congestion = "MEDIUM"
            else:
                congestion = "HIGH"

            return {
                "camera": camera_id,
                "entries": entries,
                "exits": exits,
                "occupancy": occupancy,
                "peak_hour": peak_hour,
                "rush_status": rush_data["status"],
                "congestion": congestion,
                "hourly_trend": hourly,
                "daily_trend": daily
            }
        except Exception as e:
            print(f"[ERROR] Dashboard calculation error: {e}")
            return None

    def close(self):
        self.reports.close()
        self.trend.close()
        self.rush.close()
        print("[SUCCESS] All Analytics Connections Closed")
