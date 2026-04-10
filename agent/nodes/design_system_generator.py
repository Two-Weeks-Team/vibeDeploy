"""Dynamic design system generator — creates a unique design system per app via LLM."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_DESIGN_SYSTEM_PROMPT = """\
You are a world-class UI/UX designer. Generate a complete, unique design system \
for a web application based on the provided concept.

Return a JSON object with these exact keys:

{
  "color_palette": {
    "primary": "oklch(L% C H)",
    "accent": "oklch(L% C H)",
    "base_hue": <integer 0-360>,
    "surface": "oklch(L% C H)",
    "surface_alt": "oklch(L% C H)",
    "on_primary": "oklch(L% C H)",
    "semantic_success": "oklch(L% C H)",
    "semantic_warning": "oklch(L% C H)",
    "semantic_error": "oklch(L% C H)"
  },
  "typography": {
    "display_font": "<Google Font name>",
    "body_font": "<Google Font name>",
    "mono_font": "JetBrains_Mono",
    "scale_ratio": <float like 1.25 or 1.333>,
    "base_size": "16px"
  },
  "spacing": {
    "unit": 4,
    "radius_sm": "0.375rem",
    "radius_md": "0.625rem",
    "radius_lg": "1rem",
    "radius_full": "9999px"
  },
  "motion": {
    "duration_fast": "150ms",
    "duration_normal": "300ms",
    "duration_slow": "500ms",
    "easing": "cubic-bezier(0.16, 1, 0.3, 1)",
    "stagger_delay": "0.08s",
    "intensity": "subtle|moderate|expressive"
  },
  "layout": {
    "archetype": "storyboard|operations_console|studio|atlas|notebook|lab|creator_shell|marketplace",
    "max_width": "1280px",
    "sidebar_width": "240px",
    "header_height": "56px",
    "grid_columns": 12
  },
  "visual_identity": {
    "mood": "<2-3 word mood>",
    "contrast_level": "low|medium|high",
    "border_style": "none|subtle|defined",
    "shadow_style": "flat|soft|layered",
    "icon_style": "outlined|filled|duotone",
    "illustration_style": "<brief description or 'none'>"
  }
}

Rules:
- Use oklch() color format for all colors (wide-gamut, perceptually uniform)
- Choose primary/accent colors that evoke the app's domain and emotional tone
- Pick fonts from Google Fonts that match the personality (no fallbacks to system fonts)
- The design must feel UNIQUE to this specific app — not generic SaaS or admin
- Consider the target audience, app purpose, and emotional response
- A meal planner should feel warm and inviting (not cold/corporate)
- A finance app should feel trustworthy and precise (not playful)
- A travel app should feel adventurous and aspirational
- A developer tool should feel technical and efficient
- Light mode should be the primary concern; dark mode will be derived
"""

_FALLBACK_DESIGN = {
    "color_palette": {
        "primary": "oklch(45% 0.2 250)",
        "accent": "oklch(70% 0.18 160)",
        "base_hue": 250,
        "surface": "oklch(98% 0.005 250)",
        "surface_alt": "oklch(95% 0.008 250)",
        "on_primary": "oklch(98% 0.005 250)",
        "semantic_success": "oklch(55% 0.18 142)",
        "semantic_warning": "oklch(75% 0.18 75)",
        "semantic_error": "oklch(55% 0.22 25)",
    },
    "typography": {
        "display_font": "Inter",
        "body_font": "Inter",
        "mono_font": "JetBrains_Mono",
        "scale_ratio": 1.25,
        "base_size": "16px",
    },
    "spacing": {
        "unit": 4,
        "radius_sm": "0.375rem",
        "radius_md": "0.625rem",
        "radius_lg": "1rem",
        "radius_full": "9999px",
    },
    "motion": {
        "duration_fast": "150ms",
        "duration_normal": "300ms",
        "duration_slow": "500ms",
        "easing": "cubic-bezier(0.16, 1, 0.3, 1)",
        "stagger_delay": "0.08s",
        "intensity": "moderate",
    },
    "layout": {
        "archetype": "storyboard",
        "max_width": "1280px",
        "sidebar_width": "240px",
        "header_height": "56px",
        "grid_columns": 12,
    },
    "visual_identity": {
        "mood": "clean modern",
        "contrast_level": "medium",
        "border_style": "subtle",
        "shadow_style": "soft",
        "icon_style": "outlined",
        "illustration_style": "none",
    },
}


def _parse_json_response(text: str) -> dict:
    """Extract JSON from an LLM response that may contain markdown fences."""
    # Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # Try extracting from markdown code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", str(text), re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {}


async def design_system_generator(state: dict[str, Any], config=None) -> dict:
    """Generate a unique, app-specific design system via LLM based on idea + inspiration + experience."""
    blueprint = state.get("blueprint") or {}
    idea = state.get("idea") or {}
    inspiration_pack = state.get("inspiration_pack") or {}
    experience_contract = blueprint.get("experience_contract") or {}
    design_system_from_blueprint = blueprint.get("design_system") or {}
    shared_constants = blueprint.get("shared_constants") or {}

    # Build context for the LLM
    context = {
        "app_name": blueprint.get("app_name") or idea.get("name") or "web app",
        "tagline": idea.get("tagline") or idea.get("problem") or "",
        "domain": inspiration_pack.get("domain") or design_system_from_blueprint.get("domain") or "",
        "target_audience": idea.get("target_audience") or "",
        "features": idea.get("features") or [],
        "visual_motifs": inspiration_pack.get("visual_motifs") or [],
        "interface_metaphor": inspiration_pack.get("interface_metaphor") or "",
        "layout_archetype": inspiration_pack.get("layout_archetype") or "",
        "design_direction": experience_contract.get("design_direction") or {},
        "must_have_surfaces": experience_contract.get("must_have_surfaces") or [],
        "experience_non_negotiables": experience_contract.get("experience_non_negotiables") or [],
        "anti_patterns": inspiration_pack.get("anti_patterns") or [],
    }

    generated_design = None
    try:
        from ..llm import MODEL_CONFIG, ainvoke_with_retry, content_to_str, get_llm, get_rate_limit_fallback_models

        model = MODEL_CONFIG.get("brainstorm", "gpt-5.4")
        llm = get_llm(model=model, temperature=0.6, max_tokens=2000)
        response = await ainvoke_with_retry(
            llm,
            [
                {"role": "system", "content": _DESIGN_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Generate a unique design system for this app:\n\n{json.dumps(context, indent=2, ensure_ascii=False)}",
                },
            ],
            fallback_models=get_rate_limit_fallback_models(model),
        )
        raw = content_to_str(response.content)
        generated_design = _parse_json_response(raw)
        if not generated_design.get("color_palette"):
            logger.warning("[DESIGN] LLM response missing color_palette, using fallback")
            generated_design = None
    except Exception:
        logger.warning("[DESIGN] LLM design generation failed, using fallback")

    design = generated_design or _FALLBACK_DESIGN

    # Merge LLM-generated design with any existing blueprint design context
    merged_design_system = {
        **design_system_from_blueprint,
        "generated": design,
        "domain": context["domain"],
        "visual_direction": design.get("visual_identity", {}).get("mood", ""),
    }

    return {
        "design_system_context": {
            "design_system": merged_design_system,
            "experience_contract": experience_contract,
            "shared_constants": shared_constants,
        },
        "design_preset": json.dumps(design, ensure_ascii=False),
        "phase": "design_system_generated",
    }
