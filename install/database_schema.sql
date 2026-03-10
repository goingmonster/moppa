-- ========================================
-- 事件驱动问答评价系统数据库结构
-- PostgreSQL 建表脚本
-- ========================================

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ========================================
-- 1. 基础信息表
-- ========================================

-- 用户表
CREATE TABLE user (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'operator', 'reviewer')),
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES user(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 模型表
CREATE TABLE model (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model VARCHAR(100) NOT NULL, -- 展示名称
    model_name VARCHAR(100) UNIQUE NOT NULL, -- 模型名称
    url VARCHAR(500) NOT NULL,
    api_key TEXT NOT NULL, -- 加密存储
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES user(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- ========================================
-- 2. 事件管理相关表
-- ========================================

-- 事件过滤规则表
CREATE TABLE event_filter_rule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule TEXT NOT NULL,
    level INTEGER NOT NULL CHECK (level >= 1 AND level <= 10),
    source_user_id UUID NOT NULL REFERENCES user(id),
    is_open BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES user(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 来源事件表
CREATE TABLE source_event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule TEXT,
    level INTEGER CHECK (level >= 1 AND level <= 10),
    options TEXT, -- 补充信息，JSON格式
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES user(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 事件表
CREATE TABLE event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_content TEXT NOT NULL,
    tags VARCHAR(500), -- 标签，逗号分隔
    rules TEXT, -- 命中规则
    source_user_id UUID NOT NULL REFERENCES user(id), -- 人工审核id
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES user(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- ========================================
-- 3. 问题模板相关表
-- ========================================

-- 问题模板表
CREATE TABLE question_template (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template TEXT NOT NULL,
    field VARCHAR(100) NOT NULL,
    level INTEGER CHECK (level >= 1 AND level <= 10),
    types VARCHAR(100), -- 类型，可存储多个类型，逗号分隔
    source_user_id UUID NOT NULL REFERENCES user(id), -- 模板来源
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES user(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 事件问题表
CREATE TABLE event_question (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_template_id UUID NOT NULL REFERENCES question_template(id),
    question TEXT NOT NULL,
    event_id TEXT NOT NULL, -- 关联事件ID，可能多个，JSON数组格式
    answer_scope TEXT, -- 答案范围
    question_type VARCHAR(50) CHECK (question_type IN ('single_choice', 'multiple_choice', 'text', 'number')),
    real_answer TEXT,
    end_time TIMESTAMP WITH TIME ZONE, -- 截止时间
    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    confirm_user_id UUID REFERENCES user(id), -- 确认人
    is_end BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES user(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- ========================================
-- 4. 评价系统相关表
-- ========================================

-- 模型预测问题答案表
CREATE TABLE model_predict_question_answer (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_question_id UUID NOT NULL REFERENCES event_question(id),
    answer TEXT NOT NULL,
    model_id UUID NOT NULL REFERENCES model(id),
    is_right BOOLEAN,
    reason TEXT, -- 思考原因
    score NUMERIC(5,2) CHECK (score >= 0 AND score <= 100), -- 评分
    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES user(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 用户预测问题答案表
CREATE TABLE user_predict_question_answer (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_question_id UUID NOT NULL REFERENCES event_question(id),
    answer TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES user(id), -- 评价人
    is_right BOOLEAN,
    reason TEXT, -- 思考原因
    score NUMERIC(5,2) CHECK (score >= 0 AND score <= 100), -- 评分
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES user(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 预测问题答案评分规则表
CREATE TABLE predict_question_answer_score_rule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_template_id UUID NOT NULL REFERENCES question_template(id),
    rule TEXT NOT NULL,
    source_user_id UUID NOT NULL REFERENCES user(id), -- 规则来源
    is_open BOOLEAN DEFAULT true,
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN ('model', 'user', 'both')), -- 为谁评价
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES user(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- ========================================
-- 5. 索引创建
-- ========================================

-- 用户表索引
CREATE INDEX idx_user_username ON user(username);
CREATE INDEX idx_user_role ON user(role);
CREATE INDEX idx_user_deleted_at ON user(deleted_at);

-- 模型表索引
CREATE INDEX idx_model_name ON model(model_name);
CREATE INDEX idx_model_deleted_at ON model(deleted_at);

-- 事件过滤规则表索引
CREATE INDEX idx_event_filter_rule_level ON event_filter_rule(level);
CREATE INDEX idx_event_filter_rule_is_open ON event_filter_rule(is_open);
CREATE INDEX idx_event_filter_rule_source_user_id ON event_filter_rule(source_user_id);
CREATE INDEX idx_event_filter_rule_deleted_at ON event_filter_rule(deleted_at);

-- 来源事件表索引
CREATE INDEX idx_source_event_level ON source_event(level);
CREATE INDEX idx_source_event_deleted_at ON source_event(deleted_at);

-- 事件表索引
CREATE INDEX idx_event_tags ON event USING gin(string_to_array(tags, ','));
CREATE INDEX idx_event_source_user_id ON event(source_user_id);
CREATE INDEX idx_event_created_at ON event(created_at);
CREATE INDEX idx_event_deleted_at ON event(deleted_at);

-- 问题模板表索引
CREATE INDEX idx_question_template_field ON question_template(field);
CREATE INDEX idx_question_template_level ON question_template(level);
CREATE INDEX idx_question_template_source_user_id ON question_template(source_user_id);
CREATE INDEX idx_question_template_deleted_at ON question_template(deleted_at);

-- 事件问题表索引
CREATE INDEX idx_event_question_template_id ON event_question(question_template_id);
CREATE INDEX idx_event_question_type ON event_question(question_type);
CREATE INDEX idx_event_question_end_time ON event_question(end_time);
CREATE INDEX idx_event_question_confirm_user_id ON event_question(confirm_user_id);
CREATE INDEX idx_event_question_is_end ON event_question(is_end);
CREATE INDEX idx_event_question_deleted_at ON event_question(deleted_at);

-- 模型预测答案表索引
CREATE INDEX idx_model_predict_event_question_id ON model_predict_question_answer(event_question_id);
CREATE INDEX idx_model_predict_model_id ON model_predict_question_answer(model_id);
CREATE INDEX idx_model_predict_is_right ON model_predict_question_answer(is_right);
CREATE INDEX idx_model_predict_score ON model_predict_question_answer(score);
CREATE INDEX idx_model_predict_create_time ON model_predict_question_answer(create_time);
CREATE INDEX idx_model_predict_deleted_at ON model_predict_question_answer(deleted_at);

-- 用户预测答案表索引
CREATE INDEX idx_user_predict_event_question_id ON user_predict_question_answer(event_question_id);
CREATE INDEX idx_user_predict_user_id ON user_predict_question_answer(user_id);
CREATE INDEX idx_user_predict_is_right ON user_predict_question_answer(is_right);
CREATE INDEX idx_user_predict_score ON user_predict_question_answer(score);
CREATE INDEX idx_user_predict_deleted_at ON user_predict_question_answer(deleted_at);

-- 评分规则表索引
CREATE INDEX idx_score_rule_question_template_id ON predict_question_answer_score_rule(question_template_id);
CREATE INDEX idx_score_rule_source_user_id ON predict_question_answer_score_rule(source_user_id);
CREATE INDEX idx_score_rule_is_open ON predict_question_answer_score_rule(is_open);
CREATE INDEX idx_score_rule_rule_type ON predict_question_answer_score_rule(rule_type);
CREATE INDEX idx_score_rule_deleted_at ON predict_question_answer_score_rule(deleted_at);

-- ========================================
-- 6. 触发器和函数
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
CREATE TRIGGER update_user_updated_at BEFORE UPDATE ON user FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_model_updated_at BEFORE UPDATE ON model FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_event_filter_rule_updated_at BEFORE UPDATE ON event_filter_rule FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_source_event_updated_at BEFORE UPDATE ON source_event FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_event_updated_at BEFORE UPDATE ON event FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_question_template_updated_at BEFORE UPDATE ON question_template FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_event_question_updated_at BEFORE UPDATE ON event_question FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_model_predict_updated_at BEFORE UPDATE ON model_predict_question_answer FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_predict_updated_at BEFORE UPDATE ON user_predict_question_answer FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_score_rule_updated_at BEFORE UPDATE ON predict_question_answer_score_rule FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- 7. 视图
-- ========================================

-- 活跃用户视图（排除已删除用户）
CREATE VIEW active_user AS
SELECT id, role, username, created_at, updated_at
FROM user
WHERE deleted_at IS NULL;

-- 活跃模型视图（排除已删除模型）
CREATE VIEW active_model AS
SELECT id, model, model_name, url, created_at, updated_at
FROM model
WHERE deleted_at IS NULL;

-- 事件问题详情视图
CREATE VIEW event_question_detail AS
SELECT
    eq.id,
    eq.question,
    eq.question_type,
    eq.answer_scope,
    eq.real_answer,
    eq.end_time,
    eq.is_end,
    eq.create_time,
    qt.template,
    qt.field,
    qt.level,
    u1.username as confirm_user,
    u2.username as template_creator
FROM event_question eq
LEFT JOIN question_template qt ON eq.question_template_id = qt.id
LEFT JOIN user u1 ON eq.confirm_user_id = u1.id
LEFT JOIN user u2 ON qt.source_user_id = u2.id
WHERE eq.deleted_at IS NULL AND qt.deleted_at IS NULL;

-- 模型预测统计视图
CREATE VIEW model_predict_stats AS
SELECT
    m.id,
    m.model,
    COUNT(mpa.id) as total_predictions,
    COUNT(CASE WHEN mpa.is_right = true THEN 1 END) as correct_predictions,
    AVG(mpa.score) as average_score,
    MAX(mpa.create_time) as last_prediction_time
FROM model m
LEFT JOIN model_predict_question_answer mpa ON m.id = mpa.model_id
WHERE m.deleted_at IS NULL AND mpa.deleted_at IS NULL
GROUP BY m.id, m.model;

-- ========================================
-- 8. 初始化数据
-- ========================================

-- 创建默认管理员用户（密码需要加密）
INSERT INTO user (role, username, password) VALUES
('admin', 'admin', crypt('admin123', gen_salt('bf')));

-- 添加示例数据
INSERT INTO model (model, model_name, url, api_key) VALUES
('GPT-4', 'gpt-4', 'https://api.openai.com/v1/chat/completions', crypt('sk-example-key', gen_salt('bf'))),
('Claude', 'claude-3-opus', 'https://api.anthropic.com/v1/messages', crypt('sk-ant-example-key', gen_salt('bf')));

-- ========================================
-- 9. 权限设置（可选）
-- ========================================

-- 创建只读角色
-- CREATE ROLE readonly;
-- GRANT CONNECT ON DATABASE your_database TO readonly;
-- GRANT USAGE ON SCHEMA public TO readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;

-- 创建应用角色
-- CREATE ROLE app_user;
-- GRANT CONNECT ON DATABASE your_database TO app_user;
-- GRANT USAGE ON SCHEMA public TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- ========================================
-- 注意事项
-- ========================================
-- 1. API密钥已使用pgcrypto扩展的crypt函数加密存储
-- 2. 所有包含数据的表都支持软删除（deleted_at字段）
-- 3. 使用UUID作为主键，提高安全性和分布式友好性
-- 4. event_id字段使用JSON格式存储多个事件ID
-- 5. 创建了多个视图以简化常用查询
-- 6. 所有外键都有相应的索引支持