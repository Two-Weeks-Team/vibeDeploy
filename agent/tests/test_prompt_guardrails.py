from agent.nodes.blueprint import BLUEPRINT_SYSTEM_PROMPT
from agent.nodes.enrich import ENRICH_PROMPT
from agent.nodes.fix_storm import SCOPE_DOWN_PROMPT
from agent.nodes.input_processor import IDEA_EXTRACTION_PROMPT
from agent.prompts.code_templates import BACKEND_SYSTEM_PROMPT, FRONTEND_SYSTEM_PROMPT
from agent.prompts.doc_templates import API_SPEC_SYSTEM_PROMPT, PRD_SYSTEM_PROMPT, TECH_SPEC_SYSTEM_PROMPT


def test_frontend_prompt_has_explicit_visual_guardrails():
    assert "next/font" in FRONTEND_SYSTEM_PROMPT
    assert "CSS variables" in FRONTEND_SYSTEM_PROMPT
    assert "Backgrounds must have depth" in FRONTEND_SYSTEM_PROMPT
    assert "signature interaction" in FRONTEND_SYSTEM_PROMPT
    assert "Avoid generic dashboards" in FRONTEND_SYSTEM_PROMPT


def test_backend_prompt_documents_api_prefix_constraint():
    assert 'APIRouter(prefix="/api")' in BACKEND_SYSTEM_PROMPT
    assert "DigitalOcean ingress can strip `/api`" in BACKEND_SYSTEM_PROMPT


def test_upstream_prompts_capture_design_direction_and_contracts():
    assert "visual_style_hints" in IDEA_EXTRACTION_PROMPT
    assert "design_direction" in ENRICH_PROMPT
    assert "Design direction and brand personality" in PRD_SYSTEM_PROMPT
    assert "Frontend experience architecture" in TECH_SPEC_SYSTEM_PROMPT
    assert "request body field names" in API_SPEC_SYSTEM_PROMPT
    assert "design_system" in BLUEPRINT_SYSTEM_PROMPT
    assert "lightweight Next.js" in SCOPE_DOWN_PROMPT
