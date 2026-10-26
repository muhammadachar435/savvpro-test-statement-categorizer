# AI Usage Log & Transparency Report

This document records the AI tools used during the development of the Statement Categorizer, following the requirements in `TASK.md`.

---

## 1. AI Tools Utilized
* **AI Tool / Assistant:** Google DeepMind Antigravity IDE (Gemini 3.8 Flash model).
* **Role:** Architectural analysis, boilerplate scaffolding, deterministic heuristic engine design, and test suite formulation.

---

## 2. How the AI Helped
* **Repository & Dependency Audit:** Rapidly identified host runtime versions (Python 3.14.6, Node.js 24.13.0) and uncovered Windows-specific SSL environment quirks (`CURL_CA_BUNDLE` referencing missing PostgreSQL certificate bundles).
* **Deterministic Rule Architecture:** Formulated clear regular expression and keyword patterns for bank statement classification without using LLMs at runtime.
* **Test Generation:** Authored comprehensive unit and integration tests covering tricky edge cases (expense refunds, inter-account transfers, unknown merchants, and malformed CSV rows).

---

## 3. Where the AI Got Things Wrong / Required Course Correction
* **Overly Broad Merchant Matching (Initial Heuristic):**
  * *Issue:* A draft rule for meals included the generic keyword `"CAFE"`. This caused `JOES CAFE 9921` to be automatically categorized as Business Meals.
  * *Correction:* `TASK.md` explicitly specifies that `JOES CAFE 9921` is unknown and must route to **Needs Review**. The generic `"CAFE"` and `"BISTRO"` keywords were removed to prevent false positive matches and ensure unverified merchants always require user confirmation.
* **Windows Host TLS Certificate Conflict:**
  * *Issue:* Pip initially failed due to an OS-level environment variable `CURL_CA_BUNDLE` pointing to a missing PostgreSQL certificate bundle.
  * *Correction:* Identified and cleared the environment variable during virtual environment setup.

---

## 4. Token & Tool Usage Tracking
* **Development Phase:** Module 1 (Audit & Architecture) and Module 2 (Scaffolding & Engine Foundation).
* **Estimated Interaction Stats:**
  * Model: Gemini 3.8 Flash
  * Total Prompt Tokens: ~45,000 tokens
  * Total Completion Tokens: ~8,500 tokens
  * Local Tests Executed & Passed: 13/13 backend tests
