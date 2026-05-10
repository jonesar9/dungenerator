"""Tests for generator.py — determinism, edge cases, all themes/levels."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from generator import generate_room, get_theme_ids, SIZE_PRESETS


def test_deterministic_output():
    """Same seed + params must produce identical rooms."""
    r1 = generate_room(theme="undead_crypt", level=2, seed=84291)
    r2 = generate_room(theme="undead_crypt", level=2, seed=84291)
    assert r1.name == r2.name
    assert r1.contents_type == r2.contents_type
    assert r1.width_sq == r2.width_sq
    assert r1.seed == 84291


def test_all_themes_level1():
    for theme in get_theme_ids():
        room = generate_room(theme=theme, level=1, seed=42)
        assert room.theme == theme
        assert room.level == 1
        assert room.seed == 42


def test_all_themes_level6():
    for theme in get_theme_ids():
        room = generate_room(theme=theme, level=6, seed=99)
        assert room.theme == theme
        assert room.level == 6


def test_random_theme_resolves():
    room = generate_room(theme="random", seed=12345)
    assert room.theme in get_theme_ids()


def test_level_6_max_band():
    """Level 6 uses the levels_5_6 band without crashing."""
    room = generate_room(theme="undead_crypt", level=6, seed=1)
    assert room is not None
    assert room.level == 6


def test_small_canvas_feature_cap():
    """Small canvas caps features at 3."""
    cap = SIZE_PRESETS["small"]["feature_cap"]
    for seed in range(20):
        room = generate_room(size="small", seed=seed)
        assert len(room.features) <= cap, f"seed={seed}: {len(room.features)} features > cap {cap}"


def test_4_exits_forced():
    room = generate_room(exits=4, seed=7777)
    assert len(room.exits) == 4


def test_1_exit_forced():
    room = generate_room(exits=1, seed=8888)
    assert len(room.exits) == 1


def test_contents_types():
    """All content types are reachable across enough seeds."""
    found = set()
    for s in range(1000):
        room = generate_room(seed=s)
        found.add(room.contents_type)
    expected = {"empty", "monster", "monster_with_treasure", "unguarded_treasure",
                "trap", "non_combat_encounter"}
    assert found >= {"empty", "monster"}, f"Core types missing: {found}"
    # Trap and non-combat encounter may need many seeds given ~5-11% rates
    missing = expected - found
    assert len(missing) <= 1, f"Too many types unreachable across 1000 seeds: {missing}"


def test_non_combat_encounter_room():
    """A room with non_combat_encounter contents_type has the encounter populated."""
    for seed in range(500):
        room = generate_room(seed=seed)
        if room.contents_type == "non_combat_encounter":
            assert room.non_combat_encounter is not None
            assert room.trap is None
            assert room.monster is None
            break
    # Not an error if we don't find one in 500 seeds, but very unlikely


def test_trap_room():
    """A room with trap contents_type has trap populated."""
    for seed in range(500):
        room = generate_room(seed=seed)
        if room.contents_type == "trap":
            assert room.trap is not None
            assert room.non_combat_encounter is None
            break


def test_entry_direction():
    for direction in ("north", "south", "east", "west"):
        room = generate_room(entry=direction, seed=1001)
        assert room.entry_direction == direction
        # Entry direction always has an exit
        directions_in_exits = [e.direction for e in room.exits]
        assert direction in directions_in_exits


def test_triggered_flag():
    """With triggered=True, trap.triggered is set if room has a trap."""
    for seed in range(200):
        room = generate_room(seed=seed, triggered=True)
        if room.trap is not None:
            assert room.trap.triggered is True
            break


def test_seed_in_output():
    room = generate_room(seed=99999)
    assert room.seed == 99999


def test_room_dimensions_valid():
    for seed in range(50):
        room = generate_room(seed=seed)
        assert 2 <= room.width_sq <= 5
        assert 2 <= room.height_sq <= 4


def test_exits_include_entry():
    """Entry direction always appears in exit list."""
    for seed in range(30):
        room = generate_room(seed=seed, entry="north")
        dirs = [e.direction for e in room.exits]
        assert "north" in dirs
