"""Integration tests for FastAPI endpoints."""
import io
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import CATEGORY_MEALS, CATEGORY_NEEDS_REVIEW, CATEGORY_SOFTWARE

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
    assert "tax_rules" in data


def test_load_sample_statement():
    response = client.get("/api/sample-statement")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "sample_statement.csv"
    assert data["total_rows"] > 0
    assert len(data["transactions"]) == data["total_rows"]
    assert data["summary"]["total_needs_review_count"] > 0
    assert "total_income" in data["summary"]
    assert "total_expenses" in data["summary"]


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


def test_review_transaction_invalid_category():
    res = client.get("/api/sample-statement")
    txs = res.json()["transactions"]
    update_res = client.post(
        "/api/review-transaction",
        json={
            "payload": {
                "transaction_id": txs[0]["id"],
                "new_category": "NON_EXISTENT_CATEGORY_XYZ",
            },
            "transactions": txs,
        },
    )
    assert update_res.status_code == 400
    assert "Invalid category" in update_res.json()["detail"]


def test_upload_valid_csv():
    csv_bytes = b"Date,Description,Amount\n2026-03-01,ADOBE *CREATIVE CLOUD,-54.99\n2026-03-02,STRIPE PAYOUT,1500.00\n"
    response = client.post(
        "/api/upload-statement",
        files={"file": ("test_upload.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_upload.csv"
    assert data["total_rows"] == 2
    assert len(data["transactions"]) == 2
    assert data["transactions"][0]["category"] == CATEGORY_SOFTWARE


def test_upload_non_csv_rejected():
    response = client.post(
        "/api/upload-statement",
        files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4..."), "application/pdf")},
    )
    assert response.status_code == 400
    assert "Only CSV files are currently supported" in response.json()["detail"]


def test_upload_empty_csv_rejected():
    response = client.post(
        "/api/upload-statement",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert response.status_code == 400
    assert "Unable to process statement" in response.json()["detail"]


def test_export_statement_csv():
    res = client.get("/api/sample-statement")
    txs = res.json()["transactions"]

    export_res = client.post(
        "/api/export-statement",
        json={"transactions": txs, "filename": "tax_2026.csv"},
    )
    assert export_res.status_code == 200
    assert export_res.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="tax_2026.csv"' in export_res.headers["content-disposition"]
    body = export_res.text
    assert "Row Number,Date,Description,Amount,Currency,Type,Category" in body
    assert "ADOBE" in body


def test_export_statement_empty_fails():
    export_res = client.post(
        "/api/export-statement",
        json={"transactions": [], "filename": "empty.csv"},
    )
    assert export_res.status_code == 400


def test_export_sample_statement():
    export_res = client.get("/api/export-sample")
    assert export_res.status_code == 200
    assert export_res.headers["content-type"].startswith("text/csv")
    assert 'filename="categorized_sample_statement.csv"' in export_res.headers["content-disposition"]
    assert "Row Number,Date,Description,Amount" in export_res.text
