"""AI router — flashcard generation and quiz generation endpoints."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from data import store
from models.schemas import (
    GenerateCardsRequest, GenerateCardsResponse, GeneratedCard,
    SaveCardsRequest, GenerateQuizResponse, QuizQuestion,
    SubmitQuizRequest, QuizResultResponse, QuizFeedbackItem,
    QuizHistoryResponse, QuizAttemptResponse,
)
from routers.auth import _get_current_user_id
from services.ai_service import generate_flashcards, generate_quiz, evaluate_short_answer, AIServiceError

router = APIRouter()
# Temporary in-memory store for pending quiz questions (keyed by quiz_id)
_pending_quizzes: dict = {}

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

@router.post("/generate-cards", response_model=GenerateCardsResponse)
async def gen_cards(req: GenerateCardsRequest, user_id: str = Depends(_get_current_user_id)):
    if len(req.text) < 10:
        raise HTTPException(status_code=400, detail="Input text must be at least 10 characters.")
    try:
        cards = generate_flashcards(req.text, req.target_count or 10)
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return GenerateCardsResponse(generated_cards=[GeneratedCard(front=c["front"], back=c["back"]) for c in cards])

@router.post("/save-cards", status_code=201)
async def save_cards(req: SaveCardsRequest, user_id: str = Depends(_get_current_user_id)):
    deck = store.decks.get(req.deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found.")
    if deck["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorised.")
    existing = [c for c in store.cards.values() if c["deck_id"] == req.deck_id]
    if len(existing) + len(req.cards) > 1000:
        raise HTTPException(status_code=400, detail="Adding these cards would exceed the 1,000 card limit.")
    now = _now_iso()
    start_pos = max((c["position"] for c in existing), default=-1) + 1
    new_cards = []
    for i, card in enumerate(req.cards):
        cid = str(uuid.uuid4())
        new_card = {"id": cid, "deck_id": req.deck_id, "front": card.front, "back": card.back,
                    "position": start_pos + i, "created_at": now, "updated_at": now}
        new_cards.append((cid, new_card))
    # Atomic write — all or nothing
    for cid, card in new_cards:
        store.cards[cid] = card
    deck["updated_at"] = now
    return {"status": "ok", "cards_added": len(new_cards)}

@router.post("/generate-quiz/{deck_id}", response_model=GenerateQuizResponse)
async def gen_quiz(deck_id: str, user_id: str = Depends(_get_current_user_id)):
    deck = store.decks.get(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found.")
    deck_cards = [c for c in store.cards.values() if c["deck_id"] == deck_id]
    if len(deck_cards) < 3:
        raise HTTPException(status_code=400, detail="Deck needs at least 3 cards to generate a quiz.")
    try:
        questions = generate_quiz(deck_cards, count=min(len(deck_cards) * 2, 10))
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    quiz_id = str(uuid.uuid4())
    _pending_quizzes[quiz_id] = questions
    return GenerateQuizResponse(
        quiz_id=quiz_id,
        questions=[QuizQuestion(**{k: q.get(k) for k in QuizQuestion.model_fields}) for q in questions]
    )

@router.post("/submit-quiz", response_model=QuizResultResponse)
async def submit_quiz(req: SubmitQuizRequest, user_id: str = Depends(_get_current_user_id)):
    questions = _pending_quizzes.get(req.quiz_id)
    if not questions:
        raise HTTPException(status_code=404, detail="Quiz not found or expired.")
    q_map = {q["id"]: q for q in questions}
    correct_count = 0
    feedback = []
    for ans in req.answers:
        q = q_map.get(ans.question_id)
        if not q:
            continue
        if q["type"] == "multiple_choice":
            try:
                is_correct = int(ans.answer) == q.get("correct_index", -1)
            except (ValueError, TypeError):
                is_correct = False
        else:
            is_correct = evaluate_short_answer(q.get("correct_answer",""), ans.answer)
        if is_correct:
            correct_count += 1
        feedback.append(QuizFeedbackItem(question_id=ans.question_id, correct=is_correct, correct_answer=q.get("correct_answer","")))
    total = len(req.answers)
    score = round((correct_count / total * 100) if total > 0 else 0.0, 2)
    score = max(0.0, min(100.0, score))
    attempt_id = str(uuid.uuid4())
    store.quiz_attempts[attempt_id] = {
        "id": attempt_id, "user_id": user_id, "deck_id": req.deck_id,
        "question_count": total, "score_percent": score, "timestamp": _now_iso(),
    }
    return QuizResultResponse(score_percent=score, feedback=feedback)

@router.get("/quiz-history/{deck_id}", response_model=QuizHistoryResponse)
async def quiz_history(deck_id: str, user_id: str = Depends(_get_current_user_id)):
    attempts = [a for a in store.quiz_attempts.values() if a["deck_id"] == deck_id and a["user_id"] == user_id]
    attempts.sort(key=lambda a: a["timestamp"], reverse=True)
    return QuizHistoryResponse(attempts=[QuizAttemptResponse(**{k: a[k] for k in QuizAttemptResponse.model_fields}) for a in attempts])
