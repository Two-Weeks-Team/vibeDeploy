from typing import Annotated, Dict, List, Literal, NotRequired, Optional, TypedDict

from langgraph.graph import add_messages


class AgentScore(TypedDict):
    score: int  # 0-100
    reasoning: str  # 채점 근거
    key_findings: List[str]  # 핵심 발견사항


class CouncilAnalysis(TypedDict):
    architect: Dict  # 기술 분석 결과
    scout: Dict  # 시장 분석 결과
    guardian: Dict  # 리스크 분석 결과
    catalyst: Dict  # 혁신성 분석 결과
    advocate: Dict  # UX/사용자 분석 결과


class ScoringResult(TypedDict):
    technical_feasibility: AgentScore  # Architect (25%)
    market_viability: AgentScore  # Scout (20%)
    innovation_score: AgentScore  # Catalyst (20%)
    risk_profile: AgentScore  # Guardian (20%, inverted)
    user_impact: AgentScore  # Advocate (15%)
    final_score: float  # Vibe Score™
    decision: Literal["GO", "CONDITIONAL", "NO_GO"]


class CrossExamination(TypedDict):
    architect_vs_guardian: Dict  # 기술 리스크 공방
    scout_vs_catalyst: Dict  # 시장 현실 vs 혁신 잠재력
    advocate_challenges: Dict  # UX 관점에서 양측 도전
    score_adjustments: Dict  # 토론 결과 점수 조정


class GeneratedDocs(TypedDict):
    prd: str  # Product Requirements Document
    tech_spec: str  # Technical Specification
    api_spec: str  # API Specification
    db_schema: str  # Database Schema
    app_spec_yaml: str  # DO App Platform Spec


class DeployResult(TypedDict):
    app_id: str
    live_url: str
    github_repo: str
    status: str
    ci_status: NotRequired[str]  # "pending", "running", "passed", "failed", "timeout"
    ci_url: NotRequired[str]  # Link to GitHub Actions run
    ci_repair_attempts: NotRequired[int]
    local_reason: NotRequired[str]
    local_url: NotRequired[str]
    local_backend_url: NotRequired[str]
    local_frontend_url: NotRequired[str]


class VibeDeployState(TypedDict):
    # Input
    raw_input: str
    input_type: Literal["text", "youtube"]
    transcript: Optional[str]
    key_frames: Optional[List[Dict]]
    visual_context: Optional[str]
    selected_flagship: Optional[str]
    flagship_contract: Optional[Dict]

    # Structured idea
    idea: Dict
    idea_summary: str
    original_idea: Optional[Dict]
    inspiration_pack: Optional[Dict]
    experience_spec: Optional[Dict]
    execution_tasks: Optional[List[Dict]]
    repair_tasks: Optional[List[Dict]]
    task_distribution: Optional[Dict]

    eval_iteration: int
    enrich_result: Optional[Dict]
    fix_storm_result: Optional[Dict]

    # Vibe Council Meeting
    meeting_messages: Annotated[list, add_messages]
    council_analysis: Optional[CouncilAnalysis]
    cross_examination: Optional[CrossExamination]

    # Scoring
    scoring: Optional[ScoringResult]

    user_feedback: Optional[str]  # legacy
    scope_adjustment: Optional[str]  # legacy

    # Documents
    generated_docs: Optional[GeneratedDocs]

    # Blueprint
    blueprint: Optional[Dict]
    prompt_strategy: Optional[Dict]

    # Code
    frontend_code: Optional[Dict]
    backend_code: Optional[Dict]
    code_gen_warnings: Optional[List[str]]

    # Code Evaluation
    code_eval_iteration: int
    code_eval_result: Optional[Dict]
    match_rate: Optional[float]
    build_validation: Optional[Dict]

    # Deployment
    deploy_result: Optional[DeployResult]

    # Meta
    phase: str  # 현재 단계
    error: Optional[str]
