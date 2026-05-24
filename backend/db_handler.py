import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

load_dotenv()

class DBHandler:
    def __init__(self, camera_id=None):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.camera_id = camera_id if camera_id else os.getenv("DEFAULT_CAMERA_ID", "Camera_01")
        
        if not self.url or not self.key:
            print("[WARN] Supabase credentials missing in .env")
        
        # Initialize Supabase Client
        self.supabase: Client = create_client(self.url, self.key)
        print(f"[SUCCESS] DBHandler initialized via Supabase API (Unit: {self.camera_id})")

    def insert_detection(self, track_id, obj_class, confidence, bbox, 
                         frame_number, direction=None, session_id="live", table="detections"):
        """Saves a detection event to Supabase using the API."""
        l, t, r, b = bbox
        
        data = {
            "track_id": int(track_id),
            "object_class": obj_class,
            "confidence": float(confidence),
            "bbox_x1": int(l),
            "bbox_y1": int(t),
            "bbox_x2": int(r),
            "bbox_y2": int(b),
            "frame_number": int(frame_number),
            "camera_id": self.camera_id,
            "direction": direction,
            "session_id": session_id,
            "timestamp": datetime.now().astimezone().isoformat()
        }
        
        import time
        for attempt in range(3):
            try:
                self.supabase.table(table).insert(data).execute()
                break # Success
            except Exception as e:
                if attempt == 2: # Last attempt
                    print(f"[ERROR] Supabase Insert Error (Final): {e}")
                else:
                    print(f"[WARN] Supabase Insert Attempt {attempt+1} failed, retrying...")
                    time.sleep(0.5)

    def get_total_visitors(self, session_id=None, direction='IN', table="detections"):
        """Fetch counts using API filtering."""
        try:
            query = self.supabase.table(table).select("id", count="exact").eq("camera_id", self.camera_id).eq("direction", direction)
            if session_id:
                query = query.eq("session_id", session_id)
            
            res = query.execute()
            return res.count if res.count is not None else 0
        except Exception as e:
            print(f"[ERROR] DB READ ERROR: {e}")
            return 0

    def clear_detections(self):
        """Clears detections for the active camera."""
        try:
            # Supabase requires a filter for deletes.
            self.supabase.table("detections").delete().eq("camera_id", self.camera_id).execute()
            print(f"[CLEARED] Database Cleared for {self.camera_id}")
        except Exception as e:
            print(f"[ERROR] Error clearing detections: {e}")

    def close(self):
        """HTTP clients don't need persistent connection closure."""
        pass