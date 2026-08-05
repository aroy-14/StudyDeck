-- StudyDeck v1 — Initial Schema
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Users
create table if not exists users (
  id uuid primary key default uuid_generate_v4(),
  email text unique not null,
  display_name text not null,
  password_hash text not null,
  email_verified boolean not null default true,
  created_at timestamptz not null default now()
);

-- Decks
create table if not exists decks (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references users(id) on delete cascade,
  title text not null,
  description text not null default '',
  visibility text not null default 'public' check (visibility in ('public','private')),
  tags text[] not null default '{}',
  fork_count integer not null default 0,
  source_deck_id uuid references decks(id) on delete set null,
  source_author_name text,
  view_count integer not null default 0,
  study_session_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Cards
create table if not exists cards (
  id uuid primary key default uuid_generate_v4(),
  deck_id uuid not null references decks(id) on delete cascade,
  front text not null,
  back text not null,
  position integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Card progress (per user per card)
create table if not exists card_progress (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references users(id) on delete cascade,
  card_id uuid not null references cards(id) on delete cascade,
  deck_id uuid not null references decks(id) on delete cascade,
  last_rating text check (last_rating in ('Again','Hard','Good','Easy')),
  next_review date not null default current_date,
  interval_days integer not null default 0,
  review_count integer not null default 0,
  unique (user_id, card_id)
);

-- Study sessions
create table if not exists study_sessions (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references users(id) on delete cascade,
  deck_id uuid not null references decks(id) on delete cascade,
  cards_reviewed integer not null default 0,
  ratings jsonb not null default '{}',
  duration_seconds integer not null default 0,
  started_at timestamptz not null default now(),
  ended_at timestamptz
);

-- Quiz attempts
create table if not exists quiz_attempts (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references users(id) on delete cascade,
  deck_id uuid not null references decks(id) on delete cascade,
  question_count integer not null default 0,
  score_percent float not null default 0,
  timestamp timestamptz not null default now()
);

-- Indexes for common queries
create index if not exists idx_decks_owner on decks(owner_id);
create index if not exists idx_decks_visibility on decks(visibility);
create index if not exists idx_cards_deck on cards(deck_id);
create index if not exists idx_card_progress_user_deck on card_progress(user_id, deck_id);
create index if not exists idx_study_sessions_user on study_sessions(user_id);
create index if not exists idx_quiz_attempts_user_deck on quiz_attempts(user_id, deck_id);
