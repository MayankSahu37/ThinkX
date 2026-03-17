-- ClimaSafe Supabase schema for production pilot
-- Run this in Supabase SQL editor.

create extension if not exists pgcrypto;

-- Keep all tables in public for easier PostgREST access.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique,
  full_name text,
  role text not null default 'viewer' check (role in ('admin','operator','viewer')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at
before update on public.profiles
for each row execute procedure public.set_updated_at();

create table if not exists public.facilities (
  facility_id text primary key,
  facility_name text not null,
  facility_type text not null,
  district text,
  latitude double precision,
  longitude double precision,
  complete_address text,
  street_address text,
  city text,
  state text,
  postcode text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists trg_facilities_updated_at on public.facilities;
create trigger trg_facilities_updated_at
before update on public.facilities
for each row execute procedure public.set_updated_at();

create table if not exists public.facility_risk_predictions (
  id bigserial primary key,
  facility_id text not null references public.facilities(facility_id) on delete cascade,
  prediction_ts timestamptz not null default now(),
  crs numeric(6,5),
  risk_level text,
  gwl_value numeric,
  rainfall_value numeric,
  river_level_value numeric,
  outage_risk numeric(6,5),
  pred_outage_prob_24h numeric(6,5),
  pred_outage_prob_7d numeric(6,5),
  water_availability numeric(6,5),
  flood_safety numeric(6,5),
  rainfall_stability numeric(6,5),
  electricity_reliability numeric(6,5),
  flood_risk_prob numeric(6,5),
  water_shortage_risk_prob numeric(6,5),
  power_outage_risk_prob numeric(6,5),
  sanitation_failure_risk_prob numeric(6,5),
  flood_risk_label text,
  water_shortage_risk_label text,
  power_outage_risk_label text,
  sanitation_failure_risk_label text,
  top_risk_type text,
  top_risk_score numeric(6,5),
  alert_flag boolean default false,
  alert_level text,
  source_run_id uuid,
  created_at timestamptz not null default now()
);

create index if not exists idx_predictions_facility_ts
  on public.facility_risk_predictions(facility_id, prediction_ts desc);

create index if not exists idx_predictions_alert
  on public.facility_risk_predictions(alert_flag, alert_level, prediction_ts desc);

create table if not exists public.alerts (
  id bigserial primary key,
  facility_id text not null references public.facilities(facility_id) on delete cascade,
  risk_level text not null,
  top_risk_type text,
  top_risk_score numeric(6,5),
  predicted_issue text,
  recommended_action text,
  status text not null default 'open' check (status in ('open','acknowledged','resolved')),
  created_at timestamptz not null default now(),
  acknowledged_by uuid references public.profiles(id),
  acknowledged_at timestamptz,
  resolved_at timestamptz
);

create index if not exists idx_alerts_status_created
  on public.alerts(status, created_at desc);

create table if not exists public.climate_trends_monthly (
  id bigserial primary key,
  metric text not null,
  month date not null,
  value numeric not null,
  created_at timestamptz not null default now(),
  unique(metric, month)
);

create table if not exists public.weather_snapshots (
  id bigserial primary key,
  provider text,
  city text,
  fetched_at timestamptz,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_weather_snapshots_fetched
  on public.weather_snapshots(fetched_at desc);

create table if not exists public.pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running' check (status in ('running','success','failed')),
  rows_written integer default 0,
  error_message text,
  triggered_by text,
  created_at timestamptz not null default now()
);

-- A view for latest prediction per facility.
create or replace view public.v_latest_facility_risk as
select p.*
from public.facility_risk_predictions p
join (
  select facility_id, max(prediction_ts) as prediction_ts
  from public.facility_risk_predictions
  group by facility_id
) x
on p.facility_id = x.facility_id and p.prediction_ts = x.prediction_ts;

-- Enable RLS
alter table public.profiles enable row level security;
alter table public.facilities enable row level security;
alter table public.facility_risk_predictions enable row level security;
alter table public.alerts enable row level security;
alter table public.climate_trends_monthly enable row level security;
alter table public.weather_snapshots enable row level security;
alter table public.pipeline_runs enable row level security;

-- Helper to read role from profile.
create or replace function public.current_user_role()
returns text
language sql
stable
as $$
  select coalesce((select role from public.profiles where id = auth.uid()), 'viewer');
$$;

-- Read access for authenticated users.
drop policy if exists p_read_profiles on public.profiles;
create policy p_read_profiles on public.profiles
for select
to authenticated
using (id = auth.uid() or public.current_user_role() in ('admin','operator'));

drop policy if exists p_read_facilities on public.facilities;
create policy p_read_facilities on public.facilities
for select
to authenticated
using (true);

drop policy if exists p_read_predictions on public.facility_risk_predictions;
create policy p_read_predictions on public.facility_risk_predictions
for select
to authenticated
using (true);

drop policy if exists p_read_alerts on public.alerts;
create policy p_read_alerts on public.alerts
for select
to authenticated
using (true);

drop policy if exists p_read_climate on public.climate_trends_monthly;
create policy p_read_climate on public.climate_trends_monthly
for select
to authenticated
using (true);

drop policy if exists p_read_weather on public.weather_snapshots;
create policy p_read_weather on public.weather_snapshots
for select
to authenticated
using (true);

drop policy if exists p_read_pipeline_runs on public.pipeline_runs;
create policy p_read_pipeline_runs on public.pipeline_runs
for select
to authenticated
using (public.current_user_role() in ('admin','operator'));

-- Write access only for admin/operator users.
drop policy if exists p_write_profiles on public.profiles;
create policy p_write_profiles on public.profiles
for update
to authenticated
using (id = auth.uid() or public.current_user_role() = 'admin')
with check (id = auth.uid() or public.current_user_role() = 'admin');

drop policy if exists p_write_facilities on public.facilities;
create policy p_write_facilities on public.facilities
for all
to authenticated
using (public.current_user_role() in ('admin','operator'))
with check (public.current_user_role() in ('admin','operator'));

drop policy if exists p_write_predictions on public.facility_risk_predictions;
create policy p_write_predictions on public.facility_risk_predictions
for all
to authenticated
using (public.current_user_role() in ('admin','operator'))
with check (public.current_user_role() in ('admin','operator'));

drop policy if exists p_write_alerts on public.alerts;
create policy p_write_alerts on public.alerts
for all
to authenticated
using (public.current_user_role() in ('admin','operator'))
with check (public.current_user_role() in ('admin','operator'));

drop policy if exists p_write_climate on public.climate_trends_monthly;
create policy p_write_climate on public.climate_trends_monthly
for all
to authenticated
using (public.current_user_role() in ('admin','operator'))
with check (public.current_user_role() in ('admin','operator'));

drop policy if exists p_write_weather on public.weather_snapshots;
create policy p_write_weather on public.weather_snapshots
for all
to authenticated
using (public.current_user_role() in ('admin','operator'))
with check (public.current_user_role() in ('admin','operator'));

drop policy if exists p_write_pipeline_runs on public.pipeline_runs;
create policy p_write_pipeline_runs on public.pipeline_runs
for all
to authenticated
using (public.current_user_role() in ('admin','operator'))
with check (public.current_user_role() in ('admin','operator'));
