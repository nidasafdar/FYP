from analytics_service import AnalyticsService

class AnalyticsReports:

    def __init__(self):
        self.service = AnalyticsService()
        print("[SUCCESS] AnalyticsReports initialized (via Service)")

    def get_total_entries(self, camera_id):
        self.service.cursor.execute("""
            SELECT COUNT(*) FROM detections WHERE camera_id=%s AND direction='IN'
        """, (camera_id,))
        result = self.service.cursor.fetchone()[0]
        return result or 0

    def get_total_exits(self, camera_id):
        self.service.cursor.execute("""
            SELECT COUNT(*) FROM detections WHERE camera_id=%s AND direction='OUT'
        """, (camera_id,))
        result = self.service.cursor.fetchone()[0]
        return result or 0

    def get_current_occupancy(self, camera_id):
        # Consistent in-out logic from service
        return self.service.get_current_occupancy_by_in_out(camera_id)

    def get_peak_hour(self, camera_id):
        # Wraps service method
        results = self.service.get_peak_hours(camera_id)
        return results[0] if results else None

    def get_average_flow(self, camera_id):
        return self.service.get_average_flow(camera_id)

    def close(self):
        self.service.close()