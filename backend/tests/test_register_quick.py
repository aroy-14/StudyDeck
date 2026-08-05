"""Quick verification test for task 1.1 — POST /auth/register"""
from fastapi.testclient import TestClient
from main import app
from data.store import clear_all


def test_register():
    c = TestClient(app)
    clear_all()

    # Successful registration returns 201 with correct email
    r = c.post("/auth/register", json={
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "password123",
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["email"] == "test@example.com"
    assert body["display_name"] == "Test User"
    assert "id" in body

    # Duplicate email returns 400
    r2 = c.post("/auth/register", json={
        "email": "test@example.com",
        "display_name": "Test User 2",
        "password": "password123",
    })
    assert r2.status_code == 400, f"Expected 400, got {r2.status_code}: {r2.text}"

    # Case-insensitive duplicate check
    r3 = c.post("/auth/register", json={
        "email": "TEST@EXAMPLE.COM",
        "display_name": "Test User 3",
        "password": "password123",
    })
    assert r3.status_code == 400, f"Expected 400 (case-insensitive dup), got {r3.status_code}: {r3.text}"

    # Short password returns 400
    r4 = c.post("/auth/register", json={
        "email": "other@example.com",
        "display_name": "Other",
        "password": "short",
    })
    assert r4.status_code == 400, f"Expected 400, got {r4.status_code}: {r4.text}"

    # Password exactly 8 chars is allowed
    r5 = c.post("/auth/register", json={
        "email": "other@example.com",
        "display_name": "Other",
        "password": "12345678",
    })
    assert r5.status_code == 201, f"Expected 201 for 8-char password, got {r5.status_code}: {r5.text}"

    print("register OK")


if __name__ == "__main__":
    test_register()
    print("All assertions passed.")
