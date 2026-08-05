# Supabase Database Setup — StudyDeck

Run the SQL below in your Supabase project:
**Dashboard → SQL Editor → New query → paste → Run**

---

## Tables overview

| Table | Purpose |
|---|---|
| `users` | Registered user accounts |
| `decks` | Study decks (collections of cards) |
| `cards` | Individual flashcards inside a deck |
| `card_progress` | Per-user spaced repetition progress per card |
| `study_sessions` | Records of completed study sessions |
| `quiz_attempts` | AI quiz scores and history |

---

## Full SQL — paste this entire block and click Run

```sql
-- ============================================================
-- StudyDeck v1 — Initial Schema
-- Supabase SQL Editor → New query → paste → Run
-- ============================================================

-- Required for uuid_generate_v4()
create extension if not exists "uuid-ossp";

-- ------------------------------------------------------------
-- 1. users
-- ------------------------------------------------------------
create table if not exists users (
  id             uuid        primary key default uuid_generate_v4(),
  email          text        unique not null,
  display_name   text        not null,
  password_hash  text        not null,
  email_verified boolean     not null default true,
  created_at     timestamptz not null default now()
);

-- ------------------------------------------------------------
-- 2. decks
-- ------------------------------------------------------------
create table if not exists decks (
  id                  uuid        primary key default uuid_generate_v4(),
  owner_id            uuid        not null references users(id) on delete cascade,
  title               text        not null,
  description         text        not null default '',
  visibility          text        not null default 'public'
                                  check (visibility in ('public', 'private')),
  tags                text[]      not null default '{}',
  fork_count          integer     not null default 0,
  source_deck_id      uuid        references decks(id) on delete set null,
  source_author_name  text,
  view_count          integer     not null default 0,
  study_session_count integer     not null default 0,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

-- ------------------------------------------------------------
-- 3. cards
-- ------------------------------------------------------------
create table if not exists cards (
  id         uuid        primary key default uuid_generate_v4(),
  deck_id    uuid        not null references decks(id) on delete cascade,
  front      text        not null,
  back       text        not null,
  position   integer     not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- 4. card_progress  (one row per user per card)
-- ------------------------------------------------------------
create table if not exists card_progress (
  id            uuid    primary key default uuid_generate_v4(),
  user_id       uuid    not null references users(id) on delete cascade,
  card_id       uuid    not null references cards(id) on delete cascade,
  deck_id       uuid    not null references decks(id) on delete cascade,
  last_rating   text    check (last_rating in ('Again', 'Hard', 'Good', 'Easy')),
  next_review   date    not null default current_date,
  interval_days integer not null default 0,
  review_count  integer not null default 0,
  unique (user_id, card_id)
);

-- ------------------------------------------------------------
-- 5. study_sessions
-- ------------------------------------------------------------
create table if not exists study_sessions (
  id               uuid        primary key default uuid_generate_v4(),
  user_id          uuid        not null references users(id) on delete cascade,
  deck_id          uuid        not null references decks(id) on delete cascade,
  cards_reviewed   integer     not null default 0,
  ratings          jsonb       not null default '{}',
  duration_seconds integer     not null default 0,
  started_at       timestamptz not null default now(),
  ended_at         timestamptz
);

-- ------------------------------------------------------------
-- 6. quiz_attempts
-- ------------------------------------------------------------
create table if not exists quiz_attempts (
  id             uuid        primary key default uuid_generate_v4(),
  user_id        uuid        not null references users(id) on delete cascade,
  deck_id        uuid        not null references decks(id) on delete cascade,
  question_count integer     not null default 0,
  score_percent  float       not null default 0,
  timestamp      timestamptz not null default now()
);

-- ------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------
create index if not exists idx_decks_owner         on decks(owner_id);
create index if not exists idx_decks_visibility    on decks(visibility);
create index if not exists idx_cards_deck          on cards(deck_id);
create index if not exists idx_card_progress_user  on card_progress(user_id, deck_id);
create index if not exists idx_study_sessions_user on study_sessions(user_id);
create index if not exists idx_quiz_attempts_user  on quiz_attempts(user_id, deck_id);
```

---

## After running

1. Go to **Table Editor** in the left sidebar — you should see all 6 tables.
2. Make sure your `.env` has the correct values:

```
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SECRET_KEY=your-random-secret
OPENAI_API_KEY=sk-...
```

3. Restart the backend:
```
.\venv\Scripts\uvicorn main:app --reload
```

---

## Where to find your Supabase credentials

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` | Project Settings → API → Project URL |
| `SUPABASE_SERVICE_KEY` | Project Settings → API → `service_role` secret key |

> Use `service_role`, NOT `anon` — the backend needs full table access.
