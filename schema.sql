-- Launchpad (Supabase) — run in SQL Editor or via migration
-- Requires: Auth (email provider enabled)
--
-- Reset solo Launchpad (senza DROP SCHEMA public): esegui prima reset_launchpad.sql, poi questo file.
--
-- Primo admin (dopo la prima registrazione), da SQL:
--   update public.profiles set is_admin = true, is_approved = true where email = 'TUO@EMAIL';

create extension if not exists "uuid-ossp";

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  is_approved boolean not null default false,
  is_admin boolean not null default false,
  weekly_ideas_limit int not null default 3,
  ideas_this_week int not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists public.ideas (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  title text not null default '',
  raw_transcript text,
  structured_data jsonb,
  analysis_report text,
  status text not null default 'raw'
    check (status in ('raw', 'pending_confirmation', 'ready_for_validation', 'validated')),
  pivot_used boolean not null default false,
  vision_score int,
  feasibility_score int,
  dependency_score int,
  real_feasibility numeric(5,2),
  final_score numeric(6,2),
  yc_verdict text check (yc_verdict is null or yc_verdict in ('BUILD', 'ITERATE', 'NOT NOW')),
  thought_log jsonb,
  pivot_suggestion text,
  version int not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ideas_vision_score_range check (vision_score is null or (vision_score >= 0 and vision_score <= 100)),
  constraint ideas_feasibility_score_range check (
    feasibility_score is null or (feasibility_score >= 0 and feasibility_score <= 100)
  ),
  constraint ideas_dependency_score_range check (
    dependency_score is null or (dependency_score >= 0 and dependency_score <= 100)
  ),
  constraint ideas_real_feasibility_range check (
    real_feasibility is null or (real_feasibility >= 0 and real_feasibility <= 100)
  ),
  constraint ideas_final_score_range check (
    final_score is null or (final_score >= 0 and final_score <= 100)
  )
);

create index if not exists ideas_user_id_idx on public.ideas (user_id);
create index if not exists ideas_status_idx on public.ideas (status);

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists ideas_set_updated_at on public.ideas;
create trigger ideas_set_updated_at
before update on public.ideas
for each row execute function public.set_updated_at();

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, is_approved, is_admin)
  values (new.id, new.email, false, false)
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer set search_path = public;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.ideas enable row level security;

drop policy if exists "profiles_update_own" on public.profiles;
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
on public.profiles for select
using (auth.uid() = id);

-- Allow users to backfill their own row if the signup trigger did not run (legacy accounts).
drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own"
on public.profiles for insert
with check (auth.uid() = id);

-- Profiles are created by trigger; only service role should update is_approved / is_admin.

drop policy if exists "ideas_select_own" on public.ideas;
create policy "ideas_select_own"
on public.ideas for select
using (auth.uid() = user_id);

drop policy if exists "ideas_insert_own" on public.ideas;
create policy "ideas_insert_own"
on public.ideas for insert
with check (auth.uid() = user_id);

drop policy if exists "ideas_update_own" on public.ideas;
create policy "ideas_update_own"
on public.ideas for update
using (auth.uid() = user_id);

drop policy if exists "ideas_delete_own" on public.ideas;
create policy "ideas_delete_own"
on public.ideas for delete
using (auth.uid() = user_id);

-- Permessi PostgREST: necessari se le tabelle sono state create solo da SQL (senza wizard).
grant usage on schema public to authenticated;
grant select, insert on table public.profiles to authenticated;
grant select, insert, update, delete on table public.ideas to authenticated;

-- Backfill: utenti già presenti in auth.users ma senza riga in profiles
-- (es. trigger aggiunto dopo la registrazione, o errore al signup). Esegui una volta in SQL Editor.
insert into public.profiles (id, email, is_approved, is_admin)
select u.id, u.email, false, false
from auth.users u
where not exists (select 1 from public.profiles p where p.id = u.id)
on conflict (id) do nothing;

-- v2.5: colonne e RPC (idempotente su DB già esistenti)
alter table public.profiles add column if not exists weekly_ideas_limit int not null default 3;
alter table public.profiles add column if not exists ideas_this_week int not null default 0;

alter table public.ideas add column if not exists vision_score int;
alter table public.ideas add column if not exists feasibility_score int;
alter table public.ideas add column if not exists dependency_score int;
alter table public.ideas add column if not exists real_feasibility numeric(5,2);
alter table public.ideas add column if not exists final_score numeric(6,2);
alter table public.ideas add column if not exists yc_verdict text;
alter table public.ideas add column if not exists thought_log jsonb;
alter table public.ideas add column if not exists pivot_suggestion text;
alter table public.ideas drop column if exists verdict;

alter table public.ideas drop constraint if exists ideas_vision_score_range;
alter table public.ideas add constraint ideas_vision_score_range
  check (vision_score is null or (vision_score >= 0 and vision_score <= 100));

alter table public.ideas drop constraint if exists ideas_feasibility_score_range;
alter table public.ideas add constraint ideas_feasibility_score_range
  check (feasibility_score is null or (feasibility_score >= 0 and feasibility_score <= 100));

alter table public.ideas drop constraint if exists ideas_dependency_score_range;
alter table public.ideas add constraint ideas_dependency_score_range
  check (dependency_score is null or (dependency_score >= 0 and dependency_score <= 100));

alter table public.ideas drop constraint if exists ideas_real_feasibility_range;
alter table public.ideas add constraint ideas_real_feasibility_range
  check (real_feasibility is null or (real_feasibility >= 0 and real_feasibility <= 100));

alter table public.ideas drop constraint if exists ideas_final_score_range;
alter table public.ideas add constraint ideas_final_score_range
  check (final_score is null or (final_score >= 0 and final_score <= 100));

alter table public.ideas drop constraint if exists ideas_yc_verdict_values;
alter table public.ideas add constraint ideas_yc_verdict_values
  check (yc_verdict is null or yc_verdict in ('BUILD', 'ITERATE', 'NOT NOW'));

-- Backward compatibility for old ideas without dependency score.
update public.ideas
set dependency_score = 50
where dependency_score is null
  and feasibility_score is not null;

update public.ideas
set real_feasibility = greatest(
  0,
  least(
    100,
    feasibility_score
    - (dependency_score * 0.30)
    + greatest(0, (vision_score - 55) * 0.15)
  )
)
where feasibility_score is not null
  and dependency_score is not null
  and real_feasibility is null;

update public.ideas
set final_score = greatest(
  0,
  least(
    100,
    (real_feasibility * 0.60) + (vision_score * 0.40)
  )
)
where vision_score is not null
  and real_feasibility is not null
  and final_score is null;

update public.ideas
set yc_verdict = case
  when final_score >= 70 and real_feasibility >= 50 then 'BUILD'
  when final_score >= 45 or real_feasibility >= 38 then 'ITERATE'
  else 'NOT NOW'
end
where yc_verdict is null
  and real_feasibility is not null;

create or replace function public.create_idea_with_quota(
  title text,
  raw_transcript text,
  status text default 'raw'
)
returns public.ideas
language plpgsql
security definer
set search_path = public
as $$
declare
  uid uuid := auth.uid();
  prof public.profiles%rowtype;
  new_row public.ideas%rowtype;
begin
  if uid is null then
    raise exception 'NOT_AUTHENTICATED';
  end if;

  select * into prof from public.profiles where id = uid for update;
  if not found then
    raise exception 'PROFILE_NOT_FOUND';
  end if;

  if prof.ideas_this_week >= prof.weekly_ideas_limit then
    raise exception 'WEEKLY_LIMIT_REACHED' using errcode = 'P0001';
  end if;

  update public.profiles
  set ideas_this_week = ideas_this_week + 1
  where id = uid;

  insert into public.ideas (user_id, title, raw_transcript, status)
  values (uid, title, coalesce(raw_transcript, ''), coalesce(nullif(status, ''), 'raw'))
  returning * into new_row;

  return new_row;
end;
$$;

create or replace function public.admin_reset_ideas_this_week(target_user_id uuid default null)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  n int := 0;
  is_adm boolean;
begin
  select p.is_admin into is_adm from public.profiles p where p.id = auth.uid();
  if not coalesce(is_adm, false) then
    raise exception 'ADMIN_ONLY' using errcode = '42501';
  end if;

  if target_user_id is null then
    -- Keep an explicit WHERE for environments/extensions that block UPDATE without WHERE.
    update public.profiles set ideas_this_week = 0 where true;
  else
    update public.profiles set ideas_this_week = 0 where id = target_user_id;
  end if;

  get diagnostics n = row_count;
  return n;
end;
$$;

revoke all on function public.create_idea_with_quota(text, text, text) from public;
grant execute on function public.create_idea_with_quota(text, text, text) to authenticated;

revoke all on function public.admin_reset_ideas_this_week(uuid) from public;
grant execute on function public.admin_reset_ideas_this_week(uuid) to authenticated;
