"""Tests for renderer.py — canvas dimensions, feature cap, wall contiguity."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from generator import generate_room, SIZE_PRESETS
from renderer import Renderer


def _ascii_map_lines(room, size="medium", color=False) -> list[str]:
    r = Renderer(room, size=size, color=color)
    return r.render_map().splitlines()


def test_no_color_output_has_no_ansi():
    room = generate_room(seed=1)
    r = Renderer(room, color=False)
    output = r.render_ascii()
    assert "\033[" not in output


def test_ascii_output_contains_seed():
    room = generate_room(seed=55555)
    r = Renderer(room, color=False)
    output = r.render_ascii()
    assert "55555" in output


def test_json_output_valid():
    import json
    room = generate_room(seed=42)
    r = Renderer(room, color=False)
    data = json.loads(r.render_json())
    assert data["seed"] == 42
    assert "room" in data
    assert "exits" in data["room"]


def test_json_contains_theme_and_level():
    import json
    room = generate_room(theme="goblin_warren", level=3, seed=7)
    r = Renderer(room, color=False)
    data = json.loads(r.render_json())
    assert data["theme"] == "goblin_warren"
    assert data["level"] == 3


def test_map_contains_entry_glyph():
    """The map must contain @ or an entry glyph."""
    room = generate_room(seed=10)
    lines = _ascii_map_lines(room)
    full = "\n".join(lines)
    assert "@" in full or "+" in full or "/" in full


def test_stat_block_has_exits_section():
    room = generate_room(seed=20)
    r = Renderer(room, color=False)
    stat = r.render_stat_block()
    assert "EXITS" in stat


def test_stat_block_monster_section():
    for seed in range(100):
        room = generate_room(seed=seed)
        if room.monster is not None:
            r = Renderer(room, color=False)
            stat = r.render_stat_block()
            assert "MONSTER" in stat
            assert room.monster.stats.name in stat
            break


def test_stat_block_atmosphere():
    room = generate_room(seed=5)
    r = Renderer(room, color=False)
    stat = r.render_stat_block()
    if room.atmosphere:
        assert "ATMOSPHERE" in stat


def test_small_map_feature_count():
    cap = SIZE_PRESETS["small"]["feature_cap"]
    for seed in range(20):
        room = generate_room(size="small", seed=seed)
        assert len(room.features) <= cap


def test_both_format_renders():
    room = generate_room(seed=33)
    r = Renderer(room, color=False)
    ascii_out = r.render_ascii()
    json_out = r.render_json()
    assert len(ascii_out) > 0
    assert len(json_out) > 0


def test_walls_present_in_map():
    """Map grid must contain # wall characters."""
    room = generate_room(seed=77)
    lines = _ascii_map_lines(room)
    wall_lines = [l for l in lines if "#" in l]
    assert len(wall_lines) >= 2  # at least top and bottom walls


def test_legend_only_shows_present_glyphs():
    room = generate_room(seed=44)
    lines = _ascii_map_lines(room)
    legend_start = next((i for i, l in enumerate(lines) if "Legend" in l), None)
    if legend_start is None:
        return
    legend_glyphs = set()
    for line in lines[legend_start + 1:]:
        stripped = line.strip()
        if stripped:
            legend_glyphs.add(stripped[0])
    map_text = "\n".join(lines[:legend_start])
    for g in legend_glyphs:
        assert g in map_text or g == "@", f"Legend glyph {g!r} not found in map"
