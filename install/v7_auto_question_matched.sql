DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'question_status') THEN
        BEGIN
            ALTER TYPE question_status ADD VALUE IF NOT EXISTS 'matched';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
    END IF;
END
$$;

DO $$
DECLARE
    con_name text;
BEGIN
    SELECT c.conname
    INTO con_name
    FROM pg_constraint c
    JOIN pg_class t ON c.conrelid = t.oid
    WHERE t.relname = 'event'
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) LIKE '%filter_status%';

    IF con_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE event DROP CONSTRAINT %I', con_name);
    END IF;

    ALTER TABLE event
    ADD CONSTRAINT ck_event_filter_status
    CHECK (filter_status IN ('pending', 'passed', 'filtered', 'matched'));
END
$$;

ALTER TABLE question
ADD COLUMN IF NOT EXISTS template_id UUID;

ALTER TABLE question
ADD COLUMN IF NOT EXISTS verification_conditions JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = 'question'
          AND constraint_name = 'question_template_id_fkey'
    ) THEN
        ALTER TABLE question
        ADD CONSTRAINT question_template_id_fkey FOREIGN KEY (template_id) REFERENCES question_template(id);
    END IF;
END
$$;
