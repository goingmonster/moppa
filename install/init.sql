-- MOPPA 一体化初始化脚本（无 include，PG10 触发器兼容）
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT USAGE, CREATE ON SCHEMA public TO CURRENT_USER;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- MOPPA 与 SOP 对齐数据库结构（审核版）
-- 目标数据库：PostgreSQL 10+（触发器采用 EXECUTE PROCEDURE 兼容写法）
-- 说明：
-- 1）所有时间字段统一使用 TIMESTAMPTZ（建议 UTC）
-- 2）敏感信息仅保存引用（secret_ref/api_key_ref），不保存明文
-- 3）软删除统一使用 deleted_at
-- 启用 UUID 与加密辅助函数
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 通用触发器函数：更新时自动维护 updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $func$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$func$;

CREATE OR REPLACE FUNCTION validate_feedback_target()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $func$
DECLARE
    v_exists BOOLEAN := FALSE;
BEGIN
    CASE NEW.target_type
        WHEN 'question' THEN
            SELECT EXISTS (
                SELECT 1 FROM question q
                WHERE q.id = NEW.target_id AND q.deleted_at IS NULL
            ) INTO v_exists;
        WHEN 'prediction' THEN
            SELECT EXISTS (
                SELECT 1 FROM prediction p
                WHERE p.id = NEW.target_id AND p.deleted_at IS NULL
            ) INTO v_exists;
        WHEN 'score' THEN
            SELECT EXISTS (
                SELECT 1 FROM score_record s
                WHERE s.id = NEW.target_id
            ) INTO v_exists;
        WHEN 'leaderboard' THEN
            SELECT EXISTS (
                SELECT 1 FROM leaderboard l
                WHERE l.id = NEW.target_id AND l.deleted_at IS NULL
            ) INTO v_exists;
    END CASE;

    IF NOT v_exists THEN
        RAISE EXCEPTION 'Invalid feedback target: type=% id=%', NEW.target_type, NEW.target_id;
    END IF;

    RETURN NEW;
END;
$func$;

CREATE OR REPLACE FUNCTION validate_ground_truth_publish_time()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $func$
DECLARE
    v_deadline TIMESTAMPTZ;
BEGIN
    SELECT q.deadline
    INTO v_deadline
    FROM question q
    WHERE q.id = NEW.question_id AND q.deleted_at IS NULL;

    IF v_deadline IS NULL THEN
        RAISE EXCEPTION 'Question not found or deleted for question_id=%', NEW.question_id;
    END IF;

    IF NEW.publish_time < v_deadline THEN
        RAISE EXCEPTION 'Ground truth publish_time (%) cannot be earlier than question deadline (%) for question_id=%',
            NEW.publish_time, v_deadline, NEW.question_id;
    END IF;

    RETURN NEW;
END;
$func$;

-- 枚举类型按条件创建，保证脚本可重复执行
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM (
            'admin',
            'intelligence_expert',
            'algorithm_engineer',
            'platform_engineer',
            'operator',
            'auditor',
            'data_analyst'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'provider_type') THEN
        CREATE TYPE provider_type AS ENUM ('openai', 'anthropic', 'custom', 'internal');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'record_status') THEN
        CREATE TYPE record_status AS ENUM ('active', 'inactive', 'archived');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'question_status') THEN
        CREATE TYPE question_status AS ENUM ('draft', 'pending_review', 'published', 'closed', 'expired');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'review_decision') THEN
        CREATE TYPE review_decision AS ENUM ('pass', 'reject', 'modify');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'prediction_status') THEN
        CREATE TYPE prediction_status AS ENUM ('pending', 'processing', 'completed', 'failed');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'scoring_method') THEN
        CREATE TYPE scoring_method AS ENUM ('rule', 'ai', 'hybrid');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_status') THEN
        CREATE TYPE task_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled', 'dead_letter');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leaderboard_cycle') THEN
        CREATE TYPE leaderboard_cycle AS ENUM ('weekly', 'monthly', 'quarterly');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'feedback_status') THEN
        CREATE TYPE feedback_status AS ENUM ('open', 'processing', 'resolved', 'closed');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'feedback_target_type') THEN
        CREATE TYPE feedback_target_type AS ENUM ('question', 'prediction', 'score', 'leaderboard');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'incident_severity') THEN
        CREATE TYPE incident_severity AS ENUM ('P0', 'P1', 'P2', 'P3');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'incident_status') THEN
        CREATE TYPE incident_status AS ENUM ('open', 'investigating', 'resolved', 'closed');
    END IF;
END
$$;

-- 系统用户与角色权限（RBAC）主表
CREATE TABLE IF NOT EXISTS app_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role user_role NOT NULL,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    permissions JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_app_user_email_active
ON app_user (email)
WHERE deleted_at IS NULL AND email IS NOT NULL;

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

-- 数据源注册表（S0）
CREATE TABLE IF NOT EXISTS data_source (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    source_system VARCHAR(100) NOT NULL UNIQUE,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('api', 'database', 'file', 'websocket')),
    connection_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    secret_ref TEXT,
    credibility_level SMALLINT NOT NULL DEFAULT 3 CHECK (credibility_level BETWEEN 1 AND 5),
    sync_frequency INTERVAL NOT NULL DEFAULT INTERVAL '1 hour',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT ck_data_source_no_plaintext_secret CHECK (
        secret_ref IS NOT NULL
        OR NOT (
            connection_config ?| ARRAY['password', 'passwd', 'pwd', 'api_key', 'apikey', 'token', 'secret', 'access_key']
        )
    )
);

-- 模型端点注册表：每个可调用模型对应一行
CREATE TABLE IF NOT EXISTS model_endpoint (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    provider provider_type NOT NULL,
    endpoint_url TEXT NOT NULL,
    api_key_ref TEXT,
    model_name VARCHAR(120) NOT NULL,
    model_version VARCHAR(40) NOT NULL DEFAULT 'v1.0',
    max_tokens INTEGER NOT NULL DEFAULT 4096 CHECK (max_tokens > 0),
    temperature NUMERIC(3,2) NOT NULL DEFAULT 0.7 CHECK (temperature >= 0 AND temperature <= 2),
    timeout_seconds INTEGER NOT NULL DEFAULT 120 CHECK (timeout_seconds > 0),
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    status record_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- SOP 对齐的 L1-L4 规则等级配置
CREATE TABLE IF NOT EXISTS rule_level_config (
    level SMALLINT PRIMARY KEY CHECK (level BETWEEN 1 AND 4),
    level_name VARCHAR(50) NOT NULL,
    description TEXT,
    weight NUMERIC(6,3) NOT NULL DEFAULT 1.000 CHECK (weight > 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- S1 阶段事件过滤规则表
CREATE TABLE IF NOT EXISTS event_filter_rule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    level SMALLINT NOT NULL REFERENCES rule_level_config(level),
    rule_scope VARCHAR(20) NOT NULL DEFAULT 'db_import' CHECK (rule_scope IN ('db_import', 'scrapy', 'document', 'use', 'other')),
    filter_expression TEXT NOT NULL,
    filter_prompts JSONB NOT NULL DEFAULT '[]'::jsonb,
    filter_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    priority INTEGER NOT NULL DEFAULT 0,
    pass_rate_threshold NUMERIC(5,2) CHECK (pass_rate_threshold BETWEEN 0 AND 100),
    status record_status NOT NULL DEFAULT 'active',
    version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    created_by UUID REFERENCES app_user(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- S2 阶段问题生成模板表
CREATE TABLE IF NOT EXISTS question_template (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_index INTEGER NOT NULL CHECK (template_index > 0),
    question_template TEXT NOT NULL,
    difficulty_level VARCHAR(2) NOT NULL CHECK (difficulty_level IN ('L1', 'L2', 'L3', 'L4')),
    candidate_answer_type VARCHAR(20) NOT NULL CHECK (candidate_answer_type IN ('fixed', 'dynamic', 'open')),
    event_domain VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_type_id VARCHAR(20) NOT NULL,
    operation_level VARCHAR(50) NOT NULL,
    status record_status NOT NULL DEFAULT 'active',
    version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    created_by UUID REFERENCES app_user(id),
    approved_by UUID REFERENCES app_user(id),
    usage_count BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (template_index, version),
    UNIQUE (question_template, difficulty_level, event_type_id, version)
);

-- S6 阶段评分规则版本表；通过唯一索引保证仅一个激活版本
CREATE TABLE IF NOT EXISTS scoring_rule_version (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(30) NOT NULL UNIQUE,
    description TEXT,
    dimensions JSONB NOT NULL,
    calculation_formula TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_by UUID REFERENCES app_user(id),
    approved_by UUID REFERENCES app_user(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_scoring_rule_single_active
ON scoring_rule_version ((is_active))
WHERE is_active = TRUE;

-- 标准化后的事件主表（过滤后）
CREATE TABLE IF NOT EXISTS event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_key VARCHAR(255) NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_system VARCHAR(100) NOT NULL REFERENCES data_source(source_system),
    credibility_level SMALLINT NOT NULL CHECK (credibility_level BETWEEN 1 AND 5),
    event_time TIMESTAMPTZ NOT NULL,
    url TEXT,
    tags TEXT[] NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    trace_id UUID NOT NULL DEFAULT gen_random_uuid(),
    filter_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (filter_status IN ('pending', 'passed', 'filtered')),
    filter_reasons TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (event_key, version)
);

-- 问题主表：一个事件可生成多个问题
CREATE TABLE IF NOT EXISTS question (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
  event_id UUID REFERENCES event(id) ON DELETE RESTRICT,
    template_id UUID REFERENCES question_template(id),
    level SMALLINT NOT NULL REFERENCES rule_level_config(level),
    content TEXT NOT NULL,
    answer_space TEXT,
    verification_conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
    deadline TIMESTAMPTZ NOT NULL,
    status question_status NOT NULL DEFAULT 'draft',
    duplicate_check_hash TEXT,
    source_system VARCHAR(100) NOT NULL DEFAULT 'moppa',
    trace_id UUID NOT NULL,
    created_by UUID REFERENCES app_user(id),
    published_by UUID REFERENCES app_user(id),
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT ck_question_deadline_after_created CHECK (deadline >= created_at)
);

CREATE TABLE IF NOT EXISTS question_event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES question(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES event(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (question_id, event_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_question_duplicate_hash_active
ON question (duplicate_check_hash)
WHERE duplicate_check_hash IS NOT NULL AND deleted_at IS NULL;

-- S3 阶段人工审核轨迹表（质量门）
CREATE TABLE IF NOT EXISTS question_review (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES question(id) ON DELETE RESTRICT,
    reviewer_id UUID NOT NULL REFERENCES app_user(id),
    review_type VARCHAR(30) NOT NULL CHECK (review_type IN ('initial', 'spot_check', 'duplicate_review')),
    decision review_decision NOT NULL,
    reason_tags TEXT[] NOT NULL DEFAULT '{}',
    feedback TEXT,
    evidence_links TEXT[] NOT NULL DEFAULT '{}',
    is_verifiable BOOLEAN,
    is_trustworthy_evidence BOOLEAN,
    trace_id UUID NOT NULL,
    review_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 调度执行台账：包含幂等、重试、超时控制
CREATE TABLE IF NOT EXISTS task_execution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(50) NOT NULL,
    business_id UUID,
    date_window TIMESTAMPTZ,
    model_id UUID REFERENCES model_endpoint(id),
    idempotency_key TEXT NOT NULL UNIQUE,
    status task_status NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    next_retry_at TIMESTAMPTZ,
    retry_intervals_minutes INTEGER[] NOT NULL DEFAULT ARRAY[1,5,15],
    timeout_seconds INTEGER NOT NULL DEFAULT 3600 CHECK (timeout_seconds > 0),
    result JSONB,
    error_message TEXT,
    metrics JSONB,
    trace_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    CONSTRAINT ck_task_execution_time CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
);

-- S4 阶段模型预测结果表
CREATE TABLE IF NOT EXISTS prediction (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    question_id UUID NOT NULL REFERENCES question(id) ON DELETE RESTRICT,
    model_id UUID NOT NULL REFERENCES model_endpoint(id),
    prediction_content TEXT NOT NULL,
    confidence NUMERIC(5,2) CHECK (confidence BETWEEN 0 AND 100),
    inference_time_ms INTEGER CHECK (inference_time_ms >= 0),
    token_usage JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_system VARCHAR(100) NOT NULL DEFAULT 'moppa',
    trace_id UUID NOT NULL,
    task_execution_id UUID REFERENCES task_execution(id),
    status prediction_status NOT NULL DEFAULT 'pending',
    error_message TEXT,
    submission_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_prediction_once_per_question_model
ON prediction (question_id, model_id, version)
WHERE deleted_at IS NULL;

-- S5 阶段真实答案表（Ground Truth）
CREATE TABLE IF NOT EXISTS ground_truth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    question_id UUID NOT NULL REFERENCES question(id) ON DELETE RESTRICT,
    answer TEXT NOT NULL,
    evidence_links TEXT[] NOT NULL DEFAULT '{}',
    publish_time TIMESTAMPTZ NOT NULL,
    credibility_level SMALLINT NOT NULL CHECK (credibility_level BETWEEN 1 AND 5),
    source_system VARCHAR(100) NOT NULL,
    trace_id UUID NOT NULL,
    extracted_by UUID REFERENCES app_user(id),
    verified_by UUID REFERENCES app_user(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (question_id, version)
);

-- S6 阶段评分记录表（按评分规则版本化）
CREATE TABLE IF NOT EXISTS score_record (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    prediction_id UUID NOT NULL REFERENCES prediction(id) ON DELETE RESTRICT,
    ground_truth_id UUID NOT NULL REFERENCES ground_truth(id) ON DELETE RESTRICT,
    scoring_rule_version VARCHAR(30) NOT NULL REFERENCES scoring_rule_version(version),
    dimension_scores JSONB NOT NULL,
    total_score NUMERIC(5,2) NOT NULL CHECK (total_score BETWEEN 0 AND 100),
    scoring_method scoring_method NOT NULL,
    weight_config JSONB,
    source_system VARCHAR(100) NOT NULL DEFAULT 'moppa',
    trace_id UUID NOT NULL,
    calculated_by UUID REFERENCES app_user(id),
    calculation_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_reproducible BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (prediction_id, ground_truth_id, scoring_rule_version)
);

-- 榜单头表；具体名次行拆分在 leaderboard_entry
CREATE TABLE IF NOT EXISTS leaderboard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_type leaderboard_cycle NOT NULL,
    cycle_start_time TIMESTAMPTZ NOT NULL,
    cycle_end_time TIMESTAMPTZ NOT NULL,
    level SMALLINT REFERENCES rule_level_config(level),
    scoring_rule_version VARCHAR(30) NOT NULL REFERENCES scoring_rule_version(version),
    summary_metrics JSONB,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    published_by UUID REFERENCES app_user(id),
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT ck_leaderboard_window CHECK (cycle_end_time > cycle_start_time),
    UNIQUE (cycle_type, cycle_start_time, cycle_end_time, level)
);

-- 榜单明细行（模型排名）
CREATE TABLE IF NOT EXISTS leaderboard_entry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    leaderboard_id UUID NOT NULL REFERENCES leaderboard(id) ON DELETE RESTRICT,
    model_id UUID NOT NULL REFERENCES model_endpoint(id),
    rank_no INTEGER NOT NULL CHECK (rank_no > 0),
    score NUMERIC(8,3) NOT NULL,
    stats JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (leaderboard_id, model_id),
    UNIQUE (leaderboard_id, rank_no)
);

-- S7 阶段社区反馈表（target_type + target_id 多态关联）
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('comment', 'question', 'improvement')),
    target_type feedback_target_type NOT NULL,
    target_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES app_user(id),
    content TEXT NOT NULL,
    attachments JSONB,
    status feedback_status NOT NULL DEFAULT 'open',
    priority VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    assigned_to UUID REFERENCES app_user(id),
    resolution TEXT,
    trace_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- 社区人工预测表（用于对比与互动）
CREATE TABLE IF NOT EXISTS community_prediction (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES question(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES app_user(id),
    prediction_content TEXT NOT NULL,
    confidence NUMERIC(5,2) CHECK (confidence BETWEEN 0 AND 100),
    reasoning TEXT,
    trace_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (question_id, user_id)
);

-- 变更管理与发布审计日志
CREATE TABLE IF NOT EXISTS change_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    change_id VARCHAR(100) NOT NULL UNIQUE,
    change_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id UUID,
    description TEXT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    status VARCHAR(20) NOT NULL CHECK (status IN ('request', 'review', 'approved', 'rejected', 'deployed', 'rollback')),
    requester_id UUID REFERENCES app_user(id),
    reviewer_id UUID REFERENCES app_user(id),
    approver_id UUID REFERENCES app_user(id),
    deployment_time TIMESTAMPTZ,
    rollback_time TIMESTAMPTZ,
    grey_scale_percentage INTEGER CHECK (grey_scale_percentage BETWEEN 0 AND 100),
    observation_window INTERVAL NOT NULL DEFAULT INTERVAL '1 day',
    trace_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 运行时配置表；敏感配置建议走 secret_ref
CREATE TABLE IF NOT EXISTS system_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(150) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    description TEXT,
    category VARCHAR(50),
    is_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    secret_ref TEXT,
    change_id VARCHAR(100) REFERENCES change_log(change_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 日/周期质量与性能指标表
CREATE TABLE IF NOT EXISTS quality_metric (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL CHECK (metric_type IN ('efficiency', 'data_quality', 'model_performance', 'operation_quality')),
    metric_value NUMERIC NOT NULL,
    threshold_value NUMERIC,
    unit VARCHAR(20),
    date_window DATE NOT NULL,
    dimensions JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (status IN ('normal', 'warning', 'critical')),
    trace_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 事故全生命周期记录（用于 Runbook 与复盘）
CREATE TABLE IF NOT EXISTS incident_record (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id VARCHAR(100) NOT NULL UNIQUE,
    severity incident_severity NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    affected_scope TEXT,
    detection_time TIMESTAMPTZ NOT NULL,
    response_time TIMESTAMPTZ,
    resolution_time TIMESTAMPTZ,
    root_cause TEXT,
    resolution TEXT,
    prevention_measures TEXT,
    status incident_status NOT NULL DEFAULT 'open',
    assigned_to UUID REFERENCES app_user(id),
    notification_sent BOOLEAN NOT NULL DEFAULT FALSE,
    trace_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_incident_time CHECK (
        (response_time IS NULL OR response_time >= detection_time)
        AND (resolution_time IS NULL OR resolution_time >= detection_time)
    )
);

-- 核心查询路径索引（追踪、调度、排行、审核）
CREATE INDEX IF NOT EXISTS idx_event_trace_id ON event(trace_id);
CREATE INDEX IF NOT EXISTS idx_event_source_system ON event(source_system);
CREATE INDEX IF NOT EXISTS idx_event_status_time ON event(filter_status, event_time DESC)
WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_event_tags_gin ON event USING GIN(tags);

CREATE INDEX IF NOT EXISTS idx_question_trace_id ON question(trace_id);
CREATE INDEX IF NOT EXISTS idx_question_status_deadline ON question(status, deadline)
WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_question_level ON question(level);
CREATE INDEX IF NOT EXISTS idx_question_event_question_id ON question_event(question_id);
CREATE INDEX IF NOT EXISTS idx_question_event_event_id ON question_event(event_id);

CREATE INDEX IF NOT EXISTS idx_prediction_trace_id ON prediction(trace_id);
CREATE INDEX IF NOT EXISTS idx_prediction_model ON prediction(model_id, status)
WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_prediction_question ON prediction(question_id);

CREATE INDEX IF NOT EXISTS idx_ground_truth_trace_id ON ground_truth(trace_id);
CREATE INDEX IF NOT EXISTS idx_ground_truth_publish_time ON ground_truth(publish_time)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_score_record_trace_id ON score_record(trace_id);
CREATE INDEX IF NOT EXISTS idx_score_record_total_score ON score_record(total_score DESC);

CREATE INDEX IF NOT EXISTS idx_task_execution_status_retry ON task_execution(status, next_retry_at);
CREATE INDEX IF NOT EXISTS idx_task_execution_trace_id ON task_execution(trace_id);

CREATE INDEX IF NOT EXISTS idx_feedback_target ON feedback(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_feedback_status_priority ON feedback(status, priority);

CREATE INDEX IF NOT EXISTS idx_quality_metric_name_window ON quality_metric(metric_name, date_window DESC);

-- PostgreSQL 10 兼容版：触发器使用 EXECUTE PROCEDURE
-- 触发器：为可变更表自动同步 updated_at
DROP TRIGGER IF EXISTS trg_app_user_updated_at ON app_user;
CREATE TRIGGER trg_app_user_updated_at BEFORE UPDATE ON app_user
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_data_source_updated_at ON data_source;
CREATE TRIGGER trg_data_source_updated_at BEFORE UPDATE ON data_source
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_model_endpoint_updated_at ON model_endpoint;
CREATE TRIGGER trg_model_endpoint_updated_at BEFORE UPDATE ON model_endpoint
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_rule_level_config_updated_at ON rule_level_config;
CREATE TRIGGER trg_rule_level_config_updated_at BEFORE UPDATE ON rule_level_config
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_event_filter_rule_updated_at ON event_filter_rule;
CREATE TRIGGER trg_event_filter_rule_updated_at BEFORE UPDATE ON event_filter_rule
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_question_template_updated_at ON question_template;
CREATE TRIGGER trg_question_template_updated_at BEFORE UPDATE ON question_template
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_scoring_rule_version_updated_at ON scoring_rule_version;
CREATE TRIGGER trg_scoring_rule_version_updated_at BEFORE UPDATE ON scoring_rule_version
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_event_updated_at ON event;
CREATE TRIGGER trg_event_updated_at BEFORE UPDATE ON event
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_question_updated_at ON question;
CREATE TRIGGER trg_question_updated_at BEFORE UPDATE ON question
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_prediction_updated_at ON prediction;
CREATE TRIGGER trg_prediction_updated_at BEFORE UPDATE ON prediction
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_ground_truth_updated_at ON ground_truth;
CREATE TRIGGER trg_ground_truth_updated_at BEFORE UPDATE ON ground_truth
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_ground_truth_publish_time_check ON ground_truth;
CREATE TRIGGER trg_ground_truth_publish_time_check
BEFORE INSERT OR UPDATE OF question_id, publish_time ON ground_truth
FOR EACH ROW EXECUTE PROCEDURE validate_ground_truth_publish_time();

DROP TRIGGER IF EXISTS trg_score_record_updated_at ON score_record;
CREATE TRIGGER trg_score_record_updated_at BEFORE UPDATE ON score_record
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_leaderboard_updated_at ON leaderboard;
CREATE TRIGGER trg_leaderboard_updated_at BEFORE UPDATE ON leaderboard
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_feedback_updated_at ON feedback;
CREATE TRIGGER trg_feedback_updated_at BEFORE UPDATE ON feedback
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_feedback_target_check ON feedback;
CREATE TRIGGER trg_feedback_target_check
BEFORE INSERT OR UPDATE OF target_type, target_id ON feedback
FOR EACH ROW EXECUTE PROCEDURE validate_feedback_target();

DROP TRIGGER IF EXISTS trg_community_prediction_updated_at ON community_prediction;
CREATE TRIGGER trg_community_prediction_updated_at BEFORE UPDATE ON community_prediction
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_change_log_updated_at ON change_log;
CREATE TRIGGER trg_change_log_updated_at BEFORE UPDATE ON change_log
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_task_execution_updated_at ON task_execution;
CREATE TRIGGER trg_task_execution_updated_at BEFORE UPDATE ON task_execution
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_system_config_updated_at ON system_config;
CREATE TRIGGER trg_system_config_updated_at BEFORE UPDATE ON system_config
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_incident_record_updated_at ON incident_record;
CREATE TRIGGER trg_incident_record_updated_at BEFORE UPDATE ON incident_record
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

-- 初始化基础 SOP 配置（幂等插入）
INSERT INTO rule_level_config(level, level_name, description, weight)
VALUES
    (1, 'L1', 'single-choice / objective', 1.000),
    (2, 'L2', 'multi-choice / objective', 1.500),
    (3, 'L3', 'open prediction / deep search', 2.000),
    (4, 'L4', 'open high-volatility / super-agent', 3.000)
ON CONFLICT (level) DO NOTHING;

INSERT INTO scoring_rule_version(version, description, dimensions, calculation_formula, is_active)
VALUES (
    'score.v1',
    'default baseline scoring',
    '{"accuracy":{"weight":0.6,"max_score":60},"timeliness":{"weight":0.2,"max_score":20},"confidence":{"weight":0.2,"max_score":20}}'::jsonb,
    'total = accuracy*0.6 + timeliness*0.2 + confidence*0.2',
    TRUE
)
ON CONFLICT (version) DO NOTHING;

INSERT INTO system_config(key, value, description, category, is_sensitive)
VALUES
    ('workflow.schedule.main_cron', '"0 2 * * *"'::jsonb, 'main daily run', 'schedule', FALSE),
    ('workflow.schedule.compensate_cron', '"0 * * * *"'::jsonb, 'hourly compensate run', 'schedule', FALSE),
    ('workflow.timeout.model_call_seconds', '120'::jsonb, 'single model call timeout', 'timeout', FALSE),
    ('workflow.timeout.batch_minutes', '30'::jsonb, 'single batch timeout', 'timeout', FALSE),
    ('quality_gate.question_dup_rate_max', '0.05'::jsonb, 'max duplicate ratio', 'quality_gate', FALSE),
    ('quality_gate.unverifiable_rate_max', '0.03'::jsonb, 'max unverifiable ratio', 'quality_gate', FALSE),
    ('quality_gate.truth_coverage_min', '0.97'::jsonb, 'min truth coverage', 'quality_gate', FALSE),
    ('quality_gate.delayed_truth_rate_max', '0.02'::jsonb, 'max delayed truth ratio', 'quality_gate', FALSE)
ON CONFLICT (key) DO NOTHING;
