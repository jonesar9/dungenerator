# OSE Solo Dungeon Room Generator — Design Document
**Handoff to Claude Code**
Version 1.0 | Solo Play Focused

---

## 1. Purpose & Scope

A command-line tool that generates a **single dungeon room** per invocation, suitable for OSE/B/X solo play. The player runs it before or during a session to get a fully described room — ASCII map, stocked contents, and thematic flavor — without knowing what's inside until they "open the door."

The tool is **not** a full dungeon level generator. It produces one room at a time, feeding the oracle loop of solo play. Multiple invocations chain into a dungeon organically.

---

## 2. CLI Interface

### Invocation

```
dungeonroom [OPTIONS]
```

### Options

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--theme` | `-t` | string | `random` | Dungeon theme (see §5). Accepts theme name or `random`. |
| `--level` | `-l` | int | `1` | Dungeon level (1–10). Scales monster HD and treasure. |
| `--size` | `-s` | string | `medium` | Canvas size preset: `small`, `medium`, `large`. Controls ASCII output width/height. |
| `--width` | `-W` | int | (from `--size`) | Override canvas width in characters. Min 30, max 120. |
| `--height` | `-H` | int | (from `--size`) | Override canvas height in characters. Min 15, max 50. |
| `--exits` | `-e` | int | `random` | Force number of exits (1–4). `random` uses the stocking table. |
| `--seed` | `-S` | int | (random) | RNG seed for reproducible output. Printed in output header. |
| `--format` | `-f` | string | `ascii` | Output format: `ascii`, `json`, `both`. |
| `--no-color` | | flag | false | Suppress ANSI color codes. Use for paper/plain terminal output. |
| `--verbose` | `-v` | flag | false | Include full OSE stocking rationale in output (for new players). |

### Size Presets

| Preset | Canvas (W×H) | Room interior max | Use case |
|--------|-------------|-------------------|----------|
| `small` | 40×20 | 20×12 chars | Small paper, narrow terminal, phone |
| `medium` | 60×30 | 36×18 chars | Standard terminal, A5 paper |
| `large` | 80×40 | 56×26 chars | Wide terminal, A4/letter paper |

The room itself is drawn within the canvas with a border. Stat block text wraps to fit canvas width.

---

## 3. Output Structure

### ASCII Mode

Output is three sections separated by blank lines:

```
═══════════════════════════════════════════
 DUNGEON ROOM GENERATOR  |  seed: 84291
 Theme: Undead Crypt  |  Level: 2  |  Size: medium
═══════════════════════════════════════════

[ASCII MAP BLOCK]

[STAT BLOCK]
```

#### ASCII Map Block

The map renders:
- **Room walls** using `#` (solid stone)
- **Floor** using `.` (open space)
- **Exits/doors** using `+` (closed door), `/` (open/archway), `=` (secret door, only shown post-reveal), `v`/`^`/`<`/`>` (stairs down/up/left/right)
- **Features** using single glyphs (see §4)
- **Legend** printed below the map, showing only glyphs present in this room

Exits are placed on the cardinal walls (N/S/E/W). The entry point (where the player came from) is always marked with `@` on the south wall by default, or configurable via `--entry` flag (n/s/e/w).

Example (medium, undead crypt):

```
  N
  +
###+###############
#.................#
W +...A.....c.....+ E
#.................#
#....S............#
###################
  @
  S (entry)

Legend:
  @  Entry point
  +  Closed door
  A  Altar (stone)
  c  Coffin (closed)
  S  Sarcophagus
```

#### Stat Block

```
────────────────────────────────────────────
ROOM: Preparation Chamber
CONTENTS: Monster (with treasure)
────────────────────────────────────────────
MONSTER
  2 Skeletons (HD 1, AC 7, #AT 1, D 1d6)
  Morale: 12 (mindless)
  Behavior: Guarding the sarcophagus.
            Attack on sight.

TREASURE (with monster)
  Hidden in sarcophagus (Search to find):
  35 sp, 1 gem (10 gp, cracked quartz)

FEATURES
  Altar (A): Stone altar, black-stained.
             Nothing of value. Disturbing it
             triggers a morale check for any
             undead in the room.
  Coffin (c): Empty. Disturbed recently —
              lid is ajar, drag marks on floor.
  Sarcophagus (S): Sealed. Contains monster
                   treasure (see above).

EXITS
  North: Closed wooden door (stuck, Str check)
  East:  Open archway
  West:  Closed iron door (locked)

ATMOSPHERE
  Smell of embalming herbs and old rot.
  Faint scratching from inside the coffin.
────────────────────────────────────────────
Seed: 84291 | Roll --seed 84291 to reproduce
────────────────────────────────────────────
```

### JSON Mode

When `--format json` or `--format both`, also emit a JSON object (to stdout or a `.json` file) with all generated data in structured form. Useful for piping into other tools or logging a session.

```json
{
  "seed": 84291,
  "theme": "undead_crypt",
  "level": 2,
  "room": {
    "name": "Preparation Chamber",
    "size": { "w": 7, "h": 5, "units": "10ft" },
    "contents_type": "monster_with_treasure",
    "monster": { ... },
    "treasure": { ... },
    "features": [ ... ],
    "exits": { "north": "door_stuck", "east": "archway", "west": "door_locked" },
    "atmosphere": { "smell": "...", "sound": "..." }
  }
}
```

---

## 4. Feature Glyphs

Standard glyph vocabulary. All features are optional per room; the renderer only places what was rolled/selected.

| Glyph | Feature | Notes |
|-------|---------|-------|
| `A` | Altar / shrine | |
| `B` | Barrel / cask | May contain liquid, goods, or hidden item |
| `C` | Chest | Roll locked/unlocked/trapped separately |
| `c` | Coffin | Closed by default; may be empty or occupied |
| `D` | Debris pile | May hide treasure; takes a turn to search |
| `F` | Fountain / pool | May be magical, mundane, or poisoned |
| `I` | Iron cage | May contain prisoner, beast, or be empty |
| `P` | Pillar / column | Impassable; multiple rendered as `P` |
| `S` | Sarcophagus | Sealed; roll contents separately |
| `T` | Table / workbench | |
| `t` | Throne / chair | |
| `W` | Weapon rack | |
| `X` | Trap (triggered) | Only shown post-trigger; unrevealed traps are hidden |
| `~` | Water / liquid | Floor-level; shallow or deep |
| `^` | Stairs down | |
| `v` | Stairs up | |
| `*` | Magical effect | Glow, rune, circle |
| `?` | Unknown feature | For "something is here" without reveal |

Features are placed pseudo-randomly within the room interior, avoiding overlap with exits, entry, and each other. In `small` mode, feature count is capped at 3 to prevent clutter.

---

## 5. Themes

Each theme is a **data bundle** containing:
- Room name table (d12, e.g. "Guard Post", "Ossuary", "Ritual Chamber")
- Feature weight table (which glyphs are likely for this theme)
- Monster table by level (d6 roll → monster name + OSE stats)
- Treasure flavor (coin types, item types, hiding locations)
- Atmosphere descriptors (smell, sound, light, temperature — d6 each)
- Exit flavor (door material/condition vocabulary)

### Included Themes (v1.0)

| ID | Name | Flavor |
|----|------|--------|
| `undead_crypt` | Undead Crypt | Ancient burial complex; skeletons, zombies, wights |
| `goblin_warren` | Goblin Warren | Cramped, filthy tunnels; goblins, hobgoblins, wolves |
| `ancient_temple` | Ancient Temple | Collapsed religion; cultists, giant bugs, traps |
| `bandit_lair` | Bandit Lair | Humanoid occupation of old structure; bandits, mercenaries |
| `natural_cave` | Natural Cave | Unworked stone; giant animals, fungi, cave hazards |
| `dwarven_ruin` | Dwarven Ruin | Worked stone, old machinery; constructs, troglodytes |
| `wizard_tower` | Wizard's Delve | Experimental chambers; weird monsters, magical traps |
| `random` | (roll on theme table) | Selects uniformly from the above |

Themes are defined in an external data file (`themes.yaml` or `themes.json`) so new themes can be added without modifying source code.

---

## 6. Stocking Logic (OSE-Compatible)

Room contents follow the B/X stocking table, adjusted to match OSE conventions:

### Contents Roll (d6)

| d6 | Result |
|----|--------|
| 1–2 | Empty (but may have features/atmosphere) |
| 3–4 | Monster |
| 5 | Special (trap, trick, or magical feature) |
| 6 | Monster with treasure |

*Note: Unguarded treasure (separate roll, ~1-in-6 for empty rooms) can also occur, matching Moldvay's intent.*

### Monster Selection

- Roll d6 on the theme's level-appropriate monster table.
- Monster stats are pulled from a static data file matching OSE stat block format (HD, AC, #AT, Dmg, Save, Morale, XP).
- Number appearing: use OSE "dungeon" number appearing (not wilderness). Scale by level if level > 1 (×1.5 rounded up at levels 4–6, ×2 at 7+).

### Treasure

- If monster has treasure: use the monster's OSE treasure type, rolled fully.
- If unguarded: roll one step lower on the treasure type table.
- Treasure is described with a hiding location drawn from the theme's flavor vocabulary.

### Traps (Special result)

- Roll d6 on a trap table (separate from theme): pit, spear, gas, falling block, magic, alarm.
- Trap is hidden by default — not revealed in the ASCII map unless `--triggered` flag is set.
- Stat block describes trigger condition and effect.

---

## 7. Room Geometry

Room shape is always rectangular in v1.0 (non-rectangular rooms are a future enhancement).

### Dimension Roll

Inner room dimensions (in 10-ft squares):

| d6 | Width (squares) | Height (squares) |
|----|----------------|-----------------|
| 1 | 2 | 2 |
| 2 | 3 | 2 |
| 3 | 3 | 3 |
| 4 | 4 | 3 |
| 5 | 4 | 4 |
| 6 | 5 | 4 |

The room is scaled to fit within the canvas, with each square represented by 2–4 characters depending on canvas size. In `small` mode, 1 square = 2 chars; in `large` mode, 1 square = 4 chars.

### Exit Placement

- Number of exits: roll d6 (1–2: one exit, 3–4: two exits, 5: three exits, 6: four exits), or use `--exits`.
- One exit is always designated as the entry (south by default).
- Remaining exits are placed on walls randomly, with at least one wall separating each exit.
- Door type per exit: roll d6 (1–2: open archway, 3–4: closed wooden door, 5: iron door, 6: special — stuck/locked/secret by sub-roll).

---

## 8. Project Structure

```
dungeonroom/
├── dungeonroom.py          # Entry point, CLI arg parsing
├── generator.py            # Core generation logic
├── renderer.py             # ASCII map rendering
├── stocking.py             # OSE stocking tables and rolls
├── shapes.py               # Floor mask generation (rect, l_shape, organic)
├── data/
│   ├── themes/
│   │   └── themes.json              # All theme data bundles
│   ├── monster_db.json              # Monster stat blocks and behavior strings
│   ├── monster_tables.json          # Theme/level-band monster lookup tables
│   ├── treasures.json               # Treasure type tables
│   └── non_combat_encounters.json   # Non-combat encounter pool
├── models.py               # Dataclasses: Room, Feature, Exit, Monster, Treasure
├── tests/
│   ├── test_generator.py
│   ├── test_renderer.py
│   └── test_stocking.py
└── README.md
```

**Language:** Python 3.10+
**Dependencies:** `colorama` (for ANSI color support on Windows). All data files are JSON; no YAML dependency. Standard library `random` module with explicit seed support.

---

## 9. Rendering Rules & Edge Cases

- **Small canvas + many features:** cap features at 3, abbreviate stat block lines to fit width. If stat block overflows, wrap and indent continuation lines.
- **Feature collision:** features may not occupy exit cells, the `@` entry cell, or each other. Place in order of importance (monster-associated feature first, then others) using a simple spiral-from-center placement algorithm.
- **No-color mode:** replace ANSI escape codes with plain text. The header separator uses `=` instead of `═`. Intended for copy-paste to notes or printing.
- **Seed output:** always print the seed at top and bottom of ASCII output. If the user didn't supply `--seed`, print "Seed: XXXXX (auto-generated)".
- **Stairs:** if the room is on level 1 and exits include a downward stair, label it "To Level 2." On level N, downward stairs go to N+1. Upward stairs (back to entry level) are only placed if `--exits` >= 2.

---

## 10. Example Invocations

```bash
# Quickstart: random theme, level 1, medium canvas
dungeonroom

# Small paper mode, level 2, goblin warren
dungeonroom --theme goblin_warren --level 2 --size small

# Exact canvas size override for a specific notebook column width
dungeonroom --width 45 --height 22 --theme ancient_temple

# Reproducible room for session notes
dungeonroom --seed 84291 --theme undead_crypt --level 2

# Export room data for logging
dungeonroom --format both --seed 84291 > room_session_04.txt

# Plain text, no ANSI, for paste into plaintext notes
dungeonroom --no-color --size small
```

---

## 11. Out of Scope for v1.0

- Multi-room level generation (the tool is intentionally single-room)
- Non-rectangular room shapes (L-shapes, irregular caverns)
- Connecting rooms into a graph / tracking visited rooms
- Web or GUI interface
- Sound/music
- Save/load session state (use `--seed` and session notes for continuity)

These are natural v2 targets once the single-room core is solid.

---

## 12. Testing Expectations

- `test_generator.py`: given a fixed seed, assert deterministic output for all themes and levels. Cover edge cases: level 10 (max), small canvas, 4 exits, all content types.
- `test_renderer.py`: assert canvas dimensions match preset, assert feature count cap in small mode, assert walls are contiguous.
- `test_stocking.py`: over 1000 runs, assert content-type distribution matches B/X ratios within ±5%.
- All tests runnable with `pytest` from project root.
