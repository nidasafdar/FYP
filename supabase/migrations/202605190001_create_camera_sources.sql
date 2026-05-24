create extension if not exists pgcrypto;

create table if not exists public.camera_sources (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text not null default '',
  source_type text not null default 'generate',
  stream_url text,
  camera_id text not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint camera_sources_source_type_check
    check (source_type in ('generate', 'stream')),
  constraint camera_sources_stream_url_check
    check (
      (source_type = 'generate' and stream_url is null)
      or
      (source_type = 'stream' and nullif(trim(stream_url), '') is not null)
    )
);

create index if not exists camera_sources_created_at_idx
  on public.camera_sources (created_at);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_camera_sources_updated_at on public.camera_sources;

create trigger set_camera_sources_updated_at
before update on public.camera_sources
for each row
execute function public.set_updated_at();

alter table public.camera_sources enable row level security;

drop policy if exists "Allow source reads" on public.camera_sources;
create policy "Allow source reads"
on public.camera_sources
for select
using (true);

drop policy if exists "Allow source inserts" on public.camera_sources;
create policy "Allow source inserts"
on public.camera_sources
for insert
with check (true);
