-- Create chats table to store user chat sessions
create table public.chats (
  id uuid default gen_random_uuid() primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  title text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create chat_messages table to store messages within a chat
create table public.chat_messages (
  id uuid default gen_random_uuid() primary key,
  chat_id uuid not null references public.chats(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security
alter table public.chats enable row level security;
alter table public.chat_messages enable row level security;

-- Policies for chats: users can only access their own chats

-- Allow authenticated users to view their own chats
create policy "Users can view their own chats"
  on public.chats
  for select
  to authenticated
  using (auth.uid() = user_id);

-- Allow authenticated users to insert chats for themselves
create policy "Users can create their own chats"
  on public.chats
  for insert
  to authenticated
  with check (auth.uid() = user_id);

-- Allow authenticated users to update their own chats (e.g., title, updated_at)
create policy "Users can update their own chats"
  on public.chats
  for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Allow authenticated users to delete their own chats
create policy "Users can delete their own chats"
  on public.chats
  for delete
  to authenticated
  using (auth.uid() = user_id);

-- Policies for chat_messages: scoped to chats owned by the user

-- Allow authenticated users to view messages in their own chats
create policy "Users can view messages in their chats"
  on public.chat_messages
  for select
  to authenticated
  using (
    exists (
      select 1
      from public.chats c
      where c.id = chat_id
        and c.user_id = auth.uid()
    )
  );

-- Allow authenticated users to insert messages into their own chats
create policy "Users can insert messages into their chats"
  on public.chat_messages
  for insert
  to authenticated
  with check (
    exists (
      select 1
      from public.chats c
      where c.id = chat_id
        and c.user_id = auth.uid()
    )
  );

-- Allow authenticated users to update messages in their own chats
create policy "Users can update messages in their chats"
  on public.chat_messages
  for update
  to authenticated
  using (
    exists (
      select 1
      from public.chats c
      where c.id = chat_id
        and c.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.chats c
      where c.id = chat_id
        and c.user_id = auth.uid()
    )
  );

-- Allow authenticated users to delete messages in their own chats
create policy "Users can delete messages in their chats"
  on public.chat_messages
  for delete
  to authenticated
  using (
    exists (
      select 1
      from public.chats c
      where c.id = chat_id
        and c.user_id = auth.uid()
    )
  );

