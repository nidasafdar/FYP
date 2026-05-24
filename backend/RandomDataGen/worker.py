import json
import math
import random
import time
from datetime import datetime
from urllib import request
from urllib.error import URLError, HTTPError

try:
    from analytics_service import AnalyticsService
except Exception:
    try:
        from backend.analytics_service import AnalyticsService
    except Exception:
        AnalyticsService = None


def _compute_intensity(service, camera_id):
    """Compute runtime intensity from historical behavior instead of fixed peak hours."""
    if service is None:
        return 1.0

    try:
        mean, std = service.get_hourly_stats(camera_id, table="simulated_logs")
        recent = service.get_current_count(camera_id, minutes=5, table="simulated_logs")

        if std <= 0:
            std = 1.0

        # z > 0 means current traffic is above historical average for this hour.
        z = (recent - mean) / std
        if z >= 2.0:
            return 1.6
        if z >= 1.0:
            return 1.3
        if z <= -1.5:
            return 0.7
        return 1.0
    except Exception:
        return 1.0


def _sample_poisson(rng, expected):
    """Small dependency-free Poisson sampler for event counts."""
    if expected <= 0:
        return 0
    if expected > 30:
        return max(0, int(round(rng.gauss(expected, math.sqrt(expected)))))

    limit = math.exp(-expected)
    product = 1.0
    count = 0
    while product > limit:
        count += 1
        product *= rng.random()
    return count - 1


def _time_of_day_profile(now):
    """Return normal traffic volume and IN share for the current local hour."""
    hour = now.hour + (now.minute / 60)

    if 0 <= hour < 6:
        return 0.08, 0.50
    if 6 <= hour < 8:
        return 0.55, 0.75
    if 8 <= hour < 10:
        return 1.45, 0.86
    if 10 <= hour < 12:
        return 1.10, 0.64
    if 12 <= hour < 14:
        return 1.75, 0.55
    if 14 <= hour < 16:
        return 1.15, 0.50
    if 16 <= hour < 19:
        return 1.55, 0.24
    if 19 <= hour < 22:
        return 0.62, 0.30
    return 0.16, 0.42


def _maybe_start_event(rng, now, active_event):
    if active_event and now.timestamp() < active_event["ends_at"]:
        return active_event

    # Roughly one noticeable incident every 10-20 minutes per worker.
    if rng.random() > 0.006:
        return None

    hour = now.hour
    if 7 <= hour < 11:
        choices = ["arrival_rush", "arrival_rush", "brief_lull"]
    elif 12 <= hour < 15:
        choices = ["noon_rush", "noon_rush", "brief_lull"]
    elif 16 <= hour < 20:
        choices = ["exit_wave", "exit_wave", "brief_lull"]
    else:
        choices = ["arrival_rush", "exit_wave", "brief_lull"]

    kind = rng.choice(choices)
    duration = rng.randint(90, 300)
    return {
        "kind": kind,
        "ends_at": now.timestamp() + duration,
        "multiplier": rng.uniform(2.2, 4.5),
    }


def _event_adjustment(active_event, incoming_rate, outgoing_rate):
    if not active_event:
        return incoming_rate, outgoing_rate

    multiplier = active_event["multiplier"]
    kind = active_event["kind"]

    if kind in ("arrival_rush", "noon_rush"):
        return incoming_rate * multiplier, outgoing_rate * 0.75
    if kind == "exit_wave":
        return incoming_rate * 0.65, outgoing_rate * multiplier
    if kind == "brief_lull":
        return incoming_rate * 0.2, outgoing_rate * 0.25
    return incoming_rate, outgoing_rate


def _post_counts(api_base_url, payload):
    url = f"{api_base_url.rstrip('/')}/api/simulator/ingest"
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")

    with request.urlopen(req, timeout=10) as resp:
        data = resp.read().decode("utf-8")
        return resp.getcode(), data


def run_worker(camera_id, source_id, stop_event, status_queue, api_base_url="http://127.0.0.1:8000", interval_seconds=5):
    """Generate only incoming/outgoing counts for one source and send to API for persistence."""
    rng = random.Random()
    rng.seed(f"{camera_id}:{time.time()}")

    session_id = f"SIM_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    service = AnalyticsService() if AnalyticsService is not None else None
    simulated_occupancy = 0
    active_event = None

    while not stop_event.is_set():
        now = datetime.now().astimezone()
        history_intensity = _compute_intensity(service, camera_id)
        day_volume, incoming_share = _time_of_day_profile(now)
        active_event = _maybe_start_event(rng, now, active_event)

        # Irregular local jitter keeps the graph from looking mechanically smooth.
        jitter = rng.uniform(0.55, 1.55)
        total_rate = 2.1 * day_volume * history_intensity * jitter
        incoming_rate = total_rate * incoming_share
        outgoing_rate = total_rate * (1 - incoming_share)
        incoming_rate, outgoing_rate = _event_adjustment(active_event, incoming_rate, outgoing_rate)

        # If the local simulated area is nearly empty, exits become rare.
        if simulated_occupancy < 5:
            outgoing_rate *= 0.20
        elif simulated_occupancy < 15:
            outgoing_rate *= 0.55

        incoming_count = _sample_poisson(rng, incoming_rate)
        outgoing_count = min(simulated_occupancy + incoming_count, _sample_poisson(rng, outgoing_rate))
        simulated_occupancy = max(0, simulated_occupancy + incoming_count - outgoing_count)

        payload = {
            "source_id": source_id,
            "camera_id": camera_id,
            "timestamp": now.isoformat(),
            "incoming_count": incoming_count,
            "outgoing_count": outgoing_count,
            "session_id": session_id,
        }

        ok = True
        error = None
        inserted = 0
        try:
            _, raw = _post_counts(api_base_url, payload)
            parsed = json.loads(raw)
            inserted = int(parsed.get("inserted_rows", 0))
        except (URLError, HTTPError, TimeoutError, ValueError) as e:
            ok = False
            error = str(e)

        status_queue.put({
            "camera_id": camera_id,
            "source_id": source_id,
            "session_id": session_id,
            "timestamp": now.isoformat(),
            "incoming_count": incoming_count,
            "outgoing_count": outgoing_count,
            "simulated_occupancy": simulated_occupancy,
            "event": active_event["kind"] if active_event else None,
            "inserted_rows": inserted,
            "ok": ok,
            "error": error,
        })

        stop_event.wait(interval_seconds)
