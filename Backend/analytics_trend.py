from analytics_service import AnalyticsService

class AnalyticsTrend:

    def __init__(self, service=None):
        self.service = service if service else AnalyticsService()
        print(f"[SUCCESS] AnalyticsTrend initialized (Shared: {service is not None})")

    def get_hourly_trend(self, camera_id, session_id=None, date_filter=None):
        return self.service.get_hourly_trend(camera_id, session_id, date_filter)

    def get_daily_trend(self, camera_id):
        # We don't filter daily trends by specific session usually, 
        # but the query is kept direct in service or here.
        # Let's use the service-provided structure for consistency.
        try:
            self.service.cursor.execute("""
                SELECT 
                    DATE(timestamp) AS day,
                    COUNT(*) AS people
                FROM detections
                WHERE camera_id = %s AND direction = 'IN'
                GROUP BY day
                ORDER BY day
            """, (camera_id,))
            return self.service.cursor.fetchall()
        except:
            return []

    def close(self):
        self.service.close()