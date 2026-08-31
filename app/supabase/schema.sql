-- Rode isto no SQL Editor do seu projeto Supabase (supabase.com, plano free).
-- Guarda quais palavras cada usuário já marcou como "sabidas".

create table if not exists progress (
  user_id uuid references auth.users(id) on delete cascade,
  topic_id text not null,
  word_index int not null,
  created_at timestamptz default now(),
  primary key (user_id, topic_id, word_index)
);

alter table progress enable row level security;

-- cada usuário só vê e edita o próprio progresso
create policy "usuarios veem seu progresso"
  on progress for select
  using (auth.uid() = user_id);

create policy "usuarios gerenciam seu progresso"
  on progress for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
