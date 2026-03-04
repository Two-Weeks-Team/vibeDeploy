CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id TEXT UNIQUE NOT NULL,
    raw_input TEXT NOT NULL,
    input_type TEXT NOT NULL CHECK (input_type IN ('text', 'youtube')),
    idea_summary TEXT,
    transcript TEXT,
    visual_context TEXT,
    phase TEXT NOT NULL DEFAULT 'input',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'analyzing', 'scoring', 'building', 'deploying', 'complete', 'failed')),
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE council_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_role TEXT NOT NULL CHECK (agent_role IN ('architect', 'scout', 'guardian', 'catalyst', 'advocate')),
    analysis JSONB NOT NULL DEFAULT '{}',
    score INTEGER CHECK (score >= 0 AND score <= 100),
    reasoning TEXT,
    key_findings JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_council_session_role ON council_analyses(session_id, agent_role);

CREATE TABLE cross_examinations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    debate_type TEXT NOT NULL CHECK (debate_type IN ('architect_vs_guardian', 'scout_vs_catalyst', 'advocate_challenges')),
    content JSONB NOT NULL DEFAULT '{}',
    score_adjustments JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_crossexam_session_type ON cross_examinations(session_id, debate_type);

CREATE TABLE vibe_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    technical_feasibility INTEGER NOT NULL CHECK (technical_feasibility >= 0 AND technical_feasibility <= 100),
    market_viability INTEGER NOT NULL CHECK (market_viability >= 0 AND market_viability <= 100),
    innovation_score INTEGER NOT NULL CHECK (innovation_score >= 0 AND innovation_score <= 100),
    risk_profile INTEGER NOT NULL CHECK (risk_profile >= 0 AND risk_profile <= 100),
    user_impact INTEGER NOT NULL CHECK (user_impact >= 0 AND user_impact <= 100),
    final_score NUMERIC(5, 2) NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('GO', 'CONDITIONAL', 'NO_GO')),
    strategist_reasoning TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    github_repo TEXT,
    github_url TEXT,
    do_app_id TEXT,
    live_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'repo_created', 'deploying', 'live', 'failed')),
    error TEXT,
    generated_docs JSONB DEFAULT '{}',
    frontend_code JSONB DEFAULT '{}',
    backend_code JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_thread_id ON sessions(thread_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
