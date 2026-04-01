from analytics_service import AnalyticsService

class AnalyticsReports:

    def __init__(self, service=None):
        self.service = service if service else AnalyticsService()
        print(f"[SUCCESS] AnalyticsReports initialized (Shared: {service is not None})")

    def get_total_entries(self, camera_id, session_id=None, date_filter=None, hour_range=None):
        return self.service.get_total_visitors(camera_id, session_id, direction='IN', date_filter=date_filter, hour_range=hour_range)

    def get_total_exits(self, camera_id, session_id=None, date_filter=None, hour_range=None):
        return self.service.get_total_visitors(camera_id, session_id, direction='OUT', date_filter=date_filter, hour_range=hour_range)

    def get_current_occupancy(self, camera_id, session_id=None, date_filter=None, hour_range=None):
        return self.service.get_current_occupancy_by_in_out(camera_id, session_id, date_filter, hour_range)

    def get_peak_hour(self, camera_id, session_id=None):
        results = self.service.get_peak_hours(camera_id, session_id)
        return results[0] if results else None

    def get_average_flow(self, camera_id):
        return self.service.get_average_flow(camera_id)

    def close(self):
        self.service.close()