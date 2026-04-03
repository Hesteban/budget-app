# Budget Tracking App

A Streamlit-based shared expense tracker for managing and settling transactions between two users. Built with Supabase for data storage and OpenAI Agents for intelligent transaction categorization.

## Features

- **Flexible XLS Importer** — Auto-detects account/card formats, normalizes data, deduplicates transactions
- **Settlement Calculator** — Automatic 50/50 split calculations for common expenses per user per month
- **Transaction Management** — Categorize transactions as personal, common, or uncategorized with one-click categorization
- **Fixed Expenses** — Recurring per-user expenses that auto-copy to new months
- **Monthly Summary** — View settlement amounts and who pays whom
- **AI Categorization** — Optional auto-categorization using OpenAI Agents (confidence threshold: 85%)
- **Dual-User Auth** — Shared password with user session selector in sidebar

## Tech Stack

- **Frontend:** Streamlit ≥ 1.32
- **Backend:** Supabase (PostgreSQL)
- **Testing:** pytest, pytest-playwright
- **AI:** OpenAI Agents SDK
- **Data:** openpyxl, pandas

## Setup

### Prerequisites

- Python 3.11+
- Supabase account (free tier available)

### Installation

```bash
git clone <repo-url> && cd budget
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Create `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://your-project.supabase.co"
key = "your-anon-key"

[app]
password = "shared-password-hash"

[openai]
api_key = "sk-..."  # Optional, for AI categorization
```

## Running Locally

### Production Mode
```bash
streamlit run main.py
```
Then select "I am Laerke" or "I am Hector" in the sidebar and log in with your shared password.

### Test Mode (Auto-Login)
```bash
APP_ENV=test streamlit run main.py
```
Auto-logs in as Hector with March 2026 seed data. No password required.

## Testing

### Run All Tests
```bash
pip install -r requirements-test.txt
APP_ENV=test pytest tests/ -v
```

### Run Specific Test Suite
```bash
APP_ENV=test pytest tests/unittests/test_calculator.py -v
APP_ENV=test pytest tests/unittests/test_importer.py -v
```

### Test Coverage
```bash
APP_ENV=test pytest tests/ --cov=budget --cov-report=html
```

## Project Structure

```
budget/
├── main.py                      # Streamlit app entry point
├── budget/
│   ├── db.py                    # Database abstraction
│   ├── repository.py            # Repository pattern + FakeRepository
│   ├── importer.py              # XLS import logic
│   ├── calculator.py            # Settlement calculations
│   ├── ai_categorizer.py        # OpenAI categorization
│   └── budget_repository.py     # Supabase implementation
├── pages/
│   ├── 1_📤_Upload.py           # File uploader
│   ├── 2_💳_Transactions.py     # Transaction viewer/editor
│   ├── 3_🔁_Fixed_Expenses.py   # Recurring expenses
│   └── 4_📊_Summary.py          # Settlement summary
└── tests/
    ├── conftest.py              # Shared fixtures
    ├── test_calculator.py       # Unit tests
    └── test_importer.py         # Importer tests
```

## Database Schema

**transactions** — user, month, year, date, description, amount, source (account/card), category (personal/common/uncategorized)

**fixed_expenses** — user, name, amount, active

**monthly_summary** — month, year, laerke_common, hector_common, fixed_laerke, fixed_hector, balance, who_pays_whom

**app_config** — password_hash

## Deployment

Push to GitHub (ensure `.streamlit/secrets.toml` is in `.gitignore`), then deploy to Streamlit Community Cloud and configure Supabase credentials in Cloud Secrets.

## Notes

- **Supabase free tier** pauses after 1 week of inactivity—upgrade or keep active after deployment
- Test mode uses in-memory FakeRepository; no Supabase connection required
- AI categorization requires OpenAI API key in secrets
