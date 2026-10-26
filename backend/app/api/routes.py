"""API route endpoints for statement upload, sample loading, and review resolution."""
import os
from typing import List, Dict
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.config import (
    ALL_CATEGORIES,
    TAX_RULES,
    CATEGORY_INCOME,
    CATEGORY_TRANSFER,
    CATEGORY_NEEDS_REVIEW,
)
from app.core.models import (
    CategorizedTransaction,
    CategorySummary,
    StatementSummary,
    StatementResponse,
    ReviewUpdateRequest,
)
from app.parser.csv_parser import parse_csv_statement
from app.brain.engine import categorize_transaction

router = APIRouter(prefix="/api", tags=["statements"])


def build_summary(transactions: List[CategorizedTransaction]) -> StatementSummary:
    """Compute financial and tax summary totals from categorized transactions using Decimal."""
    from decimal import Decimal
    total_income = Decimal("0.00")
    total_expenses = Decimal("0.00")
    total_refunds = Decimal("0.00")
    total_transfers = Decimal("0.00")
    needs_review_count = 0

    cat_totals: Dict[str, Decimal] = {cat: Decimal("0.00") for cat in ALL_CATEGORIES}
    cat_counts: Dict[str, int] = {cat: 0 for cat in ALL_CATEGORIES}

    for tx in transactions:
        tx_amt = abs(tx.amount)
        cat_totals[tx.category] = cat_totals.get(tx.category, Decimal("0.00")) + tx_amt
        cat_counts[tx.category] = cat_counts.get(tx.category, 0) + 1

        if tx.needs_review:
            needs_review_count += 1

        if tx.is_transfer:
            total_transfers += tx_amt
        elif tx.is_refund:
            total_refunds += tx_amt
        elif tx.category == CATEGORY_INCOME or tx.type == "credit":
            total_income += tx_amt
        else:
            total_expenses += tx_amt

    breakdown: List[CategorySummary] = []
    for cat in ALL_CATEGORIES:
        count = cat_counts.get(cat, 0)
        tot = round(cat_totals.get(cat, Decimal("0.00")), 2)
        rule = TAX_RULES.get(cat, {"deductible": "0%", "type": "expense"})
        pct_str = rule["deductible"]
        pct_dec = Decimal(pct_str.replace("%", "")) / Decimal("100")
        deductible_est = round(tot * pct_dec, 2) if rule["type"] == "expense" else Decimal("0.00")

        breakdown.append(
            CategorySummary(
                category=cat,
                total_amount=tot,
                count=count,
                deductible_percentage=pct_str,
                deductible_estimate=deductible_est,
            )
        )

    return StatementSummary(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        total_refunds=round(total_refunds, 2),
        total_transfers=round(total_transfers, 2),
        total_needs_review_count=needs_review_count,
        category_breakdown=breakdown,
    )


@router.get("/categories")
def get_categories():
    """Retrieve all standard categories and tax rules."""
    return {
        "categories": ALL_CATEGORIES,
        "tax_rules": TAX_RULES,
    }


@router.post("/upload-statement", response_model=StatementResponse)
async def upload_statement(file: UploadFile = File(...)):
    """Upload and process a statement CSV."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are currently supported.")

    raw_bytes = await file.read()
    content = raw_bytes.decode("utf-8", errors="replace")

    raw_transactions, parse_errors = parse_csv_statement(content)
    if not raw_transactions:
        raise HTTPException(status_code=400, detail="No valid transactions could be parsed from the file.")

    categorized = [categorize_transaction(t) for t in raw_transactions]
    summary = build_summary(categorized)

    return StatementResponse(
        filename=file.filename,
        total_rows=len(categorized),
        transactions=categorized,
        summary=summary,
    )


@router.get("/sample-statement", response_model=StatementResponse)
def load_sample_statement():
    """Load and process the pre-configured synthetic sample statement."""
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_statement.csv")
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample statement file not found.")

    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()

    raw_transactions, _ = parse_csv_statement(content)
    categorized = [categorize_transaction(t) for t in raw_transactions]
    summary = build_summary(categorized)

    return StatementResponse(
        filename="sample_statement.csv",
        total_rows=len(categorized),
        transactions=categorized,
        summary=summary,
    )


@router.post("/review-transaction")
def update_transaction_category(payload: ReviewUpdateRequest, transactions: List[CategorizedTransaction]):
    """Update a specific transaction category and recompute statement summaries."""
    updated = False
    for tx in transactions:
        if tx.id == payload.transaction_id:
            tx.category = payload.new_category
            tx.needs_review = payload.new_category == CATEGORY_NEEDS_REVIEW
            tx.manually_edited = True
            tx.confidence = 1.0
            tx.reason = f"Manually verified and updated by user to '{payload.new_category}'"
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Transaction ID not found.")

    new_summary = build_summary(transactions)
    return {
        "transactions": transactions,
        "summary": new_summary,
    }
