import os
from typing import Optional
from uuid import uuid4

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

TABLE_NAME = "camera_sources"


class SourceRepositoryError(Exception):
    pass


class SourceRepository:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not self.url or not self.key:
            raise SourceRepositoryError("Supabase credentials are missing")

        self.supabase: Client = create_client(self.url, self.key)

    def list_sources(self):
        response = (
            self.supabase
            .table(TABLE_NAME)
            .select("*")
            .order("created_at", desc=False)
            .execute()
        )
        return [self._to_api_source(row) for row in response.data or []]

    def create_source(self, title: str, description: str, mode: str, stream_url: Optional[str] = None):
        source_type = "stream" if mode == "stream" else "generate"
        camera_id = f"Camera_{uuid4().hex[:8]}"
        payload = {
            "title": title.strip(),
            "description": description.strip(),
            "source_type": source_type,
            "stream_url": stream_url.strip() if source_type == "stream" and stream_url else None,
            "camera_id": camera_id,
        }

        response = self.supabase.table(TABLE_NAME).insert(payload).execute()
        if not response.data:
            raise SourceRepositoryError("Supabase did not return the created source")

        return self._to_api_source(response.data[0])

    def _to_api_source(self, row):
        return {
            "id": row.get("id"),
            "title": row.get("title", ""),
            "description": row.get("description", ""),
            "mode": row.get("source_type", "generate"),
            "streamUrl": row.get("stream_url") or "",
            "stream_url": row.get("stream_url") or "",
            "camera_id": row.get("camera_id"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }
