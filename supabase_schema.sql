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
    reasoning   TEXT,
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
    year       INTEGER NOT NULL DEFAULT 2026,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Migration: assign year=2026 to existing rows that have no year
UPDATE fixed_expenses SET year = 2026 WHERE year IS NULL;

-- ============================================================
-- DIRECT EXPENSES  (shared household costs settled outside the app;
--                   reduce savings only, never affect settlement)
-- ============================================================
CREATE TABLE IF NOT EXISTS direct_expenses (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL,
    amount     NUMERIC(10, 2) NOT NULL,
    active     BOOLEAN NOT NULL DEFAULT TRUE,
    year       INTEGER NOT NULL DEFAULT 2026,
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
    fair_share        NUMERIC(10, 2) NOT NULL DEFAULT 0,
    laerke_income     NUMERIC(10, 2) NOT NULL DEFAULT 0,
    hector_income     NUMERIC(10, 2) NOT NULL DEFAULT 0,
    laerke_savings    NUMERIC(10, 2) NOT NULL DEFAULT 0,
    hector_savings    NUMERIC(10, 2) NOT NULL DEFAULT 0,
    direct_per_person NUMERIC(10, 2) NOT NULL DEFAULT 0,
    updated_at        TIMESTAMPTZ DEFAULT now(),
    UNIQUE (month, year)
);

-- Migration: add income/savings/direct/fair_share columns to existing monthly_summary table
ALTER TABLE monthly_summary
  ADD COLUMN IF NOT EXISTS fair_share         NUMERIC(10,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS laerke_income      NUMERIC(10,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS hector_income      NUMERIC(10,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS laerke_savings     NUMERIC(10,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS hector_savings     NUMERIC(10,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS direct_per_person  NUMERIC(10,2) NOT NULL DEFAULT 0;

-- ============================================================
-- MONTHLY REPORTS (AI-generated spending summary narratives)
-- ============================================================
CREATE TABLE IF NOT EXISTS monthly_reports (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    month        INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    year         INTEGER NOT NULL,
    content      TEXT    NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (month, year)
);

-- ============================================================
-- Row-Level Security
-- Enable RLS and create policies for data access control.
-- ============================================================
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixed_expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE direct_expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_reports ENABLE ROW LEVEL SECURITY;

-- RLS Policies for anon (public API access)
CREATE POLICY "transactions: read all (anon)" ON public.transactions FOR SELECT TO anon USING (true);
CREATE POLICY "transactions: insert all (anon)" ON public.transactions FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "transactions: update all (anon)" ON public.transactions FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY "transactions: delete all (anon)" ON public.transactions FOR DELETE TO anon USING (true);

CREATE POLICY "fixed_expenses: read all (anon)" ON public.fixed_expenses FOR SELECT TO anon USING (true);
CREATE POLICY "fixed_expenses: insert all (anon)" ON public.fixed_expenses FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "fixed_expenses: update all (anon)" ON public.fixed_expenses FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY "fixed_expenses: delete all (anon)" ON public.fixed_expenses FOR DELETE TO anon USING (true);

CREATE POLICY "direct_expenses: read all (anon)"   ON public.direct_expenses FOR SELECT TO anon USING (true);
CREATE POLICY "direct_expenses: insert all (anon)" ON public.direct_expenses FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "direct_expenses: update all (anon)" ON public.direct_expenses FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY "direct_expenses: delete all (anon)" ON public.direct_expenses FOR DELETE TO anon USING (true);

CREATE POLICY "monthly_summary: read all (anon)" ON public.monthly_summary FOR SELECT TO anon USING (true);
CREATE POLICY "monthly_summary: insert all (anon)" ON public.monthly_summary FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "monthly_summary: update all (anon)" ON public.monthly_summary FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY "monthly_summary: delete all (anon)" ON public.monthly_summary FOR DELETE TO anon USING (true);

CREATE POLICY "monthly_reports: read all (anon)" ON public.monthly_reports FOR SELECT TO anon USING (true);
CREATE POLICY "monthly_reports: insert all (anon)" ON public.monthly_reports FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "monthly_reports: update all (anon)" ON public.monthly_reports FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY "monthly_reports: delete all (anon)" ON public.monthly_reports FOR DELETE TO anon USING (true);

-- RLS Policies for authenticated (logged-in users)
CREATE POLICY "transactions: read all (authenticated)" ON public.transactions FOR SELECT TO authenticated USING (true);
CREATE POLICY "transactions: insert all (authenticated)" ON public.transactions FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "transactions: update all (authenticated)" ON public.transactions FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "transactions: delete all (authenticated)" ON public.transactions FOR DELETE TO authenticated USING (true);

CREATE POLICY "fixed_expenses: read all (authenticated)" ON public.fixed_expenses FOR SELECT TO authenticated USING (true);
CREATE POLICY "fixed_expenses: insert all (authenticated)" ON public.fixed_expenses FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "fixed_expenses: update all (authenticated)" ON public.fixed_expenses FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "fixed_expenses: delete all (authenticated)" ON public.fixed_expenses FOR DELETE TO authenticated USING (true);

CREATE POLICY "direct_expenses: read all (authenticated)"   ON public.direct_expenses FOR SELECT TO authenticated USING (true);
CREATE POLICY "direct_expenses: insert all (authenticated)" ON public.direct_expenses FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "direct_expenses: update all (authenticated)" ON public.direct_expenses FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "direct_expenses: delete all (authenticated)" ON public.direct_expenses FOR DELETE TO authenticated USING (true);

CREATE POLICY "monthly_summary: read all (authenticated)" ON public.monthly_summary FOR SELECT TO authenticated USING (true);
CREATE POLICY "monthly_summary: insert all (authenticated)" ON public.monthly_summary FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "monthly_summary: update all (authenticated)" ON public.monthly_summary FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "monthly_summary: delete all (authenticated)" ON public.monthly_summary FOR DELETE TO authenticated USING (true);

CREATE POLICY "monthly_reports: read all (authenticated)" ON public.monthly_reports FOR SELECT TO authenticated USING (true);
CREATE POLICY "monthly_reports: insert all (authenticated)" ON public.monthly_reports FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "monthly_reports: update all (authenticated)" ON public.monthly_reports FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "monthly_reports: delete all (authenticated)" ON public.monthly_reports FOR DELETE TO authenticated USING (true);

-- ============================================================
-- Explicit Grants for Data API access (required from May 30, 2026)
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON transactions TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON transactions TO authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON fixed_expenses TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON fixed_expenses TO authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON direct_expenses TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON direct_expenses TO authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON monthly_summary TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON monthly_summary TO authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON monthly_reports TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON monthly_reports TO authenticated;
