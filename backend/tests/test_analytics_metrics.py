import unittest
from datetime import datetime, timedelta

from backend.analytics_service import AnalyticsService
from backend.rush_detection import RushDetection


class AnalyticsMetricsTest(unittest.TestCase):
    def setUp(self):
        self.service = AnalyticsService.__new__(AnalyticsService)
        self.now = datetime.now().astimezone().replace(hour=10, minute=20, second=0, microsecond=0)
        self.rows = [
            self.row("Gate A", "IN", self.now.replace(hour=8, minute=5)),
            self.row("Gate A", "IN", self.now.replace(hour=8, minute=15)),
            self.row("Gate A", "OUT", self.now.replace(hour=8, minute=25)),
            self.row("Gate A", "IN", self.now.replace(hour=9, minute=5)),
            self.row("Gate B", "IN", self.now.replace(hour=9, minute=10)),
            self.row("Gate B", "OUT", self.now.replace(hour=9, minute=25)),
        ]

    def row(self, camera, direction, timestamp):
        return {
            "id": len(getattr(self, "rows", [])) + 1,
            "camera_id": camera,
            "direction": direction,
            "timestamp": timestamp.isoformat(),
            "session_id": "S1",
        }

    def install_rows(self, rows):
        def query_logs(table="detections", camera_id=None, camera_ids=None, session_id=None, direction=None, date=None, start_dt=None, end_dt=None):
            result = rows
            if camera_id:
                result = [row for row in result if row["camera_id"] == camera_id]
            if camera_ids is not None:
                result = [row for row in result if row["camera_id"] in camera_ids]
            if session_id:
                result = [row for row in result if row["session_id"] == session_id]
            if direction:
                result = [row for row in result if row["direction"] == direction]
            if date:
                result = [row for row in result if row["timestamp"].startswith(date)]
            if start_dt:
                result = [row for row in result if datetime.fromisoformat(row["timestamp"]) >= start_dt]
            if end_dt:
                result = [row for row in result if datetime.fromisoformat(row["timestamp"]) <= end_dt]
            return result

        self.service._query_logs = query_logs

    def test_occupancy_and_flow_split(self):
        self.install_rows(self.rows)

        occupancy = self.service.get_realtime_occupancy(camera_id="Gate A", session_id="S1")
        flow = self.service.get_flow_split(camera_id="Gate A", session_id="S1")

        self.assertEqual(occupancy["current"], 2)
        self.assertEqual(flow["incoming"], 3)
        self.assertEqual(flow["outgoing"], 1)
        self.assertEqual(flow["incoming_percent"], 75)

    def test_peak_slots(self):
        self.install_rows(self.rows)

        peaks = self.service.get_peak_slots(camera_id="Gate A", session_id="S1", bucket_minutes=30, limit=2)

        self.assertEqual(peaks[0]["count"], 2)
        self.assertIn("8:00 AM", peaks[0]["time"])

    def test_gate_comparison_percentages(self):
        self.install_rows(self.rows)

        gates = self.service.get_gate_comparison()

        self.assertEqual(gates[0]["camera"], "Gate A")
        self.assertEqual(gates[0]["traffic"], 3)
        self.assertEqual(gates[0]["percent"], 75)

    def test_congestion_levels(self):
        rows = [
            self.row("Gate A", "IN", self.now.replace(hour=8, minute=0)),
            self.row("Gate A", "IN", self.now.replace(hour=8, minute=1)),
            self.row("Gate A", "OUT", self.now.replace(hour=8, minute=2)),
        ]
        self.install_rows(rows)

        levels = self.service.get_congestion_levels(camera_id="Gate A")

        self.assertEqual(levels[0]["current"], 1)
        self.assertEqual(levels[0]["historical_max"], 2)
        self.assertEqual(levels[0]["percent"], 50)
        self.assertEqual(levels[0]["status"], "MEDIUM")

    def test_week_over_week_delta(self):
        now = datetime.now().astimezone()
        this_week = now - timedelta(days=1)
        last_week = now - timedelta(days=8)
        rows = [
            self.row("Gate A", "IN", this_week),
            self.row("Gate A", "OUT", this_week),
            self.row("Gate A", "IN", last_week),
        ]
        self.install_rows(rows)

        comparison = self.service.get_week_over_week(camera_id="Gate A")

        self.assertEqual(comparison["current_total"], 2)
        self.assertEqual(comparison["previous_total"], 1)
        self.assertEqual(comparison["change_percent"], 100)
        self.assertEqual(comparison["direction"], "up")


class RushDetectionTest(unittest.TestCase):
    def test_detects_two_times_average_in_ten_minutes(self):
        class FakeService:
            def get_current_count(self, camera_id, minutes=10, table="simulated_logs", direction=None):
                return 24

            def get_hourly_stats(self, camera_id, table="simulated_logs", bucket_minutes=10, direction=None):
                return 12, 3

        detector = RushDetection(service=FakeService())

        result = detector.detect_rush("Gate A", minutes=10, table="simulated_logs")

        self.assertEqual(result["status"], "RUSH ALERT")
        self.assertTrue(result["is_active"])
        self.assertEqual(result["ratio"], 2)


if __name__ == "__main__":
    unittest.main()
