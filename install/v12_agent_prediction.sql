-- v12: 新增 agent_prediction 表（外部 Agent 通过 API Key 提交预测）
CREATE TABLE IF NOT EXISTS agent_prediction (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES question(id) ON DELETE RESTRICT,
    api_key_id UUID NOT NULL REFERENCES api_key(id),
    model_name VARCHAR(120) NOT NULL,
    prediction_content TEXT NOT NULL,
    reasoning TEXT,
    confidence INTEGER CHECK (confidence BETWEEN 0 AND 100),
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    question_text TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (question_id, api_key_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_prediction_question_id ON agent_prediction(question_id)
WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_agent_prediction_api_key_id ON agent_prediction(api_key_id)
WHERE deleted_at IS NULL;

DROP TRIGGER IF EXISTS trg_agent_prediction_updated_at ON agent_prediction;
CREATE TRIGGER trg_agent_prediction_updated_at BEFORE UPDATE ON agent_prediction
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();
