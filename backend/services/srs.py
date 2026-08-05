"""SRS — Spaced Repetition Service (pure functions, no I/O)."""
from datetime import date, timedelta
from typing import Optional

INTERVALS = {"Again": 1, "Hard": 3, "Good": 7, "Easy": 21}
VALID_RATINGS = set(INTERVALS.keys())

def next_review_date(rating: str, from_date: date) -> date:
    if rating not in VALID_RATINGS:
        raise ValueError(f"Invalid rating '{rating}'. Must be one of {VALID_RATINGS}.")
    return from_date + timedelta(days=INTERVALS[rating])

def build_session_queue(cards: list, progress_records: dict, today: date) -> list:
    """Return ordered list of cards for a study session.
    Order: overdue (most overdue first) interleaved with new cards. Future cards excluded.
    progress_records: dict keyed by card_id -> progress dict
    """
    overdue, new_cards = [], []
    for card in cards:
        prog = progress_records.get(card["id"])
        if prog is None:
            new_cards.append(card)
        else:
            next_rev = date.fromisoformat(prog["next_review"][:10])
            if next_rev <= today:
                overdue.append((next_rev, card))
    overdue.sort(key=lambda x: x[0])
    overdue_cards = [c for _, c in overdue]
    # Interleave: insert a new card every 3 overdue cards
    result = []
    new_idx = 0
    for i, card in enumerate(overdue_cards):
        result.append(card)
        if (i + 1) % 3 == 0 and new_idx < len(new_cards):
            result.append(new_cards[new_idx]); new_idx += 1
    result.extend(new_cards[new_idx:])
    return result

def nearest_next_review(cards: list, progress_records: dict, today: date) -> Optional[str]:
    """Return the earliest future next_review date string, or None if no scheduled cards."""
    future_dates = []
    for card in cards:
        prog = progress_records.get(card["id"])
        if prog:
            next_rev = date.fromisoformat(prog["next_review"][:10])
            if next_rev > today:
                future_dates.append(next_rev)
    return str(min(future_dates)) if future_dates else None
