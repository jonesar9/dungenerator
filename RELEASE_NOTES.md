# Release Notes — v1.0.0

**Released:** 2026-05-10

---

## Overview

`dungeonroom` is a command-line tool for OSE / B/X solo play that generates one fully stocked dungeon room per invocation. Run it before you open a door. Read the output. Play what you find.

The tool is intentionally single-room: it feeds the oracle loop of solo play rather than pre-generating a full dungeon level. Each room stands alone. Chain multiple invocations to build a dungeon organically as you explore.

---

## What's in v1.0.0

### Seven Themes

Each theme is a self-contained data bundle — room names, weighted features, monster tables, atmosphere, and door vocabulary. Pick one or let the tool roll for you.

| Flag value | Theme |
|---|---|
| `undead_crypt` | Ancient burial complex. Skeletons, wights, mummies. Cold and silent. |
| `goblin_warren` | Cramped, filthy tunnels. Goblins, wolves, the occasional ogre muscle. |
| `ancient_temple` | Collapsed religion. Cultists, gargoyles, things that were summoned and never sent back. |
| `bandit_lair` | Humanoids squatting in someone else's ruin. Organized, armed, suspicious. |
| `natural_cave` | Unworked stone. Giant animals, oozes, cave bears. A dragon, if you're unlucky. |
| `dwarven_ruin` | Worked stone, old machinery. Troglodytes, constructs, golems still on post. |
| `wizard_tower` | Experimental chambers. Apprentices, flesh golems, bound djinn, and a lich if you go deep enough. |

### OSE-Compatible Stocking

Room contents follow the B/X stocking table:

- **Empty** (~28%) — may still have features and atmosphere; 1-in-6 chance of unguarded treasure
- **Monster** (~33%) — pulled from the theme's level-appropriate table
- **Special** (~17%) — one of six trap types, hidden unless `--triggered` is set
- **Monster with treasure** (~17%) — monster plus rolled treasure, hidden in a thematic location
- **Unguarded treasure** (~5%) — all items marked hidden; requires a Search

Treasure uses the full OSE treasure type tables (types A–V), rolled component by component: coins, gems (d20 table, 10 gp to 50,000 gp), jewelry, and magic items.

### Reproducible Output

Every room gets a seed — auto-generated or supplied by you. The seed appears at the top and bottom of every output. To reproduce a room exactly:

```
dungeonroom --seed 84291 --theme undead_crypt --level 2
```

Use seeds in session notes to recreate any room you've generated.

### Three Output Sizes

| Flag | Canvas | Best for |
|---|---|---|
| `--size small` | 40×20 | Narrow terminal, phone, small notebook |
| `--size medium` | 60×30 | Standard terminal, A5 paper (default) |
| `--size large` | 80×40 | Wide terminal, A4/letter paper |

Override with `--width` and `--height` for exact column widths.

### Three Output Formats

- **`--format ascii`** (default) — header, ASCII map, stat block
- **`--format json`** — structured JSON for piping or logging
- **`--format both`** — both, separated by a blank line

Add `--no-color` for plain-text output suitable for pasting into notes or printing.

---

## Quick Start

```bash
# Install
pip install -e /path/to/dungeonroom

# Random room, level 1, medium canvas
dungeonroom

# Specific theme and level
dungeonroom --theme goblin_warren --level 3

# Reproducible room for session notes
dungeonroom --seed 84291 --theme undead_crypt --level 2

# Small, no color, for paper notes
dungeonroom --size small --no-color

# Log the room to a file
dungeonroom --format both --seed 84291 > session_04_room_01.txt

# Player entered from the east, trap was triggered
dungeonroom --entry east --triggered --seed 5512
```

---

## Flags Reference

| Flag | Short | Default | Description |
|---|---|---|---|
| `--theme` | `-t` | `random` | Theme name or `random` |
| `--level` | `-l` | `1` | Dungeon level 1–6 |
| `--size` | `-s` | `medium` | `small`, `medium`, `large` |
| `--width` | `-W` | from size | Canvas width (30–120) |
| `--height` | `-H` | from size | Canvas height (15–50) |
| `--exits` | `-e` | random | Force exit count 1–4 |
| `--seed` | `-S` | auto | RNG seed for reproducibility |
| `--format` | `-f` | `ascii` | `ascii`, `json`, `both` |
| `--no-color` | | off | Plain text, no ANSI codes |
| `--verbose` | `-v` | off | Show OSE stocking rationale |
| `--entry` | | `south` | Entry wall: `north/south/east/west` |
| `--triggered` | | off | Reveal triggered traps on map |

---

## Known Limitations

These are deferred to v2 and documented in the spec:

- **Room shape**: always rectangular. L-shapes, irregular caverns, and non-rectangular rooms are a v2 feature.
- **Level cap**: monster tables cover levels 1–6 across three bands (1–2, 3–4, 5–6). The tool accepts `--level 1` through `--level 6`; levels beyond 6 are not validated by the generator itself (only the CLI).
- **Multi-room dungeons**: the tool generates one room at a time by design. Use `--seed` and session notes to chain rooms into a dungeon.
- **Text wrapping**: long feature descriptions may split across lines at word boundaries in narrow canvases. Cosmetic; does not affect data.

---

## Project Structure

```
dungeonroom/
├── dungeonroom.py      CLI entry point and argument parsing
├── generator.py        Room generation logic
├── renderer.py         ASCII map and stat block rendering
├── stocking.py         OSE stocking tables, dice, monster/treasure/trap rolls
├── models.py           Dataclasses (Room, Monster, Treasure, Feature, Exit, Trap)
├── data/
│   ├── themes.yaml     All seven theme bundles
│   ├── monsters.yaml   Monster stat blocks, three level bands per theme
│   └── treasures.yaml  Treasure types A–V, gem/jewelry tables, trap table
├── tests/
│   ├── test_generator.py
│   ├── test_renderer.py
│   └── test_stocking.py
├── pyproject.toml
├── CHANGELOG.md
└── RELEASE_NOTES.md
```

---

## Running the Tests

```bash
pip install pytest
pytest tests/ -v
```

40 tests. All passing.
