"""Deterministic rule taxonomy and keyword patterns for the Freelance Consultant persona.

This module defines transparent, deterministic matching tables.
Strict Rule: No large language models (LLMs) or external AI services are used at runtime.
"""
import re
from typing import Dict, List, Pattern, Tuple
from app.core.config import (
    CATEGORY_SOFTWARE,
    CATEGORY_HOSTING,
    CATEGORY_EQUIPMENT,
    CATEGORY_TRAVEL,
    CATEGORY_MEALS,
    CATEGORY_INCOME,
    CATEGORY_TRANSFER,
)

# ---------------------------------------------------------------------------
# Inter-account balance transfers & credit card payments (Non-deductible)
#
# NOTE: Broad keywords like bare "AUTOPAY" or "AUTOMATIC PAYMENT" are avoided
# to prevent false positive hijacking of legitimate business subscriptions
# (e.g. "GITHUB AUTOMATIC PAYMENT", "UBER AUTOPAY BILLING").
# Patterns require explicit inter-account or credit card debt payoff context.
# ---------------------------------------------------------------------------
TRANSFER_PATTERNS: List[str] = [
    r"\bTRANSFER TO SAVINGS\b",
    r"\bTRANSFER TO CHECKING\b",
    r"\bTRANSFER FROM SAVINGS\b",
    r"\bTRANSFER FROM CHECKING\b",
    r"\bONLINE TRANSFER TO\b",
    r"\bONLINE TRANSFER FROM\b",
    r"\bONLINE TRANSFER\b",
    r"\bINTERNAL TRANSFER\b",
    r"\bINTERNAL XFER\b",
    r"\b(?:AUTOMATIC PAYMENT|AUTOPAY)\s*-\s*THANK YOU\b",
    r"\bPAYMENT THANK YOU\b",
    r"\bPAYMENT - THANK YOU\b",
    r"\bCREDIT CARD PAYMENT\b",
    r"\bCREDIT CARD AUTOPAY\b",
    r"\bCREDIT CARD PAYOFF\b",
    r"\bCHASE CARD AUTOPAY\b",
    r"\bCHASE CARD EPAYMENT\b",
    r"\bAMEX EPAYMENT\b",
    r"\bCAPITAL ONE PMT\b",
    r"\bCITI CARD PAYMENT\b",
    r"\bDISCOVER E-PAYMENT\b",
    r"\bAUTOPAY (?:PAYMENT|AMEX|CHASE|CITI|DISCOVER|CAPITAL ONE|CARD|EPAYMENT)\b",
    r"\bAUTOMATIC PAYMENT - THANK YOU CHASE CARD\b",
]

# ---------------------------------------------------------------------------
# Refunds and expense returns (Expense offset, NOT taxable revenue)
# ---------------------------------------------------------------------------
REFUND_PATTERNS: List[str] = [
    r"\bREFUND\b",
    r"\bRETURN\b",
    r"\bREVERSAL\b",
    r"\bDISPUTE ADJUSTMENT\b",
    r"\bPRO-RATA\b",
    r"\bCHARGEBACK\b",
    r"\bCREDIT ADJUSTMENT\b",
]

# ---------------------------------------------------------------------------
# Client revenue receipts (Taxable gross income)
# ---------------------------------------------------------------------------
INCOME_PATTERNS: List[str] = [
    r"\bSTRIPE PAYOUT\b",
    r"\bSTRIPE\b",
    r"\bWIRE TRANSFER FROM\b",
    r"\bDIRECT DEPOSIT\b",
    r"\bCLIENT INVOICE\b",
    r"\bUPWORK ESCROW\b",
    r"\bUPWORK\b",
    r"\bINVOICE PAYMENT\b",
    r"\bPAYPAL TRANSFER IN\b",
    r"\bCONSULTING FEE\b",
    r"\bACH CREDIT CLIENT\b",
    r"\bFIVERR PAYOUT\b",
]

# ---------------------------------------------------------------------------
# Merchant expense categories for Freelance Tech Consultant / Designer
# ---------------------------------------------------------------------------
MERCHANT_CATEGORY_RULES: Dict[str, List[str]] = {
    CATEGORY_SOFTWARE: [
        r"\bADOBE\b",
        r"\bGITHUB\b",
        r"\bZOOM(\.US)?\b",
        r"\bJETBRAINS\b",
        r"\bNOTION\b",
        r"\bFIGMA\b",
        r"\bSLACK\b",
        r"\bGOOGLE \*WORKSPACE\b",
        r"\bGOOGLE WORKSPACE\b",
        r"\bMICROSOFT 365\b",
        r"\bMSFT \*365\b",
        r"\bDROPBOX\b",
        r"\bCANVA\b",
        r"\b1PASSWORD\b",
        r"\bATLASSIAN\b",
        r"\bJIRA\b",
        r"\bTRELLO\b",
        r"\bPOSTMAN\b",
        r"\bOPENAI API\b",
        r"\bANTHROPIC API\b",
    ],
    CATEGORY_HOSTING: [
        r"\bAWS\b",
        r"\bAMAZON WEB SERVICES\b",
        r"\bDIGITALOCEAN\b",
        r"\bVERCEL\b",
        r"\bNETLIFY\b",
        r"\bHEROKU\b",
        r"\bCLOUDFLARE\b",
        r"\bLINODE\b",
        r"\bDATADOG\b",
        r"\bMONGODB ATLAS\b",
        r"\bSUPABASE\b",
        r"\bRENDER\.COM\b",
    ],
    CATEGORY_EQUIPMENT: [
        r"\bOFFICE DEPOT\b",
        r"\bBEST BUY\b",
        r"\bAPPLE STORE\b",
        r"\bB&H PHOTO\b",
        r"\bSTAPLES\b",
        r"\bMICRO CENTER\b",
        r"\bAMAZON MKTPLACE\b",
        r"\bAMAZON MARKETPLACE\b",
        r"\bLOGITECH\b",
        r"\bDELL DIRECT\b",
        r"\bKEYCHRON\b",
    ],
    CATEGORY_TRAVEL: [
        r"\bUBER\b",
        r"\bLYFT\b",
        r"\bDELTA AIR\b",
        r"\bUNITED AIRLINES\b",
        r"\bAMERICAN AIRLINES\b",
        r"\bAIRBNB\b",
        r"\bAMTRAK\b",
        r"\bHERTZ\b",
        r"\bHOTEL\b",
        r"\bSHELL OIL\b",
        r"\bCHEVRON\b",
        r"\bPARKING\b",
        r"\bYELLOW CAB\b",
    ],
    # Explicit known business meeting meal chains (50% tax deductible).
    # NOTE: Generic words like "CAFE", "BISTRO", "RESTAURANT" are strictly excluded
    # so unverified local spots like "JOES CAFE 9921" correctly route to Needs Review.
    CATEGORY_MEALS: [
        r"\bSTARBUCKS\b",
        r"\bCHIPOTLE\b",
        r"\bSWEETGREEN\b",
        r"\bPANERA\b",
        r"\bPRET A MANGER\b",
    ],
}


def compile_pattern_dict() -> Dict[str, List[Tuple[Pattern, str]]]:
    """Pre-compile regex patterns for high-performance matching."""
    compiled: Dict[str, List[Tuple[Pattern, str]]] = {}
    for cat, patterns in MERCHANT_CATEGORY_RULES.items():
        compiled[cat] = [
            (re.compile(p, re.IGNORECASE), p.replace(r"\b", "").replace(r"(\.US)?", "").replace(r"\.", ".").replace(r"\*", "*"))
            for p in patterns
        ]
    return compiled


COMPILED_MERCHANT_RULES = compile_pattern_dict()
COMPILED_TRANSFER_PATTERNS = [(re.compile(p, re.IGNORECASE), p.replace(r"\b", "")) for p in TRANSFER_PATTERNS]
COMPILED_REFUND_PATTERNS = [(re.compile(p, re.IGNORECASE), p.replace(r"\b", "")) for p in REFUND_PATTERNS]
COMPILED_INCOME_PATTERNS = [(re.compile(p, re.IGNORECASE), p.replace(r"\b", "")) for p in INCOME_PATTERNS]
