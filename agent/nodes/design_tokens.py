"""Color token generator — uses LLM-generated palette or falls back to domain presets."""

import re

# Legacy presets kept as fallback only
DOMAIN_PRESETS = {
    "finance": {"primary": "oklch(25% 0.05 260)", "accent": "oklch(85% 0.15 85)", "base_hue": 260},
    "health": {"primary": "oklch(85% 0.04 150)", "accent": "oklch(70% 0.18 25)", "base_hue": 150},
    "creative": {"primary": "oklch(35% 0.2 290)", "accent": "oklch(80% 0.18 75)", "base_hue": 290},
    "food": {"primary": "oklch(30% 0.08 45)", "accent": "oklch(60% 0.25 35)", "base_hue": 45},
    "tech": {"primary": "oklch(20% 0.02 250)", "accent": "oklch(65% 0.25 250)", "base_hue": 250},
}


def _extract_hue(oklch_str: str) -> int:
    """Extract hue value from an oklch() string."""
    match = re.search(r"oklch\([^)]*\s+(\d+)\s*\)", str(oklch_str))
    return int(match.group(1)) if match else 250


def _make_scale(hue: int, chroma_base: float = 0.15, steps: int = 12) -> list[str]:
    result = []
    for i in range(1, steps + 1):
        lightness = round(100 - (i * 7.5), 1)
        chroma = chroma_base if i > 6 else round(chroma_base * (i / 7), 3)
        result.append(f"oklch({lightness}% {chroma:.3f} {hue})")
    return result


def _get_palette(design_system: dict) -> dict:
    """Extract color palette — prefer LLM-generated, fall back to domain preset."""
    generated = design_system.get("generated", {})
    palette = generated.get("color_palette") if generated else None

    if palette and palette.get("primary"):
        return {
            "primary": palette["primary"],
            "accent": palette.get("accent", palette["primary"]),
            "base_hue": palette.get("base_hue", _extract_hue(palette["primary"])),
            "surface": palette.get("surface"),
            "surface_alt": palette.get("surface_alt"),
            "on_primary": palette.get("on_primary"),
            "semantic_success": palette.get("semantic_success", "oklch(55% 0.18 142)"),
            "semantic_warning": palette.get("semantic_warning", "oklch(75% 0.18 75)"),
            "semantic_error": palette.get("semantic_error", "oklch(55% 0.22 25)"),
        }

    # Legacy fallback
    domain = design_system.get("domain", "tech")
    preset = DOMAIN_PRESETS.get(domain, DOMAIN_PRESETS["tech"])
    return {
        **preset,
        "surface": None,
        "surface_alt": None,
        "on_primary": None,
        "semantic_success": "oklch(55% 0.18 142)",
        "semantic_warning": "oklch(75% 0.18 75)",
        "semantic_error": "oklch(55% 0.22 25)",
    }


def generate_color_tokens(design_system: dict) -> str:
    """Return a CSS string with @theme block, semantic tokens, 12-step primary scale, and dark mode."""
    palette = _get_palette(design_system)

    primary = palette["primary"]
    accent = palette["accent"]
    base_hue = palette["base_hue"]
    surface = palette.get("surface") or f"oklch(98% 0.005 {base_hue})"
    surface_alt = palette.get("surface_alt") or f"oklch(95% 0.008 {base_hue})"

    scale = _make_scale(base_hue)

    lines: list[str] = ["@theme {"]

    lines.append(f"  --color-background: {surface};")
    lines.append(f"  --color-foreground: oklch(15% 0.01 {base_hue});")
    lines.append(f"  --color-card: {surface_alt};")
    lines.append(f"  --color-border: oklch(88% 0.01 {base_hue});")
    lines.append(f"  --color-primary: {primary};")
    lines.append(f"  --color-accent: {accent};")
    lines.append(f"  --color-muted: oklch(92% 0.01 {base_hue});")
    lines.append(f"  --color-success: {palette['semantic_success']};")
    lines.append(f"  --color-warning: {palette['semantic_warning']};")
    lines.append(f"  --color-error: {palette['semantic_error']};")

    for i, color in enumerate(scale, 1):
        lines.append(f"  --color-primary-{i}: {color};")

    lines.append("}")

    lines.append("")
    lines.append(".dark {")
    lines.append(f"  --color-background: oklch(12% 0.01 {base_hue});")
    lines.append(f"  --color-foreground: oklch(92% 0.005 {base_hue});")
    lines.append(f"  --color-card: oklch(18% 0.01 {base_hue});")
    lines.append(f"  --color-border: oklch(28% 0.015 {base_hue});")
    lines.append(f"  --color-muted: oklch(22% 0.01 {base_hue});")
    lines.append("}")

    return "\n".join(lines)


def to_css_variables(domain: str = "saas", design_system: dict | None = None) -> str:
    """Generate :root CSS variables. Uses LLM palette when available."""
    if design_system:
        palette = _get_palette(design_system)
    else:
        palette = {**DOMAIN_PRESETS.get(domain, DOMAIN_PRESETS["tech"]),
                   "surface": None, "surface_alt": None, "on_primary": None,
                   "semantic_success": "oklch(55% 0.18 142)",
                   "semantic_warning": "oklch(75% 0.18 75)",
                   "semantic_error": "oklch(55% 0.22 25)"}

    primary = palette["primary"]
    accent = palette["accent"]
    base_hue = palette["base_hue"]

    lines: list[str] = [":root {"]
    lines.append(f"  --background: {palette.get('surface') or f'oklch(98% 0.005 {base_hue})'};")
    lines.append(f"  --foreground: oklch(15% 0.01 {base_hue});")
    lines.append("  --card: oklch(100% 0 0);")
    lines.append(f"  --border: oklch(90% 0.01 {base_hue});")
    lines.append(f"  --primary: {primary};")
    lines.append(f"  --primary-foreground: {palette.get('on_primary') or f'oklch(98% 0.005 {base_hue})'};")
    lines.append(f"  --accent: {accent};")
    lines.append(f"  --muted: oklch(96% 0.008 {base_hue});")
    lines.append(f"  --muted-foreground: oklch(45% 0.02 {base_hue});")
    lines.append(f"  --success: {palette['semantic_success']};")
    lines.append(f"  --warning: {palette['semantic_warning']};")
    lines.append(f"  --destructive: {palette['semantic_error']};")
    lines.append("  --radius: 0.625rem;")
    lines.append("}")

    lines.append("")
    lines.append(".dark {")
    lines.append(f"  --background: oklch(12% 0.01 {base_hue});")
    lines.append(f"  --foreground: oklch(95% 0.005 {base_hue});")
    lines.append(f"  --card: oklch(18% 0.015 {base_hue});")
    lines.append(f"  --border: oklch(25% 0.02 {base_hue});")
    lines.append(f"  --primary: oklch(70% 0.2 {base_hue});")
    lines.append(f"  --accent: oklch(22% 0.03 {base_hue});")
    lines.append(f"  --muted: oklch(20% 0.015 {base_hue});")
    lines.append(f"  --muted-foreground: oklch(65% 0.01 {base_hue});")
    lines.append("}")

    return "\n".join(lines)
