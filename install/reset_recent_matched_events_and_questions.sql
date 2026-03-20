BEGIN;

WITH recent_questions AS (
    SELECT id
    FROM question
    WHERE created_at >= NOW() - INTERVAL '7 days'
),
deleted_question_events AS (
    DELETE FROM question_event
    WHERE question_id IN (SELECT id FROM recent_questions)
    RETURNING question_id
),
deleted_questions AS (
    DELETE FROM question
    WHERE id IN (SELECT id FROM recent_questions)
    RETURNING id
),
updated_events AS (
    UPDATE event
    SET filter_status = 'passed',
        updated_at = NOW()
    WHERE filter_status = 'matched'
      AND created_at >= NOW() - INTERVAL '7 days'
    RETURNING id
)
SELECT
    (SELECT COUNT(*) FROM updated_events) AS updated_event_count,
    (SELECT COUNT(*) FROM deleted_questions) AS deleted_question_count,
    (SELECT COUNT(*) FROM deleted_question_events) AS deleted_question_event_count;

COMMIT;
