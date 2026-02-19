-- Add metadata column to chat_messages to store structured tutor data (e.g., word cards)
alter table public.chat_messages
  add column if not exists metadata jsonb default '{}'::jsonb not null;

