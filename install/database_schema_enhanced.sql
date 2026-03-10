-- ========================================
-- 事件驱动问答评价系统数据库结构（增强版）
-- 基于详细流程设计优化
-- PostgreSQL 建表脚本
-- ========================================

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ========================================
-- 1. 基础信息表
-- ========================================

-- 用户表
-- 存储系统用户信息，包括管理员、操作员、评审员和API服务账号
CREATE TABLE "user" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 用户唯一标识符
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'operator', 'reviewer', 'api_service')), -- 用户角色：管理员/操作员/评审员/API服务
    username VARCHAR(100) UNIQUE NOT NULL,                             -- 用户名，唯一
    password VARCHAR(255) NOT NULL,                                     -- 密码，加密存储
    email VARCHAR(255),                                                 -- 电子邮箱地址，可选
    is_active BOOLEAN DEFAULT true,                                     -- 账户是否激活
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,      -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,      -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                              -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                 -- 软删除时间，NULL表示未删除
);

-- 模型表（增强版）
-- 存储AI模型配置信息，支持OpenAI、Claude、自定义和内部模型
CREATE TABLE model (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 模型唯一标识符
    model VARCHAR(100) NOT NULL,                                         -- 模型展示名称，如"GPT-4"
    model_name VARCHAR(100) UNIQUE NOT NULL,                             -- 模型唯一标识名称，如"gpt-4"
    url VARCHAR(500) NOT NULL,                                           -- 模型API访问地址
    api_key TEXT NOT NULL,                                               -- API密钥，使用pgcrypto加密存储
    model_type VARCHAR(50) NOT NULL CHECK (model_type IN ('openai', 'claude', 'custom', 'internal')), -- 模型类型分类
    max_tokens INTEGER DEFAULT 4096,                                     -- 最大token数限制
    temperature NUMERIC(3,2) DEFAULT 0.7 CHECK (temperature >= 0 AND temperature <= 2), -- AI生成随机性参数
    is_available BOOLEAN DEFAULT true,                                   -- 模型是否可用
    last_used_at TIMESTAMP WITH TIME ZONE,                               -- 最后使用时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,      -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,      -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                              -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                 -- 软删除时间，NULL表示未删除
);

-- ========================================
-- 2. 事件管理相关表
-- ========================================

-- 数据源表（新增）
-- 管理外部数据源配置，包括烽火、报告等系统的连接信息
CREATE TABLE data_source (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 数据源唯一标识符
    name VARCHAR(100) UNIQUE NOT NULL,                                   -- 数据源名称，如"烽火"、"报告"
    type VARCHAR(50) NOT NULL CHECK (type IN ('api', 'database', 'file', 'websocket')), -- 数据源类型
    connection_config JSONB NOT NULL,                                    -- 连接配置（包含URL、认证信息等），JSON格式
    is_active BOOLEAN DEFAULT true,                                      -- 数据源是否启用
    last_sync_at TIMESTAMP WITH TIME ZONE,                               -- 最后同步时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,      -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,      -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                              -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                 -- 软删除时间，NULL表示未删除
);

-- 事件过滤规则表（增强版）
-- 存储事件过滤的规则配置，用于判断哪些事件需要进行后续处理
CREATE TABLE event_filter_rule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                     -- 规则唯一标识符
    name VARCHAR(100) NOT NULL,                                          -- 规则名称，方便识别
    rule TEXT NOT NULL,                                                  -- 规则描述，如"包含关键词'安全'"
    rule_config JSONB,                                                   -- 规则详细配置，包含过滤条件、权重等
    level INTEGER NOT NULL CHECK (level >= 1 AND level <= 10),          -- 规则优先级，1-10，数字越大优先级越高
    source_user_id UUID NOT NULL REFERENCES "user"(id),                 -- 规则创建者ID
    is_open BOOLEAN DEFAULT true,                                        -- 规则是否启用
    filter_count INTEGER DEFAULT 0,                                     -- 过滤次数统计，用于监控规则使用情况
    last_used_at TIMESTAMP WITH TIME ZONE,                               -- 最后使用时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,      -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,      -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                              -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                 -- 软删除时间，NULL表示未删除
);

-- 来源事件表（增强版）
-- 存储从外部数据源获取的原始事件数据，支持烽火、报告等多种数据源
CREATE TABLE source_event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 事件唯一标识符
    data_source_id UUID NOT NULL REFERENCES data_source(id),               -- 数据源ID，关联数据源表
    raw_data JSONB NOT NULL,                                               -- 原始事件数据，JSON格式存储
    event_key VARCHAR(255),                                                -- 事件唯一标识键，用于去重和追踪
    extracted_content TEXT,                                                -- 从原始数据中提取的标准化事件内容
    rule_id UUID REFERENCES event_filter_rule(id),                         -- 匹配的过滤规则ID
    level INTEGER CHECK (level >= 1 AND level <= 10),                      -- 事件级别，1-10，数字越大重要级越高
    tags TEXT[],                                                           -- 事件标签数组，用于分类和检索
    metadata JSONB,                                                        -- 补充元数据，存储额外的结构化信息
    processed_at TIMESTAMP WITH TIME ZONE,                                 -- 事件处理完成时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,        -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,        -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                                 -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                    -- 软删除时间，NULL表示未删除
);

-- 事件表（增强版）
-- 存储经过人工审核确认后的事件，是后续问题生成的基础数据
CREATE TABLE event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 事件唯一标识符
    source_event_id UUID REFERENCES source_event(id),                       -- 关联的来源事件ID
    event_content TEXT NOT NULL,                                            -- 事件完整内容，经过人工确认
    tags TEXT[],                                                            -- 事件标签数组，用于分类和检索
    rules TEXT,                                                             -- 命中规则详情，记录所有匹配的过滤规则
    level INTEGER CHECK (level >= 1 AND level <= 10),                       -- 事件级别，1-10，用于问题生成优先级
    source_user_id UUID NOT NULL REFERENCES "user"(id),                     -- 人工审核员ID，关联用户表
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')), -- 事件处理状态
    processed_count INTEGER DEFAULT 0,                                      -- 处理次数，用于追踪处理历史
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                                  -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                     -- 软删除时间，NULL表示未删除
);

-- ========================================
-- 3. 问题模板相关表
-- ========================================

-- 提示词模板表（新增）
-- 存储AI交互使用的提示词模板，支持事件过滤、问题生成和答案评价等场景
CREATE TABLE prompt_template (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 模板唯一标识符
    name VARCHAR(100) UNIQUE NOT NULL,                                      -- 模板名称，唯一标识
    type VARCHAR(50) NOT NULL CHECK (type IN ('event_filter', 'question_generate', 'answer_evaluate')), -- 模板类型：事件过滤/问题生成/答案评价
    template TEXT NOT NULL,                                                 -- 模板内容，支持变量占位符替换
    variables JSONB,                                                        -- 模板变量定义，说明需要的参数及其格式
    version INTEGER DEFAULT 1,                                             -- 模板版本号，支持版本管理
    is_active BOOLEAN DEFAULT true,                                         -- 模板是否启用
    usage_count INTEGER DEFAULT 0,                                         -- 使用次数统计
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                                  -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                     -- 软删除时间，NULL表示未删除
);

-- 问题模板表（增强版）
-- 存储问题生成模板，定义如何根据事件内容生成特定类型的问题
CREATE TABLE question_template (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 模板唯一标识符
    template TEXT NOT NULL,                                                 -- 问题模板内容，包含占位符
    field VARCHAR(100) NOT NULL,                                            -- 问题所属领域或字段，如"安全"、"运维"等
    level INTEGER CHECK (level >= 1 AND level <= 10),                       -- 模板级别，与事件级别对应
    types TEXT[],                                                            -- 问题类型数组，如单选、多选、填空等
    source_user_id UUID NOT NULL REFERENCES "user"(id),                     -- 模板创建者ID，关联用户表
    is_active BOOLEAN DEFAULT true,                                         -- 模板是否启用
    usage_count INTEGER DEFAULT 0,                                         -- 使用次数统计，用于评估模板效果
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                                  -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                     -- 软删除时间，NULL表示未删除
);

-- 答案范围表（新增）
-- 定义问题答案的有效范围和验证规则，支持多种数据类型
CREATE TABLE answer_scope (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 范围定义唯一标识符
    question_template_id UUID REFERENCES question_template(id),             -- 关联的问题模板ID
    scope_type VARCHAR(50) NOT NULL CHECK (scope_type IN ('text', 'choice', 'number', 'date', 'json')), -- 答案类型：文本/选择/数字/日期/JSON
    allowed_values JSONB,                                                    -- 允许的值范围配置，如选项列表、数值区间等
    validation_rules JSONB,                                                 -- 答案验证规则，如长度限制、格式要求等
    default_value TEXT,                                                     -- 默认答案值
    is_required BOOLEAN DEFAULT false,                                      -- 是否必填
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                                  -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                     -- 软删除时间，NULL表示未删除
);

-- 事件问题关联表（新增，处理多对多关系）
-- 管理事件与问题之间的多对多关联关系，支持一个事件关联多个问题
CREATE TABLE event_question_relation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 关联关系唯一标识符
    event_id UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,          -- 事件ID，级联删除
    question_id UUID NOT NULL REFERENCES event_question(id) ON DELETE CASCADE, -- 问题ID，级联删除
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 关联创建时间
    UNIQUE(event_id, question_id)                                           -- 确保事件和问题的唯一组合
);

-- 事件问题表（增强版）
-- 存储基于事件生成的问题，支持AI生成、手动创建和模板生成等多种方式
CREATE TABLE event_question (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 问题唯一标识符
    question_template_id UUID NOT NULL REFERENCES question_template(id),    -- 关联的问题模板ID
    question TEXT NOT NULL,                                                 -- 问题完整内容
    event_count INTEGER DEFAULT 1,                                         -- 关联的事件数量，用于统计问题复用情况
    answer_scope_id UUID REFERENCES answer_scope(id),                       -- 答案范围ID，定义答案格式和验证规则
    question_type VARCHAR(50) CHECK (question_type IN ('single_choice', 'multiple_choice', 'text', 'number', 'date')), -- 问题类型：单选/多选/文本/数字/日期
    real_answer TEXT,                                                       -- 标准答案，用于评价预测结果
    end_time TIMESTAMP WITH TIME ZONE,                                      -- 问题截止时间，过期后状态变为expired
    confirm_user_id UUID REFERENCES "user"(id),                             -- 问题确认人ID，关联用户表
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'closed', 'expired')), -- 问题状态：开放/已关闭/已过期
    generation_method VARCHAR(50) DEFAULT 'ai' CHECK (generation_method IN ('ai', 'manual', 'template')), -- 生成方式：AI生成/手动创建/模板生成
    ai_model_id UUID REFERENCES model(id),                                  -- 生成时使用的AI模型ID
    generation_prompt TEXT,                                                 -- 生成时使用的提示词内容
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                                  -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                     -- 软删除时间，NULL表示未删除
);

-- ========================================
-- 4. 评价系统相关表
-- ========================================

-- 预测问题答案评分规则表（增强版）
-- 存储问题答案的评分规则，支持对模型答案和用户答案进行评分
CREATE TABLE predict_question_answer_score_rule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 规则唯一标识符
    question_template_id UUID NOT NULL REFERENCES question_template(id),    -- 关联的问题模板ID
    name VARCHAR(100) NOT NULL,                                              -- 规则名称，便于识别和管理
    rule TEXT NOT NULL,                                                      -- 规则描述，说明评分逻辑和标准
    rule_config JSONB,                                                       -- 评分规则详细配置，包含评分维度、权重等
    source_user_id UUID NOT NULL REFERENCES "user"(id),                      -- 规则创建者ID，关联用户表
    is_open BOOLEAN DEFAULT true,                                           -- 规则是否启用
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN ('model', 'user', 'both')), -- 规则适用类型：模型答案/用户答案/两者都适用
    apply_count INTEGER DEFAULT 0,                                         -- 应用次数统计，用于监控规则使用情况
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                                  -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                     -- 软删除时间，NULL表示未删除
);

-- 模型预测问题答案表（增强版）
-- 存储AI模型对生成问题的预测答案，包含详细的使用和评分信息
CREATE TABLE model_predict_question_answer (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 预测记录唯一标识符
    event_question_id UUID NOT NULL REFERENCES event_question(id),          -- 关联的事件问题ID
    answer TEXT NOT NULL,                                                   -- 模型给出的答案内容
    model_id UUID NOT NULL REFERENCES model(id),                            -- 使用的AI模型ID，关联模型表
    is_right BOOLEAN,                                                       -- 答案是否正确，与标准答案对比得出
    reason TEXT,                                                             -- 模型的思考原因或解释，用于分析预测逻辑
    score NUMERIC(5,2) CHECK (score >= 0 AND score <= 100),                -- 答案评分，0-100分
    evaluation_rule_id UUID REFERENCES predict_question_answer_score_rule(id), -- 使用的评分规则ID
    prompt_tokens INTEGER,                                                  -- 提示词消耗的token数量
    completion_tokens INTEGER,                                              -- 答案生成消耗的token数量
    total_tokens INTEGER,                                                   -- 总token消耗数量
    response_time_ms INTEGER,                                               -- 模型响应时间，单位毫秒
    error_message TEXT,                                                     -- 错误信息，记录预测过程中的异常
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')), -- 预测状态：待处理/处理中/已完成/失败
    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,         -- 预测创建时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 记录创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                                  -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                     -- 软删除时间，NULL表示未删除
);

-- 用户预测问题答案表（增强版）
-- 存储用户（评审员）对生成问题的答案，用于评价和对比AI模型的预测能力
CREATE TABLE user_predict_question_answer (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 答案记录唯一标识符
    event_question_id UUID NOT NULL REFERENCES event_question(id),          -- 关联的事件问题ID
    answer TEXT NOT NULL,                                                   -- 用户给出的答案内容
    user_id UUID NOT NULL REFERENCES "user"(id),                            -- 答题用户ID，关联用户表
    is_right BOOLEAN,                                                       -- 答案是否正确，与标准答案对比得出
    reason TEXT,                                                             -- 用户的思考原因或解释
    score NUMERIC(5,2) CHECK (score >= 0 AND score <= 100),                -- 答案评分，0-100分
    evaluation_rule_id UUID REFERENCES predict_question_answer_score_rule(id), -- 使用的评分规则ID
    answer_time_seconds INTEGER,                                            -- 答题用时，单位秒，用于评估答题效率
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 最后更新时间
    updated_by UUID REFERENCES "user"(id),                                  -- 更新者ID，关联用户表
    deleted_at TIMESTAMP WITH TIME ZONE                                     -- 软删除时间，NULL表示未删除
);

-- ========================================
-- 5. 任务调度和执行记录表（新增）
-- ========================================

-- 任务定义表
-- 存储系统定时任务的定义，支持Cron表达式调度和任务参数配置
CREATE TABLE task_definition (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 任务唯一标识符
    name VARCHAR(100) UNIQUE NOT NULL,                                      -- 任务名称，系统内唯一
    description TEXT,                                                        -- 任务描述，说明任务目的和功能
    task_type VARCHAR(50) NOT NULL CHECK (task_type IN ('event_filter', 'question_generate', 'model_predict', 'score_evaluate')), -- 任务类型：事件过滤/问题生成/模型预测/评分
    cron_expression VARCHAR(100),                                           -- Cron表达式，定义任务执行时间规则
    is_enabled BOOLEAN DEFAULT true,                                        -- 任务是否启用
    config JSONB,                                                            -- 任务配置参数，JSON格式存储
    timeout_seconds INTEGER DEFAULT 3600,                                   -- 任务超时时间，默认1小时
    retry_count INTEGER DEFAULT 3,                                          -- 失败重试次数，默认3次
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 最后更新时间
    updated_by UUID REFERENCES "user"(id)                                   -- 更新者ID，关联用户表
);

-- 任务执行记录表
-- 记录任务每次执行的详细信息，用于任务监控和问题追踪
CREATE TABLE task_execution (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 执行记录唯一标识符
    task_id UUID NOT NULL REFERENCES task_definition(id),                   -- 关联的任务定义ID
    execution_id VARCHAR(100) UNIQUE NOT NULL,                              -- 执行实例ID，每次执行唯一
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')), -- 执行状态：待执行/执行中/已完成/失败/已取消
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 任务开始执行时间
    finished_at TIMESTAMP WITH TIME ZONE,                                    -- 任务完成时间
    duration_seconds INTEGER,                                               -- 任务执行持续时间，单位秒
    result JSONB,                                                            -- 执行结果数据，JSON格式存储
    error_message TEXT,                                                     -- 错误信息，记录失败原因
    retry_count INTEGER DEFAULT 0,                                         -- 本次执行的重试次数
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP           -- 最后更新时间
);

-- 任务执行日志表
-- 存储任务执行过程中的详细日志，用于问题诊断和性能优化
CREATE TABLE task_execution_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 日志记录唯一标识符
    execution_id UUID NOT NULL REFERENCES task_execution(id),               -- 关联的任务执行记录ID
    level VARCHAR(10) NOT NULL CHECK (level IN ('debug', 'info', 'warn', 'error')), -- 日志级别：调试/信息/警告/错误
    message TEXT NOT NULL,                                                  -- 日志消息内容
    details JSONB,                                                          -- 日志详细信息，JSON格式存储
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP           -- 日志创建时间
);

-- ========================================
-- 6. 系统配置和监控表（新增）
-- ========================================

-- 系统配置表
-- 存储系统全局配置参数，支持灵活的配置管理和动态更新
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 配置项唯一标识符
    key VARCHAR(100) UNIQUE NOT NULL,                                       -- 配置键名，系统内唯一
    value JSONB NOT NULL,                                                   -- 配置值，JSON格式支持多种数据类型
    description TEXT,                                                        -- 配置项描述，说明配置用途
    is_encrypted BOOLEAN DEFAULT false,                                     -- 是否加密存储，敏感配置需要加密
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,          -- 最后更新时间
    updated_by UUID REFERENCES "user"(id)                                   -- 更新者ID，关联用户表
);

-- 系统指标表
-- 收集和存储系统运行指标，用于性能监控和容量规划
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                         -- 指标记录唯一标识符
    metric_name VARCHAR(100) NOT NULL,                                      -- 指标名称，如CPU使用率、内存占用等
    metric_value NUMERIC NOT NULL,                                          -- 指标数值
    metric_unit VARCHAR(20),                                                -- 指标单位，如%、MB、次/秒等
    tags JSONB,                                                             -- 指标标签，用于分类和筛选
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP          -- 指标记录时间
);

-- ========================================
-- 7. 索引创建
-- ========================================

-- GIN索引用于JSONB和数组字段
CREATE INDEX idx_source_event_raw_data ON source_event USING gin(raw_data);
CREATE INDEX idx_source_event_tags ON source_event USING gin(tags);
CREATE INDEX idx_event_tags ON event USING gin(tags);
CREATE INDEX idx_question_template_types ON question_template USING gin(types);
CREATE INDEX idx_answer_scope_allowed_values ON answer_scope USING gin(allowed_values);
CREATE INDEX idx_answer_scope_validation_rules ON answer_scope USING gin(validation_rules);
CREATE INDEX idx_prompt_template_variables ON prompt_template USING gin(variables);
CREATE INDEX idx_event_filter_rule_config ON event_filter_rule USING gin(rule_config);

-- 常规索引
CREATE INDEX idx_user_username ON "user"(username);
CREATE INDEX idx_user_role ON "user"(role);
CREATE INDEX idx_user_email ON "user"(email);
CREATE INDEX idx_user_deleted_at ON "user"(deleted_at);

CREATE INDEX idx_model_name ON model(model_name);
CREATE INDEX idx_model_type ON model(model_type);
CREATE INDEX idx_model_is_available ON model(is_available);
CREATE INDEX idx_model_deleted_at ON model(deleted_at);

CREATE INDEX idx_data_source_type ON data_source(type);
CREATE INDEX idx_data_source_is_active ON data_source(is_active);

CREATE INDEX idx_event_filter_rule_level ON event_filter_rule(level);
CREATE INDEX idx_event_filter_rule_is_open ON event_filter_rule(is_open);
CREATE INDEX idx_event_filter_rule_source_user_id ON event_filter_rule(source_user_id);
CREATE INDEX idx_event_filter_rule_deleted_at ON event_filter_rule(deleted_at);

CREATE INDEX idx_source_event_data_source_id ON source_event(data_source_id);
CREATE INDEX idx_source_event_rule_id ON source_event(rule_id);
CREATE INDEX idx_source_event_event_key ON source_event(event_key);
CREATE INDEX idx_source_event_level ON source_event(level);
CREATE INDEX idx_source_event_processed_at ON source_event(processed_at);
CREATE INDEX idx_source_event_created_at ON source_event(created_at);
CREATE INDEX idx_source_event_deleted_at ON source_event(deleted_at);

CREATE INDEX idx_event_source_event_id ON event(source_event_id);
CREATE INDEX idx_event_source_user_id ON event(source_user_id);
CREATE INDEX idx_event_status ON event(status);
CREATE INDEX idx_event_level ON event(level);
CREATE INDEX idx_event_created_at ON event(created_at);
CREATE INDEX idx_event_deleted_at ON event(deleted_at);

CREATE INDEX idx_prompt_template_type ON prompt_template(type);
CREATE INDEX idx_prompt_template_version ON prompt_template(version);
CREATE INDEX idx_prompt_template_is_active ON prompt_template(is_active);

CREATE INDEX idx_question_template_field ON question_template(field);
CREATE INDEX idx_question_template_level ON question_template(level);
CREATE INDEX idx_question_template_source_user_id ON question_template(source_user_id);
CREATE INDEX idx_question_template_is_active ON question_template(is_active);
CREATE INDEX idx_question_template_deleted_at ON question_template(deleted_at);

CREATE INDEX idx_answer_scope_question_template_id ON answer_scope(question_template_id);
CREATE INDEX idx_answer_scope_scope_type ON answer_scope(scope_type);

CREATE INDEX idx_event_question_relation_event_id ON event_question_relation(event_id);
CREATE INDEX idx_event_question_relation_question_id ON event_question_relation(question_id);

CREATE INDEX idx_event_question_template_id ON event_question(question_template_id);
CREATE INDEX idx_event_question_answer_scope_id ON event_question(answer_scope_id);
CREATE INDEX idx_event_question_type ON event_question(question_type);
CREATE INDEX idx_event_question_status ON event_question(status);
CREATE INDEX idx_event_question_end_time ON event_question(end_time);
CREATE INDEX idx_event_question_confirm_user_id ON event_question(confirm_user_id);
CREATE INDEX idx_event_question_generation_method ON event_question(generation_method);
CREATE INDEX idx_event_question_ai_model_id ON event_question(ai_model_id);
CREATE INDEX idx_event_question_created_at ON event_question(created_at);
CREATE INDEX idx_event_question_deleted_at ON event_question(deleted_at);

CREATE INDEX idx_score_rule_question_template_id ON predict_question_answer_score_rule(question_template_id);
CREATE INDEX idx_score_rule_source_user_id ON predict_question_answer_score_rule(source_user_id);
CREATE INDEX idx_score_rule_is_open ON predict_question_answer_score_rule(is_open);
CREATE INDEX idx_score_rule_rule_type ON predict_question_answer_score_rule(rule_type);
CREATE INDEX idx_score_rule_deleted_at ON predict_question_answer_score_rule(deleted_at);

CREATE INDEX idx_model_predict_event_question_id ON model_predict_question_answer(event_question_id);
CREATE INDEX idx_model_predict_model_id ON model_predict_question_answer(model_id);
CREATE INDEX idx_model_predict_evaluation_rule_id ON model_predict_question_answer(evaluation_rule_id);
CREATE INDEX idx_model_predict_is_right ON model_predict_question_answer(is_right);
CREATE INDEX idx_model_predict_score ON model_predict_question_answer(score);
CREATE INDEX idx_model_predict_status ON model_predict_question_answer(status);
CREATE INDEX idx_model_predict_create_time ON model_predict_question_answer(create_time);
CREATE INDEX idx_model_predict_deleted_at ON model_predict_question_answer(deleted_at);

CREATE INDEX idx_user_predict_event_question_id ON user_predict_question_answer(event_question_id);
CREATE INDEX idx_user_predict_user_id ON user_predict_question_answer(user_id);
CREATE INDEX idx_user_predict_evaluation_rule_id ON user_predict_question_answer(evaluation_rule_id);
CREATE INDEX idx_user_predict_is_right ON user_predict_question_answer(is_right);
CREATE INDEX idx_user_predict_score ON user_predict_question_answer(score);
CREATE INDEX idx_user_predict_deleted_at ON user_predict_question_answer(deleted_at);

CREATE INDEX idx_task_definition_task_type ON task_definition(task_type);
CREATE INDEX idx_task_definition_is_enabled ON task_definition(is_enabled);

CREATE INDEX idx_task_execution_task_id ON task_execution(task_id);
CREATE INDEX idx_task_execution_status ON task_execution(status);
CREATE INDEX idx_task_execution_started_at ON task_execution(started_at);
CREATE INDEX idx_task_execution_finished_at ON task_execution(finished_at);

CREATE INDEX idx_task_execution_log_execution_id ON task_execution_log(execution_id);
CREATE INDEX idx_task_execution_log_level ON task_execution_log(level);
CREATE INDEX idx_task_execution_log_created_at ON task_execution_log(created_at);

CREATE INDEX idx_system_config_key ON system_config(key);
CREATE INDEX idx_system_metrics_metric_name ON system_metrics(metric_name);
CREATE INDEX idx_system_metrics_recorded_at ON system_metrics(recorded_at);

-- ========================================
-- 8. 触发器和函数
-- ========================================

-- 更新 updated_at 字段的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有表添加 updated_at 触发器
CREATE TRIGGER update_user_updated_at BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_model_updated_at BEFORE UPDATE ON model FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_source_updated_at BEFORE UPDATE ON data_source FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_event_filter_rule_updated_at BEFORE UPDATE ON event_filter_rule FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_source_event_updated_at BEFORE UPDATE ON source_event FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_event_updated_at BEFORE UPDATE ON event FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_prompt_template_updated_at BEFORE UPDATE ON prompt_template FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_question_template_updated_at BEFORE UPDATE ON question_template FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_answer_scope_updated_at BEFORE UPDATE ON answer_scope FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_event_question_updated_at BEFORE UPDATE ON event_question FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_score_rule_updated_at BEFORE UPDATE ON predict_question_answer_score_rule FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_model_predict_updated_at BEFORE UPDATE ON model_predict_question_answer FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_predict_updated_at BEFORE UPDATE ON user_predict_question_answer FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_task_definition_updated_at BEFORE UPDATE ON task_definition FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_task_execution_updated_at BEFORE UPDATE ON task_execution FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 模型使用统计更新函数
CREATE OR REPLACE FUNCTION update_model_usage_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- 更新模型最后使用时间
    UPDATE model
    SET last_used_at = CURRENT_TIMESTAMP
    WHERE id = NEW.model_id;

    -- 更新模板使用次数
    IF TG_TABLE_NAME = 'event_question' THEN
        UPDATE question_template
        SET usage_count = usage_count + 1
        WHERE id = NEW.question_template_id;
    END IF;

    -- 更新规则过滤次数
    IF TG_TABLE_NAME = 'source_event' AND NEW.rule_id IS NOT NULL THEN
        UPDATE event_filter_rule
        SET filter_count = filter_count + 1,
            last_used_at = CURRENT_TIMESTAMP
        WHERE id = NEW.rule_id;
    END IF;

    -- 更新规则应用次数
    IF TG_TABLE_NAME IN ('model_predict_question_answer', 'user_predict_question_answer')
       AND NEW.evaluation_rule_id IS NOT NULL THEN
        UPDATE predict_question_answer_score_rule
        SET apply_count = apply_count + 1
        WHERE id = NEW.evaluation_rule_id;
    END IF;

    RETURN NEW;
END;
$$ language 'plpgsql';

-- 添加统计触发器
CREATE TRIGGER update_model_stats AFTER INSERT ON model_predict_question_answer FOR EACH ROW EXECUTE FUNCTION update_model_usage_stats();
CREATE TRIGGER update_template_stats AFTER INSERT ON event_question FOR EACH ROW EXECUTE FUNCTION update_model_usage_stats();
CREATE TRIGGER update_filter_stats AFTER INSERT OR UPDATE ON source_event FOR EACH ROW EXECUTE FUNCTION update_model_usage_stats();
CREATE TRIGGER update_rule_stats AFTER INSERT ON model_predict_question_answer FOR EACH ROW EXECUTE FUNCTION update_model_usage_stats();
CREATE TRIGGER update_rule_stats_user AFTER INSERT ON user_predict_question_answer FOR EACH ROW EXECUTE FUNCTION update_model_usage_stats();

-- ========================================
-- 9. 视图
-- ========================================

-- 活跃用户视图
CREATE VIEW active_user AS
SELECT id, role, username, email, is_active, created_at, updated_at
FROM "user"
WHERE deleted_at IS NULL AND is_active = true;

-- 活跃模型视图
CREATE VIEW active_model AS
SELECT id, model, model_name, model_type, max_tokens, temperature, is_available, last_used_at
FROM model
WHERE deleted_at IS NULL AND is_available = true;

-- 事件处理统计视图
CREATE VIEW event_processing_stats AS
SELECT
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as total_events,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_events,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_events,
    AVG(processed_count) as avg_process_count
FROM event
WHERE deleted_at IS NULL
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- 模型性能统计视图
CREATE VIEW model_performance_stats AS
SELECT
    m.id,
    m.model,
    m.model_name,
    COUNT(mpa.id) as total_predictions,
    COUNT(CASE WHEN mpa.is_right = true THEN 1 END) as correct_predictions,
    AVG(mpa.score) as average_score,
    AVG(mpa.response_time_ms) as avg_response_time,
    MAX(mpa.create_time) as last_prediction_time
FROM model m
LEFT JOIN model_predict_question_answer mpa ON m.id = mpa.model_id
WHERE m.deleted_at IS NULL AND mpa.deleted_at IS NULL
GROUP BY m.id, m.model, m.model_name;

-- 任务执行统计视图
CREATE VIEW task_execution_stats AS
SELECT
    td.id,
    td.name,
    td.task_type,
    COUNT(te.id) as total_executions,
    COUNT(CASE WHEN te.status = 'completed' THEN 1 END) as successful_executions,
    COUNT(CASE WHEN te.status = 'failed' THEN 1 END) as failed_executions,
    AVG(te.duration_seconds) as avg_duration_seconds,
    MAX(te.started_at) as last_execution_time
FROM task_definition td
LEFT JOIN task_execution te ON td.id = te.task_id
GROUP BY td.id, td.name, td.task_type;

-- ========================================
-- 10. 初始化数据
-- ========================================

-- 创建默认管理员用户
INSERT INTO "user" (role, username, password, email) VALUES
('admin', 'admin', crypt('admin123', gen_salt('bf')), 'admin@example.com');

-- 创建系统用户（用于API调用）
INSERT INTO "user" (role, username, password, email) VALUES
('api_service', 'system', crypt('system' || gen_salt('md5'), gen_salt('bf')), 'system@example.com');

-- 添加默认数据源
INSERT INTO data_source (name, type, connection_config) VALUES
('烽火', 'api', '{"url": "https://api.example.com/beacon", "auth_type": "bearer", "timeout": 30}'),
('报告', 'database', '{"host": "localhost", "port": 5432, "database": "reports", "username": "user", "password": "pass"}');

-- 添加示例模型
INSERT INTO model (model, model_name, url, api_key, model_type) VALUES
('GPT-4', 'gpt-4', 'https://api.openai.com/v1/chat/completions', crypt('sk-example-key', gen_salt('bf')), 'openai'),
('Claude', 'claude-3-opus', 'https://api.anthropic.com/v1/messages', crypt('sk-ant-example-key', gen_salt('bf')), 'claude'),
('内部模型', 'internal-v1', 'http://internal-ai:8080/predict', crypt('internal-key', gen_salt('bf')), 'internal');

-- 添加默认提示词模板
INSERT INTO prompt_template (name, type, template, variables) VALUES
('事件过滤提示词', 'event_filter', '请根据以下规则过滤事件：{rules}\n事件内容：{event_content}\n请判断是否需要处理。',
 '{"rules": "过滤规则", "event_content": "事件内容"}'),
('问题生成提示词', 'question_generate', '根据以下事件和模板生成问题：\n事件：{event}\n模板：{template}\n字段：{field}\n请生成一个{question_type}类型的问题。',
 '{"event": "事件内容", "template": "问题模板", "field": "字段", "question_type": "问题类型"}'),
('答案评分提示词', 'answer_evaluate', '请评估以下答案：\n问题：{question}\n正确答案：{correct_answer}\n用户答案：{user_answer}\n请给出评分（0-100）。',
 '{"question": "问题", "correct_answer": "正确答案", "user_answer": "用户答案"}');

-- 添加系统配置
INSERT INTO system_config (key, value, description) VALUES
('max_event_batch_size', '100', '单次处理事件的最大数量'),
('default_model_timeout', '30000', '模型调用的默认超时时间（毫秒）'),
('enable_auto_question_generation', 'true', '是否启用自动问题生成'),
('score_threshold', '60', '答案及格分数阈值');

-- 添加默认任务定义
INSERT INTO task_definition (name, description, task_type, cron_expression, config) VALUES
('事件过滤任务', '定期处理原始事件并进行过滤', 'event_filter', '*/5 * * * *', '{"batch_size": 100}'),
('问题生成任务', '为过滤后的事件生成相关问题', 'question_generate', '0 */2 * * *', '{"max_questions_per_event": 5}'),
('模型预测任务', '使用AI模型对问题进行预测', 'model_predict', '*/10 * * * *', '{"concurrent_limit": 10}'),
('评分任务', '对模型和用户答案进行评分', 'score_evaluate', '0 0 * * *', '{"re_eval_enabled": false}');

-- ========================================
-- 11. 分区表设置（可选，用于大数据量场景）
-- ========================================

-- 如果数据量很大，可以考虑对某些表进行分区
-- 示例：按月分区事件表
/*
CREATE TABLE event_partitioned (
    LIKE event INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 创建分区
CREATE TABLE event_2024_01 PARTITION OF event_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
*/

-- ========================================
-- 注意事项
-- ========================================
/*
1. 本设计基于详细流程分析，新增了多个关键表支持完整业务流程
2. 使用JSONB字段存储灵活配置，提高系统扩展性
3. 所有表都包含完整的审计字段和软删除支持
4. 创建了任务调度系统，支持定时和事件驱动处理
5. 添加了系统监控和配置管理，便于运维
6. 使用了触发器自动更新统计信息
7. 优化了索引策略，包括GIN索引用于JSON和数组字段
8. 创建了多个统计视图，便于数据分析和报表生成
*/