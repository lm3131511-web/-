PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS decisions(
  id TEXT PRIMARY KEY,
  ts_utc TEXT NOT NULL,
  asset TEXT NOT NULL,
  status TEXT NOT NULL,
  side TEXT,
  size_frac REAL,
  strategy TEXT,
  ttl_seconds INTEGER,
  snapshot_id TEXT,
  code_hash TEXT,
  idempotency_key TEXT
);
CREATE INDEX IF NOT EXISTS idx_decisions_ts_asset ON decisions(ts_utc, asset);

CREATE TABLE IF NOT EXISTS fills(
  id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  ts_utc TEXT NOT NULL,
  asset TEXT NOT NULL,
  price REAL NOT NULL,
  qty REAL NOT NULL,
  fee_usd REAL,
  slippage_bps REAL,
  FOREIGN KEY(decision_id) REFERENCES decisions(id)
);
CREATE INDEX IF NOT EXISTS idx_fills_decision ON fills(decision_id);

CREATE TABLE IF NOT EXISTS metrics(
  ts_utc TEXT NOT NULL,
  window INTEGER NOT NULL,
  ece REAL,
  brier REAL,
  reliability REAL,
  llm_cost_per_min REAL,
  approved_ratio REAL
);
