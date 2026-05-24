import os
from collections import defaultdict
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv():
        return None

try:
    from supabase import create_client, Client
except (ImportError, ModuleNotFoundError):
    Client = object

    def create_client(*_args, **_kwargs):
        raise RuntimeError("Supabase client is not installed")

from .config import DEFAULT_CAMERA_ID

load_dotenv()
SOURCE_TABLE = "camera_sources"

class AnalyticsService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.default_camera = os.getenv("DEFAULT_CAMERA_ID", "Camera_01")
        self.supabase: Client = create_client(self.url, self.key)
        print("[SUCCESS] AnalyticsService shifted to Supabase Client (No-Cursor)")

    def get_latest_session_id(self, camera_id=None, table="detections"):
        """Fetches the latest data session, optionally scoped to one camera."""
        try:
            query = self.supabase.table(table).select("session_id").order("timestamp", desc=True).limit(1)
            if camera_id:
                query = query.eq("camera_id", camera_id)

            res = query.execute()
            return res.data[0]['session_id'] if res.data else None
        except:
            return None

    def get_source_camera_ids(self, source_type=None):
        """Fetch active camera IDs from the source table for DB-side analytics filtering."""
        query = self.supabase.table(SOURCE_TABLE).select("camera_id")
        if source_type:
            query = query.eq("source_type", source_type)

        res = query.execute()
        return [
            row.get("camera_id")
            for row in res.data or []
            if row.get("camera_id")
        ]

    def _parse_timestamp(self, value):
        if isinstance(value, datetime):
            return value.astimezone()
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone()
        except ValueError:
            return None

    def _query_logs(self, table="detections", camera_id=None, camera_ids=None, session_id=None, direction=None, date=None, start_dt=None, end_dt=None):
        query = self.supabase.table(table).select("id, timestamp, camera_id, direction, session_id")
        if camera_id:
            query = query.eq("camera_id", camera_id)
        if camera_ids is not None:
            if not camera_ids:
                return []
            query = query.in_("camera_id", camera_ids)
        if session_id:
            query = query.eq("session_id", session_id)
        if direction:
            query = query.eq("direction", direction)
        if date:
            query = query.gte("timestamp", f"{date}T00:00:00").lte("timestamp", f"{date}T23:59:59")
        if start_dt:
            query = query.gte("timestamp", start_dt.isoformat())
        if end_dt:
            query = query.lte("timestamp", end_dt.isoformat())

        res = query.order("timestamp").execute()
        return res.data or []

    def _bucket_label(self, dt, bucket_minutes=30):
        minute = (dt.minute // bucket_minutes) * bucket_minutes
        start = dt.replace(minute=minute, second=0, microsecond=0)
        end = start + timedelta(minutes=bucket_minutes)
        return start, f"{start.strftime('%I:%M %p').lstrip('0')} - {end.strftime('%I:%M %p').lstrip('0')}"

    def _count_rows(self, rows, direction=None):
        if direction is None:
            return len(rows)
        return sum(1 for row in rows if row.get("direction") == direction)

    def get_total_visitors(self, camera_id=None, session_id=None, direction='IN', date=None, hours=None, table="detections"):
        """Standard count for entries or exits."""
        query = self.supabase.table(table).select("*", count="exact")
        
        if camera_id: query = query.eq("camera_id", camera_id)
        if direction: query = query.eq("direction", direction)
        if session_id: query = query.eq("session_id", session_id)
        
        # Date filter logic
        if date:
            start_dt = f"{date}T00:00:00"
            end_dt = f"{date}T23:59:59"
            query = query.gte("timestamp", start_dt).lte("timestamp", end_dt)
        
        # Hour filter logic (simplified for API)
        res = query.execute()
        count = res.count if res.count is not None else 0
        
        # If hour filtering is needed, we filter the list in Python
        if hours and res.data:
            start, end = hours
            filtered = [r for r in res.data if start <= datetime.fromisoformat(r['timestamp']).astimezone().hour <= end]
            return len(filtered)
            
        return count

    def get_current_occupancy(self, camera_id=None, session_id=None, date=None, hours=None, table="detections"):
        """Calculates IN minus OUT."""
        ins = self.get_total_visitors(camera_id, session_id, 'IN', date, hours, table=table)
        outs = self.get_total_visitors(camera_id, session_id, 'OUT', date, hours, table=table)
        return max(0, ins - outs)

    def get_realtime_occupancy(self, camera_id=None, session_id=None, date=None, table="detections"):
        rows = self._query_logs(table=table, camera_id=camera_id, session_id=session_id, date=date)
        incoming = self._count_rows(rows, "IN")
        outgoing = self._count_rows(rows, "OUT")
        return {
            "camera_id": camera_id,
            "incoming": incoming,
            "outgoing": outgoing,
            "current": max(0, incoming - outgoing),
            "scope": "gate" if camera_id else "campus",
            "last_updated": datetime.now().astimezone().isoformat(),
        }

    def get_flow_split(self, camera_id=None, session_id=None, date=None, table="detections"):
        rows = self._query_logs(table=table, camera_id=camera_id, session_id=session_id, date=date)
        incoming = self._count_rows(rows, "IN")
        outgoing = self._count_rows(rows, "OUT")
        total = incoming + outgoing
        incoming_pct = round((incoming / total) * 100) if total else 0
        outgoing_pct = 100 - incoming_pct if total else 0
        return {
            "incoming": incoming,
            "outgoing": outgoing,
            "total": total,
            "incoming_percent": incoming_pct,
            "outgoing_percent": outgoing_pct,
        }

    def get_hourly_trend(self, camera_id=None, session_id=None, date=None, table="detections"):
        """Aggregates data by hour for charts."""
        rows = self._query_logs(table=table, camera_id=camera_id, session_id=session_id, date=date, direction="IN")
        if not rows:
            return []

        hours = {}
        for r in rows:
            dt = self._parse_timestamp(r.get('timestamp'))
            if not dt:
                continue
            hr = dt.hour
            hours[hr] = hours.get(hr, 0) + 1
        
        return sorted([[hr, count] for hr, count in hours.items()])

    def get_daily_trend(self, camera_id=None, table="detections"):
        """Aggregates data by day for charts."""
        rows = self._query_logs(table=table, camera_id=camera_id, direction="IN")
        if not rows:
            return []

        days = {}
        for r in rows:
            dt = self._parse_timestamp(r.get('timestamp'))
            if not dt:
                continue
            day = dt.date().isoformat()
            days[day] = days.get(day, 0) + 1
        
        return sorted([[day, count] for day, count in days.items()])

    def get_live_occupancy_trend(self, camera_id=None, session_id=None, table="detections"):
        """Calculates running occupancy over the last hour or current session."""
        query = self.supabase.table(table).select("timestamp, direction")
        if camera_id:
            query = query.eq("camera_id", camera_id)
        
        initial_occupancy = 0
        if session_id:
            query = query.eq("session_id", session_id)
        else:
            one_hour_ago = (datetime.now().astimezone() - timedelta(hours=1)).isoformat()
            query = query.gte("timestamp", one_hour_ago)
            
            # Try to get initial occupancy before this hour to prevent starting from 0 if there's history
            try:
                ins_before = self.supabase.table(table).select("id", count="exact").eq("direction", "IN").lt("timestamp", one_hour_ago)
                outs_before = self.supabase.table(table).select("id", count="exact").eq("direction", "OUT").lt("timestamp", one_hour_ago)
                if camera_id:
                    ins_before = ins_before.eq("camera_id", camera_id)
                    outs_before = outs_before.eq("camera_id", camera_id)
                ins_before = ins_before.execute()
                outs_before = outs_before.execute()
                ins_count = ins_before.count if ins_before.count is not None else 0
                outs_count = outs_before.count if outs_before.count is not None else 0
                initial_occupancy = max(0, ins_count - outs_count)
            except:
                initial_occupancy = 0
                
        res = query.order("timestamp").execute()
            
        if not res.data: return []
        
        # Calculate running total in Python
        trend = []
        current = initial_occupancy
        for r in res.data:
            if r['direction'] == 'IN': current += 1
            elif r['direction'] == 'OUT': current -= 1
            current = max(0, current) # Prevent negative values
            
            dt = self._parse_timestamp(r.get('timestamp'))
            if not dt:
                continue
            # Convert to local time for the dashboard display
            minute = dt.astimezone().strftime("%H:%M")
            trend.append([minute, current])
        
        return trend

    def get_average_occupancy(self, camera_id, table="detections"):
        trend = self._running_occupancy_points(camera_id=camera_id, table=table)
        if not trend:
            return 0
        return round(sum(point[1] for point in trend) / len(trend), 2)

    def get_peak_hour(self, camera_id=None, session_id=None, table="detections"):
        """Finds the hour with most entries."""
        trend = self.get_hourly_trend(camera_id, session_id, table=table)
        if not trend: return 0
        return max(trend, key=lambda x: x[1])[0]
    def get_peak_slots(self, camera_id=None, session_id=None, date=None, hours=None, bucket_minutes=30, limit=3, table="detections"):
        rows = self._query_logs(table=table, camera_id=camera_id, session_id=session_id, date=date, direction="IN")
        buckets = {}
        for row in rows:
            dt = self._parse_timestamp(row.get("timestamp"))
            if not dt:
                continue
            if hours and not (hours[0] <= dt.hour <= hours[1]):
                continue
            bucket_start, label = self._bucket_label(dt, bucket_minutes)
            current = buckets.setdefault(bucket_start, {"time": label, "count": 0, "hour": bucket_start.hour})
            current["count"] += 1

        ranked = sorted(buckets.values(), key=lambda item: (-item["count"], item["time"]))
        return ranked[:limit]

    def get_peak_hours(self, camera_id=DEFAULT_CAMERA_ID, session_id=None, date=None, hours=None, table="detections"):
        return self.get_peak_slots(camera_id, session_id, date, hours, bucket_minutes=60, limit=3, table=table)

    def get_average_flow(self, camera_id=DEFAULT_CAMERA_ID, session_id=None, date=None, hours=None, table="detections"):
        trend = self.get_hourly_trend(camera_id, session_id, date, table=table)
        if hours:
            trend = [point for point in trend if hours[0] <= point[0] <= hours[1]]
        if not trend:
            return 0
        return round(sum(point[1] for point in trend) / len(trend), 2)

    def get_current_count(self, camera_id, minutes=5, table="detections", direction=None):
        """Fetches movement count in a recent sliding window."""
        delta = (datetime.now().astimezone() - timedelta(minutes=minutes)).isoformat()
        res = self.supabase.table(table)\
            .select("id", count="exact")\
            .gte("timestamp", delta)\
        
        if camera_id:
            res = res.eq("camera_id", camera_id)
        if direction:
            res = res.eq("direction", direction)
        res = res.execute()
        return res.count if res.count is not None else 0

    def get_hourly_stats(self, camera_id, table="detections", bucket_minutes=10, direction=None):
        """Calculates historical mean/std for same-hour movement buckets."""
        current_hour = datetime.now().hour # local hour
        rows = self._query_logs(table=table, camera_id=camera_id, direction=direction)
        if not rows:
            return 0.0, 1.0

        counts_per_bucket = {}
        for r in rows:
            dt = self._parse_timestamp(r.get('timestamp'))
            if not dt:
                continue
            if dt.hour == current_hour:
                minute = (dt.minute // bucket_minutes) * bucket_minutes
                key = (dt.date().isoformat(), minute)
                counts_per_bucket[key] = counts_per_bucket.get(key, 0) + 1
        
        counts = list(counts_per_bucket.values())
        if not counts:
            return 0.0, 1.0
        
        mean = sum(counts) / len(counts)
        # Simplified variance
        var = sum((x - mean) ** 2 for x in counts) / len(counts)
        std = var ** 0.5
        return mean, max(std, 1.0)

    def get_rush_event_count(self, camera_id=None, date=None, table="detections", bucket_minutes=10, multiplier=2.0, minimum_count=10):
        rows = self._query_logs(table=table, camera_id=camera_id, date=date)
        if not rows:
            return 0

        buckets = defaultdict(int)
        for row in rows:
            dt = self._parse_timestamp(row.get("timestamp"))
            if not dt:
                continue
            minute = (dt.minute // bucket_minutes) * bucket_minutes
            buckets[(dt.hour, minute)] += 1

        if not buckets:
            return 0
        average = sum(buckets.values()) / len(buckets)
        if average <= 0:
            return 0
        return sum(1 for count in buckets.values() if count >= minimum_count and count >= average * multiplier)

    def get_heatmap_data(self, camera_id=None, table="detections"):
        """Returns data structured for hourly and daily heatmaps."""
        rows = self._query_logs(table=table, camera_id=camera_id, direction="IN")
        if not rows:
            return {"hourly": [], "daily": []}

        # For Hourly: Day of Week vs Hour of Day
        # For Daily: Week of Year vs Day of Week
        hourly_matrix = {} # (day_of_week, hour) -> count
        daily_matrix = {}  # (week, day_of_week) -> count
        
        for r in rows:
            dt = self._parse_timestamp(r.get('timestamp'))
            if not dt:
                continue
            
            # Hourly flow (Day of Week vs Hour)
            dow = dt.strftime("%a") # Mon, Tue...
            hr = dt.hour
            key_h = (dow, hr)
            hourly_matrix[key_h] = hourly_matrix.get(key_h, 0) + 1
            
            # Daily comparison (Date-based for GitHub style)
            date_str = dt.date().isoformat()
            daily_matrix[date_str] = daily_matrix.get(date_str, 0) + 1

        return {
            "hourly": [{"Day": k[0], "Hour": k[1], "Traffic": v} for k, v in hourly_matrix.items()],
            "daily": [{"Date": k, "Volume": v} for k, v in daily_matrix.items()]
        }

    def get_camera_comparison(self, table="detections"):
        """Gets total IN traffic for all cameras for comparison."""
        return self.get_gate_comparison(table=table)

    def get_gate_comparison(self, date=None, table="detections", camera_ids=None):
        """Gets total traffic distribution across gates."""
        rows = self._query_logs(table=table, camera_ids=camera_ids, date=date, direction="IN")
        if not rows:
            return []

        counts = {}
        for r in rows:
            c = r['camera_id']
            counts[c] = counts.get(c, 0) + 1

        total = sum(counts.values())
        return [
            {
                "camera": k,
                "traffic": v,
                "percent": round((v / total) * 100) if total else 0,
            }
            for k, v in sorted(counts.items(), key=lambda item: item[1], reverse=True)
        ]

    def _running_occupancy_points(self, camera_id=None, date=None, table="detections"):
        rows = self._query_logs(table=table, camera_id=camera_id, date=date)
        current = 0
        points = []
        for row in rows:
            direction = row.get("direction")
            if direction == "IN":
                current += 1
            elif direction == "OUT":
                current -= 1
            current = max(0, current)
            dt = self._parse_timestamp(row.get("timestamp"))
            if dt:
                points.append((dt, current))
        return points

    def get_congestion_levels(self, camera_id=None, table="detections"):
        rows = self._query_logs(table=table, camera_id=camera_id)
        cameras = sorted({row.get("camera_id") for row in rows if row.get("camera_id")})
        if camera_id and camera_id not in cameras:
            cameras = [camera_id]

        levels = []
        for cam in cameras:
            all_points = self._running_occupancy_points(camera_id=cam, table=table)
            current = all_points[-1][1] if all_points else 0
            historical_max = max((point[1] for point in all_points), default=0)
            percent = round((current / historical_max) * 100) if historical_max else 0
            if percent >= 75:
                status = "HIGH"
            elif percent >= 40:
                status = "MEDIUM"
            else:
                status = "LOW"
            levels.append({
                "camera": cam,
                "current": current,
                "historical_max": historical_max,
                "percent": percent,
                "status": status,
            })

        return levels

    def get_daily_summary(self, camera_id=None, session_id=None, date=None, table="detections"):
        target_date = date or datetime.now().astimezone().date().isoformat()
        flow = self.get_flow_split(camera_id=camera_id, session_id=session_id, date=target_date, table=table)
        peak = self.get_peak_slots(camera_id=camera_id, session_id=session_id, date=target_date, table=table, limit=1)
        rush_events = self.get_rush_event_count(camera_id=camera_id, date=target_date, table=table)
        peak_slot = peak[0] if peak else {"time": "No peak yet", "count": 0, "hour": None}
        return {
            "date": target_date,
            "total_entries": flow["incoming"],
            "total_exits": flow["outgoing"],
            "net_occupancy": max(0, flow["incoming"] - flow["outgoing"]),
            "peak_time": peak_slot["time"],
            "peak_count": peak_slot["count"],
            "rush_events": rush_events,
        }

    def get_week_over_week(self, camera_id=None, table="detections"):
        now = datetime.now().astimezone()
        start_this_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        start_last_week = start_this_week - timedelta(days=7)
        end_last_week = start_this_week - timedelta(microseconds=1)

        current_rows = self._query_logs(table=table, camera_id=camera_id, start_dt=start_this_week, end_dt=now)
        previous_rows = self._query_logs(table=table, camera_id=camera_id, start_dt=start_last_week, end_dt=end_last_week)
        current_total = self._count_rows(current_rows, "IN") + self._count_rows(current_rows, "OUT")
        previous_total = self._count_rows(previous_rows, "IN") + self._count_rows(previous_rows, "OUT")

        if previous_total == 0:
            change = 100 if current_total > 0 else 0
        else:
            change = round(((current_total - previous_total) / previous_total) * 100)

        if change > 0:
            direction = "up"
        elif change < 0:
            direction = "down"
        else:
            direction = "same"

        return {
            "current_total": current_total,
            "previous_total": previous_total,
            "change_percent": change,
            "direction": direction,
        }

    def close(self):
        """No closure needed for HTTP-based clients."""
        pass
