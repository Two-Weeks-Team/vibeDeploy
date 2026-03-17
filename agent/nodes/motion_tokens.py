MOTION_INTENSITY = {
    "editorial": {"duration_scale": 1.2, "stagger": 0.15, "ease": "easeOut"},
    "dashboard": {"duration_scale": 0.8, "stagger": 0.05, "ease": "[0.22, 1, 0.36, 1]"},
    "creative": {"duration_scale": 1.5, "stagger": 0.2, "ease": "[0.16, 1, 0.3, 1]"},
    "default": {"duration_scale": 1.0, "stagger": 0.1, "ease": "easeInOut"},
}

REQUIRED_VARIANTS = [
    "fadeInUp",
    "fadeInDown",
    "fadeInLeft",
    "scaleIn",
    "staggerContainer",
    "staggerItem",
    "pageTransition",
    "cardHover",
    "slideInRight",
    "popIn",
]


def generate_motion_tokens(design_system: dict) -> str:
    """Generate a valid TypeScript motion-tokens.ts string for a given design system.

    Args:
        design_system: dict with optional keys:
            - visual_direction: one of "editorial", "dashboard", "creative", "default"

    Returns:
        A TypeScript string suitable for writing to motion-tokens.ts.
    """
    visual_dir = design_system.get("visual_direction", "dashboard")
    intensity = MOTION_INTENSITY.get(visual_dir, MOTION_INTENSITY["default"])

    scale = intensity["duration_scale"]
    stagger = intensity["stagger"]
    ease = intensity["ease"]

    if ease.startswith("["):
        ts_ease = ease
    else:
        ts_ease = f"'{ease}'"

    fast = round(0.15 * scale, 3)
    normal = round(0.3 * scale, 3)
    slow = round(0.5 * scale, 3)

    lines = [
        "import { Variants } from 'framer-motion';",
        "",
        "export const transitions = {",
        f"  fast: {{ duration: {fast}, ease: {ts_ease} }},",
        f"  normal: {{ duration: {normal}, ease: {ts_ease} }},",
        f"  slow: {{ duration: {slow}, ease: {ts_ease} }},",
        "};",
        "",
        "export const variants: Record<string, Variants> = {",
        "  fadeInUp: {",
        "    initial: { opacity: 0, y: 20 },",
        f"    animate: {{ opacity: 1, y: 0, transition: {{ duration: {normal}, ease: {ts_ease} }} }},",
        "  },",
        "  fadeInDown: {",
        "    initial: { opacity: 0, y: -20 },",
        f"    animate: {{ opacity: 1, y: 0, transition: {{ duration: {normal}, ease: {ts_ease} }} }},",
        "  },",
        "  fadeInLeft: {",
        "    initial: { opacity: 0, x: -20 },",
        f"    animate: {{ opacity: 1, x: 0, transition: {{ duration: {normal}, ease: {ts_ease} }} }},",
        "  },",
        "  scaleIn: {",
        "    initial: { opacity: 0, scale: 0.9 },",
        f"    animate: {{ opacity: 1, scale: 1, transition: {{ duration: {normal}, ease: {ts_ease} }} }},",
        "  },",
        "  staggerContainer: {",
        "    initial: {},",
        f"    animate: {{ transition: {{ staggerChildren: {stagger} }} }},",
        "  },",
        "  staggerItem: {",
        "    initial: { opacity: 0, y: 10 },",
        f"    animate: {{ opacity: 1, y: 0, transition: {{ duration: {normal}, ease: {ts_ease} }} }},",
        "  },",
        "  pageTransition: {",
        "    initial: { opacity: 0 },",
        f"    animate: {{ opacity: 1, transition: {{ duration: {slow}, ease: {ts_ease} }} }},",
        f"    exit: {{ opacity: 0, transition: {{ duration: {fast}, ease: {ts_ease} }} }},",
        "  },",
        "  cardHover: {",
        "    initial: { scale: 1 },",
        f"    animate: {{ scale: 1.03, transition: {{ duration: {fast}, ease: {ts_ease} }} }},",
        "  },",
        "  slideInRight: {",
        "    initial: { opacity: 0, x: 40 },",
        f"    animate: {{ opacity: 1, x: 0, transition: {{ duration: {normal}, ease: {ts_ease} }} }},",
        "  },",
        "  popIn: {",
        "    initial: { opacity: 0, scale: 0.8 },",
        f"    animate: {{ opacity: 1, scale: 1, transition: {{ duration: {fast}, ease: {ts_ease} }} }},",
        "  },",
        "};",
        "",
        "export const motionConfig = {",
        f"  stagger: {stagger},",
        f"  durationScale: {scale},",
        "  transitions,",
        "  variants,",
        "};",
        "",
        "export default motionConfig;",
    ]

    return "\n".join(lines) + "\n"
