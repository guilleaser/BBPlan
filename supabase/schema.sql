create table if not exists public.family_plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null check (char_length(name) between 1 and 80),
  form_data jsonb not null default '{}'::jsonb,
  comments jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.family_plans enable row level security;

create index if not exists family_plans_user_updated_at_idx
  on public.family_plans (user_id, updated_at desc);

revoke all on table public.family_plans from anon;
grant select, insert, update, delete on table public.family_plans to authenticated;

drop policy if exists "Users can view their own family plans" on public.family_plans;
create policy "Users can view their own family plans"
  on public.family_plans for select to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "Users can create their own family plans" on public.family_plans;
create policy "Users can create their own family plans"
  on public.family_plans for insert to authenticated
  with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update their own family plans" on public.family_plans;
create policy "Users can update their own family plans"
  on public.family_plans for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete their own family plans" on public.family_plans;
create policy "Users can delete their own family plans"
  on public.family_plans for delete to authenticated
  using ((select auth.uid()) = user_id);
