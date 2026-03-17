# Production Pilot Plan (Supabase + FastAPI)

This project should use a hybrid architecture:
- Supabase: Postgres, Auth, RLS, Storage, Realtime
- FastAPI: Python ML inference and API orchestration

## 1) Provision and secure Supabase

1. Create a Supabase project in your target region.
2. Run schema.sql in SQL Editor.
3. Enable email auth and create initial admin user.
4. Insert profile row for admin with role = admin.
5. Store service-role key only in backend environment.

## 2) Data migration from current CSV outputs

Load these files first:
- processed_outputs/facility_features_raipur.csv -> public.facilities + static attributes
- processed_outputs/facility_crs_raipur.csv -> public.facility_risk_predictions
- processed_outputs/raipur_facility_outage_risk_24h.csv -> public.facility_risk_predictions
- processed_outputs/environmental_daily_raipur.csv -> public.climate_trends_monthly aggregate
- processed_outputs/weather_snapshot_*.json -> public.weather_snapshots

## 3) Backend changes

1. Keep existing endpoints and response contracts.
2. Replace file reads in api_server.py with SQL queries against:
   - public.v_latest_facility_risk
   - public.alerts
   - public.climate_trends_monthly
   - public.weather_snapshots
3. Keep ML scripts writing outputs, then upsert into Supabase.

## 4) Reliability controls

1. Add pipeline_runs record at job start and completion.
2. Add health endpoint in FastAPI for DB connectivity.
3. Add retry with backoff for all DB writes.
4. Configure daily backups and point-in-time recovery in Supabase.
5. Add alerting for failed pipeline run and API 5xx rates.

## 5) Multi-user access model

Roles:
- admin: full management
- operator: can update alerts/status and trigger pipeline jobs
- viewer: read-only dashboard access

RLS is already enforced in schema.sql.

## 6) Deployment baseline

1. Deploy FastAPI on Render/Railway/Fly/VM with autoscaling.
2. Deploy Frontend on Vercel/Netlify.
3. Set VITE_API_URL and Supabase vars in Frontend.
4. Set backend SUPABASE env vars in hosting platform.

## 7) Pilot readiness checklist

- Auth login works for at least 2 roles
- RLS blocks unauthorized data writes
- Pipeline updates latest predictions and alerts
- Dashboard loads from DB, not local CSV
- Recovery tested from backup snapshot
