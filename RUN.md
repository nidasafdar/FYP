# Run the Project

This guide explains how to run the Camus Mobility & Occupancy Analytics System locally.

## 1. Prerequisites

Install these first:

- Python 3.9 or newer
- Node.js 18 or newer
- npm
- A Supabase project, or a PostgreSQL database with the project schema

## 2. Set Up Environment Variables

Create `backend/.env`:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres
DEFAULT_CAMERA_ID=Camera_01
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
```

Replace the placeholder values with your own database and Supabase credentials.

## 3. Set Up the Database

Run these SQL files in the Supabase SQL Editor, in this order:

```text
supabase/migrations/202605190001_create_camera_sources.sql
supabase/migrations/202605190002_create_log_tables.sql
```

## 4. Install Backend Dependencies

From the project root:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

## 5. Install Frontend Dependencies

From the project root:

```bash
cd frontend
npm install
cd ..
```

## 6. Start the Backend

From the project root:

```bash
source backend/venv/bin/activate
uvicorn backend.api:app --reload --port 8000
```

Backend URL:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/api/health
```

## 7. Start the Frontend

Open a second terminal and run:

```bash
cd frontend
npm run dev
```

Frontend URL:

```text
http://localhost:5174
```

The frontend development server proxies `/api` requests to `http://localhost:8000`.

## 8. Use the App

1. Open `http://localhost:5174`.
2. Add or select a camera source.
3. Use generated camera sources to create simulator data automatically.
4. Check dashboard analytics such as occupancy, entries, exits, congestion, trends, and rush detection.
