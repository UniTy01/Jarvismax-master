-- ================================================================
-- JARVIS MAX - Init PostgreSQL
-- Cree automatiquement au premier demarrage de docker compose
-- ================================================================

-- Jarvis core DB (deja creee par POSTGRES_DB)
-- n8n aura sa propre base

-- Extension utile
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Memoire long terme (fallback si Qdrant indisponible)
CREATE TABLE IF NOT EXISTS vault_memory (
    id         SERIAL PRIMARY KEY,
    key        VARCHAR(256) UNIQUE NOT NULL,
    value      TEXT          NOT NULL,
    tags       TEXT[]        DEFAULT '{}',
    created_at TIMESTAMPTZ   DEFAULT NOW(),
    updated_at TIMESTAMPTZ   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vault_key    ON vault_memory(key);
CREATE INDEX IF NOT EXISTS idx_vault_tags   ON vault_memory USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_vault_value  ON vault_memory USING GIN (value gin_trgm_ops);

-- Log des actions executees
CREATE TABLE IF NOT EXISTS action_log (
    id           SERIAL        PRIMARY KEY,
    ts           TIMESTAMPTZ   DEFAULT NOW(),
    session_id   VARCHAR(64),
    agent        VARCHAR(64),
    action_type  VARCHAR(64)   NOT NULL,
    target       TEXT,
    success      BOOLEAN,
    risk_level   VARCHAR(16),
    approved     BOOLEAN       DEFAULT FALSE,
    duration_ms  INTEGER,
    error        TEXT
);

CREATE INDEX IF NOT EXISTS idx_action_session ON action_log(session_id);
CREATE INDEX IF NOT EXISTS idx_action_ts      ON action_log(ts DESC);
CREATE INDEX IF NOT EXISTS idx_action_type    ON action_log(action_type);

-- Sessions memorisees
CREATE TABLE IF NOT EXISTS sessions (
    id            VARCHAR(64)  PRIMARY KEY,
    mode          VARCHAR(32),
    mission       TEXT,
    final_report  TEXT,
    status        VARCHAR(32),
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- Configuration runtime
CREATE TABLE IF NOT EXISTS runtime_config (
    key        VARCHAR(128) PRIMARY KEY,
    value      JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger mise a jour automatique de updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER vault_memory_updated_at
    BEFORE UPDATE ON vault_memory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
