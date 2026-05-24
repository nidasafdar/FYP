from .analytics_service import AnalyticsService

class AnalyticsTrend:

    def __init__(self, service=None):
        self.service = service if service else AnalyticsService()
        print(f"[SUCCESS] AnalyticsTrend initialized (Shared: {service is not None})")

    def get_hourly_trend(self, camera_id, session_id=None, date=None):
        return self.service.get_hourly_trend(camera_id, session_id, date)

    def get_daily_trend(self, camera_id):
        return self.service.get_daily_trend(camera_id)

    def close(self):
        self.service.close()