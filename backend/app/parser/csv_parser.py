"""Robust CSV statement parser for bank and credit card files.

Responsibilities:
- Reads CSV files from strings, bytes, or file-like streams.
- Handles UTF-8 with BOM, standard UTF-8, and Latin-1 encodings.
- Normalizes and validates header columns, rejecting missing or ambiguous columns.
- Preserves exact source descriptions and tracks 1-indexed row numbers.
- Normalizes monetary amounts into Python Decimals using a documented signed convention:
    * Negative (< 0): Outflow / Debit / Expense / Withdrawal.
    * Positive (> 0): Inflow / Credit / Revenue / Refund / Deposit.
- Never silently guesses ambiguous debit/credit semantics or drops malformed rows.
- Returns a structured ParsedStatementResult object containing valid transactions and row errors.
"""
import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import BinaryIO, Dict, List, Optional, Set, TextIO, Tuple, Union

from app.core.config import (
    ACCEPTED_ENCODINGS,
    DEFAULT_CURRENCY,
    MAX_TRANSACTION_ROWS,
    MAX_UPLOAD_SIZE_BYTES,
    SUPPORTED_DATE_FORMATS,
)
from app.core.models import (
    ParsedStatementResult,
    ParsedTransaction,
    ParseError,
)

# Recognized header aliases for standard columns (case-insensitive, whitespace-trimmed)
COLUMN_ALIASES: Dict[str, Set[str]] = {
    "date": {
        "date",
        "transaction date",
        "posted date",
        "trans date",
        "posting date",
        "date posted",
        "time",
    },
    "description": {
        "description",
        "transaction description",
        "merchant",
        "details",
        "payee",
        "name",
        "memo",
        "narrative",
    },
    "amount": {
        "amount",
        "transaction amount",
        "total",
        "net",
        "value",
    },
    "debit": {
        "debit",
        "withdrawal",
        "spent",
        "money out",
        "dr",
        "debit amount",
    },
    "credit": {
        "credit",
        "deposit",
        "received",
        "money in",
        "cr",
        "credit amount",
    },
    "type": {
        "type",
        "transaction type",
        "dr/cr",
        "entry type",
    },
    "currency": {
        "currency",
        "curr",
        "currency code",
    },
    "transaction_id": {
        "transaction id",
        "trans id",
        "ref",
        "reference",
        "id",
        "reference number",
    },
}


def clean_amount_string(val_str: str) -> Decimal:
    """Parse a monetary amount string into a Decimal.
    
    Handles:
    - Currency symbols ($ £ € ¥)
    - Comma separators (1,234.56)
    - Accounting parentheses for negative numbers: (54.99) -> -54.99
    - Explicit signs: -54.99, +100.00
    - Whitespace trimming
    
    Raises:
        ValueError: If the string is empty, malformed, or non-finite (NaN, Infinity).
    """
    if not val_str or not val_str.strip():
        raise ValueError("Amount string is empty")

    raw = val_str.strip()
    raw_lower = raw.lower()

    # Reject non-finite values explicitly
    if any(k in raw_lower for k in ["nan", "inf", "infinity"]):
        raise ValueError(f"Non-finite amount not permitted: '{val_str}'")

    # Reject invalid multiple or contradictory signs
    if raw.count("-") > 1 or raw.count("+") > 1 or "+-" in raw or "-+" in raw:
        raise ValueError(f"Invalid monetary format: '{val_str}'")

    # Detect accounting parentheses: (12.34) or ($12.34)
    is_parenthesized = False
    if raw.startswith("(") and raw.endswith(")"):
        is_parenthesized = True
        raw = raw[1:-1].strip()

    # Detect negative signs before or after currency symbols: -$10.00 or $-10.00
    is_explicit_negative = False
    if raw.startswith("-"):
        is_explicit_negative = True
        raw = raw[1:].strip()

    # Remove currency symbols and comma grouping
    cleaned = re.sub(r"[\$€£¥,]", "", raw).strip()

    if not cleaned:
        raise ValueError(f"No numeric digits found in amount: '{val_str}'")

    try:
        dec = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"Invalid monetary format: '{val_str}'")

    if not dec.is_finite():
        raise ValueError(f"Non-finite amount not permitted: '{val_str}'")

    if is_parenthesized or is_explicit_negative:
        dec = -abs(dec)

    return dec


def clean_amount(val_str: str) -> float:
    """Legacy helper for backward compatibility with earlier float-based tests."""
    try:
        return float(abs(clean_amount_string(val_str)))
    except Exception:
        return 0.0


def parse_date_string(date_str: str) -> date:
    """Parse calendar date string against explicitly supported formats.
    
    Raises:
        ValueError: If date does not match any recognized format or contains invalid calendar dates.
    """
    cleaned = date_str.strip()
    if not cleaned:
        raise ValueError("Date string is empty")

    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Date '{cleaned}' does not match any supported format")


def _decode_content(content: Union[str, bytes, TextIO, BinaryIO]) -> str:
    """Decode raw input content into a normalized unicode string."""
    if hasattr(content, "read"):
        raw = content.read()
    else:
        raw = content

    if isinstance(raw, bytes):
        if len(raw) > MAX_UPLOAD_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum allowed limit of {MAX_UPLOAD_SIZE_BYTES} bytes")
        for encoding in ACCEPTED_ENCODINGS:
            try:
                decoded = raw.decode(encoding)
                return decoded.lstrip("\ufeff")
            except (UnicodeDecodeError, LookupError):
                continue
        raise ValueError("Unable to decode file using supported encodings (UTF-8, UTF-8 BOM, Latin-1)")

    if isinstance(raw, str):
        if len(raw.encode("utf-8", errors="ignore")) > MAX_UPLOAD_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum allowed limit of {MAX_UPLOAD_SIZE_BYTES} bytes")
        return raw.lstrip("\ufeff")

    raise TypeError(f"Unsupported content type: {type(content)}")


def _resolve_headers(header_row: List[str]) -> Tuple[Dict[str, int], List[str]]:
    """Map normalized header columns to standardized roles and detect ambiguities.
    
    Returns:
        Tuple of (column_mapping, error_messages)
    """
    col_map: Dict[str, int] = {}
    errors: List[str] = []

    matched_roles: Dict[str, List[str]] = {role: [] for role in COLUMN_ALIASES}

    for idx, col in enumerate(header_row):
        norm = col.strip().lower()
        if not norm:
            continue

        for role, aliases in COLUMN_ALIASES.items():
            if norm in aliases:
                matched_roles[role].append(col.strip())
                col_map[role] = idx
                break

    # 1. Check for duplicate/ambiguous recognized columns for the same role
    for role, occurrences in matched_roles.items():
        if len(occurrences) > 1:
            errors.append(f"Ambiguous columns: multiple '{role}' columns recognized ({occurrences})")

    # 2. Check for conflict between Amount and separate Debit/Credit
    has_amount = len(matched_roles["amount"]) == 1
    has_debit = len(matched_roles["debit"]) == 1
    has_credit = len(matched_roles["credit"]) == 1

    if has_amount and (has_debit or has_credit):
        errors.append("Ambiguous columns: statement contains both 'Amount' and separate Debit/Credit columns")

    if (has_debit and not has_credit) or (has_credit and not has_debit):
        if not has_amount:
            errors.append("Incomplete columns: both 'Debit' and 'Credit' columns are required when 'Amount' is not provided")

    # 3. Check for required columns
    if len(matched_roles["date"]) == 0:
        errors.append("Missing required 'Date' column in header")

    if len(matched_roles["description"]) == 0:
        errors.append("Missing required 'Description' column in header")

    if not has_amount and not (has_debit and has_credit):
        if not any("Incomplete columns" in e for e in errors):
            errors.append("Missing required monetary column: either 'Amount' or both 'Debit' and 'Credit' are required")

    return col_map, errors


def parse_csv_statement(
    content: Union[str, bytes, TextIO, BinaryIO],
    filename: Optional[str] = None,
) -> ParsedStatementResult:
    """Parse CSV statement content into structured ParsedTransaction models and row errors.
    
    Policy:
    - If file-level or header structure is invalid, rejects the entire upload (is_acceptable=False).
    - If headers are valid, processes all rows, isolating malformed rows with exact row numbers.
    - Never silently converts invalid amounts to zero or guesses ambiguous semantics.
    """
    try:
        decoded_text = _decode_content(content)
    except Exception as e:
        return ParsedStatementResult(
            filename=filename,
            transactions=[],
            errors=[ParseError(row_number=0, message=str(e))],
            total_rows_processed=0,
            is_acceptable=False,
        )

    if not decoded_text.strip():
        return ParsedStatementResult(
            filename=filename,
            transactions=[],
            errors=[ParseError(row_number=0, message="File is empty")],
            total_rows_processed=0,
            is_acceptable=False,
        )

    stream = io.StringIO(decoded_text)
    try:
        reader = csv.reader(stream)
    except Exception as e:
        return ParsedStatementResult(
            filename=filename,
            transactions=[],
            errors=[ParseError(row_number=0, message=f"CSV reader initialization failed: {str(e)}")],
            total_rows_processed=0,
            is_acceptable=False,
        )

    transactions: List[ParsedTransaction] = []
    errors: List[ParseError] = []

    header_row: Optional[List[str]] = None
    col_map: Dict[str, int] = {}
    current_line_number = 0
    total_data_rows = 0

    while True:
        try:
            row = next(reader)
            current_line_number += 1
        except StopIteration:
            break
        except csv.Error as e:
            current_line_number += 1
            errors.append(ParseError(row_number=current_line_number, message=f"Malformed CSV row: {str(e)}"))
            continue

        # Skip completely blank lines
        if not row or not any(field.strip() for field in row):
            continue

        if header_row is None:
            header_row = row
            col_map, header_errors = _resolve_headers(header_row)
            if header_errors:
                return ParsedStatementResult(
                    filename=filename,
                    transactions=[],
                    errors=[ParseError(row_number=current_line_number, message=err) for err in header_errors],
                    total_rows_processed=0,
                    is_acceptable=False,
                )
            continue

        # Data row processing
        total_data_rows += 1

        if total_data_rows > MAX_TRANSACTION_ROWS:
            errors.append(
                ParseError(
                    row_number=current_line_number,
                    message=f"Statement exceeds maximum row limit of {MAX_TRANSACTION_ROWS} transactions",
                )
            )
            return ParsedStatementResult(
                filename=filename,
                transactions=transactions,
                errors=errors,
                total_rows_processed=total_data_rows,
                is_acceptable=False,
            )

        raw_line_repr = ",".join(row)

        # 1. Description validation
        idx_desc = col_map.get("description", -1)
        if idx_desc >= len(row):
            errors.append(ParseError(row_number=current_line_number, message="Missing description column in row", raw_line=raw_line_repr, column="description"))
            continue

        desc_val = row[idx_desc].strip()
        if not desc_val:
            errors.append(ParseError(row_number=current_line_number, message="Transaction description cannot be blank", raw_line=raw_line_repr, column="description"))
            continue

        # 2. Date validation
        idx_date = col_map.get("date", -1)
        if idx_date >= len(row):
            errors.append(ParseError(row_number=current_line_number, message="Missing date column in row", raw_line=raw_line_repr, column="date"))
            continue

        date_raw = row[idx_date].strip()
        if not date_raw:
            errors.append(ParseError(row_number=current_line_number, message="Transaction date cannot be blank", raw_line=raw_line_repr, column="date"))
            continue

        try:
            parsed_date = parse_date_string(date_raw)
        except ValueError as e:
            errors.append(ParseError(row_number=current_line_number, message=str(e), raw_line=raw_line_repr, column="date"))
            continue

        # 3. Monetary Amount & Sign Resolution
        signed_amount: Decimal
        debit_val: Optional[Decimal] = None
        credit_val: Optional[Decimal] = None
        tx_type: str

        if "debit" in col_map and "credit" in col_map:
            # Separate Debit / Credit columns
            idx_deb = col_map["debit"]
            idx_cred = col_map["credit"]

            deb_raw = row[idx_deb].strip() if idx_deb < len(row) else ""
            cred_raw = row[idx_cred].strip() if idx_cred < len(row) else ""

            deb_amt: Optional[Decimal] = None
            cred_amt: Optional[Decimal] = None

            if deb_raw:
                try:
                    deb_amt = clean_amount_string(deb_raw)
                except ValueError as e:
                    errors.append(ParseError(row_number=current_line_number, message=f"Invalid debit amount: {str(e)}", raw_line=raw_line_repr, column="debit"))
                    continue

            if cred_raw:
                try:
                    cred_amt = clean_amount_string(cred_raw)
                except ValueError as e:
                    errors.append(ParseError(row_number=current_line_number, message=f"Invalid credit amount: {str(e)}", raw_line=raw_line_repr, column="credit"))
                    continue

            # Check if both columns have non-zero values (ambiguous)
            has_nonzero_deb = deb_amt is not None and deb_amt != Decimal("0")
            has_nonzero_cred = cred_amt is not None and cred_amt != Decimal("0")

            if has_nonzero_deb and has_nonzero_cred:
                errors.append(ParseError(row_number=current_line_number, message="Ambiguous row: both Debit and Credit columns contain non-zero amounts", raw_line=raw_line_repr))
                continue

            if has_nonzero_deb:
                signed_amount = -abs(deb_amt)
                debit_val = abs(deb_amt)
                tx_type = "debit"
            elif has_nonzero_cred:
                signed_amount = abs(cred_amt)
                credit_val = abs(cred_amt)
                tx_type = "credit"
            else:
                # Both zero or empty
                signed_amount = Decimal("0.00")
                tx_type = "debit"
        else:
            # Single Amount column
            idx_amt = col_map.get("amount", -1)
            if idx_amt >= len(row):
                errors.append(ParseError(row_number=current_line_number, message="Missing amount column in row", raw_line=raw_line_repr, column="amount"))
                continue

            amt_raw = row[idx_amt].strip()
            if not amt_raw:
                errors.append(ParseError(row_number=current_line_number, message="Transaction amount cannot be blank", raw_line=raw_line_repr, column="amount"))
                continue

            try:
                parsed_amt = clean_amount_string(amt_raw)
            except ValueError as e:
                errors.append(ParseError(row_number=current_line_number, message=str(e), raw_line=raw_line_repr, column="amount"))
                continue

            idx_type = col_map.get("type", -1)
            type_raw = row[idx_type].strip().lower() if idx_type != -1 and idx_type < len(row) else ""

            if type_raw:
                if any(k in type_raw for k in ["debit", "dr", "expense", "out", "withdrawal"]):
                    signed_amount = -abs(parsed_amt)
                    debit_val = abs(parsed_amt)
                    tx_type = "debit"
                elif any(k in type_raw for k in ["credit", "cr", "income", "in", "deposit"]):
                    signed_amount = abs(parsed_amt)
                    credit_val = abs(parsed_amt)
                    tx_type = "credit"
                else:
                    errors.append(ParseError(row_number=current_line_number, message=f"Ambiguous entry type '{type_raw}' in row", raw_line=raw_line_repr, column="type"))
                    continue
            else:
                # Deduce from sign of parsed amount
                signed_amount = parsed_amt
                if parsed_amt < Decimal("0"):
                    debit_val = abs(parsed_amt)
                    tx_type = "debit"
                else:
                    credit_val = parsed_amt
                    tx_type = "credit" if parsed_amt > Decimal("0") else "debit"

        # 4. Optional Metadata (Currency, Transaction ID)
        idx_curr = col_map.get("currency", -1)
        curr_val = row[idx_curr].strip().upper() if idx_curr != -1 and idx_curr < len(row) and row[idx_curr].strip() else DEFAULT_CURRENCY

        idx_tx_id = col_map.get("transaction_id", -1)
        ref_id = row[idx_tx_id].strip() if idx_tx_id != -1 and idx_tx_id < len(row) and row[idx_tx_id].strip() else None

        unique_id = f"tx_{current_line_number}_{len(transactions) + 1}"

        parsed_tx = ParsedTransaction(
            row_number=current_line_number,
            date=parsed_date,
            description=desc_val,
            amount=signed_amount,
            currency=curr_val,
            debit=debit_val,
            credit=credit_val,
            transaction_id=ref_id,
            id=unique_id,
            type=tx_type,
        )
        transactions.append(parsed_tx)

    # File without data rows check
    if header_row is not None and total_data_rows == 0:
        return ParsedStatementResult(
            filename=filename,
            transactions=[],
            errors=[ParseError(row_number=1, message="File contains header but no transaction rows")],
            total_rows_processed=0,
            is_acceptable=False,
        )

    is_acceptable = len(transactions) > 0 and len(errors) == 0 or (len(transactions) > 0 and len(errors) < total_data_rows)

    return ParsedStatementResult(
        filename=filename,
        transactions=transactions,
        errors=errors,
        total_rows_processed=total_data_rows,
        is_acceptable=is_acceptable,
    )
