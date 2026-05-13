"""Core room generation logic."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from models import Feature, Room, Trap
from shapes import make_floor_mask
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
    "small":  {"canvas_w": 40, "canvas_h": 20, "char_per_sq": 2, "rows_per_sq": 1, "feature_cap": 3},
    "medium": {"canvas_w": 60, "canvas_h": 30, "char_per_sq": 3, "rows_per_sq": 2, "feature_cap": 5},
    "large":  {"canvas_w": 80, "canvas_h": 40, "char_per_sq": 4, "rows_per_sq": 2, "feature_cap": 7},
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

    preset = SIZE_PRESETS.get(size, SIZE_PRESETS["medium"])
    feature_cap = preset["feature_cap"]
    char_per_sq = preset["char_per_sq"]
    rows_per_sq = preset.get("rows_per_sq", 1)

    # Room geometry
    d6 = rng.randint(1, 6)
    width_sq, height_sq = _ROOM_DIM_TABLE[d6]

    # Shape — organic requires a large enough interior for CA to look meaningful
    rw = width_sq * char_per_sq
    rh = height_sq * rows_per_sq
    available_shapes = ["rect", "l_shape", "organic"] if rw >= 6 and rh >= 6 else ["rect", "l_shape"]
    theme_shape_w = theme_data.get("shape_weights", {})
    shape_weights = [max(theme_shape_w.get(s, 1), 0) for s in available_shapes]
    if sum(shape_weights) == 0:
        shape_weights = [1] * len(available_shapes)
    shape_type = rng.choices(available_shapes, weights=shape_weights, k=1)[0]

    # Contents
    contents_type = roll_contents_type(rng)

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
        shape_type=shape_type,
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

    # Place features only on floor cells
    mask = make_floor_mask(shape_type, rw, rh, seed)
    _place_features(room, char_per_sq, rows_per_sq, canvas_w, canvas_h, preset, mask)

    return room


def _unguarded_treasure_type(level: int, rng: random.Random) -> str:
    # One step below what's typical for the level
    if level <= 2:
        return rng.choice(["U", "P", "R"])
    elif level <= 4:
        return rng.choice(["B", "C", "U"])
    else:
        return rng.choice(["C", "D", "E"])


def _place_features(room: Room, char_per_sq: int, rows_per_sq: int,
                    canvas_w: Optional[int], canvas_h: Optional[int],
                    preset: dict, mask: list[list[bool]]) -> None:
    """Assign grid (col, row) coordinates to each feature, on floor cells only."""
    w = room.width_sq * char_per_sq
    h = room.height_sq * rows_per_sq
    occupied: set[tuple[int, int]] = set()
    spiral = _spiral_coords(w // 2, h // 2, w, h)

    for feature in room.features:
        for col, row in spiral:
            if (col, row) not in occupied and 0 <= col < w and 0 <= row < h and mask[row][col]:
                feature.col = col
                feature.row = row
                occupied.add((col, row))
                break

    if room.trap and room.trap.triggered:
        for col, row in spiral:
            if (col, row) not in occupied and mask[row][col]:
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
