# Design Document: StudyDeck Platform (v1 MVP)

## Overview

StudyDeck is a full-stack web application for creating, sharing, and studying structured learning material using spaced repetition and AI-assisted content generation. The v1 MVP covers eight core features: user auth, deck/card management, browsing and discovery, spaced repetition study sessions, deck forking, AI flashcard generation, and AI quiz generation.

Today's implementation uses a local in-memory data store (Python dicts). The architecture is designed so that swapping to Supabase tomorrow requires only changes to `data/store.py` and the service layer — no changes to routers or frontend.

**Tech Stack**

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript (no frameworks) |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Auth | python-jose (JWT), passlib (bcrypt) |
| AI | OpenAI API (`openai` Python SDK) via backend only |
| Data (today) | In-memory Python dicts + optional JSON file persistence |
| Data (tomorrow) | Supabase (PostgreSQL) |
| HTTP client | httpx (for async OpenAI calls if needed) |

---

## Architecture

```
Browser (HTML/CSS/JS)
        │  REST (JSON over HTTP)
        ▼
   FastAPI App (main.py)
        │
   ┌────┴────────────────────────┐
   │  Routers (one per domain)   │
   │  auth / decks / cards /     │
   │  study / ai                 │
   └────┬────────────────────────┘
        │
   ┌────┴────────────────────────┐
   │  Services                   │
   │  srs.py  │  ai_service.py   │
   └────┬────────────────────────┘
        │
   ┌────┴────────────────────────┐
   │  Data Store (store.py)      │
   │  In-memory dicts today      │
   │  Supabase client tomorrow   │
   └─────────────────────────────┘
```

All AI calls originate from `ai_service.py` on the backend. The frontend never calls OpenAI directly.

CORS is enabled for all origins in development (`allow_origins=["*"]`). In production this will be restricted to the deployed frontend domain.

---

## Project Structure

```
studydeck/
  backend/
    venv/                     # virtual environment (not committed)
    main.py                   # FastAPI app entry point, CORS, router includes
    routers/
      auth.py                 # POST /auth/register, POST /auth/login
      decks.py                # CRUD for decks + fork + fork count
      cards.py                # CRUD for cards + reorder
      study.py                # study session start, rate card, end session
      ai.py                   # flashcard generation, quiz generation, quiz submit
    data/
      store.py                # in-memory dicts: users, decks, cards, sessions,
                              # card_progress, quiz_attempts
    models/
      schemas.py              # Pydantic request/response models for all endpoints
    services/
      srs.py                  # pure SRS interval logic
      ai_service.py           # OpenAI API calls (generate cards, generate quiz,
                              # evaluate quiz answers)
    requirements.txt
  frontend/
    index.html                # landing page / public feed
    login.html                # login form
    register.html             # registration form
    dashboard.html            # authenticated user's deck list
    deck.html                 # deck detail: cards list + fork + study button
    study.html                # spaced repetition study session UI
    quiz.html                 # AI quiz page (generate + answer + score)
    ai-generate.html          # AI flashcard generator UI
    assets/
      css/
        style.css             # global styles, CSS variables, typography
        components.css        # reusable component styles (cards, buttons, forms)
      js/
        api.js                # fetch wrapper, BASE_URL constant, auth headers
        auth.js               # register, login, logout, token helpers
        decks.js              # deck CRUD, fork, feed, search
        study.js              # study session flow, SRS rating UI
        quiz.js               # quiz generation, answer submission, score display
        ai.js                 # flashcard generation, review/edit before save
```

---

## Components and Interfaces

### Backend Routers

#### `auth.py`
- `POST /auth/register` — create account
- `POST /auth/login` — issue JWT
- `GET /auth/me` — get current user (requires auth)

#### `decks.py`
- `GET /decks` — public feed (paginated, sorted by created_at desc)
- `GET /decks/trending` — trending feed (composite score, last 7 days)
- `GET /decks/my` — authenticated user's own decks
- `GET /decks/personalized` — authenticated personalized feed (tag-based)
- `GET /decks/{deck_id}` — get single deck
- `POST /decks` — create deck
- `PUT /decks/{deck_id}` — update deck
- `DELETE /decks/{deck_id}` — delete deck
- `POST /decks/{deck_id}/fork` — fork a deck
- `GET /decks/search` — full-text search with filters

#### `cards.py`
- `GET /decks/{deck_id}/cards` — list cards for a deck
- `POST /decks/{deck_id}/cards` — add card
- `PUT /decks/{deck_id}/cards/{card_id}` — edit card
- `DELETE /decks/{deck_id}/cards/{card_id}` — delete card
- `PUT /decks/{deck_id}/cards/reorder` — reorder cards (accepts ordered list of card IDs)

#### `study.py`
- `POST /study/{deck_id}/start` — start study session, returns due cards
- `POST /study/{deck_id}/rate` — submit recall rating for a card
- `POST /study/{deck_id}/end` — end session, persist results
- `GET /study/{deck_id}/progress` — per-user progress for a deck

#### `ai.py`
- `POST /ai/generate-cards` — generate flashcards from text
- `POST /ai/save-cards` — save accepted generated cards to a deck
- `POST /ai/generate-quiz/{deck_id}` — generate quiz from deck cards
- `POST /ai/submit-quiz` — evaluate quiz answers, return score
- `GET /ai/quiz-history/{deck_id}` — quiz attempt history for a deck

### Frontend JavaScript Modules

#### `api.js`
Thin fetch wrapper. Exposes `api.get(path)`, `api.post(path, body)`, `api.put(path, body)`, `api.delete(path)`. Automatically attaches `Authorization: Bearer <token>` header when a token is present in `localStorage`. All paths are relative to `BASE_URL = "http://localhost:8000"`.

#### `auth.js`
Handles registration form submission, login form submission, token storage (`localStorage.setItem("token", ...)`), `logout()`, and `isAuthenticated()` guard used by all protected pages.

---

## Data Models (In-Memory)

All stores live in `data/store.py` as module-level dicts. IDs are UUID strings generated with `uuid.uuid4()`.

### `users: dict[str, User]`
```python
{
  "user_id": {
    "id": str,            # UUID
    "email": str,         # unique
    "display_name": str,
    "password_hash": str, # bcrypt hash
    "created_at": str,    # ISO 8601
    "email_verified": bool  # stubbed True for v1
  }
}
```

### `decks: dict[str, Deck]`
```python
{
  "deck_id": {
    "id": str,
    "owner_id": str,       # user.id
    "title": str,
    "description": str,
    "visibility": str,     # "public" | "private"
    "tags": list[str],
    "fork_count": int,
    "source_deck_id": str | None,     # set on forks
    "source_author_name": str | None, # set on forks
    "view_count": int,
    "study_session_count": int,
    "created_at": str,
    "updated_at": str
  }
}
```

### `cards: dict[str, Card]`
```python
{
  "card_id": {
    "id": str,
    "deck_id": str,
    "front": str,   # markdown allowed
    "back": str,    # markdown allowed
    "position": int,  # 0-based ordering index
    "created_at": str,
    "updated_at": str
  }
}
```

### `card_progress: dict[str, CardProgress]`
Keyed by `f"{user_id}:{card_id}"` to ensure per-user, per-card isolation across forks.
```python
{
  "user_id:card_id": {
    "user_id": str,
    "card_id": str,
    "deck_id": str,
    "last_rating": str | None,   # "Again" | "Hard" | "Good" | "Easy"
    "next_review": str,          # ISO 8601 date
    "interval_days": int,        # current interval
    "review_count": int
  }
}
```

### `study_sessions: dict[str, StudySession]`
```python
{
  "session_id": {
    "id": str,
    "user_id": str,
    "deck_id": str,
    "cards_reviewed": int,
    "ratings": dict[str, str],   # card_id -> rating
    "duration_seconds": int,
    "started_at": str,
    "ended_at": str | None
  }
}
```

### `quiz_attempts: dict[str, QuizAttempt]`
```python
{
  "attempt_id": {
    "id": str,
    "user_id": str,
    "deck_id": str,
    "question_count": int,
    "score_percent": float,  # 0.0 – 100.0
    "timestamp": str
  }
}
```

---

## SRS Algorithm

The spaced repetition algorithm uses a fixed interval table. It is implemented as a pure function in `services/srs.py`.

```python
INTERVALS = {
    "Again": 1,
    "Hard":  3,
    "Good":  7,
    "Easy":  21,
}

def next_review_date(rating: str, from_date: date) -> date:
    if rating not in INTERVALS:
        raise ValueError(f"Invalid rating: {rating}")
    return from_date + timedelta(days=INTERVALS[rating])
```

**Session card ordering**: When a study session starts, the backend:
1. Fetches all cards for the deck.
2. Looks up `card_progress` for the requesting user.
3. Partitions cards into: **overdue** (next_review <= today), **new** (no progress record), **future** (next_review > today).
4. Sorts overdue by `next_review` ascending (most overdue first).
5. Interleaves new cards evenly among overdue cards.
6. Excludes future cards from the session queue.

If no cards are overdue or new, the session start endpoint returns `{"due_count": 0, "next_due": "<ISO date>"}`.

---

## AI Integration

### Design Principle

The browser never calls OpenAI directly. All AI calls are proxied through the FastAPI backend via `services/ai_service.py`. This keeps the API key server-side and allows prompt tuning without frontend changes.

### Flashcard Generation

**Endpoint**: `POST /ai/generate-cards`

**Request**:
```json
{
  "text": "<pasted content or topic description>",
  "target_count": 10
}
```

**Prompt strategy** (`ai_service.py`):
```
System: You are a flashcard creation assistant. Generate clear, concise study flashcards.

User: Generate {target_count} flashcards from the following text. 
Return ONLY a JSON array of objects with "front" and "back" string fields.
Each front should be a question or prompt. Each back should be a concise answer.
Limit: between 3 and 30 cards.

Text: {input_text}
```

The response is parsed as JSON. If parsing fails, `ai_service.py` retries once. If still failing, it raises an `AIServiceError`.

**Atomicity**: Cards are not written to the deck until the user calls `POST /ai/save-cards` with their accepted (and optionally edited) subset. The generate endpoint only returns the proposed cards; nothing is persisted until save is called. The save endpoint writes all cards in a single dict update — there is no partial write in the in-memory store.

### Quiz Generation

**Endpoint**: `POST /ai/generate-quiz/{deck_id}`

**Prompt strategy**:
```
System: You are a quiz generation assistant. Create quiz questions from flashcard content.

User: Generate {count} quiz questions from the following flashcards.
Mix multiple-choice (4 options, 1 correct) and short-answer questions.
Return ONLY a JSON array. Each object must have:
  - "type": "multiple_choice" | "short_answer"
  - "question": string
  - "correct_answer": string
  - "options": [string, string, string, string] (for multiple_choice only)
  - "correct_index": 0-3 (for multiple_choice only)

Flashcards:
{cards_json}
```

### Quiz Scoring

**Endpoint**: `POST /ai/submit-quiz`

For multiple-choice questions: compare submitted `selected_index` with `correct_index` (exact match, no AI needed).

For short-answer questions: call OpenAI to evaluate semantic similarity:
```
System: You are a quiz grader. Answer only "correct" or "incorrect".

User: Expected answer: {correct_answer}
Student answer: {student_answer}
Is the student's answer correct?
```

Score = (correct_count / total_questions) * 100.

---

## Auth Strategy (Today)

JWT-based authentication using `python-jose`.

**Token structure**:
```json
{
  "sub": "<user_id>",
  "exp": "<unix timestamp: now + 7 days>"
}
```

**Secret key**: Read from environment variable `SECRET_KEY`. Falls back to a hardcoded dev key `"dev-secret-key-change-in-prod"` for local development.

**Password hashing**: `passlib` with `bcrypt` scheme.

**Frontend storage**: Token stored in `localStorage` under the key `"token"`. `api.js` reads this on every request and attaches it as `Authorization: Bearer <token>`.

**Email verification**: Stubbed. All new accounts have `email_verified = True` automatically in v1. The welcome email send is a no-op log statement.

**Protected routes** (frontend): Each protected page's JavaScript checks `localStorage.getItem("token")` on load. If absent, the page redirects to `login.html`.

---

## API Endpoint Reference

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /auth/register | No | Register new user |
| POST | /auth/login | No | Login, returns JWT |
| GET | /auth/me | Yes | Get current user profile |

**Register request**: `{ "email": str, "display_name": str, "password": str }`
**Register response**: `{ "id": str, "email": str, "display_name": str }`
**Login request**: `{ "email": str, "password": str }`
**Login response**: `{ "access_token": str, "token_type": "bearer" }`

### Decks

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /decks | No | Public feed (page, limit=20) |
| GET | /decks/trending | No | Trending feed |
| GET | /decks/my | Yes | User's own decks |
| GET | /decks/personalized | Yes | Personalized feed |
| GET | /decks/search | No | Search (q, tag, date_from, date_to) |
| GET | /decks/{id} | No* | Get deck (* private requires auth+ownership) |
| POST | /decks | Yes | Create deck |
| PUT | /decks/{id} | Yes | Update deck |
| DELETE | /decks/{id} | Yes | Delete deck |
| POST | /decks/{id}/fork | Yes | Fork deck |

**Create/Update deck body**: `{ "title": str, "description": str, "visibility": "public"|"private", "tags": list[str] }`

**Deck response shape**:
```json
{
  "id": "...",
  "owner_id": "...",
  "title": "...",
  "description": "...",
  "visibility": "public",
  "tags": ["python", "beginner"],
  "fork_count": 3,
  "source_deck_id": null,
  "source_author_name": null,
  "view_count": 42,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### Cards

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /decks/{id}/cards | No* | List cards |
| POST | /decks/{id}/cards | Yes | Add card |
| PUT | /decks/{id}/cards/{cid} | Yes | Edit card |
| DELETE | /decks/{id}/cards/{cid} | Yes | Delete card |
| PUT | /decks/{id}/cards/reorder | Yes | Reorder (body: `{"order": ["id1","id2",...]}`) |

**Card body**: `{ "front": str, "back": str }`
**Card response**: `{ "id": str, "deck_id": str, "front": str, "back": str, "position": int, "created_at": str, "updated_at": str }`

### Study

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /study/{deck_id}/start | Yes | Start session, returns due cards |
| POST | /study/{deck_id}/rate | Yes | Rate a card |
| POST | /study/{deck_id}/end | Yes | End session |
| GET | /study/{deck_id}/progress | Yes | Per-user progress for deck |

**Rate request**: `{ "session_id": str, "card_id": str, "rating": "Again"|"Hard"|"Good"|"Easy" }`
**End request**: `{ "session_id": str, "duration_seconds": int }`

**Start response**:
```json
{
  "session_id": "...",
  "due_cards": [{ ...card... }],
  "due_count": 5,
  "next_due": null
}
```
When no cards due: `{ "due_count": 0, "next_due": "2025-01-08" }`

### AI

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /ai/generate-cards | Yes | Generate flashcards from text |
| POST | /ai/save-cards | Yes | Save accepted cards to deck |
| POST | /ai/generate-quiz/{deck_id} | Yes | Generate quiz from deck |
| POST | /ai/submit-quiz | Yes | Submit answers, get score |
| GET | /ai/quiz-history/{deck_id} | Yes | Quiz history for deck |

**Generate cards request**: `{ "text": str, "deck_id": str, "target_count": int (optional, 3-30) }`
**Generate cards response**: `{ "generated_cards": [{"front": str, "back": str}] }`

**Save cards request**: `{ "deck_id": str, "cards": [{"front": str, "back": str}] }`

**Generate quiz response**:
```json
{
  "quiz_id": "...",
  "questions": [
    {
      "id": "...",
      "type": "multiple_choice",
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correct_index": 2
    },
    {
      "id": "...",
      "type": "short_answer",
      "question": "...",
      "correct_answer": "..."
    }
  ]
}
```

**Submit quiz request**: `{ "quiz_id": str, "deck_id": str, "answers": [{"question_id": str, "answer": str | int}] }`
**Submit quiz response**: `{ "score_percent": float, "feedback": [{"question_id": str, "correct": bool, "correct_answer": str}] }`

---

## Error Handling

All API errors follow a consistent shape:
```json
{ "detail": "<human-readable message>" }
```

| HTTP Status | When |
|---|---|
| 400 | Validation error (empty title, short password, etc.) |
| 401 | Missing or expired JWT |
| 403 | Authenticated but not authorized (not owner, private deck, self-fork) |
| 404 | Resource not found |
| 422 | Pydantic schema validation failure (FastAPI default) |
| 500 | Upstream AI error or unhandled exception |

FastAPI's built-in exception handler covers 422. Custom exception handlers in `main.py` cover 401, 403, and 500 (for `AIServiceError`).

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Email uniqueness invariant

*For any* two registered users in the system, their email addresses SHALL be distinct. Attempting to register a second account with an already-registered email SHALL be rejected.

**Validates: Requirements 1.1, 1.5**

---

### Property 2: Token authentication round-trip

*For any* valid user credentials (email + password), submitting a login request produces a JWT token that, when used on a subsequent authenticated request before expiry, identifies the same user.

**Validates: Requirements 1.2**

---

### Property 3: Invalid credentials do not disclose field

*For any* login attempt where either the email is not registered or the password does not match, the error response SHALL be identical regardless of which field caused the failure.

**Validates: Requirements 1.3**

---

### Property 4: Password length validation

*For any* registration attempt with a password string of length strictly less than 8, the request SHALL be rejected with a validation error and no user account SHALL be created.

**Validates: Requirements 1.6**

---

### Property 5: Deck ownership invariant

*For any* deck in the system, the `owner_id` field SHALL equal the user who created or forked it. For any user who is not the owner of a deck, attempts to edit or delete that deck SHALL be rejected with an authorization error.

**Validates: Requirements 2.1, 2.5**

---

### Property 6: Private deck visibility invariant

*For any* deck with `visibility == "private"` and any user who is not the deck's owner, the deck SHALL NOT appear in any feed, search result, or direct fetch response for that user.

**Validates: Requirements 2.4, 4.1 (visibility filter)**

---

### Property 7: Deck deletion preserves forks

*For any* source deck that has been forked by one or more users, deleting the source deck SHALL leave all forks accessible to their owners with all cards intact.

**Validates: Requirements 2.3**

---

### Property 8: Card capacity invariant

*For any* deck in the system, the total number of cards associated with that deck SHALL never exceed 1,000. Any card addition that would cause the count to exceed 1,000 SHALL be rejected.

**Validates: Requirements 2.7, 3.6**

---

### Property 9: Card content round-trip

*For any* card with arbitrary front and back content (plain text, markdown, code blocks), retrieving the card after creation or edit SHALL return content byte-for-byte identical to what was submitted.

**Validates: Requirements 3.1, 3.2**

---

### Property 10: Card ordering persistence

*For any* deck and any permutation of its card IDs submitted as a reorder request, retrieving the deck's cards afterwards SHALL return them in the submitted order.

**Validates: Requirements 3.5**

---

### Property 11: Feed visibility filter invariant

*For any* feed or search query (public feed, trending feed, personalized feed, or search), no deck with `visibility == "private"` that is not owned by the requesting user SHALL appear in the results.

**Validates: Requirements 4.1, 4.2, 4.3, 4.6**

---

### Property 12: SRS interval mapping

*For any* recall rating in `{"Again", "Hard", "Good", "Easy"}`, the SRS engine SHALL produce a next-review date at exactly 1, 3, 7, or 21 days from the current date respectively. No two ratings SHALL produce the same interval.

**Validates: Requirements 5.2**

---

### Property 13: SRS invalid rating rejection

*For any* rating value that is not in `{"Again", "Hard", "Good", "Easy"}`, the rate endpoint SHALL return a validation error and the card's schedule SHALL remain unchanged.

**Validates: Requirements 5.3**

---

### Property 14: Fork schedule isolation

*For any* user who has both a source deck and a fork of that deck in their study history, rating a card in the fork SHALL NOT modify the card progress record for the same user in the source deck.

**Validates: Requirements 5.7**

---

### Property 15: Fork snapshot invariant

*For any* public deck that is forked, the resulting fork SHALL contain the same number of cards as the source deck at the moment of forking, with identical front/back content for each card.

**Validates: Requirements 6.1**

---

### Property 16: Fork modification isolation

*For any* fork and any modification applied to it (add card, edit card, delete card), the source deck's card list SHALL remain unchanged.

**Validates: Requirements 6.2**

---

### Property 17: Fork attribution invariant

*For any* forked deck, the `source_deck_id` and `source_author_name` fields SHALL be non-null, set at fork time, and SHALL remain unchanged even if the source deck is renamed or deleted.

**Validates: Requirements 6.3**

---

### Property 18: Self-fork and private-fork prevention

*For any* user and any deck they own, attempting to fork their own deck SHALL be rejected. For any private deck and any user who is not the owner, attempting to fork SHALL be rejected.

**Validates: Requirements 6.5, 6.6**

---

### Property 19: AI card count bounds

*For any* flashcard generation request with valid input (>= 10 characters), the number of cards returned SHALL be in the inclusive range [3, 30].

**Validates: Requirements 7.3**

---

### Property 20: AI generation input validation

*For any* flashcard generation request where the input text has fewer than 10 characters, the request SHALL be rejected with a validation error and no cards SHALL be added to any deck.

**Validates: Requirements 7.4**

---

### Property 21: AI card save atomicity

*For any* save-cards request, the operation SHALL either persist all submitted cards to the deck or none. If the operation fails, the deck's card list SHALL be identical to its state before the request.

**Validates: Requirements 7.5**

---

### Property 22: Quiz question count bounds

*For any* quiz generation request on a deck with >= 3 cards, the number of questions returned SHALL be in the inclusive range [3, 20].

**Validates: Requirements 8.3**

---

### Property 23: Quiz score bounds invariant

*For any* completed quiz, the score percentage returned SHALL be in the inclusive range [0.0, 100.0].

**Validates: Requirements 8.4**

---

### Property 24: Multiple-choice question structure invariant

*For any* multiple-choice question generated by the AI service, it SHALL have exactly 4 options and exactly one option SHALL be marked as correct (`correct_index` in `[0, 1, 2, 3]`).

**Validates: Requirements 8.2**

---

### Property 25: Quiz minimum deck size

*For any* quiz generation request on a deck with fewer than 3 cards, the request SHALL be rejected with an error and no quiz SHALL be generated.

**Validates: Requirements 8.5**

---

## Testing Strategy

### Dual Approach

Both unit tests and property-based tests are used, they are complementary:
- **Unit tests**: Verify specific examples, edge cases, and integration points between components
- **Property-based tests**: Validate universal invariants across generated input spaces (see Correctness Properties above)

### Property-Based Testing Library

Python property-based tests use **[Hypothesis](https://hypothesis.readthedocs.io/)**. Each property test is configured to run a minimum of 100 examples (`@settings(max_examples=100)`).

Each property test is tagged with a comment referencing the design property:
```python
# Feature: studydeck-platform, Property 12: SRS interval mapping
```

### Unit Testing

Tests live in `backend/tests/`. Use `pytest` as the test runner.

Unit tests cover:
- Auth: registration validation, login success/failure, token expiry
- Deck: CRUD operations, authorization checks
- Card: CRUD, capacity enforcement, content round-trip
- SRS: interval logic for all four ratings, invalid rating rejection
- Feed: public feed pagination, search filter correctness
- AI: input validation (< 10 chars), count bounds, score bounds

### Property Test Focus Areas

Property tests focus on the pure business logic layer:
- `services/srs.py`: interval mapping, isolation
- `data/store.py` + router logic: capacity invariants, fork isolation, card round-trips, feed visibility, auth uniqueness

### Integration Tests

A small set of integration tests run the full FastAPI app (via `httpx.AsyncClient` with `TestClient`) and exercise:
- Full auth flow (register → login → protected endpoint)
- Full study flow (create deck → add cards → start session → rate cards → end session)
- AI generate → review → save flow (using mocked OpenAI responses)

### What Is Not Property Tested

- Frontend rendering (HTML/CSS output) — use manual visual review
- OpenAI API behavior itself — use mocked responses in tests
- OAuth provider integration — integration test with mock provider
