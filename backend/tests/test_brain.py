"""Comprehensive unit tests for the deterministic categorization brain engine.

Tests cover:
- Software & SaaS subscriptions
- Cloud Hosting & Infrastructure
- Office Supplies & Equipment
- Travel & Transportation
- Business Meals (50% tax deductible rule)
- Client Revenue / Income payouts
- Inter-account balance transfers (non-deductible)
- Credit card debt settlements (non-deductible)
- Refunds as expense offsets (reversals credited back to expense categories)
- Ambiguous refunds without recognized merchants
- Unknown merchant safety fallback: JOES CAFE 9921 -> Needs Review (confidence 0.0)
- Ambiguous vendor safety fallback: SQ *LOCAL VENDOR 339 -> Needs Review (confidence 0.0)
- Unverified credit deposits -> Needs Review (confidence 0.30)
- Word-boundary protection (e.g. LAWSUIT does not falsely match AWS)
- Batch statement processing (categorize_statement)
- Preservation of Decimal amounts and audit trail reasoning
"""
import datetime
from decimal import Decimal
import pytest

from app.core.config import (
    CATEGORY_EQUIPMENT,
    CATEGORY_HOSTING,
    CATEGORY_INCOME,
    CATEGORY_MEALS,
    CATEGORY_NEEDS_REVIEW,
    CATEGORY_SOFTWARE,
    CATEGORY_TRANSFER,
    CATEGORY_TRAVEL,
)
from app.core.models import ParsedTransaction, Transaction
from app.brain.engine import categorize_statement, categorize_transaction


def _make_tx(desc: str, amount_str: str, tx_type: str = "debit") -> ParsedTransaction:
    """Helper to construct a ParsedTransaction for testing."""
    amt = Decimal(amount_str)
    return ParsedTransaction(
        row_number=2,
        id="tx_test_1",
        date=datetime.date(2026, 3, 1),
        description=desc,
        amount=amt,
        currency="USD",
        type=tx_type,
    )


# ===========================================================================
# 1. Software Subscriptions
# ===========================================================================
def test_software_subscriptions():
    vendors = [
        ("ADOBE *CREATIVE CLOUD", "-54.99"),
        ("GITHUB *PRO SUBSCRIPTION", "-21.00"),
        ("ZOOM.US MONTHLY PLAN", "-15.99"),
        ("JETBRAINS ALL PRODUCTS", "-249.00"),
        ("FIGMA ENTERPRISE", "-45.00"),
        ("NOTION TEAM SUBSCRIPTION", "-10.00"),
        ("SLACK TECHNOLOGIES", "-8.75"),
    ]
    for desc, amt in vendors:
        tx = _make_tx(desc, amt, "debit")
        res = categorize_transaction(tx)
        assert res.category == CATEGORY_SOFTWARE, f"Failed on {desc}"
        assert res.is_refund is False
        assert res.is_transfer is False
        assert res.needs_review is False
        assert res.confidence >= 0.90
        assert "Software" in res.reason


# ===========================================================================
# 2. Cloud Hosting & Infrastructure
# ===========================================================================
def test_cloud_hosting():
    vendors = [
        ("AMAZON WEB SERVICES AWS", "-142.10"),
        ("DIGITALOCEAN CLOUD HOSTING", "-24.00"),
        ("VERCEL PRO SUBSCRIPTION", "-20.00"),
        ("NETLIFY TEAM PLAN", "-19.00"),
        ("CLOUDFLARE SERVICES", "-25.00"),
    ]
    for desc, amt in vendors:
        tx = _make_tx(desc, amt, "debit")
        res = categorize_transaction(tx)
        assert res.category == CATEGORY_HOSTING, f"Failed on {desc}"
        assert res.needs_review is False
        assert res.confidence >= 0.90


# ===========================================================================
# 3. Office Supplies & Equipment
# ===========================================================================
def test_office_equipment():
    vendors = [
        ("OFFICE DEPOT #4412", "-89.20"),
        ("APPLE STORE ONLINE PURCHASE", "-1299.00"),
        ("BEST BUY #1092 CABLES", "-34.99"),
        ("B&H PHOTO VIDEO NYC", "-450.00"),
        ("AMAZON MKTPLACE MONITOR STAND", "-65.00"),
    ]
    for desc, amt in vendors:
        tx = _make_tx(desc, amt, "debit")
        res = categorize_transaction(tx)
        assert res.category == CATEGORY_EQUIPMENT, f"Failed on {desc}"
        assert res.needs_review is False
        assert res.confidence >= 0.90


# ===========================================================================
# 4. Travel & Transportation
# ===========================================================================
def test_travel_expenses():
    vendors = [
        ("UBER *TRIP 8821", "-34.50"),
        ("LYFT *RIDE 0492", "-22.10"),
        ("DELTA AIR LINES TICKET", "-312.40"),
        ("AMTRAK NORTHEAST REGIONAL", "-85.00"),
        ("AIRBNB RESERVATION NYC", "-420.00"),
    ]
    for desc, amt in vendors:
        tx = _make_tx(desc, amt, "debit")
        res = categorize_transaction(tx)
        assert res.category == CATEGORY_TRAVEL, f"Failed on {desc}"
        assert res.needs_review is False
        assert res.confidence >= 0.90


# ===========================================================================
# 5. Business Meals (50% Tax Deductible)
# ===========================================================================
def test_business_meals():
    vendors = [
        ("STARBUCKS STORE #1029", "-9.50"),
        ("CHIPOTLE ONLINE ORDER", "-14.25"),
        ("SWEETGREEN SOHO", "-16.80"),
        ("PANERA BREAD #221", "-12.40"),
    ]
    for desc, amt in vendors:
        tx = _make_tx(desc, amt, "debit")
        res = categorize_transaction(tx)
        assert res.category == CATEGORY_MEALS, f"Failed on {desc}"
        assert res.needs_review is False
        assert res.confidence >= 0.90


# ===========================================================================
# 6. Client Revenue / Income
# ===========================================================================
def test_client_revenue():
    receipts = [
        ("STRIPE PAYOUT *CLIENT INVOICE #104", "2450.00"),
        ("WIRE TRANSFER FROM ACME CORP INV-202", "3200.00"),
        ("UPWORK ESCROW PAYOUT", "850.00"),
        ("DIRECT DEPOSIT TECH CLIENT CONSULTING", "4500.00"),
    ]
    for desc, amt in receipts:
        tx = _make_tx(desc, amt, "credit")
        res = categorize_transaction(tx)
        assert res.category == CATEGORY_INCOME, f"Failed on {desc}"
        assert res.is_refund is False
        assert res.is_transfer is False
        assert res.needs_review is False
        assert res.confidence >= 0.95


# ===========================================================================
# 7. Inter-Account Transfers & Credit Card Payments (Non-Deductible)
# ===========================================================================
def test_transfers_and_debt_payments():
    transfers = [
        ("ONLINE TRANSFER TO SAVINGS 4492", "-1000.00"),
        ("AUTOMATIC PAYMENT - THANK YOU CHASE CARD", "-500.00"),
        ("AUTOPAY AMEX EPAYMENT", "-350.00"),
        ("CAPITAL ONE PMT DRAFT", "-200.00"),
        ("INTERNAL XFER TO CHECKING", "-750.00"),
    ]
    for desc, amt in transfers:
        tx = _make_tx(desc, amt, "debit")
        res = categorize_transaction(tx)
        assert res.category == CATEGORY_TRANSFER, f"Failed on {desc}"
        assert res.is_transfer is True
        assert res.is_refund is False
        assert res.needs_review is False
        assert res.confidence == 0.98
        assert "transfer" in res.reason.lower() or "debt" in res.reason.lower()


# ===========================================================================
# 8. Refunds as Expense Offsets (Reversals, NOT Income)
# ===========================================================================
def test_refunds_credited_to_original_expense_category():
    # Software refund
    tx_software_refund = _make_tx("ADOBE *REFUND PRO-RATA", "27.50", "credit")
    res_sw = categorize_transaction(tx_software_refund)
    assert res_sw.category == CATEGORY_SOFTWARE
    assert res_sw.is_refund is True
    assert res_sw.is_transfer is False
    assert res_sw.needs_review is False
    assert res_sw.confidence >= 0.90
    assert "offset" in res_sw.reason.lower() or "refund" in res_sw.reason.lower()

    # Equipment refund
    tx_equip_refund = _make_tx("AMAZON MKTPLACE REFUND RETURN", "45.00", "credit")
    res_eq = categorize_transaction(tx_equip_refund)
    assert res_eq.category == CATEGORY_EQUIPMENT
    assert res_eq.is_refund is True
    assert res_eq.needs_review is False


# ===========================================================================
# 9. Ambiguous Refund with Unknown Original Merchant
# ===========================================================================
def test_ambiguous_refund_routes_to_needs_review():
    tx = _make_tx("PRO-RATA REFUND REF#99821", "15.00", "credit")
    res = categorize_transaction(tx)
    assert res.category == CATEGORY_NEEDS_REVIEW
    assert res.is_refund is True
    assert res.needs_review is True
    assert res.confidence == 0.45
    assert "unknown" in res.reason.lower()


# ===========================================================================
# 10. Unknown Merchant Safety Rule: JOES CAFE 9921
# ===========================================================================
def test_joes_cafe_routes_to_needs_review():
    """TASK.md specification: JOES CAFE 9921 is unknown and must go to Needs Review."""
    tx = _make_tx("JOES CAFE 9921", "-18.75", "debit")
    res = categorize_transaction(tx)
    assert res.category == CATEGORY_NEEDS_REVIEW
    assert res.needs_review is True
    assert res.confidence == 0.0
    assert "safety rule" in res.reason.lower() or "unrecognized" in res.reason.lower()


# ===========================================================================
# 11. Ambiguous Mystery Vendor: SQ *LOCAL VENDOR 339
# ===========================================================================
def test_local_vendor_routes_to_needs_review():
    tx = _make_tx("SQ *LOCAL VENDOR 339", "-65.00", "debit")
    res = categorize_transaction(tx)
    assert res.category == CATEGORY_NEEDS_REVIEW
    assert res.needs_review is True
    assert res.confidence == 0.0


# ===========================================================================
# 12. Unverified Credit Deposit
# ===========================================================================
def test_unverified_credit_routes_to_needs_review():
    tx = _make_tx("MISCELLANEOUS DEPOSIT REF#4401", "200.00", "credit")
    res = categorize_transaction(tx)
    assert res.category == CATEGORY_NEEDS_REVIEW
    assert res.needs_review is True
    assert res.confidence == 0.30
    assert "unrecognized credit deposit" in res.reason.lower() or "unverified" in res.reason.lower()


# ===========================================================================
# 13. Sub-word Boundary Safety (No false positives like LAWSUIT -> AWS)
# ===========================================================================
def test_word_boundary_safety():
    tx = _make_tx("COUNTY COURT LAWSUIT FILING FEE", "-120.00", "debit")
    res = categorize_transaction(tx)
    # Must NOT match 'AWS' inside 'LAWSUIT'
    assert res.category == CATEGORY_NEEDS_REVIEW
    assert res.needs_review is True
    assert res.confidence == 0.0


# ===========================================================================
# 14. Batch Statement Processing
# ===========================================================================
def test_categorize_statement_batch():
    batch = [
        _make_tx("ADOBE *CREATIVE CLOUD", "-54.99", "debit"),
        _make_tx("STRIPE PAYOUT *INVOICE", "2000.00", "credit"),
        _make_tx("ONLINE TRANSFER TO SAVINGS", "-500.00", "debit"),
        _make_tx("JOES CAFE 9921", "-12.50", "debit"),
    ]
    results = categorize_statement(batch)
    assert len(results) == 4
    assert results[0].category == CATEGORY_SOFTWARE
    assert results[1].category == CATEGORY_INCOME
    assert results[2].category == CATEGORY_TRANSFER
    assert results[3].category == CATEGORY_NEEDS_REVIEW
    assert results[3].needs_review is True


# ===========================================================================
# 15. Decimal Precision and Model Integrity
# ===========================================================================
def test_decimal_preservation():
    tx = _make_tx("UBER *TRIP", "-34.50", "debit")
    res = categorize_transaction(tx)
    assert isinstance(res.amount, Decimal)
    assert res.amount == Decimal("-34.50")
    assert res.manually_edited is False


# ===========================================================================
# 16. Spec-Exact Test from TASK.md
# ===========================================================================
def test_adobe_refund_exact_from_spec():
    """Mirrors TASK.md example: 'ADOBE REFUND' → Software, is_refund=True."""
    tx = Transaction(
        id="t_spec",
        date="2026-03-10",
        description="ADOBE REFUND",
        amount=Decimal("27.50"),
        type="credit",
    )
    result = categorize_transaction(tx)
    assert result.category == CATEGORY_SOFTWARE
    assert result.is_refund is True
    assert result.is_transfer is False
    assert result.needs_review is False


# ===========================================================================
# 17. Float-Safety Test
# ===========================================================================
def test_float_input_does_not_corrupt_decimal():
    tx = Transaction(
        id="t1",
        date="2026-03-01",
        description="ADOBE *CREATIVE CLOUD",
        amount=54.99,
        type="debit",
    )
    assert str(tx.amount) == "54.99", f"got {tx.amount!r}"


# ===========================================================================
# 18. Debit Containing 'Refund' Word Must NOT Be an Incoming Refund
# ===========================================================================
def test_debit_with_refund_word_not_marked_as_incoming_refund():
    """A debit containing 'REFUND' is money leaving (e.g. fee/charge), NOT money returned."""
    # Debit for airline ticket refund fee
    tx_fee = _make_tx("DELTA AIR REFUND PROCESSING FEE", "-15.00", "debit")
    res_fee = categorize_transaction(tx_fee)
    assert res_fee.category == CATEGORY_TRAVEL
    assert res_fee.is_refund is False  # Outflow cannot be an incoming refund
    assert res_fee.needs_review is False

    # Unrecognized debit mentioning refund
    tx_unknown_fee = _make_tx("RETURN ITEM RESTOCKING FEE 541", "-8.50", "debit")
    res_unknown = categorize_transaction(tx_unknown_fee)
    assert res_unknown.category == CATEGORY_NEEDS_REVIEW
    assert res_unknown.is_refund is False
    assert res_unknown.needs_review is True


# ===========================================================================
# 19. Credit from Known Merchant Without Refund Keywords Routes to Needs Review
# ===========================================================================
def test_credit_from_merchant_without_refund_keyword_routes_to_needs_review():
    """Do not assume every incoming credit from a known merchant is a refund."""
    tx_deposit = _make_tx("ADOBE SYSTEMS INC PAYOUT", "500.00", "credit")
    res = categorize_transaction(tx_deposit)
    assert res.category == CATEGORY_NEEDS_REVIEW
    assert res.is_refund is False
    assert res.needs_review is True
    assert "without explicit refund" in res.reason.lower()


# ===========================================================================
# 20. Transfer False Positives Do NOT Hijack Legitimate Business Expenses
# ===========================================================================
def test_transfer_false_positives_do_not_hijack_business_expenses():
    """Autopay and automatic payment terms on software subscriptions must stay business expenses."""
    tx_sub = _make_tx("GITHUB AUTOMATIC PAYMENT", "-21.00", "debit")
    res_sub = categorize_transaction(tx_sub)
    assert res_sub.category == CATEGORY_SOFTWARE
    assert res_sub.is_transfer is False

    tx_ride = _make_tx("UBER AUTOPAY BILLING", "-34.50", "debit")
    res_ride = categorize_transaction(tx_ride)
    assert res_ride.category == CATEGORY_TRAVEL
    assert res_ride.is_transfer is False


# ===========================================================================
# 21. Explicit Verification of All Spec-Required Categories
# ===========================================================================
def test_all_required_spec_categories():
    """Verify each category specified in TASK.md maps to its canonical domain category."""
    test_cases = [
        ("ADOBE CREATIVE CLOUD", "-54.99", "debit", CATEGORY_SOFTWARE),
        ("AWS HOSTING", "-89.00", "debit", CATEGORY_HOSTING),
        ("UBER *TRIP", "-22.50", "debit", CATEGORY_TRAVEL),
        ("OFFICE DEPOT #4412", "-45.00", "debit", CATEGORY_EQUIPMENT),
        ("STARBUCKS STORE #1029", "-6.50", "debit", CATEGORY_MEALS),
        ("STRIPE PAYOUT *INVOICE #104", "1500.00", "credit", CATEGORY_INCOME),
        ("TRANSFER TO SAVINGS 4492", "-500.00", "debit", CATEGORY_TRANSFER),
        ("JOES CAFE 9921", "-18.75", "debit", CATEGORY_NEEDS_REVIEW),
    ]
    for desc, amt, tx_type, expected_cat in test_cases:
        tx = _make_tx(desc, amt, tx_type)
        res = categorize_transaction(tx)
        assert res.category == expected_cat, f"Mismatch for '{desc}': expected {expected_cat}, got {res.category}"


# ===========================================================================
# 22. Confidence Bounds and Reason Explanations
# ===========================================================================
def test_confidence_bounds_and_reason_strings():
    """Every transaction must have 0.0 <= confidence <= 1.0 and a non-empty explanation."""
    samples = [
        _make_tx("ADOBE CREATIVE CLOUD", "-54.99", "debit"),
        _make_tx("STRIPE PAYOUT", "1000.00", "credit"),
        _make_tx("TRANSFER TO SAVINGS", "-500.00", "debit"),
        _make_tx("ADOBE REFUND", "27.50", "credit"),
        _make_tx("PRO-RATA REFUND", "10.00", "credit"),
        _make_tx("UNKNOWN MYSTERY MERCH 123", "-40.00", "debit"),
        _make_tx("UNEXPECTED WIRE DEPOSIT", "300.00", "credit"),
    ]
    for tx in samples:
        res = categorize_transaction(tx)
        assert 0.0 <= res.confidence <= 1.0, f"Confidence out of bounds: {res.confidence}"
        assert res.reason and len(res.reason.strip()) > 5, f"Missing or trivial reason for {tx.description}"

