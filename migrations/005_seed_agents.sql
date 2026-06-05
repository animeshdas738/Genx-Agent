-- Seed: insert all existing agents into the agents table
-- Safe to re-run: ON CONFLICT (agent_id) DO UPDATE keeps label/description in sync

INSERT INTO "Agent".agents (agent_id, name, label, description, is_active)
VALUES
    (
        'summarize_agent',
        'Case Summarizer',
        'Case Summarization',
        'Summarizes support case details and suggests a resolution with a confidence score. Uses vector similarity search first, falling back to LLM generation.',
        TRUE
    ),
    (
        'account_summary_agent',
        'Account Summarizer',
        'Account Summary',
        'Generates an account-level summary from a website URL or raw text input using LLM analysis.',
        TRUE
    ),
    (
        'case_resolution_agent',
        'Case Resolution Agent',
        'Case Resolution',
        'Resolves support cases by matching subject and description against the case vector store. Escalates to human support when no match is found.',
        TRUE
    ),
    (
        'sentiment_analyzer',
        'Sentiment Analyzer',
        'Sentiment Analysis',
        'Classifies the sentiment of text as positive, negative, or neutral. Returns a sentiment label, strength score, confidence, and optional reasoning.',
        TRUE
    )
ON CONFLICT (agent_id) DO UPDATE
    SET
        name        = EXCLUDED.name,
        label       = EXCLUDED.label,
        description = EXCLUDED.description,
        is_active   = EXCLUDED.is_active;
