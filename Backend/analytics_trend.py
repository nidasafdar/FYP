from analytics_service import AnalyticsService

class AnalyticsTrend:

    def __init__(self):
        self.service = AnalyticsService()
        print("[SUCCESS] AnalyticsTrend initialized (via Service)")

    def get_hourly_trend(self, camera_id):
        return self.service.get_hourly_trend(camera_id)

    def get_daily_trend(self, camera_id):
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

    def close(self):
        self.service.close()