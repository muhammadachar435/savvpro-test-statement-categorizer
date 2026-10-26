"""Pure Python deterministic categorization brain.

Strict Assessment Rule:
Absolutely NO LLM / AI API calls are made at runtime.
All categorization decisions are made by transparent, deterministic heuristics with
verifiable confidence scores and audit trail reasoning strings.
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
    1. Client Revenue / Income Receipts (Money in matching recognized client patterns)
    2. Inter-Account Transfers & Credit Card Payoffs (Non-deductible balance movements)
    3. Refunds and Expense Offsets (Credits applied to original expense categories)
    4. Unverified Credit Deposits (Money in without clear payer -> Needs Review)
    5. Known Merchant Business Expenses (Money out matching tax category rules)
    6. Unknown Merchants / Ambiguities (Routed to Needs Review with confidence 0.0)
    """
    desc = tx.description.strip()
    tx_type = tx.type.strip().lower()
    amount = tx.amount

    # -----------------------------------------------------------------------
    # Stage 1: Client Revenue / Income (Money In with recognized client patterns)
    # -----------------------------------------------------------------------
    if tx_type == "credit":
        income_kw = match_income(desc)
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

    # -----------------------------------------------------------------------
    # Stage 2: Detect Inter-Account Transfers & Card Payments (Non-Deductible)
    # -----------------------------------------------------------------------
    transfer_kw = match_transfer(desc)
    if transfer_kw:
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

    # -----------------------------------------------------------------------
    # Stage 3: Detect Refunds & Expense Offsets
    # -----------------------------------------------------------------------
    refund_kw = match_refund(desc)
    matched_cat, matched_kw = match_merchant(desc)

    # A refund is indicated by explicit refund keywords OR a credit row matching an expense merchant
    if refund_kw or (tx_type == "credit" and matched_cat):
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
                reason=f"Refund/reversal offset credited back to {matched_cat} (merchant '{matched_kw}')",
                needs_review=False,
            )
        else:
            # Explicit refund indicator but merchant is unknown -> must review to assign correct expense offset
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

    # -----------------------------------------------------------------------
    # Stage 4: Unverified Deposits / Inflows (Money in not matching known rules)
    # -----------------------------------------------------------------------
    if tx_type == "credit":
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

    # -----------------------------------------------------------------------
    # Stage 5: Standard Debit Expenses (Money out)
    # -----------------------------------------------------------------------
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
            is_refund=False,
            is_transfer=False,
            confidence=0.90,
            reason=f"Matched merchant '{matched_kw}' for category {matched_cat}",
            needs_review=False,
        )

    # -----------------------------------------------------------------------
    # Stage 6: Safety Fallback - Unknown Merchant / Ambiguous Row
    # -----------------------------------------------------------------------
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
