"""Tests for prompts/council_prompts.py — validates prompt structure and content."""

import pytest
from prompts.council_prompts import (
    ADVOCATE_PROMPT,
    ARCHITECT_PROMPT,
    CATALYST_PROMPT,
    GUARDIAN_PROMPT,
    SCOUT_PROMPT,
    STRATEGIST_PROMPT,
)

_ALL_PROMPTS = [
    ("ARCHITECT_PROMPT", ARCHITECT_PROMPT),
    ("SCOUT_PROMPT", SCOUT_PROMPT),
    ("GUARDIAN_PROMPT", GUARDIAN_PROMPT),
    ("CATALYST_PROMPT", CATALYST_PROMPT),
    ("ADVOCATE_PROMPT", ADVOCATE_PROMPT),
    ("STRATEGIST_PROMPT", STRATEGIST_PROMPT),
]


# ── Basic sanity ─────────────────────────────────────────────────────────────


def test_all_prompts_are_non_empty_strings():
    """Every exported prompt must be a non-trivial string."""
    for name, prompt in _ALL_PROMPTS:
        assert isinstance(prompt, str), f"{name} must be a str"
        assert len(prompt) > 100, f"{name} is suspiciously short ({len(prompt)} chars)"


def test_all_prompts_have_meaningful_length():
    """Prompts should have enough content to guide the agent (> 200 chars)."""
    for name, prompt in _ALL_PROMPTS:
        assert len(prompt) > 200, f"{name} is too short to be a useful prompt"


# ── Role context ─────────────────────────────────────────────────────────────

_ROLE_KEYWORDS = {"역할", "role", "당신은", "you are"}


def test_each_prompt_defines_role():
    """Every prompt must establish the agent's identity / role."""
    for name, prompt in _ALL_PROMPTS:
        lower = prompt.lower()
        found = any(kw in lower for kw in _ROLE_KEYWORDS)
        assert found, f"{name} does not define an agent role (expected one of {_ROLE_KEYWORDS})"


# ── Architect-specific ───────────────────────────────────────────────────────


def test_architect_prompt_contains_technical_keywords():
    """Architect prompt must reference technical concerns."""
    lower = ARCHITECT_PROMPT.lower()
    technical_kws = {"tech", "stack", "api", "technical", "architecture", "build"}
    found = {kw for kw in technical_kws if kw in lower}
    assert found, f"ARCHITECT_PROMPT should contain at least one of {technical_kws}"


def test_architect_prompt_mentions_complexity():
    """Architect evaluates complexity — the prompt should reference it."""
    assert "complexity" in ARCHITECT_PROMPT.lower() or "complex" in ARCHITECT_PROMPT.lower()


def test_architect_prompt_mentions_digitalocean():
    """Architect should mention DigitalOcean deployment feasibility."""
    assert "digitalocean" in ARCHITECT_PROMPT.lower() or "digital ocean" in ARCHITECT_PROMPT.lower()


# ── Scout-specific ───────────────────────────────────────────────────────────


def test_scout_prompt_mentions_market():
    """Scout is the market analyst — prompt must mention market concepts."""
    lower = SCOUT_PROMPT.lower()
    market_kws = {"market", "competition", "competitor", "revenue", "user"}
    found = {kw for kw in market_kws if kw in lower}
    assert found, f"SCOUT_PROMPT should contain at least one of {market_kws}"


def test_scout_prompt_mentions_data():
    """Scout backs claims with data, not speculation."""
    lower = SCOUT_PROMPT.lower()
    assert "data" in lower or "evidence" in lower


# ── Guardian-specific ────────────────────────────────────────────────────────


def test_guardian_prompt_mentions_risk():
    """Guardian assesses risks — prompt must mention risk."""
    lower = GUARDIAN_PROMPT.lower()
    assert "risk" in lower


def test_guardian_prompt_mentions_severity():
    """Guardian classifies risk severity — prompt should contain BLOCKER or HIGH."""
    assert "BLOCKER" in GUARDIAN_PROMPT or "HIGH" in GUARDIAN_PROMPT


def test_guardian_score_is_inverted():
    """Guardian score is inverted in Vibe Score™ — prompt must warn about this."""
    assert "INVERTED" in GUARDIAN_PROMPT or "inverted" in GUARDIAN_PROMPT.lower()


# ── Catalyst-specific ────────────────────────────────────────────────────────


def test_catalyst_prompt_mentions_innovation():
    """Catalyst focuses on innovation — prompt must mention it."""
    lower = CATALYST_PROMPT.lower()
    assert "innovation" in lower or "innovati" in lower


def test_catalyst_prompt_mentions_wow_factor():
    """Catalyst evaluates 'wow factor' — prompt should reference this concept."""
    lower = CATALYST_PROMPT.lower()
    assert "wow" in lower or "unique" in lower or "disrupt" in lower


# ── Advocate-specific ────────────────────────────────────────────────────────


def test_advocate_prompt_mentions_user():
    """Advocate is the user champion — prompt must mention user experience."""
    lower = ADVOCATE_PROMPT.lower()
    user_kws = {"user", "ux", "onboarding", "experience"}
    found = {kw for kw in user_kws if kw in lower}
    assert found, f"ADVOCATE_PROMPT should contain at least one of {user_kws}"


def test_advocate_prompt_mentions_mvp():
    """Advocate keeps MVP scope minimal — prompt must reference MVP."""
    assert "mvp" in ADVOCATE_PROMPT.lower() or "MVP" in ADVOCATE_PROMPT


# ── Strategist-specific ──────────────────────────────────────────────────────


def test_strategist_prompt_mentions_vibe_score():
    """Strategist calculates Vibe Score™ — prompt must include the formula."""
    assert "Vibe Score" in STRATEGIST_PROMPT


def test_strategist_prompt_contains_formula():
    """Strategist applies the weighted formula — prompt should have weights."""
    # The formula uses weights like 0.25, 0.20, 0.15
    assert "0.25" in STRATEGIST_PROMPT or "0.20" in STRATEGIST_PROMPT


def test_strategist_prompt_defines_decision_thresholds():
    """Decision thresholds (GO, CONDITIONAL, NO-GO) must appear in strategist prompt."""
    assert "GO" in STRATEGIST_PROMPT
    assert "NO-GO" in STRATEGIST_PROMPT or "NO_GO" in STRATEGIST_PROMPT


def test_strategist_does_not_score_axes():
    """Strategist synthesizes — prompt should note it does NOT score axes."""
    lower = STRATEGIST_PROMPT.lower()
    assert (
        "not score" in lower or "do not score" in lower or "does not score" in lower or "NOT score" in STRATEGIST_PROMPT
    )


# ── Uniqueness ───────────────────────────────────────────────────────────────


def test_prompts_are_all_distinct():
    """Every prompt must be unique — no two agents share the same prompt."""
    prompt_values = [p for _, p in _ALL_PROMPTS]
    assert len(set(prompt_values)) == len(prompt_values), "Two or more prompts are identical"


def test_prompts_have_distinct_core_questions():
    """Each agent's core question should differ."""
    core_questions = []
    for _, prompt in _ALL_PROMPTS:
        # Find the line containing "core question"
        for line in prompt.splitlines():
            if "core question" in line.lower():
                core_questions.append(line.strip())
                break
    # Each agent that defines a core question should have a unique one
    if core_questions:
        assert len(set(core_questions)) == len(core_questions), "Two agents share the same core question"


# ── Score axis coverage ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "prompt_name, prompt, expected_score_label",
    [
        ("ARCHITECT_PROMPT", ARCHITECT_PROMPT, "Technical Feasibility"),
        ("SCOUT_PROMPT", SCOUT_PROMPT, "Market Viability"),
        ("GUARDIAN_PROMPT", GUARDIAN_PROMPT, "Risk Profile"),
        ("CATALYST_PROMPT", CATALYST_PROMPT, "Innovation Score"),
        ("ADVOCATE_PROMPT", ADVOCATE_PROMPT, "User Impact"),
    ],
)
def test_agent_prompt_declares_score_axis(prompt_name, prompt, expected_score_label):
    """Each scoring agent must declare its score axis label in the prompt."""
    assert expected_score_label in prompt, f"{prompt_name} should declare score axis '{expected_score_label}'"
