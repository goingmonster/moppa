BEGIN;

DO $$
DECLARE
    fk_name TEXT;
BEGIN
    SELECT con.conname
    INTO fk_name
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE nsp.nspname = 'public'
      AND rel.relname = 'question'
      AND con.contype = 'f'
      AND pg_get_constraintdef(con.oid) LIKE '%template_id%question_template%';

    IF fk_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE public.question DROP CONSTRAINT %I', fk_name);
    END IF;
END;
$$;

DROP TABLE IF EXISTS public.question_template;

CREATE TABLE public.question_template (
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

ALTER TABLE public.question
    ADD CONSTRAINT question_template_id_fkey
    FOREIGN KEY (template_id)
    REFERENCES public.question_template(id);

DROP TRIGGER IF EXISTS trg_question_template_updated_at ON public.question_template;
CREATE TRIGGER trg_question_template_updated_at
BEFORE UPDATE ON public.question_template
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

COMMIT;
