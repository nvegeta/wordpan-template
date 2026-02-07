-- Enable Row Level Security on words table
alter table public.words enable row level security;

-- Allow authenticated users to read all words (for list and random phrase)
create policy "Authenticated users can view words"
  on public.words
  for select
  to authenticated
  using (true);

-- Allow authenticated users to insert words
create policy "Authenticated users can insert words"
  on public.words
  for insert
  to authenticated
  with check (true);
