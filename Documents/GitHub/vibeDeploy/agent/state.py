from typing import Annotated, Dict, List, Literal, Optional, TypedDict

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


class VibeDeployState(TypedDict):
    # Input
    raw_input: str  # 사용자 원본 입력
    input_type: Literal["text", "youtube"]  # 입력 유형
    transcript: Optional[str]  # YouTube 트랜스크립트 (있을 경우)
    key_frames: Optional[List[Dict]]  # 추출된 키프레임 [{ timestamp, image_url, analysis }]
    visual_context: Optional[str]  # GPT-4o vision 분석 결과 종합

    # Structured idea
    idea: Dict  # 구조화된 아이디어 (텍스트 + 시각 컨텍스트 결합)
    idea_summary: str  # 한 줄 요약

    # Vibe Council Meeting
    meeting_messages: Annotated[list, add_messages]  # 회의 대화 로그
    council_analysis: Optional[CouncilAnalysis]  # Phase 1 결과
    cross_examination: Optional[CrossExamination]  # Phase 2 결과

    # Scoring
    scoring: Optional[ScoringResult]

    # Conditional path
    user_feedback: Optional[str]  # 사용자 피드백 (CONDITIONAL 시)
    scope_adjustment: Optional[str]  # 스코프 조정안

    # Documents
    generated_docs: Optional[GeneratedDocs]

    # Code
    frontend_code: Optional[Dict]  # { filepath: content }
    backend_code: Optional[Dict]  # { filepath: content }

    # Deployment
    deploy_result: Optional[DeployResult]

    # Meta
    phase: str  # 현재 단계
    error: Optional[str]
