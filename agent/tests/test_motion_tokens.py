from nodes.motion_tokens import (
    MOTION_INTENSITY,
    REQUIRED_VARIANTS,
    generate_motion_tokens,
)


def test_generates_valid_typescript_string():
    result = generate_motion_tokens({})
    assert "export const" in result


def test_contains_all_required_variants():
    result = generate_motion_tokens({})
    for variant in REQUIRED_VARIANTS:
        assert variant in result, f"Missing variant: {variant}"


def test_contains_transitions_fast_normal_slow():
    result = generate_motion_tokens({})
    assert "fast:" in result
    assert "normal:" in result
    assert "slow:" in result


def test_editorial_intensity_produces_longer_durations():
    editorial_scale = MOTION_INTENSITY["editorial"]["duration_scale"]
    dashboard_scale = MOTION_INTENSITY["dashboard"]["duration_scale"]
    assert editorial_scale > dashboard_scale


def test_dashboard_intensity_produces_shorter_durations():
    dashboard_scale = MOTION_INTENSITY["dashboard"]["duration_scale"]
    default_scale = MOTION_INTENSITY["default"]["duration_scale"]
    assert dashboard_scale < default_scale


def test_unknown_visual_direction_uses_default():
    result = generate_motion_tokens({"visual_direction": "nonexistent"})
    default_result = generate_motion_tokens({"visual_direction": "default"})
    assert result == default_result


def test_contains_framer_motion_import():
    result = generate_motion_tokens({})
    assert "import { Variants } from 'framer-motion'" in result


def test_named_exports_present():
    result = generate_motion_tokens({})
    assert "export const transitions" in result
    assert "export const variants" in result


def test_each_variant_has_initial_and_animate():
    result = generate_motion_tokens({})
    for variant in REQUIRED_VARIANTS:
        variant_block_start = result.find(f"  {variant}:")
        assert variant_block_start != -1, f"Variant block not found: {variant}"
        variant_block = result[variant_block_start : variant_block_start + 400]
        assert "initial:" in variant_block, f"No initial in {variant}"
        assert "animate:" in variant_block, f"No animate in {variant}"


def test_stagger_value_matches_intensity():
    for direction, intensity in MOTION_INTENSITY.items():
        result = generate_motion_tokens({"visual_direction": direction})
        expected_stagger = str(intensity["stagger"])
        assert f"staggerChildren: {expected_stagger}" in result, f"Stagger mismatch for {direction}"


def test_creative_intensity_has_largest_duration_scale():
    assert MOTION_INTENSITY["creative"]["duration_scale"] > MOTION_INTENSITY["editorial"]["duration_scale"]
    assert MOTION_INTENSITY["creative"]["duration_scale"] > MOTION_INTENSITY["default"]["duration_scale"]
    assert MOTION_INTENSITY["creative"]["duration_scale"] > MOTION_INTENSITY["dashboard"]["duration_scale"]


def test_transitions_respect_duration_scale():
    editorial = generate_motion_tokens({"visual_direction": "editorial"})
    dashboard = generate_motion_tokens({"visual_direction": "dashboard"})
    editorial_normal = round(0.3 * MOTION_INTENSITY["editorial"]["duration_scale"], 3)
    dashboard_normal = round(0.3 * MOTION_INTENSITY["dashboard"]["duration_scale"], 3)
    assert f"duration: {editorial_normal}" in editorial
    assert f"duration: {dashboard_normal}" in dashboard
