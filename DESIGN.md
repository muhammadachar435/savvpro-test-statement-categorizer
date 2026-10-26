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

Per the core requirement, **no large AI model is used at runtime to make categorization decisions**. All logic is transparent, explainable, and reproducible in pure Python.

### Decision Pipeline Architecture

```
                       Raw Transaction
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
       [Inflow (Credit)]             [Outflow (Debit)]
               │                             │
   1. Client Revenue Pattern?        1. Transfer/Card Payoff?
      ├─ Yes ──► Client Revenue         ├─ Yes (no merchant) ──► Transfer
      └─ No                             └─ No
         │                                 │
   2. Transfer In Pattern?           2. Known Merchant Expense?
      ├─ Yes ──► Transfer               ├─ Yes (has refund note) ──► Expense (Fee)
      └─ No                             ├─ Yes (regular) ──────────► Expense
         │                              └─ No
   3. Refund/Return Indicator?             │
      ├─ Yes + Merchant ──► Refund   3. Debit mentions return/refund?
      ├─ Yes (no merch) ──► Review      ├─ Yes ──► Needs Review
      └─ No                             └─ No
         │                                 │
   4. Vendor without refund note?    4. Safety Fallback:
      ├─ Yes ──► Needs Review           └── Unknown Merchant ──► Needs Review
      └─ No                                 (e.g., JOES CAFE 9921, conf: 0.0)
         │
   5. Unverified Deposit?
      └── Yes ──► Needs Review
```

### Safety Principle: "A wrong guess is worse than asking"
When an unrecognized or ambiguous merchant appears, the system sets `confidence = 0.0`, assigns `category = "Needs Review"`, and flags `needs_review = True`. The user resolves these via the review queue.

---

## 3. Financial & Tax Deductibility Accounting Model

### Exact Definitions

1. **Gross Revenue (`total_income`)**:
   - Strictly computed from transactions categorized as `Client Revenue (Gross Income)`.
   - Unknown credits (`Needs Review`) are quarantined and do **not** automatically inflate taxable income.

2. **Total Refunds (`total_refunds`)**:
   - Sum of all incoming credits confirmed as refunds/reversals (`is_refund = True`).
   - Refunds are treated as expense offsets, not new income.

3. **Net Operating Expenses (`total_expenses`)**:
   - For each recognized business expense category:
     $$\text{Net Category Expense} = \max(\text{Gross Category Expenses} - \text{Category Refunds}, 0)$$
   - Total Net Expenses is the sum of net expenses across all active business expense categories.
   - Unreviewed transactions (`Needs Review`) do **not** count as deductible expenses until verified.

4. **Transfers (`total_transfers`)**:
   - Non-deductible balance movements between accounts or credit card balance payoffs.
   - Excluded from both income and operating expense totals.

5. **Tax Deductible Estimate (`deductible_estimate`)**:
   - Computed per category by multiplying the net category expense by its statutory tax deductibility percentage.

### Tax Category Rules Table

| Category | Typical Tax Deductibility | Financial Flow Impact |
| :--- | :--- | :--- |
| **Software & Subscriptions** | 100% | Operating Expense |
| **Hosting & Cloud Infrastructure** | 100% | Operating Expense |
| **Office Supplies & Equipment** | 100% | Operating Expense / Depreciation |
| **Travel & Transportation** | 100% | Operating Expense |
| **Business Meals** | 50% | Operating Expense (50% rule) |
| **Client Revenue** | 0% (Taxable Gross Income) | Income |
| **Transfers & Card Payments** | Non-Deductible | Balance Movement |
| **Needs Review** | Pending user classification (0%) | Quarantined / Unclassified |

---

## 4. Confidence Scores and Explanations

Confidence values are deterministic heuristic weights $[0.0, 1.0]$ denoting rule specificity and evidentiary clarity:
* `0.98`: Explicit inter-account transfer and credit card payoff patterns.
* `0.95`: Confirmed client invoice and payment processor payout patterns.
* `0.92`: Confirmed refund matching an explicit expense category merchant.
* `0.90`: Known business merchant matching taxonomy word boundaries.
* `0.45`: Explicit refund/reversal indicator, but original merchant unknown.
* `0.35`: Credit from vendor without explicit refund or income indicators.
* `0.30`: Unverified credit deposit with no known source pattern.
* `0.00`: Unrecognized debit merchant or description (e.g. `JOES CAFE 9921`).

These values represent deterministic rule confidence, not statistically calibrated machine learning probabilities.

---

## 5. Security & CSV Formula Injection Defense

Exported CSV statements are protected against spreadsheet formula injection (CWE-1236):
* Any exported cell whose text starts with `=`, `+`, `-`, `@`, `\t`, or `\r` is automatically neutralized by prefixing with `'`.
* The in-memory Python transaction records are preserved without mutation.
