"""Cards router — CRUD and reorder for cards within a deck."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from data import store
from models.schemas import CreateCardRequest, UpdateCardRequest, CardResponse, ReorderCardsRequest
from routers.auth import _get_current_user_id, _get_current_user_id as _require_auth

router = APIRouter()

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _get_deck_or_404(deck_id: str):
    d = store.decks.get(deck_id)
    if not d:
        raise HTTPException(status_code=404, detail="Deck not found.")
    return d

def _require_owner(deck: dict, user_id: str):
    if deck["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorised.")

def _card_to_response(c: dict) -> CardResponse:
    return CardResponse(**{k: c[k] for k in CardResponse.model_fields})

def _deck_cards(deck_id: str) -> list:
    return sorted([c for c in store.cards.values() if c["deck_id"] == deck_id], key=lambda c: c["position"])

@router.get("/decks/{deck_id}/cards", response_model=list[CardResponse])
async def list_cards(deck_id: str):
    deck = _get_deck_or_404(deck_id)
    return [_card_to_response(c) for c in _deck_cards(deck_id)]

@router.post("/decks/{deck_id}/cards", response_model=CardResponse, status_code=201)
async def add_card(deck_id: str, req: CreateCardRequest, user_id: str = Depends(_get_current_user_id)):
    deck = _get_deck_or_404(deck_id)
    _require_owner(deck, user_id)
    if not req.front.strip() or not req.back.strip():
        raise HTTPException(status_code=400, detail="Front and back cannot be empty.")
    existing = _deck_cards(deck_id)
    if len(existing) >= 1000:
        raise HTTPException(status_code=400, detail="Deck has reached the 1,000 card limit.")
    position = max((c["position"] for c in existing), default=-1) + 1
    now = _now_iso()
    card_id = str(uuid.uuid4())
    card = {"id": card_id, "deck_id": deck_id, "front": req.front, "back": req.back,
            "position": position, "created_at": now, "updated_at": now}
    store.cards[card_id] = card
    deck["updated_at"] = now
    return _card_to_response(card)

@router.put("/decks/{deck_id}/cards/reorder", status_code=200)
async def reorder_cards(deck_id: str, req: ReorderCardsRequest, user_id: str = Depends(_get_current_user_id)):
    deck = _get_deck_or_404(deck_id)
    _require_owner(deck, user_id)
    for i, card_id in enumerate(req.order):
        if card_id in store.cards and store.cards[card_id]["deck_id"] == deck_id:
            store.cards[card_id]["position"] = i
    deck["updated_at"] = _now_iso()
    return {"status": "ok"}

@router.put("/decks/{deck_id}/cards/{card_id}", response_model=CardResponse)
async def update_card(deck_id: str, card_id: str, req: UpdateCardRequest, user_id: str = Depends(_get_current_user_id)):
    deck = _get_deck_or_404(deck_id)
    _require_owner(deck, user_id)
    card = store.cards.get(card_id)
    if not card or card["deck_id"] != deck_id:
        raise HTTPException(status_code=404, detail="Card not found.")
    if req.front is not None:
        if not req.front.strip():
            raise HTTPException(status_code=400, detail="Front cannot be empty.")
        card["front"] = req.front
    if req.back is not None:
        if not req.back.strip():
            raise HTTPException(status_code=400, detail="Back cannot be empty.")
        card["back"] = req.back
    now = _now_iso()
    card["updated_at"] = now
    deck["updated_at"] = now
    return _card_to_response(card)

@router.delete("/decks/{deck_id}/cards/{card_id}", status_code=204)
async def delete_card(deck_id: str, card_id: str, user_id: str = Depends(_get_current_user_id)):
    deck = _get_deck_or_404(deck_id)
    _require_owner(deck, user_id)
    card = store.cards.get(card_id)
    if not card or card["deck_id"] != deck_id:
        raise HTTPException(status_code=404, detail="Card not found.")
    del store.cards[card_id]
    deck["updated_at"] = _now_iso()
