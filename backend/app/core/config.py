"""Application configuration, parsing limits, and domain tax categories."""
from typing import List, Dict

APP_NAME = "Statement Categorizer - Freelance Consultant Edition"
APP_VERSION = "0.1.0"
DEBUG = True

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

# ---------------------------------------------------------------------------
# Module 2 Parsing & Upload Constraints
# ---------------------------------------------------------------------------

# Maximum file upload size: 5 Megabytes
MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024

# Maximum transaction data rows per statement to prevent denial-of-service
MAX_TRANSACTION_ROWS: int = 10_000

# Default ISO currency when not explicitly present in the source CSV
DEFAULT_CURRENCY: str = "USD"

# Encodings to attempt in order (handles standard UTF-8 and Excel UTF-8 BOM)
ACCEPTED_ENCODINGS: List[str] = [
    "utf-8-sig",  # UTF-8 with Byte Order Mark (BOM)
    "utf-8",      # Standard UTF-8
    "latin-1",    # Western European fallback
]

# Common explicitly documented calendar date formats supported by the parser
SUPPORTED_DATE_FORMATS: List[str] = [
    "%Y-%m-%d",   # 2026-03-01 (ISO 8601 standard)
    "%Y/%m/%d",   # 2026/03/01
    "%m/%d/%Y",   # 03/01/2026 (US banking standard)
    "%m-%d-%Y",   # 03-01-2026
    "%d/%m/%Y",   # 01/03/2026 (International standard)
    "%d-%m-%Y",   # 01-03-2026
    "%Y%m%d",     # 20260301 (Compact banking format)
    "%b %d, %Y",  # Mar 01, 2026
    "%B %d, %Y",  # March 01, 2026
    "%b %d %Y",   # Mar 01 2026
    "%d %b %Y",   # 01 Mar 2026
]


# ---------------------------------------------------------------------------
# Module 3 Categorization Taxonomy for Freelance Tech Consultant Persona
# ---------------------------------------------------------------------------

CATEGORY_SOFTWARE = "Software & Subscriptions"
CATEGORY_HOSTING = "Hosting & Cloud Infrastructure"
CATEGORY_EQUIPMENT = "Office Supplies & Equipment"
CATEGORY_TRAVEL = "Travel & Transportation"
CATEGORY_MEALS = "Business Meals (50% Deductible)"
CATEGORY_INCOME = "Client Revenue (Gross Income)"
CATEGORY_TRANSFER = "Transfers & Card Payments (Non-Deductible)"
CATEGORY_NEEDS_REVIEW = "Needs Review"

ALL_CATEGORIES: List[str] = [
    CATEGORY_SOFTWARE,
    CATEGORY_HOSTING,
    CATEGORY_EQUIPMENT,
    CATEGORY_TRAVEL,
    CATEGORY_MEALS,
    CATEGORY_INCOME,
    CATEGORY_TRANSFER,
    CATEGORY_NEEDS_REVIEW,
]

TAX_RULES: Dict[str, Dict[str, str]] = {
    CATEGORY_SOFTWARE: {"deductible": "100%", "type": "expense"},
    CATEGORY_HOSTING: {"deductible": "100%", "type": "expense"},
    CATEGORY_EQUIPMENT: {"deductible": "100%", "type": "expense"},
    CATEGORY_TRAVEL: {"deductible": "100%", "type": "expense"},
    CATEGORY_MEALS: {"deductible": "50%", "type": "expense"},
    CATEGORY_INCOME: {"deductible": "0%", "type": "income"},
    CATEGORY_TRANSFER: {"deductible": "0%", "type": "transfer"},
    CATEGORY_NEEDS_REVIEW: {"deductible": "0%", "type": "unclassified"},
}
