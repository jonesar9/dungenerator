# dungeonroom

> **OSE Solo Dungeon Room Generator** — one room, fully stocked, every time you open the door.

A command-line tool for **Old-School Essentials** (and B/X-compatible) solo play. Run it before descending a staircase or kicking in a door. Get a complete room: ASCII map, monster stats, treasure, traps, atmosphere, and exits — all derived from the official B/X stocking tables and fully reproducible by seed.

---

```
══════════════════════════════════════════════════════════
 DUNGEON ROOM GENERATOR  |  seed: 481620
 Theme: Undead Crypt  |  Level: 2  |  Size: 3×3 sq
══════════════════════════════════════════════════════════

         N
         +
  ###########+######
  #.................#
W +..c.....S.......+ E
  #.................#
  #....A............#
  #+################
    @              Legend:
    S (entry)        @  Entry point
                     +  Door (closed)
                     c  Coffin
                     S  Sarcophagus
                     A  Altar

------------------------------------------------------------
ROOM: Preparation Chamber
CONTENTS: Monster (with treasure)
------------------------------------------------------------
MONSTER
  2 Skeletons (HD 1, AC 7, #AT 1, D 1d6)
  Save: F1  |  Morale: 12  |  XP: 10 each
  Behavior: Guarding the sarcophagus. Attack on sight.

TREASURE (with monster)
  Hidden in sarcophagus:
    35 sp
    1 gem (10 gp, cracked quartz)

FEATURES
  Coffin (c):
    Empty. Lid ajar — drag marks on the floor.
  Sarcophagus (S):
    Sealed stone sarcophagus. Contains monster treasure.
  Altar (A):
    Black-stained stone altar. Nothing of value. Disturbing
    it triggers a morale check for any undead in the room.

EXITS
  North   Rotting wooden door
  East    Iron door, green with age
  South   Narrow stone archway <- entry

ATMOSPHERE
  Smell: Embalming herbs and old rot
  Sound: Faint scratching from inside a coffin

------------------------------------------------------------
Seed: 481620 | Roll --seed 481620 to reproduce
------------------------------------------------------------
```

---

## Contents

- [Why this tool?](#why-this-tool)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Options reference](#options-reference)
- [Themes](#themes)
- [Room shapes](#room-shapes)
- [Stocking logic](#stocking-logic)
- [Map glyphs](#map-glyphs)
- [Output formats](#output-formats)
- [Examples](#examples)
- [Reproducibility and seeds](#reproducibility-and-seeds)
- [Project layout](#project-layout)
- [Running the tests](#running-the-tests)
- [Known limitations](#known-limitations)

---

## Why this tool?

Solo dungeon play lives or dies on the oracle loop: *What's in the next room?* You want the answer to feel like the referee rolled it behind a screen — not like you picked it. `dungeonroom` closes that loop.

Each invocation:

1. Rolls room dimensions on the B/X dimension table (d6)
2. Selects a room shape (rectangular, L-shaped, or organic cavern)
3. Stocks it with the OSE d6 table (empty → monster → special → monster-with-treasure)
4. Picks a monster from a level-appropriate theme table with full stat block
5. Rolls treasure using the monster's OSE treasure type
6. Places features (coffins, altars, barrels, pillars…) on the floor using a spiral-from-center algorithm
7. Rolls exits and door types
8. Generates atmosphere: smell, sound, light, temperature
9. Renders everything as an ASCII map with a stat block alongside

Run it once. Descend. Run it again.

---

## Installation

**Python 3.10 or later required.**

```bash
# Clone the repo
git clone https://github.com/example/dungeonroom.git
cd dungeonroom

# Install in editable mode (exposes the `dungeonroom` command)
pip install -e .
```

Dependencies are minimal: `PyYAML` (for the data files) and `colorama` (for ANSI colors on Windows). Both are installed automatically.

### Verify it works

```bash
dungeonroom --help
```

You should see the full options list. If the command is not found, make sure your Python scripts directory is on `PATH`, or run it directly:

```bash
python dungeonroom.py
```

---

## Quickstart

```bash
# Random theme, level 1, medium canvas — just go
dungeonroom

# Specify a theme and level
dungeonroom --theme goblin_warren --level 3

# Reproduce a specific room from your session notes
dungeonroom --seed 84291 --theme undead_crypt --level 2

# Plain text for pasting into a notebook
dungeonroom --no-color --size small
```

The seed is always printed at the top and bottom of the output. Write it down. Any room can be regenerated exactly.

---

## Options reference

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--theme` | `-t` | string | `random` | Dungeon theme. See [Themes](#themes). |
| `--level` | `-l` | int | `1` | Dungeon level 1–6. Scales monster HD and treasure. |
| `--size` | `-s` | string | `medium` | Canvas size preset: `small`, `medium`, or `large`. |
| `--width` | `-W` | int | _(from size)_ | Override canvas width in characters. Range: 30–120. |
| `--height` | `-H` | int | _(from size)_ | Override canvas height in characters. Range: 15–50. |
| `--exits` | `-e` | int | _(random)_ | Force number of exits 1–4. Default uses the OSE stocking table. |
| `--seed` | `-S` | int | _(auto)_ | RNG seed for reproducible output. Auto-generated and printed when omitted. |
| `--format` | `-f` | string | `ascii` | Output format: `ascii`, `json`, or `both`. |
| `--no-color` | | flag | false | Suppress ANSI color codes. Use for plain-text notes or printing. |
| `--verbose` | `-v` | flag | false | Add OSE stocking rationale annotations to the stat block. Good for learning the system. |
| `--entry` | | string | `south` | Which wall the player entered from: `north`, `south`, `east`, `west`. |
| `--triggered` | | flag | false | Reveal triggered traps with `X` on the ASCII map. |

### Canvas size presets

| Preset | Canvas (W×H chars) | Use case |
|--------|-------------------|----------|
| `small` | 40×20 | Narrow terminal, phone, small paper |
| `medium` | 60×30 | Standard 80-column terminal, A5 paper |
| `large` | 80×40 | Wide terminal, A4/letter paper, printing |

Feature count is capped per preset: 3 (small), 5 (medium), 7 (large) — keeping small canvases legible.

---

## Themes

Seven dungeon themes are included. Each theme is a self-contained data bundle: room name table, monster table by level band, treasure flavor, atmosphere descriptors, exit vocabulary, and feature weights.

| ID | Name | Flavor |
|----|------|--------|
| `undead_crypt` | **Undead Crypt** | Ancient burial complex. Skeletons, zombies, wights, mummies. |
| `goblin_warren` | **Goblin Warren** | Cramped, filthy tunnels. Goblins, hobgoblins, bugbears, ogres. |
| `ancient_temple` | **Ancient Temple** | Collapsed religion. Cultists, gargoyles, basilisks, lamia. |
| `bandit_lair` | **Bandit Lair** | Humanoid occupation of old structure. Bandits, veterans, gnolls, trolls. |
| `natural_cave` | **Natural Cave** | Unworked stone. Giant animals, oozes, cave bears, dragons. |
| `dwarven_ruin` | **Dwarven Ruin** | Worked stone, old machinery. Troglodytes, constructs, golems, vampires. |
| `wizard_tower` | **Wizard's Delve** | Experimental chambers. Apprentices, golems, djinn, liches. |
| `random` | _(roll on theme table)_ | Selects uniformly at random from the seven themes above. |

Themes are data-driven. To add a new theme, add an entry to `data/themes/themes.json` and a matching block in `data/monsters.yaml`. No source code changes required.

---

## Room shapes

Rooms are not always rectangles. The generator picks a shape weighted by the theme data:

| Shape | Description |
|-------|-------------|
| `rect` | Standard rectangle. Available at all sizes. |
| `l_shape` | L-shaped room — one corner cut away. Available at all sizes. |
| `organic` | Irregular cavern carved by cellular automaton. Only available when the interior is large enough (≥6×6 chars). |

Natural cave and goblin warren themes weight toward organic; dwarven ruins and crypts weight toward rectangular. Features and exits are always placed on valid floor cells — the renderer respects the shape mask.

---

## Stocking logic

`dungeonroom` follows the **B/X / OSE stocking table** faithfully.

### Contents roll (d6)

| d6 | Result | Frequency |
|----|--------|-----------|
| 1–2 | Empty (features + atmosphere only) | ~33% |
| 3–4 | Monster | ~33% |
| 5 | Special (trap or non-combat encounter) | ~17% |
| 6 | Monster with treasure | ~17% |

An unguarded treasure sub-roll (1-in-6 chance on empty results) matches Moldvay's intent, giving unguarded treasure approximately 5% of rooms.

### Monster scaling

Monster counts use OSE "dungeon appearing" numbers. At levels 4–6, count is multiplied by 1.5 (rounded up). Each theme has three level bands: 1–2, 3–4, and 5–6, with progressively harder monsters.

### Traps

When the contents roll is **Special**, there is a 1-in-3 chance of a trap (otherwise a non-combat encounter). Six trap types are available:

| Type | Example effect |
|------|---------------|
| Pit | 10-ft pit, 1d6 damage, Dex save |
| Spear | Poisoned spear, 1d6+save vs. poison |
| Gas | Sleep/poison gas, save or incapacitated |
| Falling block | 2d6 damage, Str check to avoid |
| Magic | Curse, random spell effect |
| Alarm | Loud noise, nearby wandering monster check |

Traps are **hidden by default** — not shown on the map. Use `--triggered` to reveal a sprung trap as `X`.

### Non-combat encounters

The other 2-in-3 of "Special" results. Types include: neutral NPC, trick, puzzle, sanctuary, omen, and hazard. Each has a description and a list of possible player interactions.

### Treasure

Treasure uses the full OSE treasure type system. Each component (cp, sp, ep, gp, pp, gems, jewelry, magic items) is rolled independently per the type tables. Hiding location is drawn from the room's features and atmosphere vocabulary.

---

## Map glyphs

The ASCII map uses a compact glyph vocabulary. Only glyphs present in the current room appear in the legend.

### Structure

| Glyph | Meaning |
|-------|---------|
| `#` | Wall (solid stone) |
| `.` | Floor (open space) |
| `@` | Entry point |

### Exits

| Glyph | Meaning |
|-------|---------|
| `/` | Open archway |
| `+` | Closed door (wood or iron) |
| `=` | Secret door (only shown after reveal) |
| `^` | Stairs down |
| `v` | Stairs up |

### Features

| Glyph | Feature | Notes |
|-------|---------|-------|
| `A` | Altar / shrine | |
| `B` | Barrel / cask | May contain liquid, goods, or a hidden item |
| `C` | Chest | Roll locked/unlocked/trapped separately |
| `c` | Coffin | Closed by default; may be empty or occupied |
| `D` | Debris pile | Searching takes a turn; may hide treasure |
| `F` | Fountain / pool | May be magical, mundane, or poisoned |
| `I` | Iron cage | May contain a prisoner, beast, or be empty |
| `P` | Pillar / column | Impassable |
| `S` | Sarcophagus | Sealed; roll contents separately |
| `T` | Table / workbench | |
| `t` | Throne / chair | |
| `W` | Weapon rack | |
| `X` | Trap (triggered) | Only shown with `--triggered` |
| `~` | Water / liquid | Floor-level pool |
| `*` | Magical effect | Glowing rune, circle, or ward |
| `?` | Unknown feature | "Something is here" without immediate reveal |

### Color coding (ANSI mode)

| Color | Glyphs |
|-------|--------|
| Dim grey | `#` `.` (walls and floor recede) |
| Yellow | `+` `=` `/` (doors and exits) |
| Green | `@` (entry point) |
| Blue | `^` `v` `~` (stairs and water) |
| Red | `X` (triggered trap) |
| Cyan | `*` compass labels (N/S/E/W) |
| Bold white | All other features |

Use `--no-color` to disable ANSI codes entirely. The header separator switches from `═` to `=` and all colors are removed — safe for copy-pasting into plaintext notes or printing.

---

## Output formats

### `--format ascii` (default)

Three sections separated by blank lines:

1. **Header** — generator name, seed, theme, level, room dimensions
2. **Map** — ASCII grid with compass labels and inline legend
3. **Stat block** — MONSTER, TREASURE, SPECIAL/TRAP, FEATURES, EXITS, ATMOSPHERE

### `--format json`

Emits a JSON object with all generated data. Useful for piping into session-logging scripts or building on top of the generator.

```json
{
  "seed": 84291,
  "theme": "undead_crypt",
  "level": 2,
  "room": {
    "name": "Preparation Chamber",
    "size": { "w": 3, "h": 3, "shape": "rect", "units": "10ft squares" },
    "contents_type": "monster_with_treasure",
    "monster": {
      "name": "Skeleton",
      "count": 2,
      "hd": "1",
      "ac": 7,
      "attacks": "1 weapon",
      "damage": "1d6",
      "save": "F1",
      "morale": 12,
      "xp": 10,
      "special": "Undead: immune to sleep and charm",
      "treasure_type": "B",
      "behavior": "Guarding the sarcophagus. Attack on sight."
    },
    "treasure": { ... },
    "features": [ ... ],
    "exits": { ... },
    "atmosphere": { ... },
    "entry_direction": "south"
  }
}
```

### `--format both`

Prints the ASCII output followed by the JSON object, separated by a blank line. Good for session logs where you want a human-readable record and a machine-parseable one.

---

## Examples

### The basics

```bash
# Completely random — new room every time
dungeonroom

# Specific theme and level
dungeonroom --theme goblin_warren --level 3

# Only one exit (no escape routes)
dungeonroom --exits 1 --theme bandit_lair
```

### Session logging

```bash
# Redirect to a session log; seed is in the output for replay
dungeonroom --theme undead_crypt --level 2 >> session_04.txt

# Export JSON for structured logging
dungeonroom --format json >> session_04.jsonl

# Both: human-readable record + machine-parseable
dungeonroom --format both --seed 84291 > room_17.txt
```

### Reproducibility

```bash
# Reproduce a room exactly from your notes
dungeonroom --seed 84291 --theme undead_crypt --level 2

# The room above, but now the trap has sprung
dungeonroom --seed 84291 --theme undead_crypt --level 2 --triggered
```

### Paper and narrow terminal

```bash
# Small preset — 40 columns, fits a narrow terminal or index card
dungeonroom --size small --no-color

# Custom dimensions for a specific notebook column width
dungeonroom --width 45 --height 22 --no-color

# Large preset — 80 columns, good for printing
dungeonroom --size large --no-color
```

### Entry direction

By default, the player enters from the **south** wall (the bottom of the map). Change this when you came in from a different direction.

```bash
# Entered from the north — use when descending into a room from a northern passage
dungeonroom --entry north

# Entered from the east
dungeonroom --entry east --theme dwarven_ruin --level 4
```

### The verbose flag

New to OSE? `--verbose` annotates the stat block with the OSE stocking rationale — which table was rolled, which band was used, etc.

```bash
dungeonroom --verbose --theme ancient_temple --level 1
```

### Chaining rooms

`dungeonroom` generates one room per invocation by design. Chain them by redirecting to a file:

```bash
for i in {1..5}; do
  dungeonroom --theme goblin_warren --level 2 --no-color >> level2_warren.txt
  echo "---" >> level2_warren.txt
done
```

Or in PowerShell:

```powershell
1..5 | ForEach-Object {
  python dungeonroom.py --theme goblin_warren --level 2 --no-color
  "---"
} | Out-File level2_warren.txt -Encoding utf8
```

Each room's seed is printed at the top. Reference them in your notes to return to any room exactly.

---

## Reproducibility and seeds

Every room has a seed — an integer that fully determines the output. When you omit `--seed`, one is generated randomly and printed in the header:

```
 DUNGEON ROOM GENERATOR  |  seed: 481620
```

To **replay** any room, pass the seed back:

```bash
dungeonroom --seed 481620 --theme undead_crypt --level 2
```

The output is **bit-for-bit identical** regardless of platform, Python version (within 3.10+), or installation. This means:

- You can write a seed in your session notes and regenerate the room map weeks later.
- Sharing a seed with another player reproduces the same room on their machine.
- You can test what a room looks like with `--triggered` without losing the original.

The seed covers: room dimensions, shape, contents type, monster selection, monster count, treasure roll, feature selection and placement, exit count, door types, exit positions, and atmosphere.

---

## Project layout

```
dungeonroom/
├── dungeonroom.py      — CLI entry point (argparse, validation, dispatch)
├── generator.py        — Core room generation logic
├── renderer.py         — ASCII map rendering and JSON serialisation
├── stocking.py         — OSE stocking tables: monsters, treasure, traps, atmosphere
├── shapes.py           — Floor mask generation (rect, l_shape, organic)
├── models.py           — Dataclasses: Room, Monster, Treasure, Feature, Exit, Trap
├── data/
│   ├── themes/
│   │   └── themes.json     — All 7 theme bundles (room names, features, atmosphere, exits)
│   ├── monsters.yaml        — Monster stat blocks, level bands, behavior strings
│   └── treasures.yaml       — OSE treasure types A–V, gem and jewelry tables
└── tests/
    ├── test_generator.py   — Determinism, all themes, forced exits, edge cases
    ├── test_renderer.py    — Canvas dimensions, color/no-color, JSON validity, legend
    └── test_stocking.py    — Distribution tests (1,000-run B/X ratio checks), all trap types
```

---

## Running the tests

```bash
pytest
```

All 40 tests should pass. To run a specific module:

```bash
pytest tests/test_generator.py
pytest tests/test_stocking.py
pytest tests/test_renderer.py
```

The stocking distribution tests run 1,000 random rooms and assert that contents-type frequencies fall within ±10% of the B/X expected ratios. They are slower than the unit tests (~1–2 seconds) but do not require any network access or fixtures.

---

## Known limitations

These are intentional constraints for v1.0, not bugs:

- **One room at a time.** The tool is a single-room oracle, not a level generator. Multiple rooms are chained manually using session notes and seeds.
- **Level cap at 6.** Monster tables cover bands 1–2, 3–4, and 5–6. Levels 7–10 (`--level 7` through `--level 10`) work without crashing but use the 5–6 band — monsters are not distinctly harder.
- **No room graph.** Exits tell you what doors exist and in which direction; they do not connect to other generated rooms. Map your dungeon on paper.
- **No session state.** There is no save/load. Use `--seed` and your notes for continuity.
- **Stat block line wrapping.** On very narrow canvases, long monster names or trait descriptions can break mid-word. `--size medium` or larger avoids this.

---

## License

MIT. See `LICENSE` for details.
