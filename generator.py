"""Core room generation logic."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from models import Feature, Room, Trap
from stocking import (
    pick_hiding_location,
    roll_atmosphere,
    roll_contents_type,
    roll_exits,
    roll_monster,
    roll_non_combat_encounter,
    roll_trap,
    roll_treasure,
    select_features,
)

_DATA = Path(__file__).parent / "data"
_THEMES_DIR = _DATA / "themes"

_THEMES: dict = {}

SIZE_PRESETS = {
    "small":  {"canvas_w": 40, "canvas_h": 20, "char_per_sq": 2, "feature_cap": 3},
    "medium": {"canvas_w": 60, "canvas_h": 30, "char_per_sq": 3, "feature_cap": 5},
    "large":  {"canvas_w": 80, "canvas_h": 40, "char_per_sq": 4, "feature_cap": 7},
}

# Room dimension table (d6 → width_sq, height_sq)
_ROOM_DIM_TABLE = {
    1: (2, 2),
    2: (3, 2),
    3: (3, 3),
    4: (4, 3),
    5: (4, 4),
    6: (5, 4),
}


def _load_themes() -> dict:
    global _THEMES
    if not _THEMES:
        for path in sorted(_THEMES_DIR.glob("*.json")):
            with open(path, encoding="utf-8") as f:
                _THEMES.update(json.load(f))
    return _THEMES


def get_theme_ids() -> list[str]:
    return list(_load_themes().keys())


def resolve_theme(theme_arg: str, rng: random.Random) -> str:
    theme_ids = get_theme_ids()
    if theme_arg == "random":
        return rng.choice(theme_ids)
    if theme_arg in theme_ids:
        return theme_arg
    raise ValueError(f"Unknown theme: {theme_arg!r}. Choose from: {', '.join(theme_ids)} or 'random'.")


def generate_room(
    theme: str = "random",
    level: int = 1,
    size: str = "medium",
    canvas_w: Optional[int] = None,
    canvas_h: Optional[int] = None,
    exits: Optional[int] = None,
    seed: Optional[int] = None,
    entry: str = "south",
    triggered: bool = False,
) -> Room:
    if seed is None:
        seed = random.randint(0, 999999)
    rng = random.Random(seed)

    themes = _load_themes()
    resolved_theme = resolve_theme(theme, rng)
    theme_data = themes[resolved_theme]

    # Room geometry
    d6 = rng.randint(1, 6)
    width_sq, height_sq = _ROOM_DIM_TABLE[d6]

    # Contents
    contents_type = roll_contents_type(rng)

    preset = SIZE_PRESETS.get(size, SIZE_PRESETS["medium"])
    feature_cap = preset["feature_cap"]

    # Features
    features = select_features(theme_data, contents_type, feature_cap, rng)

    # Monster / treasure / trap / non-combat encounter
    monster = None
    treasure = None
    trap = None
    non_combat_encounter = None

    if contents_type in ("monster", "monster_with_treasure"):
        monster = roll_monster(resolved_theme, level, rng)
        if contents_type == "monster_with_treasure" and monster.stats.treasure_type:
            hiding = pick_hiding_location(features, rng)
            treasure = roll_treasure(monster.stats.treasure_type, rng,
                                     hiding_location=hiding)

    elif contents_type == "unguarded_treasure":
        hiding = pick_hiding_location(features, rng)
        # Unguarded treasure uses one step lower; pick a modest type
        ug_type = _unguarded_treasure_type(level, rng)
        treasure = roll_treasure(ug_type, rng, hiding_location=hiding)
        if treasure:
            for item in treasure.items:
                item.hidden = True

    elif contents_type == "special":
        # d6: 1-2 → trap (~33%), 3-6 → non-combat encounter (~67%)
        # Overall: traps ~5.6% of rooms, non-combat encounters ~11.1%
        if rng.randint(1, 6) <= 2:
            trap = roll_trap(rng)
            trap.triggered = triggered
            contents_type = "trap"
        else:
            non_combat_encounter = roll_non_combat_encounter(rng)
            contents_type = "non_combat_encounter"

    # Exits
    exit_list = roll_exits(theme_data, level, exits, entry, rng)

    # Stair labels
    for ex in exit_list:
        if ex.door_type == "stairs_down":
            ex.leads_to = f"To Level {level + 1}"
        elif ex.door_type == "stairs_up":
            ex.leads_to = f"To Level {max(1, level - 1)}"

    # Atmosphere
    atmosphere = roll_atmosphere(theme_data, rng)

    # Room name
    room_names = theme_data.get("room_names", ["Chamber"])
    room_name = rng.choice(room_names)

    room = Room(
        name=room_name,
        theme=resolved_theme,
        level=level,
        seed=seed,
        width_sq=width_sq,
        height_sq=height_sq,
        contents_type=contents_type,
        monster=monster,
        treasure=treasure,
        trap=trap,
        non_combat_encounter=non_combat_encounter,
        features=features,
        exits=exit_list,
        entry_direction=entry,
        atmosphere=atmosphere,
    )

    # Place features in room grid
    _place_features(room, preset["char_per_sq"], canvas_w, canvas_h, preset)

    return room


def _unguarded_treasure_type(level: int, rng: random.Random) -> str:
    # One step below what's typical for the level
    if level <= 2:
        return rng.choice(["U", "P", "R"])
    elif level <= 4:
        return rng.choice(["B", "C", "U"])
    else:
        return rng.choice(["C", "D", "E"])


def _place_features(room: Room, char_per_sq: int,
                    canvas_w: Optional[int], canvas_h: Optional[int],
                    preset: dict) -> None:
    """Assign grid (col, row) coordinates to each feature, avoiding exits and entry."""
    w = room.width_sq * char_per_sq
    h = room.height_sq * char_per_sq

    # Interior cells: (col, row) starting at (0,0) = top-left of room interior
    occupied: set[tuple[int, int]] = set()

    # Mark exit positions (approximate — on walls, not interior)
    # Interior is (1..w-2, 1..h-2) in rendered coordinates;
    # here we work in interior space, so just track center offsets
    # We'll place features starting from center, spiraling out
    center_col = w // 2
    center_row = h // 2

    spiral = _spiral_coords(center_col, center_row, w, h)

    for feature in room.features:
        for col, row in spiral:
            if (col, row) not in occupied and 0 <= col < w and 0 <= row < h:
                feature.col = col
                feature.row = row
                occupied.add((col, row))
                break

    # Place trap (if triggered, it gets a spot)
    if room.trap and room.trap.triggered:
        for col, row in spiral:
            if (col, row) not in occupied:
                room.trap.col = col
                room.trap.row = row
                occupied.add((col, row))
                break


def _spiral_coords(cx: int, cy: int, w: int, h: int) -> list[tuple[int, int]]:
    """Generate (col, row) pairs spiraling outward from (cx, cy), within bounds."""
    visited: set[tuple[int, int]] = set()
    result: list[tuple[int, int]] = []
    for r in range(max(w, h)):
        for dc in range(-r, r + 1):
            for dr in range(-r, r + 1):
                if abs(dc) == r or abs(dr) == r:
                    col, row = cx + dc, cy + dr
                    if (col, row) not in visited and 0 < col < w - 1 and 0 < row < h - 1:
                        visited.add((col, row))
                        result.append((col, row))
    return result
