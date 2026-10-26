"""Pydantic models for transactions, parsing results, and validation errors.

Monetary Convention:
All monetary values are represented as Python `Decimal` instances to prevent binary
floating-point precision loss.

Signed Amount Convention:
- Negative (< 0): Money leaving the account (Debits, Expenses, Outflows, Fees, Card Payments).
- Positive (> 0): Money entering the account (Credits, Deposits, Inflows, Revenue, Refunds).
- Zero (= 0): Zero-balance adjustments (Trial authorizations, zero-fee balance checks).

Source preservation:
Original descriptions and row numbers are strictly preserved for audit trails,
user review, and transparent error reporting. No categorization decisions are made
within these models.
"""
import datetime
from decimal import Decimal
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ParseError(BaseModel):
    """Represents a row-level or file-level parsing/validation failure.
    
    Attributes:
        row_number: 1-indexed line number in the source CSV (0 indicates a file or header error).
        message: Descriptive explanation of why the row or file could not be parsed.
        raw_line: Optional raw content of the source line for debugging.
        column: Optional column name that triggered the validation error.
    """
    row_number: int = Field(ge=0, description="1-indexed row number from CSV; 0 for file-level issues")
    message: str = Field(..., min_length=1, description="Descriptive error explanation")
    raw_line: Optional[str] = Field(default=None, description="Raw source line content")
    column: Optional[str] = Field(default=None, description="Column name that triggered failure")


class ParsedTransaction(BaseModel):
    """Normalized transaction record parsed from statement source data.
    
    Attributes:
        row_number: 1-indexed line number where the record originated in the CSV file.
        date: Verified calendar date when available (ISO date).
        description: Preserved exact merchant/description string from the source.
        amount: Signed Decimal amount (negative = money out, positive = money in).
        currency: 3-letter ISO currency code (defaults to USD).
        debit: Explicit debit amount if source provided separate debit column.
        credit: Explicit credit amount if source provided separate credit column.
        transaction_id: Source reference or transaction ID if provided in file.
        id: Unique internal identifier for tracking and frontend keys (e.g. 'tx_2_1').
        type: Convenient string tag ('debit' or 'credit') derived from amount sign.
    """
    row_number: int = Field(default=1, ge=1, description="1-indexed source row number")
    date: Optional[datetime.date] = Field(default=None, description="Transaction effective/posting date")
    description: str = Field(..., min_length=1, description="Original transaction narrative/merchant")
    amount: Decimal = Field(..., description="Signed transaction amount; negative = out, positive = in")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO currency code")
    debit: Optional[Decimal] = Field(default=None, description="Raw debit if separate column existed")
    credit: Optional[Decimal] = Field(default=None, description="Raw credit if separate column existed")
    transaction_id: Optional[str] = Field(default=None, description="External transaction reference ID")
    id: str = Field(..., description="Unique internal identifier")
    type: str = Field(..., description="'debit' (money leaving) or 'credit' (money entering)")

    @field_validator("date", mode="before")
    @classmethod
    def coerce_date(cls, v: Union[datetime.date, str, None]) -> Optional[datetime.date]:
        """Convert date strings (ISO or common formats) to datetime.date."""
        if v is None or v == "":
            return None
        if isinstance(v, datetime.date):
            return v
        if isinstance(v, str):
            cleaned = v.strip()
            for fmt in (
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%m/%d/%Y",
                "%m-%d-%Y",
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%Y%m%d",
                "%b %d, %Y",
                "%B %d, %Y",
            ):
                try:
                    return datetime.datetime.strptime(cleaned, fmt).date()
                except ValueError:
                    continue
            try:
                return datetime.date.fromisoformat(cleaned)
            except ValueError:
                raise ValueError(f"Unable to parse date string: {v!r}")
        return v

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount_to_decimal(cls, v: Union[Decimal, float, int, str]) -> Decimal:
        """Coerce float/int/str input to Decimal without binary floating-point corruption."""
        if isinstance(v, float):
            return Decimal(str(v))
        if isinstance(v, (int, str)):
            return Decimal(str(v))
        return v

    @field_validator("amount", mode="after")
    @classmethod
    def validate_amount_finite(cls, v: Decimal) -> Decimal:
        """Reject non-finite amounts such as NaN and Infinity."""
        if not v.is_finite():
            raise ValueError("Amount must be a finite decimal number (NaN and Infinity are rejected)")
        return v


class ParsedStatementResult(BaseModel):
    """Complete result object returned by the statement parser.
    
    Attributes:
        filename: Name of the parsed file if provided.
        transactions: List of successfully parsed and validated transactions.
        errors: List of parsing and validation errors encountered.
        total_rows_processed: Total number of evaluated data rows.
        is_acceptable: True if file structure is valid and contains processable data.
    """
    filename: Optional[str] = Field(default=None, description="Original file name")
    transactions: List[ParsedTransaction] = Field(default_factory=list, description="Parsed valid transactions")
    errors: List[ParseError] = Field(default_factory=list, description="Validation and parse errors")
    total_rows_processed: int = Field(default=0, ge=0, description="Total data rows evaluated")
    is_acceptable: bool = Field(default=False, description="Whether upload is acceptable for processing")

    def __iter__(self):
        """Allow tuple unpacking: transactions, errors = parse_csv_statement(...)"""
        return iter((self.transactions, self.errors))


# Backward compatibility alias for existing code
Transaction = ParsedTransaction


# ---------------------------------------------------------------------------
# Forward models for Module 3 (Categorization Brain) and Module 4 (API Routes)
# ---------------------------------------------------------------------------

class CategorizedTransaction(ParsedTransaction):
    """Transaction enriched by the Module 3 Categorization Brain."""
    category: str
    is_refund: bool = False
    is_transfer: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    needs_review: bool = False
    manually_edited: bool = False


class CategorySummary(BaseModel):
    """Aggregated tax category totals using exact Decimal amounts."""
    category: str
    total_amount: Decimal
    count: int
    deductible_percentage: str
    deductible_estimate: Decimal


class StatementSummary(BaseModel):
    """High-level summary of financial totals and review counts using exact Decimal amounts."""
    total_income: Decimal
    total_expenses: Decimal
    total_refunds: Decimal
    total_transfers: Decimal
    total_needs_review_count: int
    category_breakdown: List[CategorySummary]


class StatementResponse(BaseModel):
    """API response envelope for statement processing."""
    filename: str
    total_rows: int
    transactions: List[CategorizedTransaction]
    summary: StatementSummary
    errors: List[ParseError] = Field(default_factory=list, description="Row-level parsing errors encountered")


class ReviewUpdateRequest(BaseModel):
    """Payload for manual review category update."""
    transaction_id: str
    new_category: str
