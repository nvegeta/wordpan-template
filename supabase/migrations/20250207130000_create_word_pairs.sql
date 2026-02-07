-- Create word_pairs table
create table public.word_pairs (
  id uuid default gen_random_uuid() primary key,
  word1 text not null,
  word2 text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security
alter table public.word_pairs enable row level security;

-- Allow authenticated users to view all word pairs
create policy "Authenticated users can view word pairs"
  on public.word_pairs
  for select
  to authenticated
  using (true);

-- Allow authenticated users to insert word pairs
create policy "Authenticated users can insert word pairs"
  on public.word_pairs
  for insert
  to authenticated
  with check (true);

-- Allow authenticated users to update word pairs
create policy "Authenticated users can update word pairs"
  on public.word_pairs
  for update
  to authenticated
  using (true)
  with check (true);

-- Allow authenticated users to delete word pairs
create policy "Authenticated users can delete word pairs"
  on public.word_pairs
  for delete
  to authenticated
  using (true);
