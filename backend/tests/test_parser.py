"""Comprehensive unit tests for the robust statement CSV parser.

Tests cover:
A. Valid CSV with standard columns.
B. Alternative recognized column names.
C. UTF-8 BOM handling.
D. Quoted descriptions containing commas.
E. Whitespace and case normalization in headers.
F. Common supported date formats.
G. Negative, positive, zero, and decimal amounts.
H. Separate debit and credit columns.
I. Missing required columns.
J. Invalid amount values.
K. Non-finite amounts (NaN, Infinity).
L. Invalid dates.
M. Empty files.
N. Headers with no transactions.
O. Blank descriptions.
P. Malformed CSV rows.
Q. Duplicate or ambiguous recognized columns.
R. Blank rows.
S. Oversized uploads and excessive row counts.
T. Correct row numbers in validation errors.
"""
import datetime
from decimal import Decimal
import pytest

from app.core.config import MAX_TRANSACTION_ROWS, MAX_UPLOAD_SIZE_BYTES
from app.parser.csv_parser import clean_amount_string, parse_csv_statement, parse_date_string


# ===========================================================================
# Test A: Valid CSV with standard columns
# ===========================================================================
def test_valid_csv_standard_columns():
    csv_text = """date,description,amount,type
2026-03-01,ADOBE CREATIVE CLOUD,54.99,debit
2026-03-02,CLIENT WIRE TRANSFER,2500.00,credit
"""
    result = parse_csv_statement(csv_text, filename="test.csv")
    assert result.is_acceptable is True
    assert len(result.errors) == 0
    assert len(result.transactions) == 2
    assert result.total_rows_processed == 2

    t1, t2 = result.transactions
    assert t1.date == datetime.date(2026, 3, 1)
    assert t1.description == "ADOBE CREATIVE CLOUD"
    assert t1.amount == Decimal("-54.99")
    assert t1.type == "debit"
    assert t1.row_number == 2

    assert t2.date == datetime.date(2026, 3, 2)
    assert t2.description == "CLIENT WIRE TRANSFER"
    assert t2.amount == Decimal("2500.00")
    assert t2.type == "credit"
    assert t2.row_number == 3


# ===========================================================================
# Test B: Alternative recognized column names
# ===========================================================================
def test_alternative_recognized_column_names():
    csv_text = """Transaction Date,Merchant,Value,Transaction Type
2026-03-03,UBER TRIP,34.50,Debit
2026-03-04,STRIPE PAYOUT,1200.00,Credit
"""
    result = parse_csv_statement(csv_text)
    assert result.is_acceptable is True
    assert len(result.transactions) == 2
    assert result.transactions[0].description == "UBER TRIP"
    assert result.transactions[0].amount == Decimal("-34.50")
    assert result.transactions[1].description == "STRIPE PAYOUT"
    assert result.transactions[1].amount == Decimal("1200.00")


# ===========================================================================
# Test C: UTF-8 BOM
# ===========================================================================
def test_utf8_bom():
    # Byte order mark \xef\xbb\xbf prefix
    content_bytes = "\ufeffdate,description,amount\n2026-03-01,OFFICE DEPOT,-89.20\n".encode("utf-8-sig")
    result = parse_csv_statement(content_bytes)
    assert result.is_acceptable is True
    assert len(result.transactions) == 1
    assert result.transactions[0].description == "OFFICE DEPOT"
    assert result.transactions[0].amount == Decimal("-89.20")


# ===========================================================================
# Test D: Quoted descriptions containing commas
# ===========================================================================
def test_quoted_descriptions_with_commas():
    csv_text = """date,description,amount
2026-03-05,"COFFEE, BAGELS & TEA SHOP",-14.75
2026-03-06,"SMITH, JONES & ASSOCIATES, LLC",1500.00
"""
    result = parse_csv_statement(csv_text)
    assert result.is_acceptable is True
    assert len(result.transactions) == 2
    assert result.transactions[0].description == "COFFEE, BAGELS & TEA SHOP"
    assert result.transactions[0].amount == Decimal("-14.75")
    assert result.transactions[1].description == "SMITH, JONES & ASSOCIATES, LLC"
    assert result.transactions[1].amount == Decimal("1500.00")


# ===========================================================================
# Test E: Whitespace and case normalization in headers
# ===========================================================================
def test_whitespace_and_case_normalization_in_headers():
    csv_text = """   DATE   ,  DESCRIPTION  ,   AMOUNT   ,   TYPE   
2026-03-01,   ZOOM SUBSCRIPTION   ,   15.99   ,   DEBIT   
"""
    result = parse_csv_statement(csv_text)
    assert result.is_acceptable is True
    assert len(result.transactions) == 1
    assert result.transactions[0].description == "ZOOM SUBSCRIPTION"
    assert result.transactions[0].amount == Decimal("-15.99")


# ===========================================================================
# Test F: Common supported date formats
# ===========================================================================
def test_common_supported_date_formats():
    dates = [
        ("2026-03-01", datetime.date(2026, 3, 1)),
        ("2026/03/01", datetime.date(2026, 3, 1)),
        ("03/01/2026", datetime.date(2026, 3, 1)),
        ("03-01-2026", datetime.date(2026, 3, 1)),
        ("20260301", datetime.date(2026, 3, 1)),
        ("Mar 01, 2026", datetime.date(2026, 3, 1)),
        ("March 01, 2026", datetime.date(2026, 3, 1)),
    ]
    for date_str, expected_date in dates:
        parsed = parse_date_string(date_str)
        assert parsed == expected_date, f"Failed parsing {date_str}"


# ===========================================================================
# Test G: Negative, positive, zero, and decimal amounts
# ===========================================================================
def test_signed_and_decimal_amounts():
    csv_text = """date,description,amount
2026-03-01,EXPENSE MINUS,-54.99
2026-03-02,EXPENSE PARENS,(35.50)
2026-03-03,CURRENCY FORMAT,"$1,234.56"
2026-03-04,NEGATIVE CURRENCY,-$45.00
2026-03-05,ZERO BALANCE HOLD,0.00
2026-03-06,POSITIVE INFLOW,+500.00
"""
    result = parse_csv_statement(csv_text)
    assert result.is_acceptable is True
    assert len(result.transactions) == 6
    txs = result.transactions
    assert txs[0].amount == Decimal("-54.99")
    assert txs[1].amount == Decimal("-35.50")
    assert txs[2].amount == Decimal("1234.56")
    assert txs[3].amount == Decimal("-45.00")
    assert txs[4].amount == Decimal("0.00")
    assert txs[5].amount == Decimal("500.00")


# ===========================================================================
# Test H: Separate debit and credit columns
# ===========================================================================
def test_separate_debit_credit_columns():
    csv_text = """date,description,debit,credit
2026-03-01,SOFTWARE TOOL,29.00,
2026-03-02,CLIENT REVENUE,,3200.00
2026-03-03,ZERO TRANSACTION,0.00,0.00
2026-03-04,CONTRADICTORY ROW,50.00,50.00
"""
    result = parse_csv_statement(csv_text)
    assert result.is_acceptable is True
    assert len(result.transactions) == 3
    assert len(result.errors) == 1

    # Valid rows
    assert result.transactions[0].amount == Decimal("-29.00")
    assert result.transactions[0].debit == Decimal("29.00")
    assert result.transactions[0].credit is None

    assert result.transactions[1].amount == Decimal("3200.00")
    assert result.transactions[1].credit == Decimal("3200.00")
    assert result.transactions[1].debit is None

    assert result.transactions[2].amount == Decimal("0.00")

    # Contradictory row error
    err = result.errors[0]
    assert err.row_number == 5
    assert "both Debit and Credit" in err.message


# ===========================================================================
# Test I: Missing required columns
# ===========================================================================
def test_missing_required_columns():
    # Missing Date
    res1 = parse_csv_statement("description,amount\nVendor,50.00\n")
    assert res1.is_acceptable is False
    assert any("Date" in e.message for e in res1.errors)

    # Missing Description
    res2 = parse_csv_statement("date,amount\n2026-03-01,50.00\n")
    assert res2.is_acceptable is False
    assert any("Description" in e.message for e in res2.errors)

    # Missing Amount
    res3 = parse_csv_statement("date,description\n2026-03-01,Vendor\n")
    assert res3.is_acceptable is False
    assert any("monetary" in e.message.lower() for e in res3.errors)


# ===========================================================================
# Test J: Invalid amount values
# ===========================================================================
def test_invalid_amount_values():
    csv_text = """date,description,amount
2026-03-01,VALID ROW,10.00
2026-03-02,INVALID ALPHA,not-a-number
2026-03-03,DOUBLE MINUS,--50.00
2026-03-04,BLANK AMOUNT,
"""
    result = parse_csv_statement(csv_text)
    assert result.is_acceptable is True
    assert len(result.transactions) == 1
    assert len(result.errors) == 3

    assert result.errors[0].row_number == 3
    assert result.errors[1].row_number == 4
    assert result.errors[2].row_number == 5


# ===========================================================================
# Test K: Non-finite amounts (NaN, Infinity)
# ===========================================================================
def test_non_finite_amounts():
    csv_text = """date,description,amount
2026-03-01,NAN TEST,NaN
2026-03-02,INF TEST,Infinity
2026-03-03,NEG INF TEST,-inf
"""
    result = parse_csv_statement(csv_text)
    assert len(result.transactions) == 0
    assert len(result.errors) == 3
    for err in result.errors:
        assert "Non-finite" in err.message or "non-finite" in err.message.lower()


# ===========================================================================
# Test L: Invalid dates
# ===========================================================================
def test_invalid_dates():
    csv_text = """date,description,amount
2026-02-30,FEBRUARY INVALID,10.00
not-a-date,GIBBERISH DATE,20.00
99/99/9999,IMPOSSIBLE DATE,30.00
"""
    result = parse_csv_statement(csv_text)
    assert len(result.transactions) == 0
    assert len(result.errors) == 3
    assert result.errors[0].row_number == 2
    assert "date" in result.errors[0].message.lower()


# ===========================================================================
# Test M: Empty files
# ===========================================================================
def test_empty_files():
    res1 = parse_csv_statement("")
    assert res1.is_acceptable is False
    assert len(res1.errors) == 1
    assert "empty" in res1.errors[0].message.lower()

    res2 = parse_csv_statement("    \n   \n")
    assert res2.is_acceptable is False
    assert len(res2.errors) == 1
    assert "empty" in res2.errors[0].message.lower()


# ===========================================================================
# Test N: Headers with no transactions
# ===========================================================================
def test_headers_with_no_transactions():
    csv_text = "date,description,amount,type\n"
    result = parse_csv_statement(csv_text)
    assert result.is_acceptable is False
    assert len(result.transactions) == 0
    assert any("no transaction rows" in e.message.lower() for e in result.errors)


# ===========================================================================
# Test O: Blank descriptions
# ===========================================================================
def test_blank_descriptions():
    csv_text = """date,description,amount
2026-03-01,,10.00
2026-03-02,   ,20.00
"""
    result = parse_csv_statement(csv_text)
    assert len(result.transactions) == 0
    assert len(result.errors) == 2
    assert result.errors[0].row_number == 2
    assert "blank" in result.errors[0].message.lower()


# ===========================================================================
# Test P: Malformed CSV rows
# ===========================================================================
def test_malformed_csv_rows():
    # Row with fewer fields than required columns
    csv_text = """date,description,amount
2026-03-01,ONLY TWO FIELDS
2026-03-02,VALID ROW,25.00
"""
    result = parse_csv_statement(csv_text)
    assert len(result.transactions) == 1
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 2
    assert "missing" in result.errors[0].message.lower()


# ===========================================================================
# Test Q: Duplicate or ambiguous recognized columns
# ===========================================================================
def test_duplicate_or_ambiguous_columns():
    # Duplicate Date columns
    csv_text1 = "Date,Posted Date,Description,Amount\n2026-03-01,2026-03-01,Vendor,10.00\n"
    res1 = parse_csv_statement(csv_text1)
    assert res1.is_acceptable is False
    assert any("Ambiguous columns" in e.message for e in res1.errors)

    # Conflicting Amount and Debit/Credit
    csv_text2 = "Date,Description,Amount,Debit,Credit\n2026-03-01,Vendor,10.00,10.00,\n"
    res2 = parse_csv_statement(csv_text2)
    assert res2.is_acceptable is False
    assert any("Ambiguous columns" in e.message for e in res2.errors)


# ===========================================================================
# Test R: Blank rows handling
# ===========================================================================
def test_blank_rows_handling():
    csv_text = """date,description,amount

2026-03-01,VALID ROW 1,10.00

2026-03-02,VALID ROW 2,20.00

"""
    result = parse_csv_statement(csv_text)
    assert result.is_acceptable is True
    assert len(result.transactions) == 2
    assert len(result.errors) == 0
    # Line numbers track physical lines: header is 1, blank is 2, row 1 is 3, blank is 4, row 2 is 5
    assert result.transactions[0].row_number == 3
    assert result.transactions[1].row_number == 5


# ===========================================================================
# Test S: Oversized uploads and excessive row counts
# ===========================================================================
def test_oversized_uploads_and_excessive_rows():
    # Test oversized bytes
    oversized_bytes = b"x" * (MAX_UPLOAD_SIZE_BYTES + 100)
    res_size = parse_csv_statement(oversized_bytes)
    assert res_size.is_acceptable is False
    assert any("maximum allowed limit" in e.message for e in res_size.errors)

    # Test row count exceeding limit
    lines = ["date,description,amount"]
    for i in range(1, 20):
        lines.append(f"2026-03-01,Item {i},1.00")
    csv_content = "\n".join(lines)

    # Temporarily check with monkeypatched limit
    import app.parser.csv_parser as parser_module
    orig_limit = parser_module.MAX_TRANSACTION_ROWS
    try:
        parser_module.MAX_TRANSACTION_ROWS = 5
        res_rows = parser_module.parse_csv_statement(csv_content)
        assert res_rows.is_acceptable is False
        assert any("maximum row limit" in e.message for e in res_rows.errors)
    finally:
        parser_module.MAX_TRANSACTION_ROWS = orig_limit


# ===========================================================================
# Test T: Correct row numbers in validation errors
# ===========================================================================
def test_correct_row_numbers_in_validation_errors():
    csv_text = """date,description,amount
2026-03-01,VALID 1,10.00
2026-03-02,,20.00
2026-03-03,INVALID AMT,not-an-amount
2026-02-30,INVALID DATE,30.00
2026-03-05,VALID 2,40.00
"""
    result = parse_csv_statement(csv_text)
    assert len(result.transactions) == 2
    assert len(result.errors) == 3

    assert result.errors[0].row_number == 3  # blank desc
    assert result.errors[1].row_number == 4  # invalid amt
    assert result.errors[2].row_number == 5  # invalid date
    assert result.transactions[0].row_number == 2
    assert result.transactions[1].row_number == 6
