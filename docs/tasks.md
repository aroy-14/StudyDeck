# StudyDeck v1 — Task Breakdown

## Overview

This plan covers today's goal: **complete all frontend pages and backend API endpoints backed by local in-memory data**. No database, no deployment today.

Tomorrow's work (Supabase + deploy) is documented at the bottom but not tasked out.

Tech stack: HTML/CSS/Vanilla JS frontend · Python + FastAPI backend · python-jose JWT · passlib bcrypt · OpenAI API · in-memory dicts.

---

## Phase 0: Project Setup

- [x] 0.1 Create the top-level folder structure
  - Create `studydeck/backend/routers/`, `studydeck/backend/data/`, `studydeck/backend/models/`, `studydeck/backend/services/`, `studydeck/backend/tests/`
  - Create `studydeck/frontend/assets/css/` and `studydeck/frontend/assets/js/`
  - Create placeholder `__init__.py` files in each Python package directory
  - _Requirements: all_

- [x] 0.2 Set up Python virtual environment and install dependencies
  - Run `python -m venv venv` inside `studydeck/backend/`
  - Create `requirements.txt` with pinned versions: `fastapi==0.111.0`, `uvicorn[standard]==0.29.0`, `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4`, `httpx==0.27.0`, `openai==1.30.1`, `pytest==8.2.0`, `hypothesis==6.100.0`, `pytest-asyncio==0.23.7`
  - Install all dependencies into the venv
  - _Requirements: all_

- [x] 0.3 Create the in-memory data store (`data/store.py`)
  - Define six module-level dicts: `users`, `decks`, `cards`, `card_progress`, `study_sessions`, `quiz_attempts`
  - Each dict maps string UUID keys to typed Python dicts matching the data models in the design doc
  - Add a `clear_all()` helper for use in tests
  - _Requirements: all_

- [x] 0.4 Create Pydantic schemas (`models/schemas.py`)
  - Define request/response models for: `RegisterRequest`, `LoginRequest`, `TokenResponse`, `UserResponse`
  - Define: `CreateDeckRequest`, `UpdateDeckRequest`, `DeckResponse`, `DeckListResponse`
  - Define: `CreateCardRequest`, `UpdateCardRequest`, `CardResponse`, `ReorderCardsRequest`
  - Define: `StartSessionResponse`, `RateCardRequest`, `EndSessionRequest`, `ProgressResponse`
  - Define: `GenerateCardsRequest`, `GenerateCardsResponse`, `SaveCardsRequest`
  - Define: `GenerateQuizResponse`, `SubmitQuizRequest`, `QuizResultResponse`, `QuizHistoryResponse`
  - _Requirements: all_

- [x] 0.5 Scaffold FastAPI `main.py`
  - Create `main.py` with `FastAPI()` app instance
  - Add `CORSMiddleware` allowing all origins, all methods, all headers
  - Import and include routers: `auth`, `decks`, `cards`, `study`, `ai` (stubs are fine at this stage)
  - Add a `GET /health` endpoint returning `{"status": "ok"}`
  - Read `SECRET_KEY` from environment variable with a dev fallback
  - _Requirements: all_


---

## Phase 1: Auth API + Frontend

- [x] 1.1 Implement `POST /auth/register` endpoint (`routers/auth.py`)
  - Validate email uniqueness against `store.users`; return 400 if duplicate
  - Validate password length >= 8 characters; return 400 if too short
  - Hash password with passlib bcrypt
  - Generate UUID, set `email_verified = True` (stub), store in `store.users`
  - Return `UserResponse` (id, email, display_name)
  - _Requirements: 1.1, 1.5, 1.6_

- [ ]* 1.2 Write property tests for registration validation
  - **Property 1: Email uniqueness invariant** — registering same email twice returns 400
  - **Property 4: Password length validation** — any password with len < 8 returns 400
  - Feature: studydeck-platform, Property 1 and Property 4
  - _Requirements: 1.1, 1.5, 1.6_

- [-] 1.3 Implement `POST /auth/login` and `GET /auth/me` endpoints
  - Login: look up user by email; verify bcrypt hash; if mismatch return generic 401 (same message regardless of which field failed)
  - On success: create JWT with `sub=user_id`, `exp=now+7days`, sign with `SECRET_KEY`
  - Return `TokenResponse` with `access_token` and `token_type: "bearer"`
  - `GET /auth/me`: decode JWT, look up user, return `UserResponse`; return 401 if token missing/invalid/expired
  - _Requirements: 1.2, 1.3, 1.4_

- [ ]* 1.4 Write property tests for login / token round-trip
  - **Property 2: Token authentication round-trip** — register user, login, decode token, verify sub == user_id
  - **Property 3: Invalid credentials do not disclose field** — wrong email and wrong password produce identical error responses
  - Feature: studydeck-platform, Property 2 and Property 3
  - _Requirements: 1.2, 1.3_

- [-] 1.5 Create `register.html` with registration form
  - Fields: email, display name, password, confirm password
  - On submit: call `POST /auth/register` via `api.js`; on success redirect to `login.html`; on error display inline error message
  - Link to `login.html` for existing users
  - _Requirements: 1.1_

- [-] 1.6 Create `login.html` with login form
  - Fields: email, password
  - On submit: call `POST /auth/login`; on success store token in `localStorage` and redirect to `dashboard.html`
  - Display error message on failure
  - Link to `register.html`
  - _Requirements: 1.2, 1.3_

- [-] 1.7 Create `assets/js/api.js` and `assets/js/auth.js`
  - `api.js`: define `BASE_URL`, implement `api.get/post/put/delete` with automatic `Authorization` header injection from `localStorage.getItem("token")`
  - `auth.js`: implement `logout()` (clears token, redirects to `login.html`), `isAuthenticated()` (checks token exists), `requireAuth()` (redirects if not authenticated), `currentUserId()` (decodes JWT sub without a library using base64 split)
  - _Requirements: 1.2, 1.4_

- [~] 1.8 Checkpoint — Ensure auth flow works end to end
  - Ensure all auth tests pass, ask the user if questions arise.


---

## Phase 2: Decks API + Frontend

- [~] 2.1 Implement deck CRUD endpoints (`routers/decks.py`)
  - `POST /decks`: validate non-empty title; generate UUID; store in `store.decks` with `owner_id` from JWT; return `DeckResponse`
  - `GET /decks/{id}`: look up deck; if private and requester is not owner return 403; increment `view_count`; return `DeckResponse`
  - `PUT /decks/{id}`: verify ownership (403 if not owner); update title/description/tags/visibility; update `updated_at`; return updated `DeckResponse`
  - `DELETE /decks/{id}`: verify ownership (403); remove deck from `store.decks`; remove all cards with `deck_id == id` from `store.cards`; do NOT remove forks
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [ ]* 2.2 Write property tests for deck ownership and private visibility
  - **Property 5: Deck ownership invariant** — created deck has owner_id == creating user; non-owner edit/delete returns 403
  - **Property 6: Private deck visibility invariant** — private deck fetch by non-owner returns 403
  - Feature: studydeck-platform, Property 5 and Property 6
  - _Requirements: 2.1, 2.4, 2.5_

- [ ]* 2.3 Write property test for deck deletion preserving forks
  - **Property 7: Deck deletion preserves forks** — delete source deck; all forks remain accessible with correct card data
  - Feature: studydeck-platform, Property 7
  - _Requirements: 2.3_

- [~] 2.4 Implement public feed, trending, personalized, and search endpoints
  - `GET /decks`: filter `store.decks` to `visibility == "public"`; sort by `created_at` desc; paginate at 20 per page using `?page=` query param
  - `GET /decks/trending`: compute composite score = `view_count + study_session_count * 2` (simple approximation); return top 20 public decks
  - `GET /decks/personalized`: collect tags from all decks the user has studied or forked; return public decks that share at least one tag, paginated
  - `GET /decks/search`: full-text match on title + description + tags (simple `in` substring check); support `?q=`, `?tag=`, `?date_from=`, `?date_to=` query params; filter to public decks only; paginate at 20
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

- [ ]* 2.5 Write property tests for feed visibility and search filter invariants
  - **Property 11: Feed visibility filter invariant** — no private deck owned by another user appears in any feed or search result
  - Feature: studydeck-platform, Property 11
  - _Requirements: 4.1, 4.2, 4.3, 4.6_

- [~] 2.6 Create `index.html` — public landing and feed page
  - Show public feed of decks (title, description, tag chips, fork count)
  - Pagination controls (Previous / Next)
  - Search bar at top that calls `GET /decks/search?q=`
  - Nav links: Login, Register (if not authenticated); Dashboard, Logout (if authenticated)
  - Deck cards link to `deck.html?id=<deck_id>`
  - _Requirements: 4.1, 4.5, 4.8_

- [~] 2.7 Create `dashboard.html` — authenticated user's deck list
  - Call `requireAuth()` on page load
  - Fetch `GET /decks/my` and render the user's decks in a grid
  - "New Deck" button opens an inline form (title, description, visibility, tags) that calls `POST /decks`
  - Each deck card has Edit, Delete, and Study buttons
  - Delete triggers confirmation before calling `DELETE /decks/{id}`
  - _Requirements: 2.1, 2.2, 2.3_

- [~] 2.8 Create `deck.html` — deck detail page
  - Read `?id=` from URL; fetch `GET /decks/{id}` and `GET /decks/{id}/cards`
  - Display deck title, description, tags, fork count, owner display name, source attribution if forked
  - If owner: show Edit Deck form, Add Card form, Delete Deck button
  - Show Fork button for non-owners of public decks
  - Show Study button and AI Generate Quiz / AI Generate Cards buttons
  - _Requirements: 2.2, 3.1, 6.3, 6.4_

- [~] 2.9 Checkpoint — Ensure deck API and all deck pages work end to end
  - Ensure all deck-related tests pass, ask the user if questions arise.


---

## Phase 3: Cards API + Frontend

- [~] 3.1 Implement card CRUD endpoints (`routers/cards.py`)
  - `POST /decks/{deck_id}/cards`: verify requester owns deck; validate non-empty front and back (400 if empty); check card count < 1000 (400 if at capacity); assign `position = current_max_position + 1`; store in `store.cards`; update deck `updated_at`
  - `GET /decks/{deck_id}/cards`: verify deck exists and is readable (public or owned); return cards sorted by `position` asc
  - `PUT /decks/{deck_id}/cards/{card_id}`: verify deck ownership; update front/back; update deck `updated_at`
  - `DELETE /decks/{deck_id}/cards/{card_id}`: verify deck ownership; remove card from `store.cards`
  - `PUT /decks/{deck_id}/cards/reorder`: verify deck ownership; accept `{"order": ["id1","id2",...]}` and reassign `position` values 0..n-1
  - _Requirements: 3.1, 3.2, 3.4, 3.5, 3.6, 3.7_

- [ ]* 3.2 Write property tests for card content round-trip and capacity invariant
  - **Property 9: Card content round-trip** — for any front/back strings (including markdown, code blocks), create then fetch returns identical content
  - **Property 8: Card capacity invariant** — adding a card to a 1000-card deck returns 400
  - Feature: studydeck-platform, Property 8 and Property 9
  - _Requirements: 3.1, 3.2, 2.7_

- [ ]* 3.3 Write property test for card ordering persistence
  - **Property 10: Card ordering persistence** — for any permutation of card IDs submitted to reorder, fetch returns them in that exact order
  - Feature: studydeck-platform, Property 10
  - _Requirements: 3.5_

- [~] 3.4 Wire card UI into `deck.html`
  - Add Card form (front textarea, back textarea, Save button) — submits `POST /decks/{id}/cards`
  - Display card list with position, front (truncated), back (truncated)
  - Each card row: Edit (inline form), Delete buttons
  - Drag-to-reorder or Up/Down arrow buttons that call `PUT /decks/{id}/cards/reorder`
  - Show current card count and "X / 1000 cards" indicator
  - _Requirements: 3.1, 3.4, 3.5, 3.7_


---

## Phase 4: Fork API + Frontend

- [~] 4.1 Implement `POST /decks/{deck_id}/fork` endpoint
  - Verify user is authenticated (401 if not)
  - Reject if `deck.owner_id == requesting_user_id` (403, self-fork not permitted)
  - Reject if `deck.visibility == "private"` and requester is not owner (403)
  - Deep-copy all cards from `store.cards` where `card_id` belongs to the source deck; assign new card UUIDs and new deck UUID
  - Set new deck's `source_deck_id` and `source_author_name` from source deck
  - Increment `source_deck.fork_count`
  - Return the new fork's `DeckResponse`
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ]* 4.2 Write property tests for fork invariants
  - **Property 15: Fork snapshot invariant** — forked deck has identical card count and content as source at fork time
  - **Property 16: Fork modification isolation** — editing a forked deck does not change source deck cards
  - **Property 17: Fork attribution invariant** — forked deck has non-null source_deck_id and source_author_name
  - **Property 18: Self-fork and private-fork prevention** — self-fork returns 403; non-owner fork of private deck returns 403
  - Feature: studydeck-platform, Property 15, 16, 17, 18
  - _Requirements: 6.1, 6.2, 6.3, 6.5, 6.6_

- [~] 4.3 Wire Fork button into `deck.html`
  - Show "Fork this Deck" button for authenticated non-owners of public decks
  - On click: call `POST /decks/{id}/fork`; on success redirect to `deck.html?id=<new_fork_id>`
  - Show error toast for self-fork or private-fork attempts
  - Display fork count badge and source attribution section (if fork)
  - _Requirements: 6.1, 6.3, 6.4, 6.5, 6.6_


---

## Phase 5: Study Session (SRS) API + Frontend

- [~] 5.1 Implement SRS pure logic in `services/srs.py`
  - Define `INTERVALS = {"Again": 1, "Hard": 3, "Good": 7, "Easy": 21}`
  - Implement `next_review_date(rating: str, from_date: date) -> date`: raises `ValueError` for invalid ratings
  - Implement `build_session_queue(cards, progress_records, today) -> list[Card]`: partitions into overdue/new/future; sorts overdue by `next_review` asc; interleaves new cards evenly; excludes future cards
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ]* 5.2 Write property tests for SRS interval logic and isolation
  - **Property 12: SRS interval mapping** — for each of the four ratings, next_review_date returns today + correct interval; no two ratings produce same interval
  - **Property 13: SRS invalid rating rejection** — any string not in the valid set raises ValueError
  - **Property 14: Fork schedule isolation** — rating a card in a fork does not modify the source deck's card_progress entry for the same user
  - Feature: studydeck-platform, Property 12, 13, 14
  - _Requirements: 5.2, 5.3, 5.7_

- [~] 5.3 Implement study session endpoints (`routers/study.py`)
  - `POST /study/{deck_id}/start`: call `build_session_queue`; if empty return `{due_count: 0, next_due: ...}`; otherwise create a session record in `store.study_sessions` and return `{session_id, due_cards, due_count}`
  - `POST /study/{deck_id}/rate`: validate rating is in `{"Again","Hard","Good","Easy"}` (400 if not); call `next_review_date`; upsert `card_progress` keyed by `f"{user_id}:{card_id}"`; store rating in session record
  - `POST /study/{deck_id}/end`: update session `ended_at`, `duration_seconds`, `cards_reviewed`; increment `deck.study_session_count`
  - `GET /study/{deck_id}/progress`: aggregate card_progress for user+deck; compute counts of mastered (last_rating=="Easy"), learning, not studied; return `ProgressResponse`
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [~] 5.4 Create `study.html` — spaced repetition study session page
  - Read `?deck_id=` from URL; call `requireAuth()`
  - On load: call `POST /study/{id}/start`; if `due_count == 0` show "Nothing due" screen with next review date
  - Show one card at a time: display front; "Show Answer" button reveals back
  - After answer shown: display four rating buttons — Again / Hard / Good / Easy
  - On rating click: call `POST /study/{deck_id}/rate` with current `session_id` and `card_id`; advance to next card
  - Progress bar showing cards remaining
  - On last card: call `POST /study/{deck_id}/end`; show session summary (cards reviewed, duration)
  - _Requirements: 5.1, 5.2, 5.4, 5.5, 5.6_

- [~] 5.5 Checkpoint — Ensure SRS tests all pass and study flow works end to end
  - Ensure all SRS and study session tests pass, ask the user if questions arise.


---

## Phase 6: AI Flashcard Generator API + Frontend

- [~] 6.1 Implement AI flashcard generation in `services/ai_service.py`
  - Initialize `openai.OpenAI()` client; read `OPENAI_API_KEY` from environment
  - Implement `generate_flashcards(text: str, target_count: int) -> list[dict]`:
    - Validate `len(text) >= 10` (raise `ValueError` if not)
    - Clamp `target_count` to `[3, 30]`
    - Call `client.chat.completions.create()` with the prompt from the design doc
    - Parse JSON response; retry once on parse failure
    - Raise `AIServiceError` if still failing after retry
    - Validate returned list length is in `[3, 30]`
    - Return list of `{"front": str, "back": str}` dicts
  - Define `AIServiceError(Exception)` in this module
  - _Requirements: 7.1, 7.3, 7.4, 7.5_

- [~] 6.2 Implement AI flashcard endpoints (`routers/ai.py`)
  - `POST /ai/generate-cards`: validate `len(request.text) >= 10` (400 if not); call `ai_service.generate_flashcards`; return `GenerateCardsResponse` with the proposed cards (nothing written to store yet)
  - `POST /ai/save-cards`: validate deck ownership; validate deck capacity (deck.card_count + len(cards) <= 1000); write ALL cards atomically to `store.cards` in a single loop (no partial write); update deck `updated_at`; return updated card count
  - Add exception handler in `main.py` for `AIServiceError` → 500 with `{"detail": "AI service unavailable. Please try again."}`
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ]* 6.3 Write property tests for AI card count bounds and input validation
  - **Property 19: AI card count bounds** — mock OpenAI; verify any valid input returns 3–30 cards
  - **Property 20: AI generation input validation** — any input with len < 10 returns 400 from the endpoint
  - **Property 21: AI card save atomicity** — mock a failure mid-save; verify deck card count is unchanged
  - Feature: studydeck-platform, Property 19, 20, 21
  - _Requirements: 7.3, 7.4, 7.5_

- [~] 6.4 Create `ai-generate.html` — AI flashcard generator page
  - Call `requireAuth()`; read optional `?deck_id=` from URL (pre-selects target deck)
  - Textarea for input text (paste content or topic description)
  - Optional "Target card count" number input (3–30)
  - Deck selector dropdown (fetches `GET /decks/my`)
  - "Generate" button calls `POST /ai/generate-cards`; shows loading spinner
  - Generated cards displayed in an editable list: each card shows front/back with inline edit, remove button, drag-to-reorder
  - "Save to Deck" button calls `POST /ai/save-cards` with current (edited) list; on success redirect to `deck.html?id=<deck_id>`
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6, 7.7_


---

## Phase 7: AI Quiz Generator API + Frontend

- [~] 7.1 Implement AI quiz generation and scoring in `services/ai_service.py`
  - Implement `generate_quiz(cards: list[dict], count: int) -> list[dict]`:
    - Validate `len(cards) >= 3` (raise `ValueError` if not)
    - Clamp `count` to `[3, 20]`
    - Call OpenAI with quiz prompt from design doc
    - Parse JSON; validate each multiple-choice question has exactly 4 options and `correct_index` in `[0,1,2,3]`
    - Return list of question dicts
  - Implement `evaluate_short_answer(expected: str, student: str) -> bool`:
    - Call OpenAI with grading prompt from design doc
    - Return `True` if response is "correct", `False` otherwise
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [~] 7.2 Implement AI quiz endpoints (`routers/ai.py`)
  - `POST /ai/generate-quiz/{deck_id}`: fetch deck cards; validate >= 3 cards (400 if not); call `ai_service.generate_quiz`; store generated questions temporarily in a module-level `pending_quizzes` dict keyed by `quiz_id`; return `GenerateQuizResponse`
  - `POST /ai/submit-quiz`: retrieve questions from `pending_quizzes` by `quiz_id`; for each answer: multiple-choice uses index comparison; short-answer calls `evaluate_short_answer`; compute `score_percent = correct_count / total * 100`; validate `0 <= score_percent <= 100`; persist to `store.quiz_attempts`; return `QuizResultResponse`
  - `GET /ai/quiz-history/{deck_id}`: return all quiz attempts for requesting user and deck from `store.quiz_attempts`
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [ ]* 7.3 Write property tests for quiz structure and score bounds
  - **Property 22: Quiz question count bounds** — mock OpenAI; for any deck with >= 3 cards, generated quiz has 3–20 questions
  - **Property 23: Quiz score bounds invariant** — for any submitted answers, returned score_percent is in [0, 100]
  - **Property 24: Multiple-choice question structure invariant** — every multiple-choice question has exactly 4 options and correct_index in [0,1,2,3]
  - **Property 25: Quiz minimum deck size** — quiz generation on deck with < 3 cards returns 400
  - Feature: studydeck-platform, Property 22, 23, 24, 25
  - _Requirements: 8.2, 8.3, 8.4, 8.5_

- [~] 7.4 Create `quiz.html` — AI quiz page
  - Call `requireAuth()`; read `?deck_id=` from URL
  - On load: call `POST /ai/generate-quiz/{deck_id}`; show loading spinner; display error if deck has < 3 cards
  - Render quiz: one question at a time or all questions on one scrollable page (choose one-at-a-time for UX)
  - Multiple-choice: show 4 radio buttons; Short-answer: show text input
  - "Submit Quiz" button collects all answers, calls `POST /ai/submit-quiz`; shows score and per-question feedback
  - "View History" section at the bottom fetches and displays `GET /ai/quiz-history/{deck_id}`
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [~] 7.5 Checkpoint — Ensure AI endpoints work end to end with mocked OpenAI
  - Ensure all AI-related tests pass, ask the user if questions arise.


---

## Phase 8: Integration, Styling & Polish

- [~] 8.1 Create `assets/css/style.css` — global styles
  - Define CSS custom properties (color tokens, spacing scale, border-radius)
  - Base reset (box-sizing, margin 0, font family)
  - Typography scale (h1–h4, body, code)
  - Layout utilities (container max-width, flex helpers)
  - Responsive breakpoints for mobile (< 768px)
  - _Requirements: all frontend_

- [~] 8.2 Create `assets/css/components.css` — reusable component styles
  - `.card` — deck card component used across index/dashboard
  - `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger` — button variants
  - `.form-group`, `.form-label`, `.form-input`, `.form-error` — form elements
  - `.tag-chip` — tag badge
  - `.loading-spinner` — CSS spinner for AI loading states
  - `.toast` — transient error/success notifications (appears bottom-right, auto-dismisses)
  - `.progress-bar` — study session progress
  - `.quiz-question` — question card layout
  - _Requirements: all frontend_

- [~] 8.3 Wire up navigation and auth guards across all pages
  - Add consistent nav bar to all pages (`index.html`, `dashboard.html`, `deck.html`, `study.html`, `quiz.html`, `ai-generate.html`)
  - All authenticated pages call `requireAuth()` in their JS on load
  - Logout button on nav calls `auth.logout()`
  - Active nav link highlighted based on current page
  - _Requirements: 1.4, all frontend_

- [~] 8.4 Add error handling and loading states to all frontend JS modules
  - All `api.js` calls wrapped in try/catch; errors displayed as toast notifications
  - Loading state (disable button + show spinner) during all async operations
  - 401 responses from API trigger automatic logout + redirect to `login.html`
  - _Requirements: 1.4, all frontend_

- [ ]* 8.5 Write integration tests for core flows
  - Full auth flow: register → login → access protected endpoint → token expiry
  - Full deck flow: create deck → add cards → fork deck → verify fork isolation
  - Full study flow: start session → rate all cards → end session → verify progress
  - Use `httpx.AsyncClient` with `TestClient` wrapper; mock OpenAI for AI tests
  - _Requirements: all_

- [~] 8.6 Final checkpoint — All tests pass, all pages load correctly
  - Run `pytest backend/tests/` with the venv activated; verify 0 failures
  - Manually load each HTML page in a browser and verify no console errors
  - Ask the user if any questions arise before considering this complete.

---

## Tomorrow (not tasked out today)

- [~] T.1 Wire Supabase PostgreSQL — replace `data/store.py` in-memory dicts with Supabase Python client calls
- [~] T.2 Write and run Supabase migrations (users, decks, cards, card_progress, study_sessions, quiz_attempts tables)
- [~] T.3 Add `DATABASE_URL` / Supabase credentials to environment config
- [~] T.4 Deploy backend to Railway or Render
- [~] T.5 Deploy frontend static files to Vercel or Netlify
- [~] T.6 Update `BASE_URL` in `api.js` to point to deployed backend URL
- [~] T.7 Restrict CORS in `main.py` to deployed frontend domain

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP build
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each phase
- Property tests validate universal correctness properties using Hypothesis (min 100 examples each)
- Unit/integration tests validate specific flows and edge cases
- The in-memory store (`data/store.py`) is the only file that changes when wiring Supabase tomorrow
