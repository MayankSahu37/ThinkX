# Supabase Setup

Files in this folder:
- schema.sql: Database schema, RLS policies, and core view
- PRODUCTION_PILOT_PLAN.md: Rollout and reliability checklist

Quick start:
1. Create Supabase project.
2. Run schema.sql in SQL Editor.
3. Configure Backend/.env from Backend/.env.example.
4. Configure Frontend/.env.local from Frontend/.env.example.
5. Update api_server.py to read from Supabase tables.

One-shot initial data load:
1. Ensure Backend/.env has SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
2. Run:
	.\\.venv\\Scripts\\python.exe supabase\\ingest_from_processed_outputs.py

Important:
- Keep SUPABASE_SERVICE_ROLE_KEY only in backend.
- Frontend must use only anon key.
