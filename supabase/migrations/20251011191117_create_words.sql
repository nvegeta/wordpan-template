create table public.words (
  id uuid default gen_random_uuid() primary key,
  word text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);
