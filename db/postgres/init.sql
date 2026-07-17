CREATE TABLE IF NOT EXISTS audit_log (
  id            SERIAL PRIMARY KEY,
  event_type    VARCHAR(64) NOT NULL,  -- attested, poisoning_detected, unlearning_completed
  dataset_id    VARCHAR(255),
  request_id    VARCHAR(255),
  detail        JSONB NOT NULL DEFAULT '{}',
  occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_occurred_at ON audit_log (occurred_at);

CREATE TABLE IF NOT EXISTS erasure_requests (
  id              VARCHAR(64) PRIMARY KEY,
  requested_by    VARCHAR(255),
  target_records  JSONB NOT NULL,  -- record/document IDs to be forgotten
  status          VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending, in_progress, completed, failed
  requested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at    TIMESTAMPTZ
);
