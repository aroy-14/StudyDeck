"""
StudyDeck data layer — Supabase (PostgreSQL) backend.

All routers import from this module via:
  from data import store
  store.users  -> SupabaseTable("users")
  store.decks  -> SupabaseTable("decks")
  etc.

Each SupabaseTable exposes .values(), .get(id), .set(id, data),
.delete(id), .clear() — matching the dict interface the routers expect
so no router code needs to change.
"""

import os
from typing import Any
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def _get_client() -> Client:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment. "
            "Copy .env.example to .env and fill in your Supabase project credentials."
        )
    return create_client(url, key)

# ---------------------------------------------------------------------------
# SupabaseTable — dict-like wrapper around a Supabase table
# ---------------------------------------------------------------------------

class SupabaseTable:
    """
    Thin wrapper that makes a Supabase table behave like a Python dict.
    Routers use store.users[id], store.users.values(), etc.
    """

    def __init__(self, table_name: str, pk: str = "id"):
        self._table = table_name
        self._pk = pk

    def _db(self) -> Client:
        return _get_client()

    # --- dict-style reads ---

    def get(self, key: str, default: Any = None) -> Any:
        res = self._db().table(self._table).select("*").eq(self._pk, key).execute()
        rows = res.data
        return rows[0] if rows else default

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def values(self) -> list:
        res = self._db().table(self._table).select("*").execute()
        return res.data or []

    def items(self) -> list[tuple]:
        rows = self.values()
        return [(r[self._pk], r) for r in rows]

    def keys(self) -> list:
        rows = self.values()
        return [r[self._pk] for r in rows]

    # --- dict-style writes ---

    def __setitem__(self, key: str, value: dict) -> None:
        """Upsert a row. key must match value[pk]."""
        db = self._db()
        # Convert any non-serialisable types
        row = _prepare(value)
        db.table(self._table).upsert(row).execute()

    def __delitem__(self, key: str) -> None:
        self._db().table(self._table).delete().eq(self._pk, key).execute()

    def clear(self) -> None:
        """Delete all rows — only used in tests."""
        self._db().table(self._table).delete().neq(self._pk, "00000000-0000-0000-0000-000000000000").execute()

    def pop(self, key: str, *args) -> Any:
        val = self.get(key)
        if val is not None:
            del self[key]
            return val
        if args:
            return args[0]
        raise KeyError(key)


# ---------------------------------------------------------------------------
# card_progress uses a composite key "user_id:card_id"
# ---------------------------------------------------------------------------

class CardProgressTable(SupabaseTable):
    """
    card_progress is keyed by "user_id:card_id" in the router layer
    but stored with (user_id, card_id) unique constraint in Postgres.
    """

    def _parse_key(self, key: str) -> tuple[str, str]:
        parts = key.split(":", 1)
        return parts[0], parts[1]

    def get(self, key: str, default: Any = None) -> Any:
        uid, cid = self._parse_key(key)
        res = self._db().table(self._table).select("*").eq("user_id", uid).eq("card_id", cid).execute()
        rows = res.data
        return rows[0] if rows else default

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __setitem__(self, key: str, value: dict) -> None:
        db = self._db()
        row = _prepare(value)
        # Use upsert on the unique (user_id, card_id) constraint
        db.table(self._table).upsert(row, on_conflict="user_id,card_id").execute()

    def __delitem__(self, key: str) -> None:
        uid, cid = self._parse_key(key)
        self._db().table(self._table).delete().eq("user_id", uid).eq("card_id", cid).execute()

    def values(self) -> list:
        res = self._db().table(self._table).select("*").execute()
        return res.data or []


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _prepare(value: dict) -> dict:
    """Convert Python types to JSON-serialisable forms for Supabase."""
    result = {}
    for k, v in value.items():
        if isinstance(v, dict):
            result[k] = v  # jsonb columns accept dicts directly
        elif isinstance(v, list):
            result[k] = v
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# Module-level store objects (used by all routers)
# ---------------------------------------------------------------------------

users          = SupabaseTable("users")
decks          = SupabaseTable("decks")
cards          = SupabaseTable("cards")
card_progress  = CardProgressTable("card_progress")
study_sessions = SupabaseTable("study_sessions")
quiz_attempts  = SupabaseTable("quiz_attempts")


def clear_all() -> None:
    """Clear all tables — only for use in tests."""
    for t in [quiz_attempts, study_sessions, card_progress, cards, decks, users]:
        t.clear()
