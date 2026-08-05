"""Decks router — CRUD, feeds, search, fork."""
import uuid, math
from datetime import datetime, timezone, date
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from data import store
from models.schemas import (
    CreateDeckRequest, UpdateDeckRequest, DeckResponse, DeckListResponse
)
from routers.auth import _get_current_user_id

router = APIRouter()

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _deck_to_response(d: dict) -> DeckResponse:
    return DeckResponse(**{k: d[k] for k in DeckResponse.model_fields})

def _get_deck_or_404(deck_id: str) -> dict:
    d = store.decks.get(deck_id)
    if not d:
        raise HTTPException(status_code=404, detail="Deck not found.")
    return d

def _require_owner(deck: dict, user_id: str):
    if deck["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorised.")

def _optional_user(credentials=Depends(__import__('fastapi.security', fromlist=['HTTPBearer']).HTTPBearer(auto_error=False))):
    import os
    from jose import jwt, JWTError
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        uid = payload.get("sub")
        return uid if uid and uid in store.users else None
    except JWTError:
        return None

@router.post("", response_model=DeckResponse, status_code=201)
async def create_deck(req: CreateDeckRequest, user_id: str = Depends(_get_current_user_id)):
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Title is required.")
    now = _now_iso()
    deck_id = str(uuid.uuid4())
    deck = {
        "id": deck_id, "owner_id": user_id, "title": req.title.strip(),
        "description": req.description, "visibility": req.visibility,
        "tags": req.tags, "fork_count": 0,
        "source_deck_id": None, "source_author_name": None,
        "view_count": 0, "study_session_count": 0,
        "created_at": now, "updated_at": now,
    }
    store.decks[deck_id] = deck
    return _deck_to_response(deck)

@router.get("/my", response_model=DeckListResponse)
async def my_decks(page: int = Query(1, ge=1), user_id: str = Depends(_get_current_user_id)):
    items = [d for d in store.decks.values() if d["owner_id"] == user_id]
    items.sort(key=lambda d: d["created_at"], reverse=True)
    total = len(items); limit = 20
    pages = max(1, math.ceil(total / limit))
    start = (page - 1) * limit
    return DeckListResponse(decks=[_deck_to_response(d) for d in items[start:start+limit]], total=total, page=page, pages=pages)

@router.get("/trending", response_model=DeckListResponse)
async def trending():
    items = [d for d in store.decks.values() if d["visibility"] == "public"]
    items.sort(key=lambda d: d["view_count"] + d["study_session_count"] * 2, reverse=True)
    return DeckListResponse(decks=[_deck_to_response(d) for d in items[:20]], total=len(items), page=1, pages=1)

@router.get("/personalized", response_model=DeckListResponse)
async def personalized(page: int = Query(1, ge=1), user_id: str = Depends(_get_current_user_id)):
    studied_deck_ids = {s["deck_id"] for s in store.study_sessions.values() if s["user_id"] == user_id}
    forked_deck_ids = {d["id"] for d in store.decks.values() if d["owner_id"] == user_id and d.get("source_deck_id")}
    user_tags: set[str] = set()
    for did in studied_deck_ids | forked_deck_ids:
        if did in store.decks:
            user_tags.update(store.decks[did].get("tags", []))
    if not user_tags:
        return await public_feed(page=page)
    items = [d for d in store.decks.values() if d["visibility"] == "public" and d["owner_id"] != user_id and any(t in user_tags for t in d.get("tags", []))]
    items.sort(key=lambda d: d["created_at"], reverse=True)
    total = len(items); limit = 20; pages = max(1, math.ceil(total / limit))
    start = (page - 1) * limit
    return DeckListResponse(decks=[_deck_to_response(d) for d in items[start:start+limit]], total=total, page=page, pages=pages)

@router.get("/search", response_model=DeckListResponse)
async def search_decks(q: str = Query(""), tag: str = Query(""), date_from: str = Query(""), date_to: str = Query(""), page: int = Query(1, ge=1)):
    items = [d for d in store.decks.values() if d["visibility"] == "public"]
    if q:
        ql = q.lower()
        items = [d for d in items if ql in d["title"].lower() or ql in d.get("description","").lower() or any(ql in t.lower() for t in d.get("tags",[]))]
    if tag:
        items = [d for d in items if tag in d.get("tags", [])]
    if date_from:
        items = [d for d in items if d["created_at"] >= date_from]
    if date_to:
        items = [d for d in items if d["created_at"] <= date_to + "Z"]
    items.sort(key=lambda d: d["created_at"], reverse=True)
    total = len(items); limit = 20; pages = max(1, math.ceil(total / limit))
    start = (page - 1) * limit
    return DeckListResponse(decks=[_deck_to_response(d) for d in items[start:start+limit]], total=total, page=page, pages=pages)

@router.get("", response_model=DeckListResponse)
async def public_feed(page: int = Query(1, ge=1)):
    items = [d for d in store.decks.values() if d["visibility"] == "public"]
    items.sort(key=lambda d: d["created_at"], reverse=True)
    total = len(items); limit = 20; pages = max(1, math.ceil(total / limit))
    start = (page - 1) * limit
    return DeckListResponse(decks=[_deck_to_response(d) for d in items[start:start+limit]], total=total, page=page, pages=pages)

@router.get("/{deck_id}", response_model=DeckResponse)
async def get_deck(deck_id: str, user_id: Optional[str] = Depends(_optional_user)):
    deck = _get_deck_or_404(deck_id)
    if deck["visibility"] == "private" and deck["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="This deck is private.")
    deck["view_count"] += 1
    return _deck_to_response(deck)

@router.put("/{deck_id}", response_model=DeckResponse)
async def update_deck(deck_id: str, req: UpdateDeckRequest, user_id: str = Depends(_get_current_user_id)):
    deck = _get_deck_or_404(deck_id)
    _require_owner(deck, user_id)
    if req.title is not None:
        if not req.title.strip():
            raise HTTPException(status_code=400, detail="Title cannot be empty.")
        deck["title"] = req.title.strip()
    if req.description is not None: deck["description"] = req.description
    if req.visibility is not None: deck["visibility"] = req.visibility
    if req.tags is not None: deck["tags"] = req.tags
    deck["updated_at"] = _now_iso()
    return _deck_to_response(deck)

@router.delete("/{deck_id}", status_code=204)
async def delete_deck(deck_id: str, user_id: str = Depends(_get_current_user_id)):
    deck = _get_deck_or_404(deck_id)
    _require_owner(deck, user_id)
    to_delete = [cid for cid, c in store.cards.items() if c["deck_id"] == deck_id]
    for cid in to_delete:
        del store.cards[cid]
    del store.decks[deck_id]

@router.post("/{deck_id}/fork", response_model=DeckResponse, status_code=201)
async def fork_deck(deck_id: str, user_id: str = Depends(_get_current_user_id)):
    source = _get_deck_or_404(deck_id)
    if source["owner_id"] == user_id:
        raise HTTPException(status_code=403, detail="You cannot fork your own deck.")
    if source["visibility"] == "private":
        raise HTTPException(status_code=403, detail="Cannot fork a private deck.")
    now = _now_iso()
    new_deck_id = str(uuid.uuid4())
    owner = store.users.get(source["owner_id"], {})
    new_deck = {**source, "id": new_deck_id, "owner_id": user_id, "fork_count": 0,
                "source_deck_id": deck_id, "source_author_name": owner.get("display_name","Unknown"),
                "view_count": 0, "study_session_count": 0, "created_at": now, "updated_at": now}
    store.decks[new_deck_id] = new_deck
    source_cards = [c for c in store.cards.values() if c["deck_id"] == deck_id]
    for c in source_cards:
        new_cid = str(uuid.uuid4())
        store.cards[new_cid] = {**c, "id": new_cid, "deck_id": new_deck_id, "created_at": now, "updated_at": now}
    source["fork_count"] += 1
    return _deck_to_response(new_deck)
