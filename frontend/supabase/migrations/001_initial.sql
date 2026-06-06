-- SpendPilot / DecisionOS schema for Supabase

CREATE TABLE IF NOT EXISTS cases (
  case_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
  payload_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cases_review_queue
  ON cases (requires_human_review, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_cases_created_at
  ON cases (created_at DESC);

CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id TEXT REFERENCES cases(case_id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  file_type TEXT NOT NULL DEFAULT 'other',
  file_size BIGINT NOT NULL DEFAULT 0,
  storage_path TEXT,
  extracted_text TEXT,
  document_signals JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents (case_id);

-- Auto-update updated_at on cases
CREATE OR REPLACE FUNCTION update_cases_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS cases_updated_at ON cases;
CREATE TRIGGER cases_updated_at
  BEFORE UPDATE ON cases
  FOR EACH ROW
  EXECUTE FUNCTION update_cases_updated_at();

-- Storage bucket for uploaded documents (run in Supabase dashboard or via API)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('documents', 'documents', false);
