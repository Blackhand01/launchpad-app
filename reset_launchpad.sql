-- Launchpad — reset SOLO dati e oggetti dell'app (sicuro su Supabase hosted).
-- NON usare DROP SCHEMA public CASCADE: elimina tutto lo schema public (altre tabelle, grant, ecc.).
-- Dopo questo script, esegui schema.sql dall'inizio (include trigger, policy, grant, backfill).

drop trigger if exists on_auth_user_created on auth.users;

drop function if exists public.create_idea_with_quota(text, text, text);
drop function if exists public.admin_reset_ideas_this_week(uuid);

drop table if exists public.ideas cascade;
drop table if exists public.profiles cascade;

drop function if exists public.handle_new_user();
drop function if exists public.set_updated_at();
