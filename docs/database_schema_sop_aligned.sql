-- ========================================
-- MOPPA系统数据库结构（与SOP对齐版）
-- 支持完整的事件流：事件获取->出题->预测->真值回填->评分->排行与反馈
-- PostgreSQL 建表脚本
-- ========================================

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ========================================
-- 1. 基础信息表
-- ========================================

-- 用户表（增强，支持SOP中的角色体系）
-- 存储系统用户信息，对应SOP中定义的5类角色
CREATE TABLE "user" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 用户唯一标识符
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'intelligence_expert', 'algorithm_engineer', 'platform_engineer', 'operator', 'auditor', 'data_analyst')), -- 角色完全对齐SOP
    username VARCHAR(100) UNIQUE NOT NULL,                             -- 用户名，唯一
    password VARCHAR(255) NOT NULL,                                     -- 密码，加密存储
    email VARCHAR(255),                                                 -- 电子邮箱地址，可选
    is_active BOOLEAN DEFAULT true,                                     -- 账户是否激活
    permissions JSONB,                                                  -- 用户权限配置
    last_login_at TIMESTAMP WITH TIME ZONE,                             -- 最后登录时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 模型表（增强，增加更多模型属性）
-- 存储AI模型配置信息，用于S4阶段模型预测
CREATE TABLE model (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 模型唯一标识符
    name VARCHAR(100) NOT NULL,                                         -- 模型展示名称
    identifier VARCHAR(100) UNIQUE NOT NULL,                            -- 模型唯一标识名称
    version VARCHAR(20) DEFAULT 'v1.0',                                 -- 模型版本号
    url VARCHAR(500) NOT NULL,                                          -- 模型API访问地址
    api_key TEXT ENCRYPTED,                                             -- API密钥，加密存储
    provider VARCHAR(50) CHECK (provider IN ('openai', 'claude', 'custom', 'internal')), -- 模型提供商
    max_tokens INTEGER DEFAULT 4096,                                    -- 最大token数限制
    temperature NUMERIC(3,2) DEFAULT 0.7,                               -- AI生成随机性参数
    is_available BOOLEAN DEFAULT true,                                  -- 模型是否可用
    performance_metrics JSONB,                                          -- 模型性能指标（平均准确率、响应时间等）
    last_used_at TIMESTAMP WITH TIME ZONE,                              -- 最后使用时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- ========================================
-- 2. 配置管理表（S0阶段）
-- ========================================

-- 数据源配置表
-- 管理外部数据源，S0阶段配置的核心内容
CREATE TABLE data_source (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 数据源唯一标识符
    name VARCHAR(100) UNIQUE NOT NULL,                                  -- 数据源名称
    source_system VARCHAR(100) NOT NULL,                                -- 来源系统标识（对应SOP的source字段）
    type VARCHAR(50) NOT NULL CHECK (type IN ('api', 'database', 'file', 'websocket')),
    connection_config JSONB ENCRYPTED,                                  -- 连接配置，加密存储
    credibility_level INTEGER DEFAULT 3 CHECK (credibility_level >= 1 AND credibility_level <= 5), -- 可信度等级
    is_active BOOLEAN DEFAULT true,
    sync_frequency INTERVAL DEFAULT '1 hour',                           -- 同步频率
    last_sync_at TIMESTAMP WITH TIME ZONE,
    version VARCHAR(20) DEFAULT 'v1.0',                                 -- 配置版本号
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- ====== 提取数据源配置表 ======
-- 管理数据的提取策略
CREATE TABLE extraction_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    data_source_id UUID NOT NULL REFERENCES data_source(id),
    extraction_type VARCHAR(50) NOT NULL CHECK (extraction_type IN ('full', 'incremental', 'streaming')),
    schedule_config JSONB,                                              -- 调度配置
    retry_policy JSONB,                                                 -- 重试策略
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id)
);

-- 规则等级配置表（S0阶段）
-- 配置L1-L4等级的过滤规则
CREATE TABLE rule_level_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level INTEGER UNIQUE NOT NULL CHECK (level >= 1 AND level <= 4),   -- L1-L4等级
    level_name VARCHAR(50) NOT NULL,                                    -- 等级名称（如：基础、中级、高级、专家级）
    description TEXT,                                                   -- 等级描述
    weight NUMERIC(3,2) DEFAULT 1.0 CHECK (weight > 0),                -- 等级权重
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 事件过滤规则表（增强，S1阶段使用）
-- 存储事件过滤的具体规则，支持多层级过滤
CREATE TABLE event_filter_rule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 规则唯一标识符
    name VARCHAR(100) NOT NULL,                                          -- 规则名称
    level INTEGER NOT NULL REFERENCES rule_level_config(level),         -- 规则等级（L1-L4）
    filter_expression TEXT NOT NULL,                                    -- 过滤表达式
    filter_config JSONB,                                                -- 过滤配置详情
    priority INTEGER DEFAULT 0,                                         -- 规则优先级
    pass_rate_threshold NUMERIC(5,2) CHECK (pass_rate_threshold >= 0 AND pass_rate_threshold <= 100), -- 通过率阈值
    is_active BOOLEAN DEFAULT true,
    version VARCHAR(20) DEFAULT 'v1.0',                                 -- 规则版本
    created_by UUID NOT NULL REFERENCES "user"(id),                     -- 创建者（情报专家或算法工程师）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- ========================================
-- 3. 问题模板与规则表（S0和S2阶段）
-- ========================================

-- 问题模板表（增强，完全支持SOP的模板体系）
-- 存储S2阶段自动出题的模板
CREATE TABLE question_template (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 模板唯一标识符
    name VARCHAR(100) NOT NULL,                                          -- 模板名称
    level INTEGER NOT NULL REFERENCES rule_level_config(level),         -- 问题等级（L1-L4）
    category VARCHAR(100),                                              -- 问题分类
    template_content TEXT NOT NULL,                                      -- 模板内容，支持变量替换
    variables JSONB,                                                    -- 模板变量定义
    generation_config JSONB,                                             -- 生成配置（答案空间、验证条件等）
    verification_conditions JSONB,                                       -- 可验证条件定义
    duplicate_check_window INTERVAL DEFAULT '7 days',                   -- 重复检查窗口期
    max_duplicate_rate NUMERIC(5,2) DEFAULT 5.0 CHECK (max_duplicate_rate >= 0 AND max_duplicate_rate <= 100), -- 最大重复率
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'deprecated')),
    version VARCHAR(20) DEFAULT 'v1.0',                                 -- 模板版本
    created_by UUID NOT NULL REFERENCES "user"(id),
    approved_by UUID REFERENCES "user"(id),                             -- 审批人（情报专家）
    usage_count INTEGER DEFAULT 0,                                      -- 使用次数统计
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 评分规则版本表（S0阶段配置，S6阶段使用）
-- 管理评分规则的版本，确保评分可复现
CREATE TABLE scoring_rule_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version VARCHAR(20) UNIQUE NOT NULL,                                 -- 版本号，如score.v1
    description TEXT,                                                   -- 版本描述
    dimensions JSONB NOT NULL,                                          -- 评分维度定义（维度、权重、满分等）
    calculation_formula TEXT,                                           -- 计算公式
    is_active BOOLEAN DEFAULT true,                                     -- 是否为当前活跃版本
    created_by UUID NOT NULL REFERENCES "user"(id),
    approved_by UUID REFERENCES "user"(id),                             -- 审批人
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id)
);

-- ========================================
-- 4. 核心业务表
-- ========================================

-- 事件表（S1阶段，完全符合SOP定义）
-- 存储标准化后的原始事件
CREATE TABLE event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 事件唯一标识符
    event_key VARCHAR(255) UNIQUE,                                      -- 事件唯一键（用于幂等）
    version VARCHAR(20) DEFAULT 'v1.0',                                 -- schema版本号
    content TEXT NOT NULL,                                               -- 事件原文（标准化后）
    source_system VARCHAR(100) NOT NULL REFERENCES data_source(source_system), -- 来源系统标识
    credibility_level INTEGER NOT NULL CHECK (credibility_level >= 1 AND credibility_level <= 5), -- 来源可信度
    event_time TIMESTAMP WITH TIME ZONE NOT NULL,                       -- 事件发生时间
    tags TEXT[],                                                         -- 分类标签数组
    metadata JSONB,                                                      -- 事件元数据
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    filter_status VARCHAR(20) DEFAULT 'pending' CHECK (filter_status IN ('pending', 'passed', 'filtered')), -- 过滤状态
    filter_reasons TEXT[],                                               -- 过滤原因标签
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT event_unique_key UNIQUE (event_key, version)              -- 确保事件+版本唯一
);

-- 问题表（S2-S3阶段，完全符合SOP定义）
-- 存储生成的问题
CREATE TABLE question (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 问题唯一标识符
    version VARCHAR(20) DEFAULT 'v1.0',                                 -- schema版本号
    event_id UUID NOT NULL REFERENCES event(id),                        -- 关联事件
    template_id UUID NOT NULL REFERENCES question_template(id),         -- 使用的模板
    level INTEGER NOT NULL REFERENCES rule_level_config(level),         -- 问题等级（L1-L4）
    content TEXT NOT NULL,                                               -- 题干
    answer_space JSONB,                                                 -- L1/L2答案空间（可选）
    verification_conditions JSONB,                                       -- 可验证条件
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,                          -- 截止时间
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'pending_review', 'published', 'closed', 'expired')),
    source_system VARCHAR(100) NOT NULL DEFAULT 'moppa',                 -- 来源系统标识
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    duplicate_check_hash TEXT,                                           -- 重复检查哈希值
    review_queue_id UUID,                                                -- 审核队列ID
    created_by UUID NOT NULL REFERENCES "user"(id),
    published_by UUID REFERENCES "user"(id),                            -- 发布人
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 审核清单表（S3阶段）
-- 管理人工质检的审核记录
CREATE TABLE checklist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES question(id),                   -- 关联问题
    reviewer_id UUID NOT NULL REFERENCES "user"(id),                    -- 审核人ID
    review_type VARCHAR(20) NOT NULL CHECK (review_type IN ('initial', 'spot_check', 'duplicate_review')), -- 审核类型
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('pass', 'reject', 'modify')), -- 审核结论
    reason_tags TEXT[],                                                  -- 驳回原因标签
    feedback TEXT,                                                       -- 详细反馈
    evidence_links TEXT[],                                               -- 证据链接
    is_verifiable BOOLEAN,                                              -- 可验证条件是否明确
    is_trust_evidence BOOLEAN,                                           -- 证据来源是否可信
    review_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 预测表（S4阶段，完全符合SOP定义）
-- 存储模型预测结果
CREATE TABLE prediction (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 预测记录唯一标识符
    version VARCHAR(20) DEFAULT 'v1.0',                                 -- schema版本号
    question_id UUID NOT NULL REFERENCES question(id),                  -- 关联问题
    model_id UUID NOT NULL REFERENCES model(id),                        -- 预测模型
    prediction_content TEXT NOT NULL,                                    -- 预测内容
    confidence NUMERIC(5,2) CHECK (confidence >= 0 AND confidence <= 100), -- 置信度（0-100）
    inference_time_ms INTEGER,                                           -- 推理耗时（毫秒）
    token_usage JSONB,                                                   -- Token使用统计
    source_system VARCHAR(100) NOT NULL DEFAULT 'moppa',                 -- 来源系统标识
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    task_execution_id UUID,                                              -- 任务执行ID
    submission_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- 提交时间
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,                                                  -- 错误信息
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 真实答案表（S5阶段，独立存储）
-- 存储问题的真实答案，来自外部真值系统
CREATE TABLE ground_truth (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 真值记录唯一标识符
    version VARCHAR(20) DEFAULT 'v1.0',                                 -- schema版本号
    question_id UUID NOT NULL REFERENCES question(id),                  -- 关联问题
    answer TEXT NOT NULL,                                                -- 真实答案
    evidence_links TEXT[],                                               -- 证据链接
    publish_time TIMESTAMP WITH TIME ZONE NOT NULL,                      -- 答案发布时间
    credibility_level INTEGER NOT NULL CHECK (credibility_level >= 1 AND credibility_level <= 5), -- 可信度等级
    source_system VARCHAR(100) NOT NULL,                                -- 答案来源系统
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    extracted_by UUID NOT NULL REFERENCES "user"(id),                   -- 提取者
    verified_by UUID REFERENCES "user"(id),                             -- 验证者
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(question_id, version)                                         -- 每个问题每个版本只能有一个真值
);

-- 评分记录表（S6阶段，支持多维度评分）
-- 存储详细的评分记录
CREATE TABLE score_record (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 评分记录唯一标识符
    version VARCHAR(20) DEFAULT 'v1.0',                                 -- schema版本号
    prediction_id UUID NOT NULL REFERENCES prediction(id),              -- 关联预测
    ground_truth_id UUID NOT NULL REFERENCES ground_truth(id),           -- 关联真值
    scoring_rule_version VARCHAR(20) NOT NULL REFERENCES scoring_rule_version(version), -- 评分规则版本
    dimension_scores JSONB NOT NULL,                                     -- 维度得分（JSON格式）
    total_score NUMERIC(5,2) CHECK (total_score >= 0 AND total_score <= 100), -- 总分
    scoring_method VARCHAR(20) NOT NULL CHECK (scoring_method IN ('rule', 'ai', 'hybrid')), -- 评分方式
    weight_config JSONB,                                                 -- 权重配置快照
    source_system VARCHAR(100) NOT NULL DEFAULT 'moppa',                 -- 来源系统标识
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    calculated_by UUID NOT NULL REFERENCES "user"(id),                  -- 计算者
    calculation_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- 计算时间
    is_reproducible BOOLEAN DEFAULT true,                               -- 评分是否可复现
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id)
);

-- 榜单表（S6阶段输出）
-- 存储各期榜单数据
CREATE TABLE leaderboard (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle_type VARCHAR(20) NOT NULL CHECK (cycle_type IN ('weekly', 'monthly', 'quarterly')), -- 榜单周期
    cycle_start_time TIMESTAMP WITH TIME ZONE NOT NULL,                  -- 周期开始时间
    cycle_end_time TIMESTAMP WITH TIME ZONE NOT NULL,                    -- 周期结束时间
    level INTEGER REFERENCES rule_level_config(level),                   -- 等级分榜（NULL表示总榜）
    scoring_rule_version VARCHAR(20) NOT NULL REFERENCES scoring_rule_version(version), -- 使用的评分规则版本
    rankings JSONB NOT NULL,                                             -- 排名数据
    summary_metrics JSONB,                                               -- 摘要指标
    is_published BOOLEAN DEFAULT false,                                  -- 是否已发布
    published_by UUID REFERENCES "user"(id),                             -- 发布人
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(cycle_type, cycle_start_time, cycle_end_time, level)         -- 确保榜单唯一性
);

-- ========================================
-- 5. 社区反馈表（S7阶段）
-- ========================================

-- 反馈表
-- 存储社区反馈和评论
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(20) NOT NULL CHECK (type IN ('comment', 'question', 'improvement')), -- 反馈类型
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('question', 'prediction', 'score', 'leaderboard')), -- 目标对象类型
    target_id UUID NOT NULL,                                             -- 目标对象ID
    user_id UUID NOT NULL REFERENCES "user"(id),                        -- 反馈者
    content TEXT NOT NULL,                                               -- 反馈内容
    attachments JSONB,                                                   -- 附件
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'processing', 'resolved', 'closed')), -- 处理状态
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')), -- 优先级
    assigned_to UUID REFERENCES "user"(id),                             -- 分配给谁处理
    resolution TEXT,                                                     -- 解决方案
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 人工预测表（S7阶段）
-- 存储社区用户的预测
CREATE TABLE community_prediction (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES question(id),                  -- 关联问题
    user_id UUID NOT NULL REFERENCES "user"(id),                        -- 预测者
    prediction_content TEXT NOT NULL,                                    -- 预测内容
    confidence NUMERIC(5,2) CHECK (confidence >= 0 AND confidence <= 100), -- 置信度
    reasoning TEXT,                                                      -- 推理过程
    source_system VARCHAR(100) NOT NULL DEFAULT 'moppa',                 -- 来源系统标识
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- ========================================
-- 6. 系统管理表
-- ========================================

-- 变更管理表（确保所有变更可追溯）
-- 存储重要的系统变更记录
CREATE TABLE change_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    change_id VARCHAR(100) UNIQUE NOT NULL,                              -- 变更ID（用于追溯）
    change_type VARCHAR(50) NOT NULL,                                     -- 变更类型（规则/模板/权重等）
    target_type VARCHAR(50) NOT NULL,                                    -- 变更目标类型
    target_id UUID,                                                      -- 变更目标ID
    description TEXT NOT NULL,                                           -- 变更描述
    old_value JSONB,                                                     -- 变更前值
    new_value JSONB,                                                     -- 变更后值
    status VARCHAR(20) NOT NULL CHECK (status IN ('request', 'review', 'approved', 'rejected', 'deployed', 'rollback')), -- 变更状态
    requester_id UUID NOT NULL REFERENCES "user"(id),                    -- 请求者
    reviewer_id UUID REFERENCES "user"(id),                              -- 审查者
    approver_id UUID REFERENCES "user"(id),                              -- 批准者
    deployment_time TIMESTAMP WITH TIME ZONE,                            -- 部署时间
    rollback_time TIMESTAMP WITH TIME ZONE,                              -- 回滚时间
    grey_scale_percentage INTEGER CHECK (grey_scale_percentage >= 0 AND grey_scale_percentage <= 100), -- 灰度比例
    observation_window INTERVAL DEFAULT '1 day',                         -- 观察窗口
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id)
);

-- 任务执行表（增强版，支持完整的调度策略）
-- 记录任务的执行情况，实现幂等和重试
CREATE TABLE task_execution (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type VARCHAR(50) NOT NULL,                                      -- 任务类型
    business_id UUID,                                                    -- 业务ID
    date_window TIMESTAMP WITH TIME ZONE,                                -- 日期窗口
    model_id UUID REFERENCES model(id),                                  -- 模型ID（如适用）
    idempotency_key TEXT UNIQUE NOT NULL,                                -- 幂等键：task_type+business_id+date_window+model_id
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'dead_letter')), -- 执行状态
    attempt_count INTEGER DEFAULT 0,                                     -- 尝试次数
    max_attempts INTEGER DEFAULT 3,                                      -- 最大尝试次数
    next_retry_at TIMESTAMP WITH TIME ZONE,                              -- 下次重试时间
    retry_intervals JSONB DEFAULT '[1, 5, 15]',                          -- 重试间隔（分钟）
    timeout_seconds INTEGER DEFAULT 3600,                                -- 超时时间（秒）
    result JSONB,                                                        -- 执行结果
    error_message TEXT,                                                  -- 错误信息
    metrics JSONB,                                                       -- 执行指标
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE
);

-- 系统配置表（增强版）
-- 存储系统级配置
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,                                    -- 配置键
    value JSONB NOT NULL,                                                -- 配置值
    description TEXT,                                                    -- 配置描述
    category VARCHAR(50),                                                -- 配置分类
    is_encrypted BOOLEAN DEFAULT false,                                  -- 是否加密
    is_sensitive BOOLEAN DEFAULT false,                                  -- 是否敏感
    change_id VARCHAR(100) REFERENCES change_log(change_id),             -- 关联变更ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id)
);

-- ========================================
-- 7. 指标监控表
-- ========================================

-- 质量指标表（存储SOP定义的核心指标）
CREATE TABLE quality_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,                                   -- 指标名称
    metric_type VARCHAR(50) NOT NULL CHECK (metric_type IN ('efficiency', 'data_quality', 'model_performance', 'operation_quality')), -- 指标类型
    value NUMERIC NOT NULL,                                               -- 指标值
    threshold_value NUMERIC,                                             -- 阈值
    unit VARCHAR(20),                                                    -- 单位
    date_window DATE NOT NULL,                                           -- 日期窗口
    dimensions JSONB,                                                    -- 维度（如模型ID、等级等）
    status VARCHAR(20) DEFAULT 'normal' CHECK (status IN ('normal', 'warning', 'critical')), -- 状态
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_name, date_window, COALESCE((dimensions->>'model_id')::TEXT, ''))
);

-- 异常记录表（Runbook）
-- 记录系统异常和处理过程
CREATE TABLE incident_record (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id VARCHAR(100) UNIQUE NOT NULL,                            -- 事故ID
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('P0', 'P1', 'P2', 'P3')), -- 严重程度
    title TEXT NOT NULL,                                                 -- 事故标题
    description TEXT NOT NULL,                                           -- 详细描述
    affected_scope TEXT,                                                 -- 影响范围
    detection_time TIMESTAMP WITH TIME ZONE NOT NULL,                    -- 发现时间
    response_time TIMESTAMP WITH TIME ZONE,                              -- 响应时间
    resolution_time TIMESTAMP WITH TIME ZONE,                            -- 解决时间
    root_cause TEXT,                                                     -- 根本原因
    resolution TEXT,                                                     -- 解决方案
    prevention_measures TEXT,                                            -- 预防措施
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'investigating', 'resolved', 'closed')), -- 处理状态
    assigned_to UUID REFERENCES "user"(id),                              -- 分配给谁
    notification_sent BOOLEAN DEFAULT false,                             -- 是否已发送通知
    trace_id UUID NOT NULL,                                              -- 链路追踪ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES "user"(id)
);

-- ========================================
-- 8. 索引创建
-- ========================================

-- 为trace_id创建索引（所有核心表）
CREATE INDEX idx_event_trace_id ON event(trace_id);
CREATE INDEX idx_question_trace_id ON question(trace_id);
CREATE INDEX idx_prediction_trace_id ON prediction(trace_id);
CREATE INDEX idx_ground_truth_trace_id ON ground_truth(trace_id);
CREATE INDEX idx_score_record_trace_id ON score_record(trace_id);

-- 为version创建索引
CREATE INDEX idx_event_version ON event(version);
CREATE INDEX idx_question_version ON question(version);
CREATE INDEX idx_prediction_version ON prediction(version);
CREATE INDEX idx_ground_truth_version ON ground_truth(version);

-- 为source_system创建索引
CREATE INDEX idx_event_source_system ON event(source_system);
CREATE INDEX idx_prediction_source_system ON prediction(source_system);
CREATE INDEX idx_score_record_source_system ON score_record(source_system);

-- 为credibility_level创建索引
CREATE INDEX idx_event_credibility_level ON event(credibility_level);
CREATE INDEX idx_ground_truth_credibility_level ON ground_truth(credibility_level);

-- 其他关键索引
CREATE INDEX idx_question_level ON question(level);
CREATE INDEX idx_prediction_model_id ON prediction(model_id);
CREATE INDEX idx_prediction_confidence ON prediction(confidence);
CREATE INDEX idx_question_deadline ON question(deadline);
CREATE INDEX idx_question_status ON question(status);
CREATE INDEX idx_score_record_total_score ON score_record(total_score);
CREATE INDEX idx_leaderboard_cycle ON leaderboard(cycle_type, cycle_start_time);

-- 唯一索引
CREATE UNIQUE INDEX idx_task_execution_idempotency ON task_execution(idempotency_key);

-- ========================================
-- 9. 触发器和函数
-- ========================================

-- 更新updated_at的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有需要的表添加触发器
CREATE TRIGGER update_user_updated_at BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_model_updated_at BEFORE UPDATE ON model FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_source_updated_at BEFORE UPDATE ON data_source FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_rule_level_config_updated_at BEFORE UPDATE ON rule_level_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_event_filter_rule_updated_at BEFORE UPDATE ON event_filter_rule FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_question_template_updated_at BEFORE UPDATE ON question_template FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_scoring_rule_version_updated_at BEFORE UPDATE ON scoring_rule_version FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_event_updated_at BEFORE UPDATE ON event FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_question_updated_at BEFORE UPDATE ON question FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_prediction_updated_at BEFORE UPDATE ON prediction FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ground_truth_updated_at BEFORE UPDATE ON ground_truth FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_score_record_updated_at BEFORE UPDATE ON score_record FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_leaderboard_updated_at BEFORE UPDATE ON leaderboard FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_feedback_updated_at BEFORE UPDATE ON feedback FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_change_log_updated_at BEFORE UPDATE ON change_log FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_task_execution_updated_at BEFORE UPDATE ON task_execution FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- 10. 视图
-- ========================================

-- 模型性能视图（支持S4阶段监控）
CREATE VIEW model_performance_view AS
SELECT
    m.id,
    m.name,
    m.identifier,
    p.level,
    COUNT(p.id) as total_predictions,
    AVG(p.confidence) as avg_confidence,
    AVG(p.inference_time_ms) as avg_inference_time,
    AVG(sf.total_score) as avg_score,
    MAX(p.submission_time) as last_prediction_time
FROM model m
LEFT JOIN prediction p ON m.id = p.model_id
LEFT JOIN score_record sf ON p.id = sf.prediction_id
WHERE m.deleted_at IS NULL AND p.deleted_at IS NULL
GROUP BY m.id, m.name, m.identifier, p.level;

-- 质量指标汇总视图（支持SOP指标体系）
CREATE VIEW quality_metrics_summary AS
SELECT
    DATE_TRUNC('day', created_at) as metric_date,
    metric_type,
    metric_name,
    AVG(value) as avg_value,
    MAX(value) as max_value,
    MIN(value) as min_value,
    COUNT(*) as sample_count
FROM quality_metrics
GROUP BY DATE_TRUNC('day', created_at), metric_type, metric_name
ORDER BY metric_date DESC;

-- 完整流程追踪视图
CREATE VIEW process_trace_view AS
SELECT
    e.id as event_id,
    e.trace_id,
    e.content as event_content,
    q.id as question_id,
    q.content as question_content,
    q.level as question_level,
    q.deadline as question_deadline,
    p.id as prediction_id,
    p.model_id,
    p.prediction_content,
    p.confidence,
    gt.id as ground_truth_id,
    gt.answer as ground_truth_answer,
    gt.publish_time as ground_truth_publish_time,
    sr.id as score_id,
    sr.total_score,
    sr.scoring_method
FROM event e
LEFT JOIN question q ON e.id = q.event_id
LEFT JOIN prediction p ON q.id = p.question_id
LEFT JOIN ground_truth gt ON q.id = gt.question_id
LEFT JOIN score_record sr ON p.id = sr.prediction_id AND gt.id = sr.ground_truth_id
WHERE e.trace_id IS NOT NULL
ORDER BY e.created_at, q.created_at, p.submission_time;

-- ========================================
-- 11. 初始化数据
-- ========================================

-- 创建默认系统用户
INSERT INTO "user" (role, username, password, email) VALUES
('admin', 'admin', crypt('admin123', gen_salt('bf')), 'admin@moppa.com'),
('intelligence_expert', 'expert001', crypt('expert123', gen_salt('bf')), 'expert@moppa.com'),
('algorithm_engineer', 'algo001', crypt('algo123', gen_salt('bf')), 'algo@moppa.com'),
('platform_engineer', 'platform001', crypt('platform123', gen_salt('bf')), 'platform@moppa.com');

-- 初始化规则等级配置（L1-L4）
INSERT INTO rule_level_config (level, level_name, description, weight) VALUES
(1, 'L1-基础', '基础级别问题， evaluating basic understanding', 1.0),
(2, 'L2-中级', '中等级别问题， requiring analysis and interpretation', 1.5),
(3, 'L3-高级', '高级别问题， requiring deep analysis and prediction', 2.0),
(4, 'L4-专家级', '专家级别问题， comprehensive evaluation and synthesis', 3.0);

-- 初始评分规则版本
INSERT INTO scoring_rule_version (version, description, dimensions, calculation_formula) VALUES
('score.v1', '基础评分规则版本', '{
    "accuracy": {"weight": 0.6, "max_score": 60},
    "timeliness": {"weight": 0.2, "max_score": 20},
    "confidence": {"weight": 0.2, "max_score": 20}
}', '总分 = 准确性得分 * 0.6 + 时效性得分 * 0.2 + 置信度得分 * 0.2');

-- 初始系统配置
INSERT INTO system_config (key, value, description, category) VALUES
('quality_gate.question_dup_rate_max', '5.0', '最大重复率阈值', 'quality'),
('quality_gate.unverifiable_rate_max', '3.0', '最大不可判定率阈值', 'quality'),
('quality_gate.truth_coverage_min', '97.0', '最小真值覆盖率', 'quality'),
('quality_gate.delayed_truth_rate_max', '2.0', '最大延迟回填率', 'quality'),
('schedule.main_cron', '0 2 * * *', '每日主任务调度时间', 'schedule'),
('schedule.compensate_cron', '0 * * * *', '每小时补偿任务', 'schedule'),
('performance.model_call_timeout', '120', '模型调用超时时间（秒）', 'performance'),
('performance.batch_timeout', '1800', '批次处理超时时间（秒）', 'performance');

-- ========================================
-- 12. 注意事项
-- ========================================
/*
设计要点：
1. 完全对齐SOP文档定义的实体和字段
2. 支持L1-L4等级体系
3. 贯穿全流程的trace_id追踪
4. 版本化管理确保可复现
5. 完整的审计和变更管理
6. 支持社区反馈和人工预测
7. 完备的指标监控体系
8. 幂等性和重试策略实现
9. 密钥加密存储
10. 软删除支持
11. 完善的索引策略
12. RACI角色权限体系映射
*/