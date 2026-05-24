# Camus Mobility & Occupancy Analytics System

This project is a Final Year Project dashboard for smart camera monitoring and crowd analytics. It uses a FastAPI backend, a React/Vite frontend, Supabase/PostgreSQL storage, and simulator workers that generate camera movement data for testing.

## Main Features

- Camera source management for generated and stream-based sources.
- Real-time dashboard metrics for entries, exits, occupancy, congestion, trends, and rush detection.
- Supabase-backed tables for simulated, live, and audit logs.
- Background simulator workers for generated camera sources.
- React frontend with charts and analytics views.

## Project Structure

```text
backend/
  api.py                    FastAPI application and API routes
  analytics_engine.py       Central analytics coordinator
  analytics_service.py      Database queries and metric calculations
  simulator_supervisor.py   Starts and manages simulator workers
  RandomDataGen/worker.py   Generates simulated IN/OUT camera events
  requirements.txt          Python dependencies

frontend/
  src/                      React application source
  package.json              Frontend scripts and dependencies
  vite.config.js            Vite config and API proxy

supabase/
  migrations/               Database table migrations
```

## Requirements

- Python 3.9 or newer
- Node.js 18 or newer
- npm
- Supabase project, or a compatible PostgreSQL database with the provided schema

## Environment Setup

Create a `backend/.env` file with your own credentials:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres
DEFAULT_CAMERA_ID=Camera_01
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
```

Do not commit real passwords, service-role keys, or production database URLs.

## Database Setup

Run the SQL migrations in Supabase SQL Editor, in this order:

1. `supabase/migrations/202605190001_create_camera_sources.sql`
2. `supabase/migrations/202605190002_create_log_tables.sql`

These migrations create:

- `camera_sources`
- `simulated_logs`
- `live_logs`
- `audit_logs`

## Backend Setup

From the project root:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

Start the FastAPI server:

```bash
uvicorn backend.api:app --reload --port 8000
```

The backend will be available at:

```text
http://localhost:8000
```

Useful API endpoints:

- `GET /api/health`
- `GET /api/sources`
- `POST /api/sources`
- `GET /api/dashboard?camera=Camera_01&mode=simulation`
- `GET /api/camera_comparison?mode=simulation`
- `GET /api/frame`
- `GET /api/simulator/workers`

## Frontend Setup

Open a second terminal and run:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at:

```text
http://localhost:5174
```

The Vite development server proxies `/api` requests to `http://localhost:8000`.

## Running the Full Project

1. Start the backend:

   ```bash
   uvicorn backend.api:app --reload --port 8000
   ```

2. Start the frontend:

   ```bash
   cd frontend
   npm run dev
   ```

3. Open:

   ```text
   http://localhost:5174
   ```

4. Add or select camera sources from the dashboard.

5. For generated sources, simulator workers automatically insert movement events into `simulated_logs`.

## Data Modes

The analytics API supports these modes:

- `simulation`, `simulated`, or `generate`: reads from `simulated_logs`
- `live` or `stream`: reads from `live_logs`
- `audit`: reads from `audit_logs`

Example:

```text
http://localhost:8000/api/dashboard?camera=Camera_01&mode=simulation
```

## Build Frontend for Production

```bash
cd frontend
npm run build
```

Preview the production build:

```bash
npm run preview
```

## Tests

Backend tests are stored in `backend/tests`.

```bash
cd backend
source venv/bin/activate
python -m pytest
```

If `pytest` is not installed, install it inside the virtual environment:

```bash
pip install pytest
```

## Troubleshooting

- If `/api/sources` returns a Supabase error, check `SUPABASE_URL` and `SUPABASE_KEY` in `backend/.env`.
- If the dashboard has no data, create a generated camera source and confirm simulator workers are running with `GET /api/simulator/workers`.
- If frontend API calls fail, make sure the backend is running on port `8000`.
- If port `5174` is busy, change the port in `frontend/vite.config.js`.
