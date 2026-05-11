"""ASCII map and stat block rendering."""
from __future__ import annotations

import json
import random
import re
import textwrap
from dataclasses import asdict
from typing import Optional

from models import Exit, Feature, Room, Trap
from generator import SIZE_PRESETS

# ─── ANSI color codes ─────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
RED    = "\033[31m"
GREEN  = "\033[32m"
BLUE   = "\033[34m"
WHITE  = "\033[37m"

DOOR_TYPES_DISPLAY = {
    "archway":     "Open archway",
    "door_wood":   "Closed wooden door",
    "door_iron":   "Closed iron door",
    "door_stuck":  "Wooden door (stuck)",
    "door_locked": "Iron door (locked)",
    "door_secret": "Secret door",
    "stairs_down": "Stairs (down)",
    "stairs_up":   "Stairs (up)",
}

CONTENTS_DISPLAY = {
    "empty":                 "Empty",
    "monster":               "Monster",
    "monster_with_treasure": "Monster (with treasure)",
    "unguarded_treasure":    "Unguarded treasure",
    "trap":                  "Special (trap)",
    "non_combat_encounter":  "Non-Combat Encounter",
    "special":               "Special (trap)",  # fallback for old seeds
}


# Strip ANSI codes to measure true terminal column width
_ANSI_RE = re.compile(r'\033\[[0-9;]*m')


def _visual_len(s: str) -> int:
    return len(_ANSI_RE.sub('', s))


def _pad_to(s: str, width: int) -> str:
    return s + ' ' * max(0, width - _visual_len(s))


class Renderer:
    def __init__(self, room: Room, size: str = "medium",
                 canvas_w: Optional[int] = None, canvas_h: Optional[int] = None,
                 color: bool = True, verbose: bool = False):
        self.room = room
        self.color = color
        self.verbose = verbose

        preset = SIZE_PRESETS.get(size, SIZE_PRESETS["medium"])
        self.canvas_w = canvas_w or preset["canvas_w"]
        self.canvas_h = canvas_h or preset["canvas_h"]
        self.char_per_sq = preset["char_per_sq"]

        # Interior room pixel dimensions
        self.room_w = room.width_sq * self.char_per_sq
        self.room_h = room.height_sq * self.char_per_sq

    # ─── Color helpers ────────────────────────────────────────────────────────

    def _c(self, code: str, text: str) -> str:
        if self.color:
            return f"{code}{text}{RESET}"
        return text

    def _sep(self, char: str = "─", width: Optional[int] = None) -> str:
        w = width or min(self.canvas_w, 60)
        if not self.color:
            char = "-" if char == "─" else "="
        return char * w

    # ─── Header ───────────────────────────────────────────────────────────────

    def render_header(self) -> str:
        room = self.room
        w = min(self.canvas_w, 60)
        sep = ("═" if self.color else "=") * w
        lines = [
            sep,
            self._c(BOLD, f" DUNGEON ROOM GENERATOR  |  seed: {room.seed}"),
            f" Theme: {room.theme.replace('_', ' ').title()}  "
            f"|  Level: {room.level}  |  Size: {room.width_sq}×{room.height_sq} sq",
            sep,
        ]
        return "\n".join(lines)

    # ─── ASCII Map ────────────────────────────────────────────────────────────

    def render_map(self) -> str:
        room = self.room
        rw = self.room_w
        rh = self.room_h

        # Build grid: +2 for walls on each side
        grid_w = rw + 2
        grid_h = rh + 2
        grid = [["#"] * grid_w for _ in range(grid_h)]

        # Fill interior with floor
        for r in range(1, rh + 1):
            for c in range(1, rw + 1):
                grid[r][c] = "."

        # Place exit glyphs on walls
        exit_positions: dict[str, tuple[int, int]] = {}
        for ex in room.exits:
            glyph, pos = self._exit_glyph_and_pos(ex, rw, rh)
            r, c = pos
            grid[r][c] = glyph
            exit_positions[ex.direction] = (r, c)

        # Place features
        for feat in room.features:
            # feat.col/row are 0-indexed interior coords
            gr = feat.row + 1
            gc = feat.col + 1
            if 1 <= gr <= rh and 1 <= gc <= rw:
                grid[gr][gc] = feat.glyph

        # Place triggered trap
        if room.trap and room.trap.triggered:
            tr = room.trap.row + 1
            tc = room.trap.col + 1
            if 1 <= tr <= rh and 1 <= tc <= rw:
                grid[tr][tc] = "X"

        # Build map lines
        map_lines: list[str] = []

        # North label
        north_c = exit_positions.get("north", (0, grid_w // 2))[1]
        north_label = "N" if "north" in exit_positions else ""
        map_lines.append(self._compass_label("N", north_label, north_c, grid_w))

        # Rows
        for r in range(grid_h):
            map_lines.append(self._render_row(r, grid[r], grid_h, rh, exit_positions))

        # South label
        south_c = exit_positions.get("south", (0, grid_w // 2))[1]
        entry_char = "@" if room.entry_direction == "south" else "v"
        map_lines.append(self._compass_label("S", entry_char, south_c, grid_w))
        map_lines.append("  S (entry)" if room.entry_direction == "south" else "  S")

        # Legend lines alongside the map
        legend_lines = self._render_legend(room, exit_positions)

        GUTTER = "   "
        map_width = max(_visual_len(line) for line in map_lines)
        n = max(len(map_lines), len(legend_lines))

        result: list[str] = []
        for i in range(n):
            left = map_lines[i] if i < len(map_lines) else ""
            right = legend_lines[i] if i < len(legend_lines) else ""
            if right:
                result.append(_pad_to(left, map_width) + GUTTER + right)
            else:
                result.append(left)

        return "\n".join(result)

    def _exit_glyph_and_pos(self, ex: Exit,
                             rw: int, rh: int) -> tuple[str, tuple[int, int]]:
        glyph_map = {
            "archway":     "/",
            "door_wood":   "+",
            "door_iron":   "+",
            "door_stuck":  "+",
            "door_locked": "+",
            "door_secret": "=",
            "stairs_down": "^",
            "stairs_up":   "v",
        }
        glyph = glyph_map.get(ex.door_type, "+")

        # Deterministic per-room, per-direction drift — avoids corner cells
        _DIR_SALT = {"north": 0, "south": 1, "east": 2, "west": 3}
        rng = random.Random(self.room.seed * 7 + _DIR_SALT[ex.direction])
        col = rng.randint(2, rw - 1) if rw >= 3 else (rw + 2) // 2
        row = rng.randint(2, rh - 1) if rh >= 3 else (rh + 2) // 2

        if ex.direction == "north":
            return glyph, (0, col)
        elif ex.direction == "south":
            if ex.door_type == "archway":
                return "@", (rh + 1, col)
            return glyph, (rh + 1, col)
        elif ex.direction == "west":
            return glyph, (row, 0)
        else:  # east
            return glyph, (row, rw + 1)

    def _render_row(self, r: int, row: list[str], grid_h: int, rh: int,
                    exit_positions: dict) -> str:
        parts: list[str] = []

        # West label
        west_r = exit_positions.get("west", (None, None))[0]
        if west_r == r:
            parts.append(self._c(CYAN, "W "))
        else:
            parts.append("  ")

        for c, ch in enumerate(row):
            parts.append(self._colorize_glyph(ch))

        # East label
        east_r = exit_positions.get("east", (None, None))[0]
        if east_r == r:
            parts.append(self._c(CYAN, " E"))

        return "".join(parts)

    def _compass_label(self, compass: str, exit_char: str,
                       col: int, grid_w: int) -> str:
        indent = "  " + " " * col
        if exit_char:
            return f"{indent}{self._c(CYAN, exit_char)}"
        return f"{indent}{self._c(DIM, compass)}"

    def _colorize_glyph(self, ch: str) -> str:
        if not self.color:
            return ch
        if ch == "#":
            return self._c(DIM, ch)
        if ch == ".":
            return self._c(DIM, ch)
        if ch in ("+", "=", "/"):
            return self._c(YELLOW, ch)
        if ch == "@":
            return self._c(GREEN, ch)
        if ch in ("^", "v"):
            return self._c(BLUE, ch)
        if ch == "X":
            return self._c(RED, ch)
        if ch == "*":
            return self._c(CYAN, ch)
        if ch == "~":
            return self._c(BLUE, ch)
        return self._c(BOLD, ch)

    def _render_legend(self, room: Room,
                       exit_positions: dict) -> list[str]:
        lines = ["Legend:"]
        used: dict[str, str] = {}

        # Always include @
        if room.entry_direction:
            used["@"] = "Entry point"

        # Exits
        door_glyphs = {"/": "Open archway / entry", "+": "Door (closed)",
                       "=": "Secret door", "^": "Stairs (down)", "v": "Stairs (up)"}
        for ex in room.exits:
            glyph = "/"
            if ex.door_type in ("door_wood", "door_iron", "door_stuck", "door_locked"):
                glyph = "+"
            elif ex.door_type == "door_secret":
                glyph = "="
            elif ex.door_type == "stairs_down":
                glyph = "^"
            elif ex.door_type == "stairs_up":
                glyph = "v"
            # South archway renders as @ on the map (already in legend as "Entry point")
            if ex.direction == "south" and ex.door_type == "archway":
                continue
            used.setdefault(glyph, door_glyphs.get(glyph, "Door"))

        for feat in room.features:
            used.setdefault(feat.glyph, feat.name)

        if room.trap and room.trap.triggered:
            used["X"] = "Trap (triggered)"

        for glyph, label in used.items():
            lines.append(f"  {self._c(BOLD, glyph)}  {label}")
        return lines

    # ─── Stat Block ───────────────────────────────────────────────────────────

    def render_stat_block(self) -> str:
        room = self.room
        w = min(self.canvas_w, 60)
        sep = self._sep("─", w)
        lines: list[str] = [sep]

        lines.append(self._c(BOLD, f"ROOM: {room.name}"))
        lines.append(f"CONTENTS: {CONTENTS_DISPLAY.get(room.contents_type, room.contents_type)}")
        lines.append(sep)

        # Monster
        if room.monster:
            m = room.monster
            s = m.stats
            lines.append(self._c(BOLD, "MONSTER"))
            count_str = f"{m.count} {s.name}" + ("s" if m.count > 1 and not s.name.endswith("s") else "")
            lines.append(f"  {count_str} (HD {s.hd}, AC {s.ac}, #AT {s.attacks}, D {s.damage})")
            lines.append(f"  Save: {s.save}  |  Morale: {s.morale}  |  XP: {s.xp} each")
            if s.special:
                for line in textwrap.wrap(f"  Special: {s.special}", w - 2):
                    lines.append(line)
            lines.append(f"  Behavior: {m.behavior}")
            if self.verbose:
                lines.append(f"  [OSE: roll d6 on theme monster table, band {_level_band_label(room.level)}]")
            lines.append("")

        # Treasure
        if room.treasure and room.treasure.items:
            t = room.treasure
            prefix = "TREASURE (with monster)" if room.contents_type == "monster_with_treasure" \
                else "TREASURE (unguarded)"
            lines.append(self._c(BOLD, prefix))
            # Group by hiding location
            grouped: dict[str, list[str]] = {}
            for item in t.items:
                key = item.hiding_location or "In the open"
                grouped.setdefault(key, []).append(item.description)
            for loc, descs in grouped.items():
                lines.append(f"  {loc}:")
                for desc in descs:
                    lines.append(f"    {desc}")
            lines.append("")

        # Trap
        if room.trap:
            trap = room.trap
            lines.append(self._c(BOLD, "SPECIAL / TRAP"))
            lines.append(f"  {trap.name}")
            for line in textwrap.wrap(f"  Trigger: {trap.trigger}", w - 2):
                lines.append(line)
            for line in textwrap.wrap(f"  Effect:  {trap.effect}", w - 2):
                lines.append(line)
            if not trap.triggered:
                lines.append(f"  {self._c(DIM, '[Hidden — not shown on map. Use --triggered to reveal.]')}")
            lines.append("")

        # Non-combat encounter
        if room.non_combat_encounter:
            enc = room.non_combat_encounter
            lines.append(self._c(BOLD, f"NON-COMBAT ENCOUNTER — {enc.name.upper()}"))
            for line in textwrap.wrap(f"  {enc.description}", w - 2):
                lines.append(line)
            if enc.interactions:
                lines.append(f"  {self._c(DIM, 'Possible interactions:')}")
                for interaction in enc.interactions:
                    for line in textwrap.wrap(f"    • {interaction}", w - 4):
                        lines.append(line)
            lines.append("")

        # Features
        if room.features:
            lines.append(self._c(BOLD, "FEATURES"))
            for feat in room.features:
                header = f"  {feat.name} ({feat.glyph}):"
                lines.append(header)
                for line in textwrap.wrap(f"    {feat.description}", w - 4):
                    lines.append(line)
            lines.append("")

        # Exits
        lines.append(self._c(BOLD, "EXITS"))
        for ex in room.exits:
            direction_label = ex.direction.capitalize()
            is_entry = ex.direction == room.entry_direction
            flavor = ex.flavor
            if ex.leads_to:
                flavor = f"{flavor} [{ex.leads_to}]"
            entry_note = " <- entry" if is_entry else ""
            lines.append(f"  {direction_label:<6} {flavor}{entry_note}")
        lines.append("")

        # Atmosphere
        if room.atmosphere:
            lines.append(self._c(BOLD, "ATMOSPHERE"))
            for cat, desc in room.atmosphere.items():
                lines.append(f"  {cat.capitalize()}: {desc}")
            lines.append("")

        lines.append(sep)
        seed_note = f"Seed: {room.seed} | Roll --seed {room.seed} to reproduce"
        lines.append(self._c(DIM, seed_note))
        lines.append(sep)

        return "\n".join(lines)

    # ─── JSON ─────────────────────────────────────────────────────────────────

    def render_json(self) -> str:
        room = self.room
        data = {
            "seed": room.seed,
            "theme": room.theme,
            "level": room.level,
            "room": {
                "name": room.name,
                "size": {
                    "w": room.width_sq,
                    "h": room.height_sq,
                    "units": "10ft squares",
                },
                "contents_type": room.contents_type,
                "monster": _monster_to_dict(room.monster),
                "treasure": _treasure_to_dict(room.treasure),
                "trap": _trap_to_dict(room.trap),
                "non_combat_encounter": _non_combat_to_dict(room.non_combat_encounter),
                "features": [
                    {"glyph": f.glyph, "name": f.name, "description": f.description}
                    for f in room.features
                ],
                "exits": {
                    ex.direction: {
                        "type": ex.door_type,
                        "flavor": ex.flavor,
                        "leads_to": ex.leads_to,
                    }
                    for ex in room.exits
                },
                "atmosphere": room.atmosphere,
                "entry_direction": room.entry_direction,
            },
        }
        return json.dumps(data, indent=2)

    # ─── Full output ──────────────────────────────────────────────────────────

    def render_ascii(self) -> str:
        parts = [
            self.render_header(),
            "",
            self.render_map(),
            "",
            self.render_stat_block(),
        ]
        return "\n".join(parts)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _level_band_label(level: int) -> str:
    if level <= 2:
        return "1-2"
    elif level <= 4:
        return "3-4"
    return "5-6"


def _monster_to_dict(monster) -> Optional[dict]:
    if monster is None:
        return None
    s = monster.stats
    return {
        "name": s.name,
        "count": monster.count,
        "hd": s.hd,
        "ac": s.ac,
        "attacks": s.attacks,
        "damage": s.damage,
        "save": s.save,
        "morale": s.morale,
        "xp": s.xp,
        "special": s.special,
        "treasure_type": s.treasure_type,
        "behavior": monster.behavior,
    }


def _treasure_to_dict(treasure) -> Optional[dict]:
    if treasure is None:
        return None
    return {
        "total_gp_value": treasure.total_gp_value,
        "items": [
            {
                "description": item.description,
                "hidden": item.hidden,
                "hiding_location": item.hiding_location,
            }
            for item in treasure.items
        ],
    }


def _trap_to_dict(trap) -> Optional[dict]:
    if trap is None:
        return None
    return {
        "type": trap.trap_type,
        "name": trap.name,
        "trigger": trap.trigger,
        "effect": trap.effect,
        "triggered": trap.triggered,
    }


def _non_combat_to_dict(enc) -> Optional[dict]:
    if enc is None:
        return None
    return {
        "type": enc.encounter_type,
        "name": enc.name,
        "description": enc.description,
        "interactions": enc.interactions,
    }
