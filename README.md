# 🤖 Smart Camera Monitoring & Forensic Analytics Dashboard (FYP)

An industrial-grade, AI-powered system designed for real-time pedestrian tracking, crowd flow analysis, and forensic historical auditing. This project leverages state-of-the-art computer vision to provide actionable intelligence for multi-camera gate monitoring.

---

## 🌟 Key Features

### 🧠 Dual-Mode Intelligence
*   **Active Monitoring**: Real-time tracking of entries, exits, and current occupancy using YOLOv8 and DeepSORT.
*   **Baseline Forensic Mode**: Visualizes historical traffic patterns, peak hours, and daily headcounts when the AI engine is idle.

### 🕵️ Forensic Time Filtering
*   **Date & Hour Investigation**: Filter analytics by specific dates and hour ranges (e.g., "Show me traffic between 2 PM and 5 PM on July 10th").
*   **Session-Aware Tracking**: Automatically labels and isolates data per video file (e.g., footage1.mp4, footage2.mp4) without deleting historical records.

### 📊 Professional Analytics Dashboard
*   **Live Comparison**: Compare real-time occupancy against historical averages to detect anomalies or overcrowding.
*   **Scene Verification**: View the processed AI stream directly in the dashboard for visual audit validation.
*   **Rush Detection**: Integrated Z-Score logic to automatically flag high-traffic congestion periods.

---

## 🛠️ Technology Stack

*   **Frontend**: Streamlit (Premium Light Design System)
*   **Backend Core**: Python, OpenCV, Ultralytics YOLOv8
*   **Object Tracking**: DeepSORT (Simple Online and Realtime Tracking with a Deep Association Metric)
*   **Database**: PostgreSQL (Structured persistent storage)
*   **Integration**: Subprocess-based communication and Database-level data sharing.

---

## 🏗️ System Architecture

The system follows an industry-standard **Separation of Concerns** model:
1.  **AI Engine (`Backend/main.py`)**: Handles computer vision, tracking logic, and direct database entry.
2.  **Analytics Service**: Centralized SQL query engine for generating complex reports.
3.  **Dashboard (`Frontend/app.py`)**: High-fidelity UI that reads from the database and controls the AI engine via signaling.

---

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.10+
*   PostgreSQL installed and running.
*   NVIDIA GPU (Recommended for real-time YOLOv8 performance).

### 2. Database Setup
Create a database named `FYP_Tracking` and run the provided SQL scripts in the `Backend/` folder to initialize the `detections` table.

### 3. Installation
```powershell
pip install -r requirements.txt
```

### 4. Running the Dashboard
```powershell
cd Frontend
streamlit run app.py
```

---

## 🎨 Design Philosophy
The dashboard implements a **"Decision Support System"** UX, prioritizing clean white aesthetics, vibrant indicators, and forensic accessibility over raw data output.

---

**Developed for Final Year Project (FYP) | AI & Edge Intelligence Platform**