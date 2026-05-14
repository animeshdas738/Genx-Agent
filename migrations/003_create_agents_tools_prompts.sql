-- Migration: create agents, tools and prompts tables under Agent schema
CREATE TABLE IF NOT EXISTS "Agent".agents (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "Agent".tools (
    id SERIAL PRIMARY KEY,
    tool_id VARCHAR NOT NULL UNIQUE,
    agent_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    metadata JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT fk_tools_agent FOREIGN KEY (agent_id) REFERENCES "Agent".agents(agent_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "Agent".prompts (
    id SERIAL PRIMARY KEY,
    prompt_key VARCHAR NOT NULL UNIQUE,
    tool_id VARCHAR NOT NULL,
    prompt_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT fk_prompt_tool FOREIGN KEY (tool_id) REFERENCES "Agent".tools(tool_id) ON DELETE CASCADE
);
