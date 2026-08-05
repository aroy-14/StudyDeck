"""AI service — OpenAI-backed flashcard and quiz generation."""
import os, json, uuid
from openai import OpenAI

class AIServiceError(Exception):
    """Raised when the OpenAI API call fails after retries."""
    pass

def _get_client() -> OpenAI:
    key = os.environ.get("OPENAI_API_KEY", "")
    return OpenAI(api_key=key) if key else OpenAI()

def _chat(messages: list, client: OpenAI) -> str:
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()

def _parse_json(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)

def generate_flashcards(text: str, target_count: int = 10) -> list[dict]:
    if len(text) < 10:
        raise ValueError("Input text must be at least 10 characters.")
    target_count = max(3, min(30, target_count))
    client = _get_client()
    prompt = (
        f"Generate {target_count} flashcards from the following text. "
        "Return ONLY a JSON array of objects with \"front\" and \"back\" string fields. "
        "Each front is a question or prompt. Each back is a concise answer. "
        f"Generate between 3 and 30 cards.\n\nText:\n{text}"
    )
    messages = [
        {"role": "system", "content": "You are a flashcard creation assistant. Generate clear, concise study flashcards."},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(2):
        try:
            raw = _chat(messages, client)
            cards = _parse_json(raw)
            if not isinstance(cards, list) or not cards:
                raise ValueError("Empty or invalid response")
            cards = [{"front": str(c.get("front","")).strip(), "back": str(c.get("back","")).strip()} for c in cards if c.get("front") and c.get("back")]
            cards = cards[:30]
            if len(cards) < 3:
                raise ValueError("Too few cards generated")
            return cards
        except Exception as e:
            if attempt == 1:
                raise AIServiceError(f"Failed to generate flashcards: {e}") from e

def generate_quiz(cards: list[dict], count: int = 10) -> list[dict]:
    if len(cards) < 3:
        raise ValueError("Need at least 3 cards to generate a quiz.")
    count = max(3, min(20, count))
    client = _get_client()
    cards_json = json.dumps([{"front": c["front"], "back": c["back"]} for c in cards[:40]])
    prompt = (
        f"Generate {count} quiz questions from the following flashcards. "
        "Mix multiple-choice (4 options, 1 correct) and short-answer questions. "
        "Return ONLY a JSON array. Each object must have:\n"
        "  - \"type\": \"multiple_choice\" or \"short_answer\"\n"
        "  - \"question\": string\n"
        "  - \"correct_answer\": string\n"
        "  - \"options\": [string,string,string,string] (multiple_choice only)\n"
        "  - \"correct_index\": 0-3 integer (multiple_choice only)\n\n"
        f"Flashcards:\n{cards_json}"
    )
    messages = [
        {"role": "system", "content": "You are a quiz generation assistant. Create quiz questions from flashcard content."},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(2):
        try:
            raw = _chat(messages, client)
            questions = _parse_json(raw)
            result = []
            for q in questions:
                qtype = q.get("type", "short_answer")
                item = {"id": str(uuid.uuid4()), "type": qtype, "question": q.get("question",""), "correct_answer": q.get("correct_answer","")}
                if qtype == "multiple_choice":
                    opts = q.get("options", [])
                    idx = q.get("correct_index", 0)
                    if len(opts) == 4 and isinstance(idx, int) and 0 <= idx <= 3:
                        item["options"] = opts; item["correct_index"] = idx
                    else:
                        item["type"] = "short_answer"
                result.append(item)
            result = result[:20]
            if len(result) < 3:
                raise ValueError("Too few questions generated")
            return result
        except Exception as e:
            if attempt == 1:
                raise AIServiceError(f"Failed to generate quiz: {e}") from e

def evaluate_short_answer(expected: str, student: str) -> bool:
    client = _get_client()
    try:
        messages = [
            {"role": "system", "content": "You are a quiz grader. Answer only \"correct\" or \"incorrect\"."},
            {"role": "user", "content": f"Expected answer: {expected}\nStudent answer: {student}\nIs the student's answer correct?"},
        ]
        result = _chat(messages, client).lower()
        return "correct" in result and "incorrect" not in result
    except Exception:
        return expected.strip().lower() == student.strip().lower()
