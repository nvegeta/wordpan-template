-- Public/shared word pairs for the voice vocabulary game.
-- These rows have user_id = NULL so they can be used as a global deck
-- by the voice agent without needing a per-user JWT.

insert into public.word_pairs (word1, word2, user_id)
values
  ('dog', 'cachorro', null),
  ('cat', 'gato', null),
  ('house', 'casa', null),
  ('water', 'água', null),
  ('book', 'livro', null),
  ('food', 'comida', null),
  ('car', 'carro', null),
  ('sun', 'sol', null),
  ('moon', 'lua', null),
  ('friend', 'amigo', null);

