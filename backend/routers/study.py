"""Study session router — start, rate, end, progress."""
import uuid
from datetime import datetime, timezone, date
from fastapi import APIRouter, HTTPException, status, Depends
from data import store
from models.schemas import (
    StartSessionResponse, RateCardRequest, EndSessionRequest,
    ProgressResponse, CardProgressItem, CardResponse
)
from routers.auth import _get_current_user_id
from services.srs import build_session_queue, next_review_date, nearest_next_review, VALID_RATINGS

router = APIRouter()

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _card_to_response(c: dict) -> CardResponse:
    return CardResponse(**{k: c[k] for k in CardResponse.model_fields})

@router.post("/{deck_id}/start", response_model=StartSessionResponse)
async def start_session(deck_id: str, user_id: str = Depends(_get_current_user_id)):
    deck = store.decks.get(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found.")
    deck_cards = [c for c in store.cards.values() if c["deck_id"] == deck_id]
    if not deck_cards:
        return StartSessionResponse(due_count=0, next_due=None)
    progress = {c["id"]: store.card_progress.get(f"{user_id}:{c['id']}") for c in deck_cards}
    progress_clean = {k: v for k, v in progress.items() if v is not None}
    today = date.today()
    queue = build_session_queue(deck_cards, progress_clean, today)
    if not queue:
        next_due = nearest_next_review(deck_cards, progress_clean, today)
        return StartSessionResponse(due_count=0, next_due=next_due)
    session_id = str(uuid.uuid4())
    store.study_sessions[session_id] = {
        "id": session_id, "user_id": user_id, "deck_id": deck_id,
        "cards_reviewed": 0, "ratings": {}, "duration_seconds": 0,
        "started_at": _now_iso(), "ended_at": None,
    }
    return StartSessionResponse(session_id=session_id, due_cards=[_card_to_response(c) for c in queue], due_count=len(queue))

@router.post("/{deck_id}/rate", status_code=200)
async def rate_card(deck_id: str, req: RateCardRequest, user_id: str = Depends(_get_current_user_id)):
    if req.rating not in VALID_RATINGS:
        raise HTTPException(status_code=400, detail=f"Invalid rating. Must be one of {VALID_RATINGS}.")
    session = store.study_sessions.get(req.session_id)
    if not session or session["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Session not found.")
    card = store.cards.get(req.card_id)
    if not card or card["deck_id"] != deck_id:
        raise HTTPException(status_code=404, detail="Card not found in this deck.")
    today = date.today()
    next_rev = next_review_date(req.rating, today)
    key = f"{user_id}:{req.card_id}"
    existing = store.card_progress.get(key, {})
    store.card_progress[key] = {
        "user_id": user_id, "card_id": req.card_id, "deck_id": deck_id,
        "last_rating": req.rating, "next_review": str(next_rev),
        "interval_days": 21 if req.rating == "Easy" else 7 if req.rating == "Good" else 3 if req.rating == "Hard" else 1,
        "review_count": existing.get("review_count", 0) + 1,
    }
    session["ratings"][req.card_id] = req.rating
    session["cards_reviewed"] = len(session["ratings"])
    return {"status": "ok", "next_review": str(next_rev)}

@router.post("/{deck_id}/end", status_code=200)
async def end_session(deck_id: str, req: EndSessionRequest, user_id: str = Depends(_get_current_user_id)):
    session = store.study_sessions.get(req.session_id)
    if not session or session["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Session not found.")
    session["ended_at"] = _now_iso()
    session["duration_seconds"] = req.duration_seconds
    deck = store.decks.get(deck_id)
    if deck:
        deck["study_session_count"] += 1
    return {"status": "ok", "cards_reviewed": session["cards_reviewed"], "duration_seconds": req.duration_seconds}

@router.get("/{deck_id}/progress", response_model=ProgressResponse)
async def get_progress(deck_id: str, user_id: str = Depends(_get_current_user_id)):
    deck = store.decks.get(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found.")
    deck_cards = [c for c in store.cards.values() if c["deck_id"] == deck_id]
    mastered = learning = not_studied = 0
    progress_items = []
    for card in deck_cards:
        prog = store.card_progress.get(f"{user_id}:{card['id']}")
        if prog is None:
            not_studied += 1
            progress_items.append(CardProgressItem(card_id=card["id"]))
        elif prog["last_rating"] == "Easy":
            mastered += 1
            progress_items.append(CardProgressItem(card_id=card["id"], last_rating=prog["last_rating"], next_review=prog["next_review"], interval_days=prog["interval_days"], review_count=prog["review_count"]))
        else:
            learning += 1
            progress_items.append(CardProgressItem(card_id=card["id"], last_rating=prog["last_rating"], next_review=prog["next_review"], interval_days=prog["interval_days"], review_count=prog["review_count"]))
    return ProgressResponse(deck_id=deck_id, total_cards=len(deck_cards), mastered=mastered, learning=learning, not_studied=not_studied, card_progress=progress_items)
