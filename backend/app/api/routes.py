"""API route endpoints for statement upload, sample loading, review resolution, and export."""
import csv
import io
import os
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from app.core.config import (
    ALL_CATEGORIES,
    CATEGORY_INCOME,
    CATEGORY_NEEDS_REVIEW,
    TAX_RULES,
)
from app.core.models import (
    CategorizedTransaction,
    CategorySummary,
    ReviewUpdateRequest,
    StatementResponse,
    StatementSummary,
)
from app.parser.csv_parser import parse_csv_statement
from app.brain.engine import categorize_statement, categorize_transaction

router = APIRouter(prefix="/api", tags=["statements"])


class ExportStatementRequest(BaseModel):
    """Payload for CSV statement export."""
    transactions: List[CategorizedTransaction]
    filename: Optional[str] = "categorized_statement.csv"


def build_summary(transactions: List[CategorizedTransaction]) -> StatementSummary:
    """Compute financial and tax summary totals from categorized transactions using Decimal."""
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


def generate_statement_csv(transactions: List[CategorizedTransaction]) -> str:
    """Generate standardized RFC 4180 CSV content from categorized transactions."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "Row Number",
        "Date",
        "Description",
        "Amount",
        "Currency",
        "Type",
        "Category",
        "Is Refund",
        "Is Transfer",
        "Confidence",
        "Needs Review",
        "Manually Edited",
        "Reason",
    ])
    for tx in transactions:
        writer.writerow([
            tx.row_number,
            tx.date.isoformat() if tx.date else "",
            tx.description,
            str(tx.amount),
            tx.currency,
            tx.type,
            tx.category,
            "Yes" if tx.is_refund else "No",
            "Yes" if tx.is_transfer else "No",
            f"{tx.confidence:.2f}",
            "Yes" if tx.needs_review else "No",
            "Yes" if tx.manually_edited else "No",
            tx.reason,
        ])
    return output.getvalue()


@router.get("/categories")
def get_categories():
    """Retrieve all standard categories and tax rules for the Freelance persona."""
    return {
        "categories": ALL_CATEGORIES,
        "tax_rules": TAX_RULES,
    }


@router.post("/upload-statement", response_model=StatementResponse)
async def upload_statement(file: UploadFile = File(...)):
    """Upload and process a statement CSV via the parser and deterministic brain."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are currently supported.")

    raw_bytes = await file.read()
    result = parse_csv_statement(raw_bytes, filename=file.filename)
    if not result.is_acceptable or not result.transactions:
        err_details = (
            "; ".join([e.message for e in result.errors])
            if result.errors
            else "No valid transactions could be parsed from the file."
        )
        raise HTTPException(status_code=400, detail=f"Unable to process statement: {err_details}")

    categorized = categorize_statement(result.transactions)
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

    result = parse_csv_statement(content, filename="sample_statement.csv")
    if not result.is_acceptable or not result.transactions:
        raise HTTPException(status_code=500, detail="Failed to parse synthetic sample dataset.")

    categorized = categorize_statement(result.transactions)
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
    if payload.new_category not in ALL_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{payload.new_category}'. Allowed categories: {ALL_CATEGORIES}",
        )

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


@router.post("/export-statement")
def export_statement(request: ExportStatementRequest):
    """Export current categorized transactions to standard CSV for tax preparation."""
    if not request.transactions:
        raise HTTPException(status_code=400, detail="No transactions provided to export.")

    csv_data = generate_statement_csv(request.transactions)
    fname = request.filename if request.filename.endswith(".csv") else f"{request.filename}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/export-sample")
def export_sample_statement():
    """Export the processed synthetic sample statement as a downloadable CSV."""
    sample_response = load_sample_statement()
    csv_data = generate_statement_csv(sample_response.transactions)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="categorized_sample_statement.csv"'},
    )
