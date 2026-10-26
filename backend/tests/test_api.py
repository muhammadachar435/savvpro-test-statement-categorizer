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


# ===========================================================================
# Financial Summary Regression Tests (Net Refund Offsets & Unknown Credits)
# ===========================================================================
def test_financial_summary_regression_net_refund_and_unknown_credit():
    """Verify exact accounting:
    - Software expense: $100.00
    - Confirmed software refund: $20.00
    - Expected net software expense: $80.00
    - Expected income from these: $0.00
    - Expected transfer spending: $0.00
    - Unknown $500 incoming credit: remains Needs Review, does NOT count as income or expense.
    """
    csv_content = (
        "Date,Description,Amount\n"
        "2026-03-01,ADOBE *CREATIVE CLOUD,-100.00\n"
        "2026-03-05,ADOBE *REFUND PRO-RATA,20.00\n"
        "2026-03-10,ONLINE TRANSFER TO SAVINGS,-250.00\n"
        "2026-03-15,MISCELLANEOUS UNKNOWN DEPOSIT REF#9982,500.00\n"
    )
    response = client.post(
        "/api/upload-statement",
        files={"file": ("accounting_test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    summary = data["summary"]

    # 1. Total income must be 0 (the $500 unknown deposit must NOT count as income)
    assert summary["total_income"] == "0.00" or summary["total_income"] == 0.0 or str(summary["total_income"]) == "0.00"

    # 2. Net expenses must be $80.00 ($100 Software - $20 Software Refund)
    assert str(summary["total_expenses"]) == "80.00"

    # 3. Total refunds must be $20.00
    assert str(summary["total_refunds"]) == "20.00"

    # 4. Total transfers must be $250.00
    assert str(summary["total_transfers"]) == "250.00"

    # 5. Total needs review count must be 1 (for the unknown $500 deposit)
    assert summary["total_needs_review_count"] == 1

    # 6. Check category breakdown for Software
    sw_cat = next(c for c in summary["category_breakdown"] if c["category"] == CATEGORY_SOFTWARE)
    assert str(sw_cat["total_amount"]) == "80.00"
    assert str(sw_cat["deductible_estimate"]) == "80.00"

    # 7. Check category breakdown for Needs Review
    nr_cat = next(c for c in summary["category_breakdown"] if c["category"] == CATEGORY_NEEDS_REVIEW)
    assert str(nr_cat["total_amount"]) == "500.00"
    assert str(nr_cat["deductible_estimate"]) == "0.00"


# ===========================================================================
# CSV Formula Injection Defense Test (CWE-1236 / OWASP)
# ===========================================================================
def test_export_csv_formula_injection_defense():
    """Verify that formula triggers (=, +, -, @), including those preceded by whitespace
    or control characters (tabs, newlines, CRs), are neutralized with a leading single quote,
    while harmless descriptions remain untouched and in-memory payloads are not mutated.
    """
    test_cases = [
        ("=SUM(A1:A10)", True),
        ("+123", True),
        ("-cmd", True),
        ("@MACRO", True),
        (" =SUM(A1:A10)", True),
        ("  @SUM(A1:A2)", True),
        ("\t=1+1", True),
        ("\r=1+1", True),
        ("\n=1+1", True),
        ("   +cmd", True),
        ("Ordinary bank transaction", False),
        ("GITHUB AUTOMATIC PAYMENT", False),
    ]

    tx_payload = []
    for idx, (desc, _is_dangerous) in enumerate(test_cases, start=1):
        tx_payload.append({
            "row_number": idx,
            "id": f"tx_{idx}",
            "date": "2026-03-01",
            "description": desc,
            "amount": "-50.00",
            "currency": "USD",
            "type": "debit",
            "category": "Office Supplies & Equipment",
            "is_refund": False,
            "is_transfer": False,
            "confidence": 0.9,
            "reason": f"Reason for {desc}",
            "needs_review": False,
            "manually_edited": False,
        })

    export_res = client.post(
        "/api/export-statement",
        json={"transactions": tx_payload, "filename": "safe_export.csv"},
    )
    assert export_res.status_code == 200
    csv_text = export_res.text

    for idx, (desc, is_dangerous) in enumerate(test_cases):
        # 1. In-memory description must NOT be modified
        assert tx_payload[idx]["description"] == desc

        if is_dangerous:
            # Dangerous values must be prefixed with a single quote in exported CSV
            expected_in_csv = f"'{desc}"
            assert expected_in_csv in csv_text, f"Failed to escape dangerous cell: {desc!r}"
        else:
            # Harmless descriptions must NOT have a leading quote added
            assert f"'{desc}" not in csv_text, f"Harmless cell was erroneously quoted: {desc!r}"
            assert desc in csv_text, f"Harmless cell missing from CSV: {desc!r}"


# ===========================================================================
# Upload Streaming Limits and Header-Only Rejection
# ===========================================================================
def test_upload_header_only_file_rejected():
    """Header-only statement with zero transactions returns HTTP 400."""
    csv_content = b"Date,Description,Amount\n"
    response = client.post(
        "/api/upload-statement",
        files={"file": ("headers_only.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert response.status_code == 400
    assert "Unable to process statement" in response.json()["detail"]


def test_upload_streaming_size_limit_rejected():
    """Uploading a file exceeding MAX_UPLOAD_SIZE_BYTES is rejected with 413."""
    # Create a dummy large stream > 5MB (250_000 lines * 23 bytes = ~5.75 MB)
    large_payload = b"Date,Description,Amount\n" + b"2026-03-01,TEST,-10.00\n" * 250_000
    assert len(large_payload) > 5 * 1024 * 1024

    response = client.post(
        "/api/upload-statement",
        files={"file": ("too_large.csv", io.BytesIO(large_payload), "text/csv")},
    )
    assert response.status_code == 413
    assert "exceeds maximum upload size" in response.json()["detail"]
