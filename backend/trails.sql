-- Create a table for recent trails
create table public.trails (
  id uuid not null default gen_random_uuid (),
  query text not null,
  created_at timestamp with time zone not null default now(),
  synthesis text,
  nodes jsonb,
  edges jsonb,
  constraint trails_pkey primary key (id)
);

-- If you already have the table, run these:
-- alter table public.trails add column synthesis text;
-- alter table public.trails add column nodes jsonb;
-- alter table public.trails add column edges jsonb;

-- Enable Row Level Security (RLS)
alter table public.trails enable row level security;

-- Create a policy that allows all operations for now (since we don't have auth)
-- In a real app with auth, you'd restrict this to the owner.
create policy "Allow all access to trails"
on public.trails
for all
using (true)
with check (true);
