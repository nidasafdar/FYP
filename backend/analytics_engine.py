from .analytics_reports import AnalyticsReports
from .analytics_trend import AnalyticsTrend
from .rush_detection import RushDetection
from .analytics_service import AnalyticsService
from datetime import datetime

TABLE_MAP = {
    "simulation": "simulated_logs",
    "simulated": "simulated_logs",
    "generate": "simulated_logs",
    "live": "live_logs",
    "stream": "live_logs",
    "audit": "audit_logs",
}

SOURCE_TYPE_MAP = {
    "simulation": "generate",
    "simulated": "generate",
    "generate": "generate",
    "live": "stream",
    "stream": "stream",
}

class AnalyticsEngine:

    def __init__(self):
        # Create a single shared service to avoid opening multiple DB connections
        self.shared_service = AnalyticsService()
        self.reports = AnalyticsReports(service=self.shared_service)
        self.trend = AnalyticsTrend(service=self.shared_service)
        self.rush = RushDetection(service=self.shared_service)
        print("[SUCCESS] Central Analytics Engine Ready (Optimized Shared Connection)")

        # Z-Score = (current - mean) / std



    def get_dashboard_data(self, camera_id=None, date_val=None, hour_range=None, mode="simulation"):
        """ONE FUNCTION -> ALL ANALYTICS OUTPUT (Session & Filter Aware)"""
        try:
            target_table = TABLE_MAP.get(mode, "simulated_logs")

            # 2. Identify which session we are looking at (Latest one in DB)
            latest_session = self.shared_service.get_latest_session_id(camera_id=camera_id, table=target_table)

            # 3. Fetch Live Metrics (Filtered by logic if user provided date/time)
            occupancy_data = self.shared_service.get_realtime_occupancy(camera_id, latest_session, date_val, table=target_table)
            flow = self.shared_service.get_flow_split(camera_id, latest_session, date_val, table=target_table)
            entries = flow["incoming"]
            exits = flow["outgoing"]
            occupancy = occupancy_data["current"]
            
            # 4. Fetch Historical Intelligence (Across all time/sessions)
            avg_occupancy = self.shared_service.get_average_occupancy(camera_id, table=target_table)
            hist_total = self.shared_service.get_total_visitors(camera_id, table=target_table) # All history
            
            peak_hours = self.shared_service.get_peak_slots(camera_id, latest_session, date_val, hour_range, table=target_table)
            peak_hour = peak_hours[0]["hour"] if peak_hours else None
            
            # 5. Rush Detection — Z-Score Statistical Analysis
            rush_result = self.rush.detect_rush(camera_id, minutes=10, table=target_table)
            rush_alert = {
                "status": rush_result["status"],
                "active": rush_result["is_active"],
                "window_minutes": rush_result["window_minutes"],
                "current": rush_result["current"],
                "average": round(rush_result["mean"], 2),
                "ratio": round(rush_result["ratio"], 2),
                "z_score": round(rush_result["z"], 2),
            }

            hourly = self.shared_service.get_hourly_trend(camera_id, latest_session, date_val, table=target_table)
            live_trend = self.shared_service.get_live_occupancy_trend(camera_id, session_id=latest_session, table=target_table)
            daily = self.shared_service.get_daily_trend(camera_id, table=target_table) 
            heatmap = self.shared_service.get_heatmap_data(camera_id, table=target_table)
            daily_summary = self.shared_service.get_daily_summary(camera_id, latest_session, date_val, table=target_table)
            comparison_date = date_val or datetime.now().astimezone().date().isoformat()
            source_type = SOURCE_TYPE_MAP.get(mode)
            comparison_camera_ids = self.shared_service.get_source_camera_ids(source_type=source_type)
            gate_comparison = self.shared_service.get_gate_comparison(
                comparison_date,
                table=target_table,
                camera_ids=comparison_camera_ids,
            )
            congestion = self.shared_service.get_congestion_levels(camera_id, table=target_table)
            week_over_week = self.shared_service.get_week_over_week(camera_id, table=target_table)
            wait_metric = {
                "available": False,
                "label": "Unavailable",
                "reason": "Requires first-seen and last-seen timestamps per track_id.",
            }

            return {
                "camera": camera_id,
                "session": latest_session,
                "mode": mode,
                "table": target_table,
                "entries": entries,
                "exits": exits,
                "occupancy": occupancy,
                "occupancy_details": occupancy_data,
                "flow": flow,
                "avg_occupancy": avg_occupancy,
                "historical_total": hist_total,
                "peak_hour": peak_hour,
                "peak_hours": peak_hours,
                "rush_alert": rush_alert,
                "rush_status": rush_alert["status"],
                "congestion": congestion,
                "rush_z_score": round(rush_result["z"], 2),
                "rush_current": rush_result["current"],
                "rush_mean": round(rush_result["mean"], 2),
                "rush_std": round(rush_result["std"], 2),
                "hourly_trend": hourly,
                "live_trend": live_trend,
                "daily_trend": daily,
                "heatmap_data": heatmap,
                "daily_summary": daily_summary,
                "gate_comparison": gate_comparison,
                "week_over_week": week_over_week,
                "average_wait_time": wait_metric,
                "metric_availability": {
                    "average_wait_time": wait_metric,
                },
            }
        except Exception as e:
            print(f"[ERROR] Dashboard calculation error: {e}")
            return None

    def get_camera_comparison(self, mode="simulation"):
        """Fetch comparative traffic data across all cameras."""
        target_table = TABLE_MAP.get(mode, "simulated_logs")
        source_type = SOURCE_TYPE_MAP.get(mode)
        camera_ids = self.shared_service.get_source_camera_ids(source_type=source_type)
        return self.shared_service.get_gate_comparison(table=target_table, camera_ids=camera_ids)

    def close(self):
        self.reports.close()
        self.trend.close()
        self.rush.close()
        print("[SUCCESS] All Analytics Connections Closed")
