# Module 3 & Module 4 — Verification, Audit & Quality Report

**Repository:** `muhammadachar435/savvpro-test-statement-categorizer`  
**Branch:** `candidate-muhammadachar435`  
**Date:** 2026-10-26  
**Auditor:** Senior Backend & Test Engineer

---

## 1. Summary & Final Verdict

### Module 3 — Deterministic Categorization Brain: **ACCEPTED**
- The categorization brain in `backend/app/brain/` operates on 100% deterministic, transparent Python regex and keyword heuristics.
- Verified: Zero LLM / external AI API dependencies are imported or called (`openai`, `anthropic`, `google.generativeai`, `langchain`, etc. are strictly absent).
- Verified: Every required canonical category (`Software & Subscriptions`, `Hosting & Cloud Infrastructure`, `Office Supplies & Equipment`, `Travel & Transportation`, `Business Meals (50% Deductible)`, `Client Revenue (Gross Income)`, `Transfers & Card Payments (Non-Deductible)`, and `Needs Review`) is correctly matched using word-boundary protection.
- Verified: Unknown merchants (e.g. `JOES CAFE 9921`) and ambiguous credits/debits route strictly to `Needs Review` with confidence `0.0`.
- Verified: Decimals are strictly preserved without floating-point precision loss.

### Module 4 — API, Summaries, Review Resolution & CSV Export: **ACCEPTED**
- Verified: `/api/upload-statement` enforces the 5 MB file size limit during streaming chunk reads to safeguard server memory.
- Verified: `build_summary` computes exact net operating expenses where refunds offset their respective expense categories instead of inflating totals.
- Verified: Unknown credits in `Needs Review` do **not** increase income; unknown debits do **not** count as deductible expenses.
- Verified: `/api/review-transaction` validates categories against domain constants, updates audit metadata (`manually_edited=True`, `confidence=1.0`), and recalculates summary totals statelessly.
- Verified: `/api/export-statement` neutralizes spreadsheet formula injection (CWE-1236 / OWASP) on untrusted narrative fields while keeping in-memory model instances unmodified.

---

## 2. Files Inspected and Files Changed

### Files Inspected
- `TASK.md` (Assessment specification)
- `README.md` (Setup and repository guide)
- `DESIGN.md` (Domain persona, decision pipeline, and tax accounting model)
- `AI_USAGE.md` (AI tool transparency tracking)
- `backend/app/main.py` (FastAPI app, CORS, root health route)
- `backend/app/core/config.py` (Domain categories, limits, tax rules)
- `backend/app/core/models.py` (Pydantic models with Decimal and date validators)
- `backend/app/parser/csv_parser.py` (CSV parser with encoding and column aliasing)
- `backend/app/brain/rules.py` (Taxonomy patterns)
- `backend/app/brain/engine.py` (6-stage deterministic categorization engine)
- `backend/app/api/routes.py` (FastAPI routes, streaming upload, summary, review, export)
- `backend/tests/test_parser.py` (20 parser unit tests)
- `backend/tests/test_brain.py` (22 categorization unit tests)
- `backend/tests/test_api.py` (15 API integration tests)

### Files Changed
1. `backend/app/brain/rules.py`:
   - Refined `TRANSFER_PATTERNS` to avoid bare `AUTOPAY` and `AUTOMATIC PAYMENT` keywords that previously conflicted with subscription payment descriptions.
2. `backend/app/brain/engine.py`:
   - Enforced strict debit vs credit distinction for refund detection (`is_refund=True` only for inflows with explicit refund indicators).
   - Prevented credits from known vendors lacking refund indicators from blindly becoming refunds; they now route safely to `Needs Review`.
   - Prevented transfer patterns from hijacking legitimate business expenses paid by autopay (e.g. `GITHUB AUTOMATIC PAYMENT`).
3. `backend/app/core/models.py`:
   - Added `errors: List[ParseError] = Field(default_factory=list)` to `StatementResponse` to preserve row-level errors for partial acceptance.
4. `backend/app/api/routes.py`:
   - Updated `build_summary` with mathematically sound net operating expense accounting (`net_expense = max(gross_expense - refunds, 0)`).
   - Prevented unknown credits in `Needs Review` from inflating `total_income`.
   - Added streaming chunk size checks (64 KB chunks) in `upload_statement` to reject uploads exceeding 5 MB with HTTP 413.
   - Added `sanitize_csv_cell` to `generate_statement_csv` to neutralize CSV formula injection (`=`, `+`, `-`, `@`, `\t`, `\r`) without mutating in-memory descriptions.
5. `backend/tests/test_brain.py`:
   - Added 5 focused unit tests covering debit refunds, vendor credits without refund notes, transfer false-positive prevention, canonical spec categories, and confidence score bounds.
6. `backend/tests/test_api.py`:
   - Added 4 integration tests covering financial summary net refund calculations, unknown credit isolation, CSV formula injection defense, streaming size rejection (413), and header-only statement rejection (400).
7. `DESIGN.md`:
   - Updated the decision pipeline diagram, financial summary accounting definitions, and security specifications.

---

## 3. Confirmed Bugs, Impact, and Fixes

| # | Bug Description | Severity | Impact | Fix Applied |
|---|---|---|---|---|
| **1** | **Debit with word "REFUND" marked as `is_refund=True`** | High | Outflow fees (e.g. `AIRLINE TICKET REFUND PROCESSING FEE` -$15.00) were classified as incoming refunds and deducted from category spending. | Refactored `engine.py` so `is_refund=True` is only assigned when `tx.type == "credit"`. Debits mentioning refunds are classified as regular debit expenses or routed to `Needs Review`. |
| **2** | **Unknown Credits added to `total_income`** | Critical | In `routes.py`, `elif tx.category == CATEGORY_INCOME or tx.type == "credit"` caused unverified deposits (e.g. $500 miscellaneous credit) to be added to taxable gross income. | Removed `or tx.type == "credit"`. Only transactions explicitly confirmed as `CATEGORY_INCOME` are included in `total_income`. Unknown credits remain in `Needs Review` with 0 income impact. |
| **3** | **Refunds did not offset Category Net Totals in Summary** | High | `cat_totals[tx.category] += tx_amt` added refund amounts to category totals as positive spending rather than offsetting them. | Implemented net category expense computation: `net_amt = max(gross_debits - refund_offsets, Decimal("0.00"))`. Tax deductible estimates use this net amount. |
| **4** | **Unreviewed transactions counted in Net Operating Expenses** | Medium | Unreviewed debit entries (`Needs Review`) were previously lumped into `total_expenses`. | Confined `total_expenses` to confirmed business expense categories. `Needs Review` items are reported in the category breakdown with `deductible_estimate = $0.00` until confirmed by user. |
| **5** | **Autopay business subscriptions hijacked by Transfer rule** | Medium | Bare `\bAUTOPAY\b` pattern in `rules.py` caused `GITHUB AUTOMATIC PAYMENT` and `UBER AUTOPAY` to be categorized as non-deductible transfers. | Refined transfer patterns to require debt payoff context (`AUTOMATIC PAYMENT - THANK YOU`, `CREDIT CARD AUTOPAY`, etc.) and prioritized merchant matches in `engine.py`. |
| **6** | **Unbounded Upload In-Memory Buffering** | Medium | `await file.read()` read entire uploads into memory before checking file size. | Replaced with 64 KB streaming chunk evaluation that halts reading and returns HTTP 413 if accumulated bytes exceed 5 MB. |
| **7** | **CSV Formula Injection (CWE-1236)** | Medium | Descriptions starting with `=`, `+`, `-`, `@`, including those preceded by whitespace or control characters (`\t`, `\r`, `\n`), could execute formulas when exported CSV was opened in spreadsheet tools. | Added OWASP formula escaping (`'`) during CSV serialization for any untrusted text starting with or, after stripping whitespace, beginning with triggers, without altering source in-memory data. |

---

## 4. Important Accounting Decisions & Refund-Handling Behavior

1. **Refunds as Expense Offsets, Not Income**:
   - In business tax reporting (IRS Schedule C), a refund returned from an expense vendor (e.g. Adobe refunding $20 for a canceled subscription) is not taxable gross revenue.
   - It is an expense reversal that reduces the deductible expense of that specific category:
     $$\text{Net Software Expense} = \$100.00 - \$20.00 = \$80.00$$
2. **Gross Revenue vs. Unverified Deposits**:
   - Only recognized client revenue receipts (Stripe payouts, Upwork payouts, client wire transfers, direct invoicing) count as `total_income`.
   - Miscellaneous or unverified deposits route to `Needs Review` and do **not** inflate taxable income.
3. **Inter-Account Transfers & Credit Card Payoffs**:
   - Money moved from checking to savings or payments toward credit card balances are non-deductible balance movements. They are isolated in `total_transfers` and excluded from income and expenses.
4. **Business Meals 50% Rule**:
   - Business meals (Starbucks, Chipotle, Panera meetings) are tracked at 100% of their transaction value, but `deductible_estimate` computes exactly 50% per IRS regulations.

---

## 5. Test Suite Verification & Actual Terminal Results

### Full Pytest Run Command:
```powershell
cd backend; $env:PYTHONPATH="."; & ".\.venv\Scripts\pytest.exe" -v
```

### Actual Output:
```
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.7.0 -- E:\savv PRO\savvpro-test-statement-categorizer\backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\savv PRO\savvpro-test-statement-categorizer\backend
plugins: anyio-4.15.1
collecting ... collected 57 items

tests/test_api.py::test_health_root PASSED                               [  1%]
tests/test_api.py::test_get_categories PASSED                            [  3%]
tests/test_api.py::test_load_sample_statement PASSED                     [  5%]
tests/test_api.py::test_manual_review_resolution PASSED                  [  7%]
tests/test_api.py::test_review_transaction_invalid_category PASSED       [  8%]
tests/test_api.py::test_upload_valid_csv PASSED                          [ 10%]
tests/test_api.py::test_upload_non_csv_rejected PASSED                   [ 12%]
tests/test_api.py::test_upload_empty_csv_rejected PASSED                 [ 14%]
tests/test_api.py::test_export_statement_csv PASSED                      [ 15%]
tests/test_api.py::test_export_statement_empty_fails PASSED              [ 17%]
tests/test_api.py::test_export_sample_statement PASSED                   [ 19%]
tests/test_api.py::test_financial_summary_regression_net_refund_and_unknown_credit PASSED [ 21%]
tests/test_api.py::test_export_csv_formula_injection_defense PASSED      [ 22%]
tests/test_api.py::test_upload_header_only_file_rejected PASSED          [ 24%]
tests/test_api.py::test_upload_streaming_size_limit_rejected PASSED      [ 26%]
tests/test_brain.py::test_software_subscriptions PASSED                  [ 28%]
tests/test_brain.py::test_cloud_hosting PASSED                           [ 29%]
tests/test_brain.py::test_office_equipment PASSED                        [ 31%]
tests/test_brain.py::test_travel_expenses PASSED                         [ 33%]
tests/test_brain.py::test_business_meals PASSED                          [ 35%]
tests/test_brain.py::test_client_revenue PASSED                          [ 36%]
tests/test_brain.py::test_transfers_and_debt_payments PASSED             [ 38%]
tests/test_brain.py::test_refunds_credited_to_original_expense_category PASSED [ 40%]
tests/test_brain.py::test_ambiguous_refund_routes_to_needs_review PASSED [ 42%]
tests/test_brain.py::test_joes_cafe_routes_to_needs_review PASSED        [ 43%]
tests/test_brain.py::test_local_vendor_routes_to_needs_review PASSED     [ 45%]
tests/test_brain.py::test_unverified_credit_routes_to_needs_review PASSED [ 47%]
tests/test_brain.py::test_word_boundary_safety PASSED                    [ 49%]
tests/test_brain.py::test_categorize_statement_batch PASSED              [ 50%]
tests/test_brain.py::test_decimal_preservation PASSED                    [ 52%]
tests/test_brain.py::test_adobe_refund_exact_from_spec PASSED            [ 54%]
tests/test_brain.py::test_float_input_does_not_corrupt_decimal PASSED    [ 56%]
tests/test_brain.py::test_debit_with_refund_word_not_marked_as_incoming_refund PASSED [ 57%]
tests/test_brain.py::test_credit_from_merchant_without_refund_keyword_routes_to_needs_review PASSED [ 59%]
tests/test_brain.py::test_transfer_false_positives_do_not_hijack_business_expenses PASSED [ 61%]
tests/test_brain.py::test_all_required_spec_categories PASSED            [ 63%]
tests/test_brain.py::test_confidence_bounds_and_reason_strings PASSED    [ 64%]
tests/test_parser.py::test_valid_csv_standard_columns PASSED             [ 66%]
tests/test_parser.py::test_alternative_recognized_column_names PASSED    [ 68%]
tests/test_parser.py::test_utf8_bom PASSED                               [ 70%]
tests/test_parser.py::test_quoted_descriptions_with_commas PASSED        [ 71%]
tests/test_parser.py::test_whitespace_and_case_normalization_in_headers PASSED [ 73%]
tests/test_parser.py::test_common_supported_date_formats PASSED          [ 75%]
tests/test_parser.py::test_signed_and_decimal_amounts PASSED             [ 77%]
tests/test_parser.py::test_separate_debit_credit_columns PASSED          [ 78%]
tests/test_parser.py::test_missing_required_columns PASSED               [ 80%]
tests/test_parser.py::test_invalid_amount_values PASSED                  [ 82%]
tests/test_parser.py::test_non_finite_amounts PASSED                     [ 84%]
tests/test_parser.py::test_invalid_dates PASSED                          [ 85%]
tests/test_parser.py::test_empty_files PASSED                            [ 87%]
tests/test_parser.py::test_headers_with_no_transactions PASSED           [ 89%]
tests/test_parser.py::test_blank_descriptions PASSED                     [ 91%]
tests/test_parser.py::test_malformed_csv_rows PASSED                     [ 92%]
tests/test_parser.py::test_duplicate_or_ambiguous_columns PASSED         [ 94%]
tests/test_parser.py::test_blank_rows_handling PASSED                    [ 96%]
tests/test_parser.py::test_oversized_uploads_and_excessive_rows PASSED   [ 98%]
tests/test_parser.py::test_correct_row_numbers_in_validation_errors PASSED [100%]

======================== 57 passed, 1 warning in 1.78s ========================
```

---

## 6. Remaining Risks & Limitations

1. **Stateless Manual Review**:
   - The application does not currently connect to a persistent database. Manual review changes are held in client state and passed back to the server for recalculation. If the browser page is refreshed without saving the exported CSV, the session state resets.
2. **Generic Word Fallbacks**:
   - Generic merchant terms (such as `CAFE`, `BISTRO`, `DELI`) are deliberately omitted from the meal rules. While this causes local coffee shops (like `JOES CAFE 9921`) to require manual review, it prevents false positive tax deductions.
3. **Single Currency Model**:
   - Currency is standardized to USD. Multi-currency conversions with fluctuating exchange rates are not currently performed.

---

## 7. Manual Steps to Verify Frontend Integration

When building or testing the React frontend in Module 5:
1. **Health & Categories**: Verify the frontend fetches `GET /api/categories` on mount to populate the category dropdown filters.
2. **Synthetic Demo Button**: Click "Load Sample Statement" to fetch `GET /api/sample-statement` and confirm:
   - 18 synthetic transactions render.
   - Summary cards show Gross Income ($5,650.00), Net Expenses ($683.48), Refunds ($72.50), Transfers ($1,500.00), and Needs Review (4 items).
3. **Manual Review Dropdown**: For row 11 (`JOES CAFE 9921`), select "Business Meals (50% Deductible)" and observe:
   - Row updates to `Business Meals` with `Needs Review = False` and `Manually Edited = True`.
   - Needs Review badge decreases from 4 to 3.
   - Business Meals category total and 50% deductible estimate increase live.
4. **Export CSV**: Click "Export CSV" to trigger `POST /api/export-statement`, open the downloaded file in Excel, and verify formatted columns, net totals, and formula safety.

---

## 8. Compliance with Official `TASK.md`

| Requirement from `TASK.md` | Status | Implementation Evidence |
|---|---|---|
| Read each transaction and decide its category | Compliant | Deterministic pipeline in `app/brain/engine.py` |
| "The brain must be your own code. Do not use a big AI model (GPT, Claude, Gemini)" | Compliant | 100% pure Python regex and heuristics. 0 LLM runtime imports. |
| Pick a persona and use case | Compliant | Freelance Tech Consultant / Designer tax preparation |
| "ADOBE CREATIVE CLOUD becomes Software" | Compliant | Tested in `test_all_required_spec_categories` |
| "UBER *TRIP becomes Travel" | Compliant | Tested in `test_all_required_spec_categories` |
| "TRANSFER TO SAVINGS is not spending" | Compliant | Flagged `is_transfer=True`, non-deductible balance movement |
| "JOES CAFE 9921 is unknown, so it goes to Needs Review" | Compliant | Safety fallback sets `confidence=0.0`, `needs_review=True` |
| "A refund is money back, not income" | Compliant | Credits with refund keywords offset expense categories, 0 income impact |
| Total for each category and review queue | Compliant | `StatementSummary` with `CategorySummary` and `ReviewUpdateRequest` |
| Fake data only, no real bank details | Compliant | Synthetic sample dataset in `backend/data/sample_statement.csv` |
| Automated test suite | Compliant | 57 automated tests covering parser, brain, and API endpoints |
