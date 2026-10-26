"""Pure Python deterministic categorization brain.

Strict Assessment Rule:
Absolutely NO LLM / AI API calls are made at runtime.
All categorization decisions are made by transparent, deterministic heuristics with
bounded confidence scores and audit trail reasoning strings.

Note on Confidence Scores:
Confidence scores are deterministic heuristic weights [0.0 - 1.0] representing
rule specificity and evidentiary clarity. They are NOT statistically calibrated
probabilities from a machine learning model.
"""
from typing import List, Tuple, Union
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
from app.core.models import CategorizedTransaction, ParsedTransaction, Transaction
from app.brain.rules import (
    COMPILED_INCOME_PATTERNS,
    COMPILED_MERCHANT_RULES,
    COMPILED_REFUND_PATTERNS,
    COMPILED_TRANSFER_PATTERNS,
)


def match_merchant(description: str) -> Tuple[str, str]:
    """Scan compiled merchant regex rules to find a matching expense category.
    
    Uses word boundaries to avoid false positives (e.g. 'LAWSUIT' will not match 'AWS').
    """
    for category, patterns in COMPILED_MERCHANT_RULES.items():
        for regex, clean_name in patterns:
            if regex.search(description):
                return category, clean_name
    return "", ""


def match_transfer(description: str) -> str:
    """Check if description matches inter-account transfer or card payoff patterns."""
    for regex, clean_name in COMPILED_TRANSFER_PATTERNS:
        if regex.search(description):
            return clean_name
    return ""


def match_refund(description: str) -> str:
    """Check if description contains explicit refund or return indicators."""
    for regex, clean_name in COMPILED_REFUND_PATTERNS:
        if regex.search(description):
            return clean_name
    return ""


def match_income(description: str) -> str:
    """Check if description matches recognized client revenue / deposit patterns."""
    for regex, clean_name in COMPILED_INCOME_PATTERNS:
        if regex.search(description):
            return clean_name
    return ""


def categorize_transaction(tx: Union[ParsedTransaction, Transaction]) -> CategorizedTransaction:
    """Categorize an individual transaction using deterministic heuristics.
    
    Evaluation Pipeline:
    1. Inflow Handling (Credits / Deposits):
       a. Client Revenue (Matches recognized client invoicing/deposit patterns)
       b. Inflow Transfers (e.g., Transfer from Savings)
       c. Confirmed Refunds (Explicit refund/return indicator + merchant match -> offsets expense)
       d. Ambiguous Refunds (Explicit refund indicator but unknown merchant -> Needs Review)
       e. Vendor Credits without Refund Note (Unverified -> Needs Review; do not assume refund)
       f. Unverified Credit Deposits (Unrecognized inflow -> Needs Review; do not assume income)

    2. Outflow Handling (Debits / Expenses):
       a. Inter-Account Transfers & Card Payoffs (Non-deductible balance movements)
       b. Known Merchant Business Expenses (Matches tax category rules; autopay does not hijack)
       c. Debit Refund Fees (Debits mentioning refund/return are fees, NOT incoming refunds)
       d. Unknown Merchants / Ambiguities (Routed to Needs Review with confidence 0.0)
    """
    desc = tx.description.strip()
    tx_type = tx.type.strip().lower()
    amount = tx.amount

    matched_cat, matched_kw = match_merchant(desc)
    transfer_kw = match_transfer(desc)
    refund_kw = match_refund(desc)
    income_kw = match_income(desc)

    # =======================================================================
    # INFLOW HANDLING (Credits / Money Entering Account)
    # =======================================================================
    if tx_type == "credit":
        # 1a. Client Revenue / Taxable Gross Income
        if income_kw:
            return CategorizedTransaction(
                row_number=tx.row_number,
                id=tx.id,
                date=tx.date,
                description=tx.description,
                amount=amount,
                currency=tx.currency,
                debit=tx.debit,
                credit=tx.credit,
                transaction_id=tx.transaction_id,
                type=tx.type,
                category=CATEGORY_INCOME,
                is_refund=False,
                is_transfer=False,
                confidence=0.95,
                reason=f"Matched client revenue pattern '{income_kw}'",
                needs_review=False,
            )

        # 1b. Inflow Transfers (e.g. Online Transfer from Savings)
        if transfer_kw and not matched_cat:
            return CategorizedTransaction(
                row_number=tx.row_number,
                id=tx.id,
                date=tx.date,
                description=tx.description,
                amount=amount,
                currency=tx.currency,
                debit=tx.debit,
                credit=tx.credit,
                transaction_id=tx.transaction_id,
                type=tx.type,
                category=CATEGORY_TRANSFER,
                is_refund=False,
                is_transfer=True,
                confidence=0.98,
                reason=f"Matched transfer pattern '{transfer_kw}' (inter-account transfer in)",
                needs_review=False,
            )

        # 1c. Confirmed Refunds (Explicit refund/return indicator present)
        if refund_kw:
            if matched_cat:
                return CategorizedTransaction(
                    row_number=tx.row_number,
                    id=tx.id,
                    date=tx.date,
                    description=tx.description,
                    amount=amount,
                    currency=tx.currency,
                    debit=tx.debit,
                    credit=tx.credit,
                    transaction_id=tx.transaction_id,
                    type=tx.type,
                    category=matched_cat,
                    is_refund=True,
                    is_transfer=False,
                    confidence=0.92,
                    reason=f"Refund/return offset credited back to {matched_cat} (merchant '{matched_kw}')",
                    needs_review=False,
                )
            else:
                return CategorizedTransaction(
                    row_number=tx.row_number,
                    id=tx.id,
                    date=tx.date,
                    description=tx.description,
                    amount=amount,
                    currency=tx.currency,
                    debit=tx.debit,
                    credit=tx.credit,
                    transaction_id=tx.transaction_id,
                    type=tx.type,
                    category=CATEGORY_NEEDS_REVIEW,
                    is_refund=True,
                    is_transfer=False,
                    confidence=0.45,
                    reason="Explicit refund indicator detected but original expense category is unknown",
                    needs_review=True,
                )

        # 1d. Vendor Credit WITHOUT explicit refund or income indicators
        # Rule: Do not assume every credit from a known merchant is a refund.
        if matched_cat:
            return CategorizedTransaction(
                row_number=tx.row_number,
                id=tx.id,
                date=tx.date,
                description=tx.description,
                amount=amount,
                currency=tx.currency,
                debit=tx.debit,
                credit=tx.credit,
                transaction_id=tx.transaction_id,
                type=tx.type,
                category=CATEGORY_NEEDS_REVIEW,
                is_refund=False,
                is_transfer=False,
                confidence=0.35,
                reason=f"Incoming credit from vendor '{matched_kw}' without explicit refund or income indicators; requires manual verification",
                needs_review=True,
            )

        # 1e. Unverified Credit Deposit (Safety Fallback)
        return CategorizedTransaction(
            row_number=tx.row_number,
            id=tx.id,
            date=tx.date,
            description=tx.description,
            amount=amount,
            currency=tx.currency,
            debit=tx.debit,
            credit=tx.credit,
            transaction_id=tx.transaction_id,
            type=tx.type,
            category=CATEGORY_NEEDS_REVIEW,
            is_refund=False,
            is_transfer=False,
            confidence=0.30,
            reason="Unrecognized credit deposit; requires user verification",
            needs_review=True,
        )

    # =======================================================================
    # OUTFLOW HANDLING (Debits / Money Leaving Account)
    # =======================================================================

    # 2a. Inter-Account Transfers & Credit Card Payoffs
    # Checked only if no business merchant matched to avoid false positives on autopay subscriptions
    if transfer_kw and not matched_cat:
        return CategorizedTransaction(
            row_number=tx.row_number,
            id=tx.id,
            date=tx.date,
            description=tx.description,
            amount=amount,
            currency=tx.currency,
            debit=tx.debit,
            credit=tx.credit,
            transaction_id=tx.transaction_id,
            type=tx.type,
            category=CATEGORY_TRANSFER,
            is_refund=False,
            is_transfer=True,
            confidence=0.98,
            reason=f"Matched transfer pattern '{transfer_kw}' (inter-account or debt payment)",
            needs_review=False,
        )

    # 2b. Known Merchant Business Expenses (Money Out)
    # Rule: Debits containing 'refund' (e.g. refund processing fee) are fees, NOT incoming refunds.
    if matched_cat:
        reason_str = (
            f"Debit fee/charge associated with refund/return for {matched_cat} (merchant '{matched_kw}')"
            if refund_kw
            else f"Matched merchant '{matched_kw}' for category {matched_cat}"
        )
        return CategorizedTransaction(
            row_number=tx.row_number,
            id=tx.id,
            date=tx.date,
            description=tx.description,
            amount=amount,
            currency=tx.currency,
            debit=tx.debit,
            credit=tx.credit,
            transaction_id=tx.transaction_id,
            type=tx.type,
            category=matched_cat,
            is_refund=False,
            is_transfer=False,
            confidence=0.90,
            reason=reason_str,
            needs_review=False,
        )

    # 2c. Debit mentioning refund/return but unknown merchant (e.g. 'RETURN RESTOCKING FEE')
    if refund_kw:
        return CategorizedTransaction(
            row_number=tx.row_number,
            id=tx.id,
            date=tx.date,
            description=tx.description,
            amount=amount,
            currency=tx.currency,
            debit=tx.debit,
            credit=tx.credit,
            transaction_id=tx.transaction_id,
            type=tx.type,
            category=CATEGORY_NEEDS_REVIEW,
            is_refund=False,
            is_transfer=False,
            confidence=0.0,
            reason="Debit transaction mentioning refund/return but merchant is unrecognized; routed to Needs Review",
            needs_review=True,
        )

    # 2d. Safety Fallback: Unknown Merchant / Ambiguous Debit
    # Rule: A wrong guess is worse than asking. Ambiguous entries MUST route to Needs Review.
    return CategorizedTransaction(
        row_number=tx.row_number,
        id=tx.id,
        date=tx.date,
        description=tx.description,
        amount=amount,
        currency=tx.currency,
        debit=tx.debit,
        credit=tx.credit,
        transaction_id=tx.transaction_id,
        type=tx.type,
        category=CATEGORY_NEEDS_REVIEW,
        is_refund=False,
        is_transfer=False,
        confidence=0.0,
        reason="Unrecognized merchant or description; routed to Needs Review per safety rule",
        needs_review=True,
    )


def categorize_statement(transactions: List[Union[ParsedTransaction, Transaction]]) -> List[CategorizedTransaction]:
    """Categorize an entire statement batch of transactions."""
    return [categorize_transaction(tx) for tx in transactions]
