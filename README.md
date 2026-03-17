# ThinkX - Climate Risk Monitoring for Critical Facilities

ThinkX is a full-stack software platform for monitoring climate and infrastructure outage risk for facilities (for example hospitals and public infrastructure) in and around Raipur.

It combines:
- A React + Vite frontend dashboard (maps, trends, risk views)
- A FastAPI backend serving analytics APIs
- A Supabase-backed production data layer (with local-file fallback)
- Data processing outputs used for prediction and alert generation

## Features

- Facility-level risk scoring (CRS and outage-risk probabilities)
- Climate trend visualization and district-level context
- Alert feed for high-risk facilities
- Weather snapshot and trend endpoints
- Explainability endpoint for risk-factor contribution
- Supabase integration for multi-user pilot reliability

## Tech Stack

- Frontend: React, TypeScript, Vite, Axios, Leaflet
- Backend: Python, FastAPI, Pandas, Uvicorn
- Database/Auth (production): Supabase (PostgreSQL + REST)

## Repository Structure

- `api_server.py`: FastAPI application entry point
- `src/`, `public/`, `index.html`, `vite.config.ts`: Frontend app
- `processed_outputs/`: generated feature/prediction/weather files
- `supabase/schema.sql`: database schema + policies
- `supabase/ingest_from_processed_outputs.py`: one-shot ingestion script

## Prerequisites

Install these first:
- Git
- Node.js 20+ and npm
- Python 3.10+ (3.11 or 3.12 recommended)

## Clone the Repository

```powershell
git clone https://github.com/Saurabh-8816/ThinkX.git
cd ThinkX
```

If your clone root is named differently, run commands from the folder containing `api_server.py` and `package.json`.

## 1) Setup Backend (Python)

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Install backend dependencies:

```powershell
pip install fastapi uvicorn pandas
```

## 2) Setup Frontend (Node)

Install frontend dependencies:

```powershell
npm install
```

## 3) Configure Environment

Create a `.env` file in the project root (same folder as `api_server.py`).

Minimal local config:

```env
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

Supabase production/pilot config (recommended):

```env
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
```

Notes:
- Backend can run without Supabase; it falls back to local files.
- Keep `SUPABASE_SERVICE_ROLE_KEY` private. Never expose it in frontend code.

## 4) Run the App Locally

Use two terminals.

Terminal A - Backend:

```powershell
.\.venv\Scripts\python.exe api_server.py
```

Backend runs at:
- `http://localhost:8000`
- Health check: `http://localhost:8000/api/health`

Terminal B - Frontend:

```powershell
npm run dev
```

Frontend runs at:
- `http://localhost:5173`

## Optional: Load Data into Supabase

After running `supabase/schema.sql` in your Supabase SQL Editor, ingest current processed outputs:

```powershell
.\.venv\Scripts\python.exe supabase\ingest_from_processed_outputs.py
```

This script loads facilities, predictions, climate trends, alerts, and the latest weather snapshot.

## Common Issues

1. Python command not found
- Use the full interpreter path: `.\.venv\Scripts\python.exe`

2. CORS error in browser
- Ensure `.env` has `CORS_ORIGINS=http://localhost:5173`
- Restart backend after changing `.env`

3. Frontend cannot reach backend
- Verify backend is running on port 8000
- Check `http://localhost:8000/api/health`

4. Supabase data not showing
- Confirm `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are correct
- Re-run ingestion script

## Production Notes

- Do not commit `.env` files or secrets
- Keep Supabase service role key only on backend
- Consider running backend behind a process manager/reverse proxy for uptime

## License

Add your preferred license information here.
