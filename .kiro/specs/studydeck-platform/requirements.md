# Requirements Document

## Introduction

StudyDeck is a platform where people create, share, and study structured learning material. Content is organized into **Decks** — topic-focused collections of **Cards** — that any user can browse, fork, and study using spaced repetition. The platform combines community-sourced content with AI-assisted creation to make building and studying high-quality material as frictionless as possible.

This document covers three tiers of scope:

- **MVP (v1 Launch)** — Requirements 1–8: core features required for a useful, shippable product
- **Should Have (v1.1)** — Requirements 9–11: high-value additions prioritized for shortly after launch
- **Could Have (v2+)** — Requirements 12–13: deferred features documented for future planning

**Explicitly deferred from v1:** Mindmap generation, collaborative editing (fork-only model applies instead).

---

## Glossary

- **User**: A registered person who can create, study, fork, and interact with content on the platform
- **Guest**: An unauthenticated visitor who can browse and view public content but cannot create or study
- **Deck**: A named, topic-focused collection of Cards created and owned by a User
- **Card**: A single study unit within a Deck, consisting of a front (prompt) and back (answer/explanation), optionally containing rich text, images, or code blocks
- **Fork**: A personal copy of another User's Deck that the forking User can modify independently without affecting the source Deck
- **Study_Session**: A timed, interactive review of a Deck's Cards using the SRS_Engine
- **SRS_Engine**: The system component responsible for scheduling Cards in Study_Sessions using spaced repetition intervals
- **Auth_Service**: The system component responsible for user registration, login, session management, and notification delivery
- **Deck_Service**: The system component responsible for creating, updating, deleting, and retrieving Decks and Cards
- **Search_Service**: The system component responsible for full-text search and filtering of public Decks
- **Feed_Service**: The system component responsible for generating public, trending, and personalized Deck feeds
- **Progress_Tracker**: The system component responsible for recording and reporting per-User study progress and streaks
- **AI_Service**: The system component responsible for generating Cards and quiz questions using a large language model
- **Rating**: A 1–5 star score a User assigns to a Deck after completing a Study_Session
- **Tag**: A keyword label attached to a Deck for discovery and categorization
- **Spaced Repetition**: A learning technique that schedules Card reviews at increasing intervals based on recall performance
- **StudyDeck Export Schema**: The canonical JSON schema defining the portable format for Deck import and export

---

## Requirements

---

## MVP (Must Have — v1 Launch)

---

### Requirement 1: User Registration and Authentication

**User Story:** As a visitor, I want to create an account and log in, so that I can save my progress and share my own study material.

#### Acceptance Criteria

1. WHEN a visitor submits a registration form with a unique email address, a display name, and a password of at least 8 characters, THE Auth_Service SHALL create a new User account and send a verification email to the provided address.
2. WHEN a User submits valid credentials (email and password), THE Auth_Service SHALL issue a signed session token with a 7-day expiry.
3. WHEN a User submits incorrect credentials, THE Auth_Service SHALL return an error response indicating authentication failure without disclosing which specific field (email or password) was incorrect.
4. WHEN a session token expires, THE Auth_Service SHALL reject subsequent authenticated requests and require the User to log in again.
5. IF a registration form is submitted with an email address already associated with an existing account, THEN THE Auth_Service SHALL return an error indicating the email is already in use.
6. IF a registration form is submitted with a password shorter than 8 characters, THEN THE Auth_Service SHALL return a validation error without creating the account.
7. WHERE third-party OAuth providers (Google, GitHub) are configured, THE Auth_Service SHALL allow Users to register and log in using those providers without requiring a separate password.

#### Correctness Properties

- **Uniqueness invariant**: For all registered Users, no two Users SHALL share the same email address.
- **Token round-trip**: A session token issued by Auth_Service, when submitted on a subsequent request before expiry, SHALL authenticate the same User that received it.

---

### Requirement 2: Deck Creation and Management

**User Story:** As a User, I want to create and manage study decks, so that I can organize my knowledge and share it with others.

#### Acceptance Criteria

1. WHEN a User submits a new Deck with a title and a visibility setting (public or private), THE Deck_Service SHALL persist the Deck and associate it with the creating User.
2. WHEN a User updates the title, description, or Tags of a Deck they own, THE Deck_Service SHALL save the changes and update the Deck's last-modified timestamp.
3. WHEN a User deletes a Deck they own, THE Deck_Service SHALL remove the Deck and all its Cards from the platform while preserving any Forks made by other Users.
4. WHILE a Deck has a visibility setting of "private", THE Deck_Service SHALL restrict read and write access to the owning User only.
5. IF a User attempts to edit or delete a Deck they do not own, THEN THE Deck_Service SHALL return an authorization error.
6. IF a Deck is submitted with an empty or missing title, THEN THE Deck_Service SHALL return a validation error without creating the Deck.
7. THE Deck_Service SHALL enforce a maximum of 1,000 Cards per Deck, rejecting any Card addition that would cause the total to exceed 1,000.

#### Correctness Properties

- **Ownership invariant**: For all Decks, the owning User SHALL be the User who created the Deck or the User who forked it; a Deck SHALL NOT have more than one owner.
- **Deletion isolation**: WHEN a source Deck is deleted, all Forks of that Deck SHALL remain accessible to their owning Users with no data loss.

---

### Requirement 3: Card Creation and Editing

**User Story:** As a User, I want to add rich study cards to my decks, so that I can represent diverse types of knowledge clearly.

#### Acceptance Criteria

1. WHEN a User adds a Card to a Deck they own, THE Deck_Service SHALL persist the Card with a non-empty front (prompt) and non-empty back (answer), and associate it with the parent Deck.
2. THE Deck_Service SHALL accept Card fronts and backs containing plain text, Markdown-formatted text, inline code spans, and fenced code blocks.
3. THE Deck_Service SHALL accept Card fronts and backs containing image attachments up to 5 MB each in JPEG, PNG, GIF, or WebP format.
4. WHEN a User edits a Card's front or back, THE Deck_Service SHALL save the updated content and update the parent Deck's last-modified timestamp.
5. WHEN a User reorders Cards within a Deck, THE Deck_Service SHALL persist the new ordering.
6. IF a User attempts to add a Card to a Deck that already contains 1,000 Cards, THEN THE Deck_Service SHALL return an error indicating the Deck has reached capacity.
7. IF a Card is submitted with an empty front or an empty back, THEN THE Deck_Service SHALL return a validation error without creating the Card.

#### Correctness Properties

- **Capacity invariant**: For all Decks, the Card count SHALL never exceed 1,000.
- **Content preservation**: WHEN a Card is retrieved after being created or edited, THE Deck_Service SHALL return content byte-for-byte identical to the content that was submitted.

---

### Requirement 4: Browsing and Discovery

**User Story:** As a User or Guest, I want to browse and discover public study decks, so that I can find material relevant to my learning goals.

#### Acceptance Criteria

1. THE Feed_Service SHALL expose a public feed of recently published, public Decks sorted by creation date descending, paginated at 20 items per page.
2. THE Feed_Service SHALL expose a trending feed of public Decks ranked by a composite score derived from view count, Study_Session count, and average Rating over the past 7 days.
3. WHEN a User is authenticated, THE Feed_Service SHALL expose a personalized feed of public Decks based on Tags from Decks the User has previously studied or forked.
4. WHILE a User is unauthenticated, THE Feed_Service SHALL serve only the public feed and trending feed without requiring login.
5. THE Search_Service SHALL support full-text search over Deck titles, descriptions, and Tags for all public Decks.
6. WHEN a search query is submitted, THE Search_Service SHALL return matching Decks ranked by relevance, paginated at 20 items per page.
7. THE Search_Service SHALL support filtering search results by Tag, and creation date range.
8. WHEN a Guest views the platform, THE Feed_Service SHALL serve public content without requiring authentication.

#### Correctness Properties

- **Visibility filter invariant**: For all feed and search results, no Deck with a visibility setting of "private" SHALL appear in any result returned to a User who does not own that Deck.
- **Pagination completeness**: For a stable dataset, iterating through all pages of a paginated result set SHALL return each public Deck exactly once.

---

### Requirement 5: Studying a Deck with Spaced Repetition

**User Story:** As a User, I want to study a deck using spaced repetition, so that I can retain information more effectively over time.

#### Acceptance Criteria

1. WHEN a User starts a Study_Session for a Deck, THE SRS_Engine SHALL present Cards scheduled for review based on each Card's last review date and recall performance, prioritizing overdue Cards first.
2. WHEN a User rates their recall of a Card as "Again", "Hard", "Good", or "Easy" during a Study_Session, THE SRS_Engine SHALL schedule the Card's next review at an interval of 1 day, 3 days, 7 days, or 21 days respectively, starting from the current date.
3. IF a User submits a recall rating with a value other than "Again", "Hard", "Good", or "Easy", THEN THE SRS_Engine SHALL return a validation error and reject the rating without updating the Card's schedule.
4. WHEN a Study_Session is completed or explicitly ended by the User, THE Progress_Tracker SHALL persist the session result including: Cards reviewed count, per-Card recall ratings, and total session duration in seconds.
5. WHILE a Study_Session is in progress, THE SRS_Engine SHALL present Cards in an order that interleaves new Cards and due Cards, not in the original Deck order.
6. IF a User starts a Study_Session on a Deck with no Cards due for review, THEN THE SRS_Engine SHALL notify the User that no Cards are currently due and display the date of the next scheduled review.
7. THE SRS_Engine SHALL track per-User Card progress independently for each Fork, so that studying a Fork does not affect the source Deck's per-User schedule for that User.

#### Correctness Properties

- **Interval monotonicity**: For all recall ratings submitted in a Study_Session, the next review interval assigned by THE SRS_Engine SHALL be greater than or equal to the previous interval for the same Card for the same User (intervals do not shrink unless the rating is "Again").
- **Schedule isolation (fork)**: WHEN a User studies a Fork, THE SRS_Engine SHALL not modify the Card schedules of the source Deck for that User; the two schedules SHALL remain independent.
- **Rating coverage**: For all four valid recall ratings ("Again", "Hard", "Good", "Easy"), THE SRS_Engine SHALL produce a distinct, valid next-review interval. No two ratings SHALL map to the same interval.

---

### Requirement 6: Forking Decks

**User Story:** As a User, I want to fork a public deck, so that I can customize it for my own study needs without affecting the original.

#### Acceptance Criteria

1. WHEN a User forks a public Deck, THE Deck_Service SHALL create a new Deck owned by the forking User containing copies of all Cards from the source Deck at the time of forking.
2. WHEN a User modifies a forked Deck, THE Deck_Service SHALL apply changes only to the Fork and SHALL NOT modify the source Deck.
3. THE Deck_Service SHALL record the source Deck reference (original Deck ID and original author display name) on every Fork, and display that attribution on the Fork's detail page.
4. WHEN a User views a Deck, THE Deck_Service SHALL display the total number of times that Deck has been forked.
5. IF a User attempts to fork their own Deck, THEN THE Deck_Service SHALL return an error indicating self-forking is not permitted.
6. IF a User attempts to fork a private Deck, THEN THE Deck_Service SHALL return an authorization error.

#### Correctness Properties

- **Fork isolation**: WHEN the source Deck is modified after a Fork is created, the Fork SHALL reflect the state of the source Deck at fork time, not the modified state.
- **Attribution invariant**: For all Forks, the source Deck ID and original author display name SHALL be recorded at fork time and SHALL remain unchanged even if the source Deck is subsequently renamed or deleted.

---

### Requirement 7: AI Flashcard Generator

**User Story:** As a User, I want to generate flashcards from a topic or pasted text using AI, so that I can quickly populate a deck without manually writing each card.

#### Acceptance Criteria

1. WHEN a User submits a text input (pasted content or a topic description) to the AI flashcard generator, THE AI_Service SHALL generate a set of Cards in front/back format and return them for the User to review before saving.
2. WHEN a User accepts the generated Cards, THE Deck_Service SHALL add the accepted Cards to the User's specified Deck as if they were manually created.
3. THE AI_Service SHALL generate between 3 and 30 Cards per generation request, based on the length and complexity of the input.
4. IF the input text submitted to the AI flashcard generator is fewer than 10 characters, THEN THE AI_Service SHALL return a validation error requesting more descriptive input.
5. IF the AI_Service fails to generate Cards due to an upstream error, THEN THE AI_Service SHALL return an error message to the User and SHALL NOT partially add Cards to the Deck.
6. WHERE the User provides a target Card count (between 3 and 30), THE AI_Service SHALL attempt to generate approximately that number of Cards.
7. WHEN generated Cards are presented to the User for review, THE AI_Service SHALL allow the User to edit, remove, or reorder individual generated Cards before saving.

#### Correctness Properties

- **Atomicity**: WHEN a User accepts generated Cards, THE Deck_Service SHALL either persist all accepted Cards or none; a partial write on failure SHALL NOT occur.
- **Count bounds**: For all generation requests, the number of Cards returned by THE AI_Service SHALL be within the range [3, 30] (inclusive), or an error SHALL be returned.

---

### Requirement 8: AI Quiz Generator

**User Story:** As a User, I want to generate a quiz from a deck using AI, so that I can test my knowledge with multiple-choice or short-answer questions.

#### Acceptance Criteria

1. WHEN a User requests a quiz from a Deck, THE AI_Service SHALL generate a set of quiz questions derived from the Cards in that Deck and return them for the User to attempt.
2. THE AI_Service SHALL support two quiz question types: multiple-choice (one correct answer among four options) and short-answer (a free-text response evaluated against an expected answer).
3. THE AI_Service SHALL generate between 3 and 20 quiz questions per quiz generation request.
4. WHEN a User submits answers to a quiz, THE AI_Service SHALL evaluate the answers and return a score as a percentage of correct answers, along with per-question feedback.
5. IF the Deck contains fewer than 3 Cards, THEN THE AI_Service SHALL return an error indicating the Deck does not contain enough Cards to generate a quiz.
6. IF the AI_Service fails to generate a quiz due to an upstream error, THEN THE AI_Service SHALL return a descriptive error message to the User.
7. WHEN a User completes a quiz, THE Progress_Tracker SHALL record the quiz attempt, including: Deck ID, question count, score percentage, and timestamp.

#### Correctness Properties

- **Score bounds invariant**: For all completed quizzes, the score percentage returned by THE AI_Service SHALL be in the range [0, 100] inclusive.
- **Question type validity**: For all multiple-choice questions generated by THE AI_Service, exactly one of the four answer options SHALL be marked as correct.

---

## Should Have (v1.1 — Shortly After Launch)

---

### Requirement 9: Rating and Community Feedback

**User Story:** As a User, I want to rate decks I have studied, so that the community can identify high-quality content.

#### Acceptance Criteria

1. WHEN a User completes a Study_Session on a Deck, THE Deck_Service SHALL make a rating interface available to that User for that Deck.
2. WHEN a User submits a Rating for a Deck, THE Deck_Service SHALL store the Rating associated with that User and Deck and recalculate the Deck's average Rating.
3. THE Deck_Service SHALL allow each User to submit exactly one Rating per Deck; a subsequent submission by the same User for the same Deck SHALL update the existing Rating rather than creating a duplicate.
4. THE Deck_Service SHALL display the average Rating and total rating count on every public Deck's detail page.
5. WHILE a User has not completed at least one Study_Session on a Deck, THE Deck_Service SHALL not display the rating interface for that Deck to that User.
6. IF a User submits a Rating with a value outside the integer range 1 to 5 inclusive, THEN THE Deck_Service SHALL return a validation error.

#### Correctness Properties

- **One-rating-per-user invariant**: For all (User, Deck) pairs, THE Deck_Service SHALL store at most one Rating; submitting a second Rating SHALL overwrite the first, not create a second record.
- **Average accuracy**: The average Rating displayed for a Deck SHALL equal the arithmetic mean of all stored Ratings for that Deck, rounded to one decimal place.

---

### Requirement 10: User Progress and Statistics

**User Story:** As a User, I want to see my study progress and streaks, so that I stay motivated and can track my learning over time.

#### Acceptance Criteria

1. THE Progress_Tracker SHALL maintain a daily study streak counter for each User, incrementing it for each calendar day on which the User completes at least one Study_Session.
2. WHEN a User's study streak is broken by missing a full calendar day with no Study_Session, THE Progress_Tracker SHALL reset the streak counter to zero on the next session start.
3. THE Progress_Tracker SHALL display the following statistics on a User's profile dashboard: total Cards studied (all time), total Study_Sessions completed, current streak in days, longest streak in days, and per-Deck retention rate.
4. WHEN a User views a specific Deck's progress page, THE Progress_Tracker SHALL display: total Cards in the Deck, Cards mastered (rated "Easy" at least once), Cards still learning, and Cards not yet studied.
5. THE Progress_Tracker SHALL render a heatmap of daily study activity for the past 365 days on the User's profile page.
6. IF a User has no recorded Study_Sessions, THEN THE Progress_Tracker SHALL display zeroed statistics without returning an error.

#### Correctness Properties

- **Card state partition invariant**: For a given User and Deck, the sum of (Cards mastered + Cards learning + Cards not yet studied) SHALL equal the total Card count of the Deck.
- **Streak monotonicity**: THE Progress_Tracker SHALL only increment the streak counter once per calendar day, regardless of how many Study_Sessions a User completes on that day.

---

### Requirement 11: Notifications and Reminders

**User Story:** As a User, I want to receive reminders when cards are due for review, so that I can maintain my study schedule without manual tracking.

#### Acceptance Criteria

1. WHEN a User's scheduled Card reviews become due, THE Auth_Service SHALL send a notification via the User's preferred channel (email or in-app notification).
2. IF a notification cannot be delivered at the scheduled time, THEN THE Auth_Service SHALL attempt re-delivery and SHALL send the notification at the earliest available opportunity rather than suppressing it.
3. THE Auth_Service SHALL support in-app notifications displayed in the platform header as an unread count badge.
4. WHEN a User marks a notification as read, THE Auth_Service SHALL update the notification status and decrement the unread count badge.
5. IF a User has disabled notifications for a specific Deck, THEN THE Auth_Service SHALL suppress review reminders for Cards belonging to that Deck.
6. WHERE email notifications are enabled, THE Auth_Service SHALL include a one-click unsubscribe link in every notification email.

---

## Could Have (v2+ — Deferred)

---

### Requirement 12: Deck Import/Export

**User Story:** As a User, I want to export and import decks in a portable format, so that I can back up my content and migrate between platforms.

> **Status: Deferred to v2.** Import/export is valuable but not required for a useful v1. Anki import in particular requires significant format-parsing work that is better addressed after core study loops are validated.

#### Acceptance Criteria

1. WHEN a User requests an export of a Deck they own, THE Deck_Service SHALL serialize the Deck and all its Cards into a valid JSON document conforming to the StudyDeck Export Schema and return it as a downloadable file.
2. WHEN a User uploads a JSON file conforming to the StudyDeck Export Schema, THE Deck_Service SHALL parse the file and create a new Deck owned by the importing User with all Cards from the file.
3. WHEN a User uploads a valid Anki-format (.apkg) file, THE Deck_Service SHALL convert it into a new Deck owned by the importing User with equivalent Cards.
4. IF an uploaded file does not conform to the StudyDeck Export Schema and is not a recognized Anki file, THEN THE Deck_Service SHALL return a descriptive error message identifying the format violation.
5. THE Deck_Service SHALL include a pretty-printer that formats Deck objects back into valid JSON matching the StudyDeck Export Schema.
6. FOR ALL valid Deck objects, exporting then importing then re-exporting SHALL produce a JSON document structurally equivalent to the original export (round-trip property).

#### Correctness Properties

- **Round-trip property**: `parse(format(deck)) ≡ deck` — for all valid Deck objects, importing an exported JSON SHALL produce a Deck semantically equivalent to the original.
- **Error coverage**: For all malformed inputs, THE Deck_Service SHALL return a descriptive error; no malformed input SHALL silently produce a partial or corrupt Deck.

---

### Requirement 13: Mindmap Generation

> **Status: Explicitly deferred from v1 by product decision.** Mindmap generation adds significant implementation complexity (graph rendering, AI topology generation) relative to v1 value. This requirement is documented for future planning only.

**User Story:** As a User, I want to visualize a deck as a mindmap, so that I can understand relationships between concepts at a glance.

*Acceptance criteria to be defined in a future spec iteration when this feature is prioritized.*
