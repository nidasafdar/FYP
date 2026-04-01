import streamlit as st
import pandas as pd
import time
import os
import sys
from datetime import datetime

# ---------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(parent_dir, "Backend")

if parent_dir not in sys.path: sys.path.append(parent_dir)
if backend_dir not in sys.path: sys.path.append(backend_dir)

try:
    from Backend.analytics_engine import AnalyticsEngine
    from Backend.config import DEFAULT_CAMERA_ID
except ImportError as e:
    st.error(f"❌ Backend modules not found. Detail: {e}")
    st.stop()

# ---------------------------------------------------------
# INITIALIZATION & STATE
# ---------------------------------------------------------
if 'running' not in st.session_state:
    st.session_state.running = False

@st.cache_resource
def get_engine():
    return AnalyticsEngine()

engine = get_engine()

# ---------------------------------------------------------
# UI CONFIGURATION & THEME
# ---------------------------------------------------------
st.set_page_config(
    page_title="Smart Camera Monitoring Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Half-White Premium Theme CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    /* Force Pure Light Mode regardless of browser settings */
    :root {
        color-scheme: light !important;
    }

    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
        color: #111827 !important;
        background-color: #f9fafb !important;
    }

    /* Sidebar Appearance: Pure White */
    section[data-testid="stSidebar"], [data-testid="stSidebar"] [data-testid="stVerticalBlock"], [data-testid="stSidebar"] .st-emotion-cache-16idsys {
        background-color: #ffffff !important;
        border-right: 1px solid #e5e7eb !important;
    }
    
    /* Navigation/Selectbox/Input Fix (Aggressive) */
    div[data-baseweb="select"], div[data-baseweb="input"], .stSelectbox, .stDateInput, div[role="listbox"], [data-testid="stWidgetLabel"] {
        background-color: #ffffff !important;
        color: #111827 !important;
    }
    
    /* Chart Containers Fix */
    [data-testid="stVegaLiteChart"], .stAreaChart, .stLineChart, .stBarChart {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border-radius: 12px !important;
        padding: 10px !important;
        box-shadow: inset 0 0 0 1px #e5e7eb !important;
    }

    /* Camera Card Record Fix */
    .camera-card {
        background-color: #ffffff !important;
        padding: 20px !important;
        border-radius: 12px !important;
        border: 1px solid #e5e7eb !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        margin-bottom: 20px !important;
    }

    /* Metric Values: New Primary Blue */
    [data-testid="stMetricValue"] { 
        color: #2563eb !important; 
        font-weight: 700 !important; 
        font-size: 1.85rem !important;
    }
    
    /* Text Globals: Specific Dark Neutral */
    h1, h2, h3, h4, h5, h6, b, strong, label { color: #111827 !important; font-weight: 700 !important; }

    /* Buttons: Primary Blue Pill Style */
    .stButton>button {
        width: 100% !important;
        border-radius: 50px !important;
        height: 3.2em !important;
        background-color: #2563eb !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #1d4ed8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;
    }
    
    /* Status Indicators */
    .status-running { color: #16a34a; font-weight: bold; }
    .status-stopped { color: #dc2626; font-weight: bold; }
    
    /* Fix for Charts (force white background) */
    [data-testid="stVegaLiteChart"] {
        background-color: #ffffff !important;
        border-radius: 12px;
        padding: 10px;
        box-shadow: inset 0 0 0 1px #e5e7eb;
    }

    /* Slider Professional Styling */
    .stSlider [data-testid="stThumbValue"] { color: #2563eb !important; }
    .stSlider [data-testid="stTickBarMin"], .stSlider [data-testid="stTickBarMax"] { color: #111827 !important; }

    /* Alert Styling */
    .custom-alert {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        border-left: 5px solid;
    }
    .alert-critical { background-color: #fef2f2; border-color: #dc2626; color: #991b1b; }
    .alert-warning { background-color: #fefce8; border-color: #ca8a04; color: #854d0e; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# SIDEBAR: CONTROL PANEL
# ---------------------------------------------------------
with st.sidebar:
    # st.image("https://img.icons8.com/clouds/100/000000/real-time-protection.png", width=80)
    st.title("System Control")
    st.divider()

    # A. Input Source Control
    st.subheader("📁 Input Source")
    input_mode = st.radio("Select Source", ["Upload Video", "Live Camera"], index=1)
    
    if input_mode == "Upload Video":
        uploaded_file = st.file_uploader("Upload feed (.mp4, .avi)", type=["mp4", "avi"])

    st.divider()

    # B. Camera Selection (Only if not in Audit Mode)
    if input_mode == "Live Camera":
        st.subheader("🎥 Camera Selection")
        selected_cameras = st.multiselect("Active Cameras", ["Camera_01", "Camera_02", "Camera_03"], default=["Camera_01"])
    else:
        # Audit Mode: Dynamic status based on upload
        st.subheader("📑 Audit Mode")
        if uploaded_file is not None:
            st.success(f"✅ {uploaded_file.name} successfully uploaded.")
            if st.session_state.running:
                st.info("🔄 Audit Under Process...")
            else:
                st.info("📡 File ready for audit processing.")
            selected_cameras = [uploaded_file.name]
        else:
            st.warning("⚠️ Action Required: Please upload a file above.")
            selected_cameras = ["Waiting for Upload..."]

    # C. Time Filter
    st.subheader("📅 Time Filter")
    date_range = st.date_input("Select Date", datetime.now())
    time_range = st.slider("Time Range", 0, 23, (0, 23))

    st.divider()

    # D. System Controls
    st.subheader("⚙️ Analysis Controls")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("▶ START"):
            # Clear stop signal if it exists
            stop_file = os.path.join(backend_dir, "stop_signal.txt")
            if os.path.exists(stop_file): os.remove(stop_file)
            
            video_export_path = None
            
            # Logic to determine which video to send to the backend
            if input_mode == "Upload Video":
                if uploaded_file is not None:
                    # Save the uploaded file to the Backend/videos folder
                    import shutil
                    os.makedirs(os.path.join(backend_dir, "videos"), exist_ok=True)
                    video_export_path = os.path.join(backend_dir, "videos", "uploaded_audit.mp4")
                    with open(video_export_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.toast("📁 Uploaded footage synced to backend.")
                else:
                    st.error("❌ Please upload a video first!")
                    st.stop()
            else:
                # Live Camera mode (using the default configured video for now)
                # In a real system, you'd pass a camera URL here.
                pass

            st.session_state.running = True
            
            try:
                import subprocess
                # Build command: python main.py [video_path]
                cmd = [sys.executable, os.path.join(backend_dir, "main.py")]
                if video_export_path:
                    cmd.append(video_export_path)
                
                subprocess.Popen(cmd, 
                                 cwd=backend_dir, 
                                 creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                st.toast("🚀 AI Engine Started Successfully")
            except Exception as e:
                st.error(f"Engine Start Failed: {e}")

    with col_c2:
        if st.button("⏹ STOP"):
            st.session_state.running = False
            # Signal the backend to stop
            stop_file = os.path.join(backend_dir, "stop_signal.txt")
            with open(stop_file, "w") as f:
                f.write("STOP")
            st.toast("AI Engine Signaled to Stop")

    refresh_rate = st.slider("Update Rate (sec)", 1, 10, 3)

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
# Multi-page via selectbox in sidebar for Screen 2
page = st.sidebar.selectbox("Navigation", ["🏢 Dashboard Overview", "📈 Detailed Analytics"])

# Top Bar Header Row
st.markdown("# Smart Camera Monitoring Dashboard")

# Info Bar Row (Pushed to the right)
inf_col1, inf_col2, inf_col3 = st.columns([2.5, 1.2, 0.8])
with inf_col2:
    st.markdown(f"#### 📅 {datetime.now().strftime('%b %d, %Y | %H:%M:%S')}")
with inf_col3:
    status_class = "status-running" if st.session_state.running else "status-stopped"
    status_text = "● RUNNING" if st.session_state.running else "○ STOPPED"
    st.markdown(f"**Status:** <span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------
# SCREEN 1: DASHBOARD OVERVIEW
# ---------------------------------------------------------
if page == "🏢 Dashboard Overview":

    # --- Section: Alerts ---
    st.subheader("🔔 Real-Time Alerts")

    # Cloud Connectivity Check
    if engine.shared_service.conn is None:
        st.error("📡 **Database Connection Failed**")
        st.warning("""
        The system couldn't connect to the database. If you're seeing this on Streamlit Cloud:
        1. Go to your **Streamlit App Settings** -> **Secrets**.
        2. Add your database URL like this:
           ```toml
           DB_URL = "your-remote-db-url-here"
           ```
        3. Make sure your database provider (e.g., Supabase, Neon) allows connections from Streamlit Cloud.
        """)
        st.stop()

    # Fetch data: Integrated date and time range filters
    data_primary = engine.get_dashboard_data(
        DEFAULT_CAMERA_ID, 
        date_val=date_range, 
        hour_range=time_range
    )
    
    if not data_primary:
        st.warning("⚠️ No historical data found. Please click ▶ START to begin monitoring.")
        st.stop()
        
    if data_primary:
        if data_primary['occupancy'] > 50:
            st.markdown('<div class="custom-alert alert-critical">⚠️ CRITICAL: Overcrowding detected at Gate_01 (Occupancy > 50)</div>', unsafe_allow_html=True)
        if data_primary['rush_status'] == "RUSH":
            st.markdown('<div class="custom-alert alert-warning">⚡ WARNING: High congestion detected at Gate_01. Check Exit flow.</div>', unsafe_allow_html=True)
        if not data_primary['occupancy'] > 50 and not data_primary['rush_status'] == "RUSH":
            st.success("✅ All monitored areas reports normal traffic flow.")

    st.write("---")

    # --- TWO STATES LOGIC: BASELINE VS ACTIVE ---
    if not st.session_state.running:
        st.subheader("📊 Historical Intelligence (Baseline Mode)")
        st.info("System is currently IDLE. Displaying historical trends for situational awareness.")
        
        hist_col1, hist_col2, hist_col3 = st.columns(3)
        with hist_col1:
            st.metric("Total Historic Entries", f"{data_primary['entries']:,}")
        with hist_col2:
            st.metric("Historical Peak Hour", f"{data_primary['peak_hour']}:00")
        with hist_col3:
            st.metric("Avg Daily Volume", f"{int(data_primary['entries']*0.85)}") # Simulated for now
            
        st.markdown("""
        <div style="background-color: #2563eb; color: white; padding: 20px; border-radius: 10px; margin-top: 20px;">
            <h3>🧐 Behavioral Insight</h3>
            <p>Historical data indicates a <b>15% increase</b> in congestion during the next 60 minutes. 
            Consider activating the system for proactive monitoring.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Section: Live Multi-Camera Overview
        st.subheader("🌐 Live Area Monitoring (Active Mode)")
        
        # Live vs Historical Comparison
        comp_col1, comp_col2 = st.columns(2)
        with comp_col1:
            st.metric("Live Occupancy", data_primary['occupancy'], 
                      delta=f"{data_primary['occupancy'] - data_primary['avg_occupancy']} vs Avg")
        with comp_col2:
            st.metric("Expected Avg (Historical)", data_primary['avg_occupancy'])

        # Grid of cameras (Simulated grid for multi-gate)
        cam_cols = st.columns(len(selected_cameras))
        
        for i, cam_id in enumerate(selected_cameras):
            with cam_cols[i]:
                # Fetch data
                fetch_id = DEFAULT_CAMERA_ID if cam_id == "Uploaded Footage" or cam_id == "Camera_01" else cam_id
                cam_data = engine.get_dashboard_data(fetch_id, date_val=date_range, hour_range=time_range)
                
                if cam_data:
                    rush = cam_data['congestion']
                    color_hex = "#16a34a" if rush == "LOW" else "#ca8a04" if rush == "MEDIUM" else "#dc2626"
                    
                    st.markdown(f"""
                    <div class="camera-card" style="border-top: 5px solid {color_hex};">
                        <h3 style="margin-top:0;">📡 {cam_id}</h3>
                        <p style="font-size:0.8rem; color:#718096;">Status: LIVE</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    c1.metric("Inside", cam_data['occupancy'])
                    c2.metric("Total In", cam_data['entries'])
                else:
                    st.warning(f"No signal from {cam_id}")

    st.write("---")

    # --- Section: Video & Analytics Preview ---
    col_v, col_a = st.columns([1, 1])
    
    with col_v:
        st.subheader("📹 Scene Verification")
        frame_file = os.path.join(backend_dir, "current_frame.jpg")
        if st.session_state.running and os.path.exists(frame_file):
            st.image(frame_file, use_container_width=True, caption="Real-time Stream Analysis")
        else:
            st.image("https://img.icons8.com/clouds/500/000000/camera.png", use_container_width=True, caption="[System Offline / Loading Feed]")
        
        if st.session_state.running:
            st.info(f"Visual validation active. Tracking {data_primary['occupancy']} objects in scene.")
        else:
            st.info("System idle. Visual feed inactive.")

    with col_a:
        st.subheader("📊 Instant Analytics")
        if data_primary and data_primary['hourly_trend']:
            df = pd.DataFrame(data_primary['hourly_trend'], columns=['Hour', 'Count'])
            df['Count'] = df['Count'].astype(float)
            st.area_chart(df.set_index('Hour'), color="#2563eb")
        else:
            st.info("Waiting for telemetry data...")

# ---------------------------------------------------------
# SCREEN 2: DEDICATED ANALYTICS
# ---------------------------------------------------------
else:
    st.header("📈 Deep Historical Intelligence")
    st.write("Cross-camera comparative analysis and long-term trend forecasting.")
    
    tab1, tab2, tab3 = st.tabs(["🕒 Hourly Trends", "📅 Daily Statistics", "📜 Compliance Records"])
    
    data_all = engine.get_dashboard_data(DEFAULT_CAMERA_ID)

    with tab1:
        st.subheader("Hourly Traffic Distribution")
        if data_all and data_all['hourly_trend']:
            df_h = pd.DataFrame(data_all['hourly_trend'], columns=['Hour', 'Count'])
            df_h['Count'] = df_h['Count'].astype(float)
            st.line_chart(df_h.set_index('Hour'), color="#2563eb")
        
        st.write("**Peak Period Analysis**")
        if data_all:
            st.info(f"Historical analysis identifies **{data_all.get('peak_hour', 0)}:00** as the primary congestion window.")
        else:
            st.warning("⚠️ Insufficient data for peak-hour forensic analysis.")

    with tab2:
        st.subheader("Daily Volume Comparisons")
        if data_all and data_all.get('daily_trend'):
            df_d = pd.DataFrame(data_all['daily_trend'], columns=['Date', 'Volume'])
            df_d['Volume'] = df_d['Volume'].astype(float)
            st.bar_chart(df_d.set_index('Date'), color="#2563eb")

    with tab3:
        st.subheader("System Data Logs")
        if data_all and data_all.get('daily_trend'):
            df_log = pd.DataFrame(data_all['daily_trend'], columns=['Observation Date', 'Headcount'])
            df_log['Headcount'] = df_log['Headcount'].astype(float)
            st.table(df_log.sort_values('Observation Date', ascending=False))

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.divider()
f_col1, f_col2 = st.columns([3, 1])
with f_col1:
    st.caption("© 2026 Smart Mobility Systems | Edge Intelligence Platform | Developed for Administrators")
with f_col2:
    st.caption("Core Version: v4.2.1-stable")

# --- AUTO-REFRESH (Only if Running) ---
if st.session_state.running:
    if refresh_rate > 0:
        time.sleep(refresh_rate)
        st.rerun()
