PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS final_decisions (
  idempotency_key TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_final_decisions_created_at ON final_decisions(created_at);
