from analytics_engine import AnalyticsEngine
from config import DEFAULT_CAMERA_ID

# Initialize Engine
engine = AnalyticsEngine()

# Get data for dashboard
data = engine.get_dashboard_data(DEFAULT_CAMERA_ID)

if data:
    print("\n[PHASE 5 READY] DASHBOARD DATA")
    print("-" * 30)
    print(f"Camera ID:    {data['camera']}")
    print(f"Entries/Exits: {data['entries']} IN / {data['exits']} OUT")
    print(f"Occupancy:    {data['occupancy']}")
    print(f"Peak Hour:    {data['peak_hour']}:00")
    print(f"Rush Status:  {data['rush_status']}")
    print(f"Congestion:   {data['congestion']}")
    print(f"Hourly Trend: {len(data['hourly_trend'])} hours recorded")
    print("-" * 30)
else:
    print("[ERROR] Failed to fetch dashboard data.")

# Close connection
engine.close()
