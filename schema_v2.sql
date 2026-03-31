-- ============================================================
-- schema_v2.sql — Run in Supabase Dashboard > SQL Editor
-- https://supabase.com/dashboard/project/lyaxzyjqvfwphcmmmibt/sql/new
-- ============================================================

-- 1. Extend jobs table with enrichment/scoring columns
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS relevant        boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS description     text,
  ADD COLUMN IF NOT EXISTS enriched_at     timestamptz,
  ADD COLUMN IF NOT EXISTS match_score     float,
  ADD COLUMN IF NOT EXISTS match_reasoning text,
  ADD COLUMN IF NOT EXISTS scored_at       timestamptz;

-- Indexes to make pipeline queries fast
CREATE INDEX IF NOT EXISTS jobs_relevant_unenriched_idx
  ON jobs (relevant, enriched_at)
  WHERE relevant = true AND enriched_at IS NULL;

CREATE INDEX IF NOT EXISTS jobs_unscored_idx
  ON jobs (scored_at)
  WHERE scored_at IS NULL AND enriched_at IS NOT NULL AND relevant = true;

-- 2. seen_jobs table (replaces seen_jobs.json — survives droplet rebuilds)
CREATE TABLE IF NOT EXISTS seen_jobs (
  url_hash      text PRIMARY KEY,
  first_seen_at timestamptz DEFAULT now()
);
-- Internal only: service_role bypasses RLS, anon cannot read
ALTER TABLE seen_jobs ENABLE ROW LEVEL SECURITY;

-- 3. sources table (replaces job_sources.json — manageable via UI/form later)
CREATE TABLE IF NOT EXISTS sources (
  id         serial PRIMARY KEY,
  name       text NOT NULL,
  url        text NOT NULL,
  type       text NOT NULL,  -- ashby | greenhouse | lever | vc_job_board | career_page | playwright | workatastartup
  enabled    boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
-- Public read so frontend can display source list
CREATE POLICY "public_read" ON sources FOR SELECT USING (true);
