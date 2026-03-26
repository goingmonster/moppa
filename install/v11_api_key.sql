-- v11: 新增 api_key 表（API Key 身份认证管理）
CREATE TABLE IF NOT EXISTS api_key (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    token TEXT NOT NULL,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    token_prefix VARCHAR(12) NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('agent', 'user', 'other')),
    purpose VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    created_by UUID REFERENCES app_user(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_api_key_name_active
ON api_key (name)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_api_key_token_hash ON api_key(token_hash)
WHERE deleted_at IS NULL AND is_active = TRUE;

DROP TRIGGER IF EXISTS trg_api_key_updated_at ON api_key;
CREATE TRIGGER trg_api_key_updated_at BEFORE UPDATE ON api_key
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();
