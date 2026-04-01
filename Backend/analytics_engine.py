from analytics_reports import AnalyticsReports
from analytics_trend import AnalyticsTrend
from rush_detection import RushDetection
from config import DEFAULT_CAMERA_ID

from analytics_service import AnalyticsService

class AnalyticsEngine:

    def __init__(self):
        # Create a single shared service to avoid opening multiple DB connections
        self.shared_service = AnalyticsService()
        self.reports = AnalyticsReports(service=self.shared_service)
        self.trend = AnalyticsTrend(service=self.shared_service)
        self.rush = RushDetection(service=self.shared_service)
        print("[SUCCESS] Central Analytics Engine Ready (Optimized Shared Connection)")

    def get_dashboard_data(self, camera_id=DEFAULT_CAMERA_ID, date_val=None, hour_range=None):
        """ONE FUNCTION -> ALL ANALYTICS OUTPUT (Session & Filter Aware)"""
        try:
            # 1. Identify which session we are looking at (Latest one in DB)
            latest_session = self.shared_service.get_latest_session_id()

            # 2. Fetch Live Metrics (Filtered by logic if user provided date/time)
            entries = self.reports.get_total_entries(camera_id, latest_session, date_val, hour_range)
            exits = self.reports.get_total_exits(camera_id, latest_session, date_val, hour_range)
            occupancy = self.reports.get_current_occupancy(camera_id, latest_session, date_val, hour_range)
            
            # 3. Fetch Historical Intelligence (Across all time/sessions)
            avg_occupancy = self.shared_service.get_average_occupancy(camera_id)
            hist_total = self.reports.get_total_entries(camera_id) # All history
            
            peak_list = self.reports.get_peak_hour(camera_id, latest_session)
            peak_hour = int(peak_list[0]) if peak_list else 0
            
            rush_data = self.rush.detect_rush(camera_id) 

            hourly = self.trend.get_hourly_trend(camera_id, latest_session, date_val)
            daily = self.trend.get_daily_trend(camera_id) # Usually multi-session

            # Simple congestion logic
            if occupancy < 50:
                congestion = "LOW"
            elif occupancy < 150:
                congestion = "MEDIUM"
            else:
                congestion = "HIGH"

            return {
                "camera": camera_id,
                "session": latest_session,
                "entries": entries,
                "exits": exits,
                "occupancy": occupancy,
                "avg_occupancy": avg_occupancy,
                "historical_total": hist_total,
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
