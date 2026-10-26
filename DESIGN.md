# DESIGN: Statement Categorizer Architecture

## 1. Selected Persona: Freelance Tech Consultant / Digital Designer

### The Real-World Tax Problem
Freelance technology consultants, software engineers, and digital designers frequently deal with a mix of:
* Recurring software SaaS subscriptions (Adobe, GitHub, JetBrains, Figma, Zoom).
* Cloud hosting and infrastructure costs (AWS, DigitalOcean, Vercel).
* Equipment and electronics (hardware purchases from Apple, Best Buy, Office Depot).
* Travel and local transportation for client meetings (Uber, Lyft, airlines).
* Business meals (client lunches, coffee discussions) which have specific 50% tax deductibility rules.
* Client revenue payouts (Stripe payouts, wire transfers, direct invoices).
* Non-deductible personal-to-business transfers and credit card payments.
* Refunds from returned hardware or canceled software plans.
* Ambiguous merchant entries on bank feeds (e.g., `JOES CAFE 9921`, `SQ *LOCAL VENDOR 339`).

At tax preparation time (e.g., IRS Schedule C), miscategorizing a refund as taxable income inflates tax liability, while claiming a credit card balance transfer as a deductible business expense triggers audit penalties.

---

## 2. "The Brain": Pure Deterministic Heuristics (Zero LLM Runtime)

Per the core requirement, **no large AI model is used at runtime to make categorization decisions**. All logic is transparent, explainable, and reproducible in Python.

### 5-Stage Decision Pipeline

```
Raw Transaction
      │
      ▼
[Stage 1: Inter-Account Transfer & Debt Check]
  ├── Matches Transfer/Autopay/Card keywords? ──► CATEGORY_TRANSFER (is_transfer=True, Non-deductible)
      │ No
      ▼
[Stage 2: Refund & Return Detection]
  ├── Contains 'REFUND' / 'RETURN' or (Credit + Matched Expense)? ──► Original Category (is_refund=True, Expense Offset)
      │ No
      ▼
[Stage 3: Client Revenue / Income Detection]
  ├── Type == 'credit' and matches Income patterns? ──► CATEGORY_INCOME (Gross Revenue)
  ├── Type == 'credit' but unmatched? ───────────────► CATEGORY_NEEDS_REVIEW (Unverified credit)
      │ No (Type == 'debit')
      ▼
[Stage 4: Merchant Pattern Matching]
  ├── Matches specific Software, Hosting, Equipment, Travel, or Meals rules? ──► Matched Category
      │ No
      ▼
[Stage 5: Safety Fallback - Needs Review]
  └── Low confidence / Ambiguous (e.g., JOES CAFE 9921) ───────────► CATEGORY_NEEDS_REVIEW (User Must Confirm)
```

### Safety Principle: "A wrong guess is worse than asking"
When an unrecognized or ambiguous merchant appears, the system sets `confidence = 0.0`, assigns `category = "Needs Review"`, and flags `needs_review = True`. The user resolves these via the frontend review queue.

---

## 3. Financial & Tax Deductibility Model

| Category | Typical Tax Deductibility | Financial Flow Impact |
| :--- | :--- | :--- |
| **Software & Subscriptions** | 100% | Operating Expense |
| **Hosting & Cloud Infrastructure** | 100% | Operating Expense |
| **Office Supplies & Equipment** | 100% | Operating Expense / Depreciation |
| **Travel & Transportation** | 100% | Operating Expense |
| **Business Meals** | 50% | Operating Expense (50% rule) |
| **Client Revenue** | 0% (Taxable Gross Income) | Income |
| **Transfers & Card Payments** | Non-Deductible | Balance Movement |
| **Needs Review** | Pending user classification | Unclassified |
