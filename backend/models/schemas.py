from pydantic import BaseModel, Field
from typing import Optional, List, Literal


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    display_name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str


# ---------------------------------------------------------------------------
# Deck schemas
# ---------------------------------------------------------------------------

class CreateDeckRequest(BaseModel):
    title: str
    description: str = ""
    visibility: Literal["public", "private"] = "public"
    tags: List[str] = []


class UpdateDeckRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[Literal["public", "private"]] = None
    tags: Optional[List[str]] = None


class DeckResponse(BaseModel):
    id: str
    owner_id: str
    title: str
    description: str
    visibility: str
    tags: List[str]
    fork_count: int
    source_deck_id: Optional[str] = None
    source_author_name: Optional[str] = None
    view_count: int
    study_session_count: int
    created_at: str
    updated_at: str


class DeckListResponse(BaseModel):
    decks: List[DeckResponse]
    total: int
    page: int
    pages: int


# ---------------------------------------------------------------------------
# Card schemas
# ---------------------------------------------------------------------------

class CreateCardRequest(BaseModel):
    front: str
    back: str


class UpdateCardRequest(BaseModel):
    front: Optional[str] = None
    back: Optional[str] = None


class CardResponse(BaseModel):
    id: str
    deck_id: str
    front: str
    back: str
    position: int
    created_at: str
    updated_at: str


class ReorderCardsRequest(BaseModel):
    order: List[str]  # ordered list of card IDs


# ---------------------------------------------------------------------------
# Study session schemas
# ---------------------------------------------------------------------------

class StartSessionResponse(BaseModel):
    session_id: Optional[str] = None
    due_cards: List[CardResponse] = []
    due_count: int
    next_due: Optional[str] = None  # ISO date, set when due_count == 0


class RateCardRequest(BaseModel):
    session_id: str
    card_id: str
    rating: Literal["Again", "Hard", "Good", "Easy"]


class EndSessionRequest(BaseModel):
    session_id: str
    duration_seconds: int


class CardProgressItem(BaseModel):
    card_id: str
    last_rating: Optional[str] = None
    next_review: Optional[str] = None
    interval_days: int = 0
    review_count: int = 0


class ProgressResponse(BaseModel):
    deck_id: str
    total_cards: int
    mastered: int       # last_rating == "Easy"
    learning: int       # has a rating but not "Easy"
    not_studied: int    # no progress record yet
    card_progress: List[CardProgressItem] = []


# ---------------------------------------------------------------------------
# AI schemas
# ---------------------------------------------------------------------------

class GeneratedCard(BaseModel):
    front: str
    back: str


class GenerateCardsRequest(BaseModel):
    text: str
    deck_id: str
    target_count: Optional[int] = 10  # 3-30


class GenerateCardsResponse(BaseModel):
    generated_cards: List[GeneratedCard]


class SaveCardsRequest(BaseModel):
    deck_id: str
    cards: List[GeneratedCard]


class QuizQuestion(BaseModel):
    id: str
    type: Literal["multiple_choice", "short_answer"]
    question: str
    options: Optional[List[str]] = None       # 4 items for multiple_choice
    correct_index: Optional[int] = None       # 0-3 for multiple_choice
    correct_answer: Optional[str] = None      # for short_answer


class GenerateQuizResponse(BaseModel):
    quiz_id: str
    questions: List[QuizQuestion]


class QuizAnswer(BaseModel):
    question_id: str
    answer: str  # string for both MC (index as string) and short answer


class SubmitQuizRequest(BaseModel):
    quiz_id: str
    deck_id: str
    answers: List[QuizAnswer]


class QuizFeedbackItem(BaseModel):
    question_id: str
    correct: bool
    correct_answer: str


class QuizResultResponse(BaseModel):
    score_percent: float
    feedback: List[QuizFeedbackItem]


class QuizAttemptResponse(BaseModel):
    id: str
    deck_id: str
    question_count: int
    score_percent: float
    timestamp: str


class QuizHistoryResponse(BaseModel):
    attempts: List[QuizAttemptResponse]
