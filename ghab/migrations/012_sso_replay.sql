-- Persist consumed SSO signatures across process restarts.
CREATE TABLE IF NOT EXISTS sso_used (
    signature TEXT PRIMARY KEY,
    expires REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sso_used_expires ON sso_used(expires);
