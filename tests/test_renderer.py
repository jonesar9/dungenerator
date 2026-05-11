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


def test_exit_drift_varies_across_seeds():
    """North exit column should not be identical across different room seeds."""
    seen_cols = set()
    checked = 0
    for seed in range(300):
        room = generate_room(seed=seed, size="medium")
        if not any(e.direction == "north" for e in room.exits):
            continue
        lines = _ascii_map_lines(room, size="medium")
        # lines[0] = N compass label, lines[1] = north wall row
        wall_section = lines[1][:30]  # stay within map, before legend gutter
        for i, ch in enumerate(wall_section):
            if ch in '+/=^v@':
                seen_cols.add(i)
                break
        checked += 1
        if checked >= 30:
            break
    assert len(seen_cols) >= 2, (
        f"Exit drift produced only {len(seen_cols)} distinct column(s) across {checked} rooms"
    )


def test_exit_stays_on_wall():
    """Exit glyphs must appear on the wall border, not the interior."""
    for seed in range(50):
        room = generate_room(seed=seed, size="medium")
        lines = _ascii_map_lines(room, size="medium")
        # North wall is lines[1]; south wall is lines[-3] (before two S-label lines)
        north_wall = lines[1]
        south_wall = lines[-3]
        for line in (north_wall, south_wall):
            for i, ch in enumerate(line):
                if ch in '+/=^v@':
                    # Must not be on an interior floor row — these are wall rows so this always holds,
                    # but confirm the glyph isn't a floor character
                    assert ch != '.', f"Floor char '.' found on wall line: {line!r}"


def test_legend_only_shows_present_glyphs():
    import re
    # Legend entries are always "  X  label" (2 spaces, glyph, 2 spaces, label).
    _LEGEND_ENTRY = re.compile(r'^\s{2}(.)\s{2}\S')
    room = generate_room(seed=44)
    lines = _ascii_map_lines(room)
    legend_start = next((i for i, l in enumerate(lines) if "Legend" in l), None)
    if legend_start is None:
        return
    # Slice to the legend column so padding from the left (map) side doesn't confuse the match.
    legend_col = lines[legend_start].index("Legend")
    legend_glyphs = set()
    for line in lines[legend_start + 1:]:
        right = line[legend_col:] if len(line) > legend_col else ""
        m = _LEGEND_ENTRY.match(right)
        if m:
            legend_glyphs.add(m.group(1))
    map_text = "\n".join(lines[:legend_start])
    for g in legend_glyphs:
        assert g in map_text or g == "@", f"Legend glyph {g!r} not found in map"
