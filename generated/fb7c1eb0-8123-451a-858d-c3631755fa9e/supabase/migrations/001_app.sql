create extension if not exists pgcrypto;

create table if not exists public.items (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    created_at timestamptz not null default now()
);

alter table public.items enable row level security;

create policy "authenticated users can read items"
on public.items
for select
to authenticated
using (true);
