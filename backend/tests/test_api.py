"""Integration tests for FastAPI endpoints."""
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import CATEGORY_MEALS, CATEGORY_NEEDS_REVIEW

client = TestClient(app)


def test_health_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Deterministic" in data["engine"]


def test_get_categories():
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert len(data["categories"]) > 0


def test_load_sample_statement():
    response = client.get("/api/sample-statement")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "sample_statement.csv"
    assert data["total_rows"] > 0
    assert len(data["transactions"]) == data["total_rows"]
    assert data["summary"]["total_needs_review_count"] > 0


def test_manual_review_resolution():
    # Load sample statement first
    res = client.get("/api/sample-statement")
    data = res.json()
    txs = data["transactions"]

    # Find the Needs Review transaction for JOES CAFE
    review_tx = next((t for t in txs if "JOES CAFE" in t["description"]), None)
    assert review_tx is not None
    assert review_tx["category"] == CATEGORY_NEEDS_REVIEW
    assert review_tx["needs_review"] is True

    # User re-categorizes it to Business Meals
    update_res = client.post(
        "/api/review-transaction",
        json={
            "payload": {
                "transaction_id": review_tx["id"],
                "new_category": CATEGORY_MEALS,
            },
            "transactions": txs,
        },
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    updated_tx = next(t for t in updated_data["transactions"] if t["id"] == review_tx["id"])
    assert updated_tx["category"] == CATEGORY_MEALS
    assert updated_tx["needs_review"] is False
    assert updated_tx["manually_edited"] is True
