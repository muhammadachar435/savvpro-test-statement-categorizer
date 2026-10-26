"""API route endpoints for statement upload, sample loading, review resolution, and export."""
import csv
import io
import os
import re
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from app.core.config import (
    ALL_CATEGORIES,
    CATEGORY_INCOME,
    CATEGORY_NEEDS_REVIEW,
    CATEGORY_TRANSFER,
    MAX_UPLOAD_SIZE_BYTES,
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
    """Compute financial and tax summary totals from categorized transactions using Decimal.

    Accounting Model:
    1. total_income: Sum of all transactions explicitly categorized as CATEGORY_INCOME.
       - Unknown or ambiguous credits (Needs Review) do NOT increase income.
    2. total_refunds: Sum of all confirmed refunds (is_refund=True).
    3. total_transfers: Sum of all inter-account balance movements (is_transfer=True).
       - Transfers are non-deductible balance adjustments, not spending or income.
    4. total_expenses: Net operating expenses across confirmed business categories
       (Software, Hosting, Equipment, Travel, Business Meals).
       - For each expense category: net_expense = max(gross_debit_expenses - refunds, 0).
       - Total net expenses = sum of category net expenses.
       - Unreviewed transactions (Needs Review) do NOT count as deductible expenses until verified.
    5. deductible_estimate: Calculated per category as net_expense * deductible_percentage.
       - Business Meals are 50% deductible; standard tech expenses are 100% deductible.
       - Needs Review, Transfers, and Income have 0% deductible estimates.
    """
    total_income = Decimal("0.00")
    total_refunds = Decimal("0.00")
    total_transfers = Decimal("0.00")
    needs_review_count = 0

    gross_debits: Dict[str, Decimal] = {cat: Decimal("0.00") for cat in ALL_CATEGORIES}
    refund_offsets: Dict[str, Decimal] = {cat: Decimal("0.00") for cat in ALL_CATEGORIES}
    category_counts: Dict[str, int] = {cat: 0 for cat in ALL_CATEGORIES}

    for tx in transactions:
        amt = abs(tx.amount)
        cat = tx.category

        if cat not in gross_debits:
            gross_debits[cat] = Decimal("0.00")
            refund_offsets[cat] = Decimal("0.00")
            category_counts[cat] = 0

        category_counts[cat] += 1

        if tx.needs_review:
            needs_review_count += 1

        if tx.is_transfer:
            total_transfers += amt
        elif tx.is_refund:
            total_refunds += amt
            refund_offsets[cat] += amt
        elif cat == CATEGORY_INCOME:
            total_income += amt
        elif cat == CATEGORY_NEEDS_REVIEW:
            # Pending review item: track in Needs Review bucket, but do not classify as operating expense
            gross_debits[cat] += amt
        else:
            # Confirmed business expense debit
            gross_debits[cat] += amt

    breakdown: List[CategorySummary] = []
    total_net_expenses = Decimal("0.00")

    for cat in ALL_CATEGORIES:
        count = category_counts.get(cat, 0)
        rule = TAX_RULES.get(cat, {"deductible": "0%", "type": "expense"})
        cat_type = rule["type"]
        pct_str = rule["deductible"]
        pct_dec = Decimal(pct_str.replace("%", "")) / Decimal("100")

        if cat_type == "expense":
            # Net expense = gross expense minus refund offsets for this category
            gross = gross_debits.get(cat, Decimal("0.00"))
            ref = refund_offsets.get(cat, Decimal("0.00"))
            net_amt = max(gross - ref, Decimal("0.00"))
            total_net_expenses += net_amt
            deductible_est = (net_amt * pct_dec).quantize(Decimal("0.01"))
            cat_total = net_amt.quantize(Decimal("0.01"))
        elif cat == CATEGORY_INCOME:
            cat_total = total_income.quantize(Decimal("0.01"))
            deductible_est = Decimal("0.00")
        elif cat == CATEGORY_TRANSFER:
            cat_total = total_transfers.quantize(Decimal("0.01"))
            deductible_est = Decimal("0.00")
        elif cat == CATEGORY_NEEDS_REVIEW:
            # Total unclassified amounts pending review (0% tax deduction until classified)
            unreviewed_amt = gross_debits.get(cat, Decimal("0.00")) + refund_offsets.get(cat, Decimal("0.00"))
            cat_total = unreviewed_amt.quantize(Decimal("0.01"))
            deductible_est = Decimal("0.00")
        else:
            cat_total = Decimal("0.00")
            deductible_est = Decimal("0.00")

        breakdown.append(
            CategorySummary(
                category=cat,
                total_amount=cat_total,
                count=count,
                deductible_percentage=pct_str,
                deductible_estimate=deductible_est,
            )
        )

    return StatementSummary(
        total_income=total_income.quantize(Decimal("0.01")),
        total_expenses=total_net_expenses.quantize(Decimal("0.01")),
        total_refunds=total_refunds.quantize(Decimal("0.01")),
        total_transfers=total_transfers.quantize(Decimal("0.01")),
        total_needs_review_count=needs_review_count,
        category_breakdown=breakdown,
    )


FORMULA_TRIGGERS = ("=", "+", "-", "@")
CONTROL_CHARS = ("\t", "\r", "\n")


def sanitize_csv_cell(val: str) -> str:
    """Neutralize spreadsheet formula injection (CWE-1236 / OWASP) for CSV export.

    If text begins with, or after stripping leading whitespace/control characters begins
    with formula triggers ('=', '+', '-', '@'), or starts with control characters
    ('\\t', '\\r', '\\n'), prefixes with a single quote (') so spreadsheet applications
    (Excel, Google Sheets, LibreOffice Calc) treat it as literal text rather than an
    executable formula.

    Original in-memory Python models are NOT modified.

    Limitations:
    - Relies on standard spreadsheet convention of treating leading single-quote as text escape.
    - If a user opens the CSV in raw text editors or non-spreadsheet tools, the leading single-quote is visible.
    """
    if not val:
        return ""
    stripped = val.lstrip()
    if (stripped and stripped.startswith(FORMULA_TRIGGERS)) or val.startswith(CONTROL_CHARS):
        return f"'{val}"
    return val


def generate_statement_csv(transactions: List[CategorizedTransaction]) -> str:
    """Generate standardized RFC 4180 CSV content from categorized transactions with formula safety."""
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
            sanitize_csv_cell(tx.description),
            str(tx.amount),
            tx.currency,
            tx.type,
            sanitize_csv_cell(tx.category),
            "Yes" if tx.is_refund else "No",
            "Yes" if tx.is_transfer else "No",
            f"{tx.confidence:.2f}",
            "Yes" if tx.needs_review else "No",
            "Yes" if tx.manually_edited else "No",
            sanitize_csv_cell(tx.reason),
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
    """Upload and process a statement CSV via the parser and deterministic brain.

    Enforces the configured file size limit (5 MB) during stream reading to protect memory.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are currently supported.")

    CHUNK_SIZE = 64 * 1024  # 64 KB
    total_bytes = 0
    chunks = []

    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum upload size of {MAX_UPLOAD_SIZE_BYTES} bytes (5 MB).",
            )
        chunks.append(chunk)

    raw_bytes = b"".join(chunks)

    result = parse_csv_statement(raw_bytes, filename=file.filename)
    if not result.is_acceptable or not result.transactions:
        err_details = (
            "; ".join([e.message for e in result.errors])
            if result.errors
            else "No transaction rows found in statement."
        )
        raise HTTPException(status_code=400, detail=f"Unable to process statement: {err_details}")

    categorized = categorize_statement(result.transactions)
    summary = build_summary(categorized)

    return StatementResponse(
        filename=file.filename,
        total_rows=len(categorized),
        transactions=categorized,
        summary=summary,
        errors=result.errors,
    )


@router.get("/sample-statement", response_model=StatementResponse)
def load_sample_statement():
    """Load the built-in synthetic statement for 1-click live demo."""
    sample_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "sample_statement.csv",
    )
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Synthetic sample dataset file not found.")

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
        errors=result.errors,
    )


@router.post("/review-transaction")
def update_transaction_category(payload: ReviewUpdateRequest, transactions: List[CategorizedTransaction]):
    """Update a specific transaction category and recompute statement summaries.

    Stateless Behavior:
    This endpoint is stateless. It applies the category change to the submitted
    in-memory transactions, recalculates all summary totals, and returns the updated
    data to the frontend. No persistent database state is altered.
    """
    if payload.new_category not in ALL_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{payload.new_category}'. Allowed categories: {ALL_CATEGORIES}",
        )

    updated = False
    for tx in transactions:
        if tx.id == payload.transaction_id:
            tx.category = payload.new_category
            tx.needs_review = False
            tx.manually_edited = True
            tx.confidence = 1.0
            tx.reason = f"Manually verified and updated by user to {payload.new_category}"
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail=f"Transaction with ID '{payload.transaction_id}' not found.")

    new_summary = build_summary(transactions)
    return {
        "status": "success",
        "transactions": transactions,
        "summary": new_summary,
    }


@router.post("/export-statement")
def export_statement(request: ExportStatementRequest):
    """Export current categorized transactions to standard CSV for tax preparation."""
    if not request.transactions:
        raise HTTPException(status_code=400, detail="No transactions provided to export.")

    csv_data = generate_statement_csv(request.transactions)

    # Sanitize attachment filename against path traversal
    base_name = os.path.basename(request.filename or "categorized_statement.csv")
    fname = base_name if base_name.endswith(".csv") else f"{base_name}.csv"

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
