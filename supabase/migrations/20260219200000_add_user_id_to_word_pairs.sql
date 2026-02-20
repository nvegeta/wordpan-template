-- Add user_id to word_pairs for per-user flashcard decks
alter table public.word_pairs
  add column user_id uuid references auth.users(id) on delete cascade;

-- Backfill existing rows: set user_id to first authenticated user or leave null
-- (optional; if table is empty, skip) For now we leave existing rows as user_id NULL.

-- Update RLS policies for user-scoped access

-- Drop old policies
drop policy if exists "Authenticated users can view word pairs" on public.word_pairs;
drop policy if exists "Authenticated users can insert word pairs" on public.word_pairs;
drop policy if exists "Authenticated users can update word pairs" on public.word_pairs;
drop policy if exists "Authenticated users can delete word pairs" on public.word_pairs;

-- Users can only view their own word pairs (or legacy rows with null user_id)
create policy "Users can view their own word pairs"
  on public.word_pairs
  for select
  to authenticated
  using (auth.uid() = user_id or user_id is null);

-- Users can insert word pairs for themselves (user_id must match auth.uid())
create policy "Users can insert their own word pairs"
  on public.word_pairs
  for insert
  to authenticated
  with check (auth.uid() = user_id);

-- Users can update their own word pairs
create policy "Users can update their own word pairs"
  on public.word_pairs
  for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Users can delete their own word pairs
create policy "Users can delete their own word pairs"
  on public.word_pairs
  for delete
  to authenticated
  using (auth.uid() = user_id);
