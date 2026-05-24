from .analytics_service import AnalyticsService

class AnalyticsReports:

    def __init__(self, service=None):
        self.service = service if service else AnalyticsService()
        print(f"[SUCCESS] AnalyticsReports initialized (Shared: {service is not None})")

    def get_total_entries(self, camera_id, session_id=None, date=None, hours=None):
        return self.service.get_total_visitors(camera_id, session_id, direction='IN', date=date, hours=hours)

    def get_total_exits(self, camera_id, session_id=None, date=None, hours=None):
        return self.service.get_total_visitors(camera_id, session_id, direction='OUT', date=date, hours=hours)

    def get_current_occupancy(self, camera_id, session_id=None, date=None, hours=None):
        return self.service.get_current_occupancy(camera_id, session_id, date, hours)
    def get_total_entries(self, camera_id, session_id=None, date_filter=None, hour_range=None):
        return self.service.get_total_visitors(camera_id, session_id, direction='IN', date=date_filter, hours=hour_range)

    def get_total_exits(self, camera_id, session_id=None, date_filter=None, hour_range=None):
        return self.service.get_total_visitors(camera_id, session_id, direction='OUT', date=date_filter, hours=hour_range)

    def get_current_occupancy(self, camera_id, session_id=None, date_filter=None, hour_range=None):
        return self.service.get_current_occupancy(camera_id, session_id, date_filter, hour_range)

    def get_peak_hour(self, camera_id, session_id=None):
        return self.service.get_peak_hour(camera_id, session_id)

    def get_average_flow(self, camera_id):
        return self.service.get_average_occupancy(camera_id)

    def close(self):
        self.service.close()