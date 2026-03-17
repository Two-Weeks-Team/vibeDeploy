DOMAIN_PRESETS = {
    "finance": {"primary": "oklch(25% 0.05 260)", "accent": "oklch(85% 0.15 85)", "base_hue": 260},
    "health": {"primary": "oklch(85% 0.04 150)", "accent": "oklch(70% 0.18 25)", "base_hue": 150},
    "creative": {"primary": "oklch(35% 0.2 290)", "accent": "oklch(80% 0.18 75)", "base_hue": 290},
    "food": {"primary": "oklch(30% 0.08 45)", "accent": "oklch(60% 0.25 35)", "base_hue": 45},
    "tech": {"primary": "oklch(20% 0.02 250)", "accent": "oklch(65% 0.25 250)", "base_hue": 250},
}


def _make_scale(hue: int, chroma_base: float = 0.15, steps: int = 12) -> list[str]:
    result = []
    for i in range(1, steps + 1):
        lightness = round(100 - (i * 7.5), 1)
        chroma = chroma_base if i > 6 else round(chroma_base * (i / 7), 3)
        result.append(f"oklch({lightness}% {chroma:.3f} {hue})")
    return result


def generate_color_tokens(design_system: dict) -> str:
    """Return a CSS string with @theme block, semantic tokens, 12-step primary scale, and dark mode."""
    domain = design_system.get("domain", "tech")
    preset = DOMAIN_PRESETS.get(domain, DOMAIN_PRESETS["tech"])

    primary = preset["primary"]
    accent = preset["accent"]
    base_hue = preset["base_hue"]

    scale = _make_scale(base_hue)

    lines: list[str] = ["@theme {"]

    lines.append(f"  --color-background: oklch(98% 0.005 {base_hue});")
    lines.append(f"  --color-foreground: oklch(15% 0.01 {base_hue});")
    lines.append(f"  --color-card: oklch(97% 0.005 {base_hue});")
    lines.append(f"  --color-border: oklch(88% 0.01 {base_hue});")
    lines.append(f"  --color-primary: {primary};")
    lines.append(f"  --color-accent: {accent};")
    lines.append(f"  --color-muted: oklch(92% 0.01 {base_hue});")
    lines.append("  --color-success: oklch(55% 0.18 142);")
    lines.append("  --color-warning: oklch(75% 0.18 75);")
    lines.append("  --color-error: oklch(55% 0.22 25);")

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
