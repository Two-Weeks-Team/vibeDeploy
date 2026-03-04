from __future__ import annotations

import uuid

from .connection import get_pool


async def create_session(
    thread_id: str,
    raw_input: str,
    input_type: str,
) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO sessions (thread_id, raw_input, input_type)
        VALUES ($1, $2, $3)
        RETURNING id, thread_id, raw_input, input_type, phase, status, created_at
        """,
        thread_id,
        raw_input,
        input_type,
    )
    return dict(row)


async def get_session(thread_id: str) -> dict | None:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM sessions WHERE thread_id = $1", thread_id)
    return dict(row) if row else None


async def update_session_phase(thread_id: str, phase: str, status: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE sessions SET phase = $1, status = $2, updated_at = NOW() WHERE thread_id = $3",
        phase,
        status,
        thread_id,
    )


async def save_council_analysis(
    session_id: uuid.UUID,
    agent_role: str,
    analysis: dict,
    score: int,
    reasoning: str,
    key_findings: list,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO council_analyses (session_id, agent_role, analysis, score, reasoning, key_findings)
        VALUES ($1, $2, $3::jsonb, $4, $5, $6::jsonb)
        ON CONFLICT (session_id, agent_role) DO UPDATE
        SET analysis = EXCLUDED.analysis, score = EXCLUDED.score,
            reasoning = EXCLUDED.reasoning, key_findings = EXCLUDED.key_findings
        """,
        session_id,
        agent_role,
        analysis,
        score,
        reasoning,
        key_findings,
    )


async def save_cross_examination(
    session_id: uuid.UUID,
    debate_type: str,
    content: dict,
    score_adjustments: dict,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO cross_examinations (session_id, debate_type, content, score_adjustments)
        VALUES ($1, $2, $3::jsonb, $4::jsonb)
        ON CONFLICT (session_id, debate_type) DO UPDATE
        SET content = EXCLUDED.content, score_adjustments = EXCLUDED.score_adjustments
        """,
        session_id,
        debate_type,
        content,
        score_adjustments,
    )


async def save_vibe_score(
    session_id: uuid.UUID,
    technical_feasibility: int,
    market_viability: int,
    innovation_score: int,
    risk_profile: int,
    user_impact: int,
    final_score: float,
    decision: str,
    strategist_reasoning: str,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO vibe_scores (session_id, technical_feasibility, market_viability,
            innovation_score, risk_profile, user_impact, final_score, decision, strategist_reasoning)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (session_id) DO UPDATE
        SET technical_feasibility = EXCLUDED.technical_feasibility,
            market_viability = EXCLUDED.market_viability,
            innovation_score = EXCLUDED.innovation_score,
            risk_profile = EXCLUDED.risk_profile,
            user_impact = EXCLUDED.user_impact,
            final_score = EXCLUDED.final_score,
            decision = EXCLUDED.decision,
            strategist_reasoning = EXCLUDED.strategist_reasoning
        """,
        session_id,
        technical_feasibility,
        market_viability,
        innovation_score,
        risk_profile,
        user_impact,
        final_score,
        decision,
        strategist_reasoning,
    )


async def save_deployment(
    session_id: uuid.UUID,
    github_repo: str | None = None,
    github_url: str | None = None,
    do_app_id: str | None = None,
    live_url: str | None = None,
    status: str = "pending",
) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO deployments (session_id, github_repo, github_url, do_app_id, live_url, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (session_id) DO UPDATE
        SET github_repo = COALESCE(EXCLUDED.github_repo, deployments.github_repo),
            github_url = COALESCE(EXCLUDED.github_url, deployments.github_url),
            do_app_id = COALESCE(EXCLUDED.do_app_id, deployments.do_app_id),
            live_url = COALESCE(EXCLUDED.live_url, deployments.live_url),
            status = EXCLUDED.status,
            updated_at = NOW()
        """,
        session_id,
        github_repo,
        github_url,
        do_app_id,
        live_url,
        status,
    )
