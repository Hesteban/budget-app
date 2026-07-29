# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project Overview

A Streamlit-based shared expense tracker for two users (Laerke and Hector). It imports bank statements, categorizes transactions, calculates 50/50 settlements, and generates AI-powered monthly spending summaries using OpenAI Agents.

## Commands

### Setup
```bash
# The project uses a pyenv virtualenv named .venv (linked to .venv/ in this repo)
# Prefer the venv activation when pyenv shell integration is not enabled:
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-test.txt  # for testing
```

### Run the app
```bash
# Production (requires Supabase + auth secrets):
streamlit run main.py

# Test mode (auto-login as Hector, in-memory data, no secrets needed):
APP_ENV=test streamlit run main.py
```

### Tests
Ensure the `.venv` pyenv virtualenv is active before running any test command. If `pyenv shell .venv` is unavailable (pyenv shell integration not enabled), use `source .venv/bin/activate`. Otherwise `pytest` resolves to the base interpreter which is missing all packages.

```bash
# All unit tests
source .venv/bin/activate && APP_ENV=test pytest tests/unittests/ -v

# Single test file
source .venv/bin/activate && APP_ENV=test pytest tests/unittests/test_calculator.py -v

# E2E tests (requires Streamlit server running in another terminal)
source .venv/bin/activate && APP_ENV=test pytest tests/e2e/ -v -m e2e
```

Run e2e tests whenever a Streamlit page is added or changed — unit tests only cover business logic and won't catch UI-level regressions. Start the app in test mode in one terminal, then run the e2e suite in another.

## Architecture

### Repository pattern (`budget/db.py`)
All data access goes through module-level functions in `budget/db.py` (e.g., `get_transactions()`, `upsert_transactions()`). These delegate to the active repository returned by `get_repo()`:
- `SupabaseRepository` — production, requires `.streamlit/secrets.toml`
- `FakeRepository` (`budget/fake_repository.py`) — in-memory, activated by `APP_ENV=test`

Pages and the calculator never instantiate repositories directly. The `BudgetRepository` protocol in `budget/budget_repository.py` defines the interface both implementations must satisfy.

### Settlement engine (`budget/calculator.py`)
`calculate_settlement(month, year)` sums each user's common + fixed expenses, divides by 2 for fair share, and computes who owes whom. `ensure_month_exists()` is idempotent — safe to call before any upsert.

### Bank importer (`budget/importer.py`)
Auto-detects two CSV/Excel export formats ("account" and "card") from a Spanish bank. Handles European number formats (comma decimals, period thousands). `parse_bank_file()` filters to a single month; `parse_bank_file_bulk()` derives month/year from transaction dates for multi-month imports. Deduplicates on `(user, date, description, amount, source)`.

### AI agents (`budget/agents/`)
- `ai_categorizer.py` — Classifies transactions as `personal`, `common`, `covered`, or `uncategorized` using few-shot prompting. Only auto-applies if confidence ≥ 85%.
- `ai_summarizer.py` — Generates a Markdown narrative summary of monthly spending with 5 key observations.

### Streamlit pages
| Page | Purpose |
|------|---------|
| `main.py` | Auth (bcrypt password), home overview, test-mode auto-login |
| `pages/1_📤_Upload.py` | Single-month and bulk bank file import |
| `pages/2_💳_Transactions.py` | Browse/edit categories, bulk AI categorization |
| `pages/3_🔁_Fixed_Expenses.py` | CRUD for recurring expenses per user |
| `pages/4_📊_Summary.py` | Settlement display, category breakdown, trend chart |

### Database schema
```
transactions    — (user, date, description, amount, source, category, reasoning)
fixed_expenses  — (user, name, amount, active)
monthly_summary — (month, year, per-user totals, balance, who_pays_whom)
monthly_reports — (month, year, content, generated_at)
```
Unique constraints: transactions on `(user, date, description, amount, source)`, monthly_summary on `(month, year)`.

### Test infrastructure
`tests/conftest.py` provides pytest fixtures that inject a fresh `FakeRepository` with March 2026 seed data (defined in `tests/seed_data.py`) into `budget.db` via `unittest.mock.patch`. Each test gets an isolated state — no cross-test pollution.

## Configuration

`.streamlit/secrets.toml` (not in git) is required for production:
```toml
[supabase]
url = "..."
anon_key = "..."

[auth]
password_hash = "<bcrypt-hash>"

[openai]
api_key = "sk-..."

[bank]
header_row = 10  # 0-based row index for the header in bank exports
```

## Key conventions

- **Category vocabulary**: `personal`, `common`, `covered`, `uncategorized` — used in DB, UI, and AI prompts consistently.
- **User names**: Hardcoded as `"Laerke"` and `"Hector"` throughout DB constraints, calculations, and UI.
- **Amounts**: Stored as floats; negative = debit/expense. Settlement math uses absolute values.
- **`APP_ENV=test`**: Must be set for all test commands; activates FakeRepository and seeds test data in `main.py`.

## Deployment / Keepalive

The app is deployed on Streamlit Community Cloud. The Supabase free tier pauses projects after ~7 days of inactivity, so a GitHub Actions cron workflow pings the Supabase REST API twice a day.

Workflow: `.github/workflows/keep_supabase_alive.yml`.
Required repository secrets: `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
The endpoint hit is a read-only `GET` on `monthly_summary` with `limit=1`; the existing `anon` RLS policies allow this.

If the Supabase project is already paused when the workflow starts, resume it manually once from the Supabase Dashboard.