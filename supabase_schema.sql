-- Run this SQL in your Supabase SQL Editor to create all required tables.
-- Navigate to: Supabase Dashboard > SQL Editor > New Query > Paste & Run

-- ============================================================
-- TRANSACTIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "user"      TEXT NOT NULL CHECK ("user" IN ('Laerke', 'Hector')),
    month       INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    year        INTEGER NOT NULL,
    date        DATE NOT NULL,
    description TEXT NOT NULL,
    amount      NUMERIC(10, 2) NOT NULL,
    source      TEXT NOT NULL CHECK (source IN ('account', 'card')),
    category    TEXT NOT NULL DEFAULT 'uncategorized'
                    CHECK (category IN ('personal', 'common', 'uncategorized', 'covered')),
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE ("user", date, description, amount, source)
);

-- ============================================================
-- FIXED EXPENSES
-- ============================================================
CREATE TABLE IF NOT EXISTS fixed_expenses (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "user"     TEXT NOT NULL CHECK ("user" IN ('Laerke', 'Hector')),
    name       TEXT NOT NULL,
    amount     NUMERIC(10, 2) NOT NULL,
    active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- MONTHLY SUMMARY  (upserted by the calculator after categorisation)
-- ============================================================
CREATE TABLE IF NOT EXISTS monthly_summary (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    month             INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    year              INTEGER NOT NULL,
    laerke_common     NUMERIC(10, 2) NOT NULL DEFAULT 0,
    hector_common     NUMERIC(10, 2) NOT NULL DEFAULT 0,
    fixed_laerke      NUMERIC(10, 2) NOT NULL DEFAULT 0,
    fixed_hector      NUMERIC(10, 2) NOT NULL DEFAULT 0,
    laerke_personal   NUMERIC(10, 2) NOT NULL DEFAULT 0,
    hector_personal   NUMERIC(10, 2) NOT NULL DEFAULT 0,
    balance           NUMERIC(10, 2) NOT NULL DEFAULT 0,
    who_pays_whom     TEXT,
    updated_at        TIMESTAMPTZ DEFAULT now(),
    UNIQUE (month, year)
);

-- ============================================================
-- Row-Level Security (optional but recommended)
-- Enable if you want to restrict access to authenticated users.
-- For simplicity with the shared-password approach, leave RLS off
-- and secure via Streamlit auth instead.
-- ============================================================
-- ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE fixed_expenses ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE monthly_summary ENABLE ROW LEVEL SECURITY;
