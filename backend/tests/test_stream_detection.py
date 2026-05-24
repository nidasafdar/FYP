import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend import api
from backend import stream_supervisor
from backend.stream_worker import get_crossing_direction


class StreamDirectionTest(unittest.TestCase):
    def test_vertical_left_to_right_is_in(self):
        self.assertEqual(get_crossing_direction(90, 110, 100), "IN")

    def test_vertical_right_to_left_is_out(self):
        self.assertEqual(get_crossing_direction(110, 90, 100), "OUT")

    def test_no_crossing_has_no_direction(self):
        self.assertIsNone(get_crossing_direction(80, 95, 100))


class StreamSupervisorSourceTest(unittest.TestCase):
    def test_loads_only_stream_sources_from_repository(self):
        class FakeRepository:
            def list_sources(self):
                return [
                    {
                        "id": "stream-source",
                        "mode": "stream",
                        "camera_id": "Camera_stream",
                        "streamUrl": "rtsp://example.test/live",
                    },
                    {
                        "id": "generated-source",
                        "mode": "generate",
                        "camera_id": "Camera_generated",
                        "streamUrl": "",
                    },
                ]

        supervisor = stream_supervisor.StreamSupervisor()

        with patch.object(stream_supervisor, "SourceRepository", FakeRepository):
            sources = supervisor._load_stream_sources()

        self.assertIn("Camera_stream", sources)
        self.assertNotIn("Camera_generated", sources)
        self.assertEqual(sources["Camera_stream"]["stream_url"], "rtsp://example.test/live")


class ApiFrameTest(unittest.TestCase):
    def test_camera_frame_uses_per_camera_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            frames_dir = os.path.join(temp_dir, "frames")
            os.makedirs(frames_dir)
            frame_path = os.path.join(frames_dir, "Camera_abc.jpg")
            with open(frame_path, "wb") as f:
                f.write(b"fake-jpeg")

            with patch.object(api, "BACKEND_DIR", temp_dir):
                response = api.frame(camera="Camera_abc")

        self.assertEqual(response.path, frame_path)

    def test_missing_camera_frame_returns_404(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(api, "BACKEND_DIR", temp_dir):
                with self.assertRaises(HTTPException) as raised:
                    api.frame(camera="Camera_missing")

        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
