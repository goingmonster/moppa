BEGIN;

CREATE TABLE IF NOT EXISTS auth_refresh_token (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_refresh_token_user_id ON auth_refresh_token(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_refresh_token_expires_at ON auth_refresh_token(expires_at);

COMMIT;
