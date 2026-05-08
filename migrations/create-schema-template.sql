-- Create schema named "Agent" and two standard tables: errorlog and users
-- Note: schema name is quoted to preserve capitalization exactly as requested.
CREATE SCHEMA IF NOT EXISTS "Agent";

-- Table: Agent.errorlog
-- Stores application/runtime errors with optional structured metadata
CREATE TABLE IF NOT EXISTS "Agent".errorlog (
	id BIGSERIAL PRIMARY KEY,
	occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
	level VARCHAR(20) NOT NULL DEFAULT 'ERROR',
	message TEXT NOT NULL,
	traceback TEXT,
	service VARCHAR(128),
	host VARCHAR(256),
	metadata JSONB,
	created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_errorlog_occurred_at ON "Agent".errorlog (occurred_at);
CREATE INDEX IF NOT EXISTS idx_agent_errorlog_level ON "Agent".errorlog (level);

-- Table: Agent.users
-- Standard user table for authentication/authorization
CREATE TABLE IF NOT EXISTS "Agent".users (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	username VARCHAR(150) NOT NULL UNIQUE,
	email VARCHAR(254) NOT NULL UNIQUE,
	password_hash VARCHAR(512) NOT NULL,
	full_name VARCHAR(256),
	is_active BOOLEAN NOT NULL DEFAULT TRUE,
	is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
	created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
	updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
	last_login TIMESTAMPTZ,
	profile JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_users_username ON "Agent".users (username);
CREATE INDEX IF NOT EXISTS idx_agent_users_email ON "Agent".users (email);

-- Optional: function to update updated_at on row modification
CREATE OR REPLACE FUNCTION "Agent".trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
	NEW.updated_at = now();
	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger to users table
DROP TRIGGER IF EXISTS set_timestamp ON "Agent".users;
CREATE TRIGGER set_timestamp
BEFORE UPDATE ON "Agent".users
FOR EACH ROW
EXECUTE FUNCTION "Agent".trigger_set_timestamp();

-- End of schema/template