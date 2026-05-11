# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.0.0] - 2026-05-10

Initial release of the OSE Solo Dungeon Room Generator.

### Added

#### CLI (`dungeonroom`)
- `--theme` / `-t` — choose a dungeon theme or `random` (default)
- `--level` / `-l` — dungeon level 1–6, scales monster HD and treasure
- `--size` / `-s` — canvas preset: `small` (40×20), `medium` (60×30), `large` (80×40)
- `--width` / `-W` and `--height` / `-H` — override canvas dimensions (30–120 × 15–50)
- `--exits` / `-e` — force number of exits 1–4 (default: random per OSE stocking table)
- `--seed` / `-S` — integer RNG seed for fully reproducible output; auto-generated and printed when omitted
- `--format` / `-f` — output mode: `ascii` (default), `json`, or `both`
- `--no-color` — suppress ANSI escape codes for plain-text / paper output
- `--verbose` / `-v` — include OSE stocking rationale annotations in stat block
- `--entry` — specify which wall the player entered from: `north`, `south` (default), `east`, `west`
- `--triggered` — reveal triggered traps with glyph `X` on the ASCII map

#### Themes (7 total, data-driven via `data/themes/themes.json`)
- `undead_crypt` — ancient burial complex; skeletons, zombies, wights, mummies
- `goblin_warren` — cramped tunnels; goblins, hobgoblins, bugbears, ogres
- `ancient_temple` — collapsed religion; cultists, gargoyles, basilisks, lamia
- `bandit_lair` — humanoid occupation; bandits, veterans, gnolls, trolls
- `natural_cave` — unworked stone; giant animals, oozes, cave bears, dragons
- `dwarven_ruin` — worked stone; troglodytes, constructs, golems, vampires
- `wizard_tower` — experimental chambers; apprentices, golems, djinn, liches
- `random` — selects uniformly from the seven themes

#### Monster tables (`data/monster_tables.json`, `data/monster_db.json`)
- Full OSE-format stat blocks: HD, AC, #AT, Damage, Save, Morale, XP, Treasure Type
- Three level bands per theme: 1–2, 3–4, 5–6
- Multiple behavior descriptions per monster entry; one selected at random
- Monster count scaled by level: ×1.5 (rounded up) at levels 4–6, ×2 at levels 7+ (future)
- Cross-theme monster reuse where thematically appropriate (e.g. skeletons appear in crypts and temples)

#### Treasure system (`data/treasures.json`)
- Full OSE treasure types A–H (lair) and P, Q, R, U, V (individual)
- Each component rolled independently: cp, sp, ep, gp, pp, gems, jewelry, magic items
- Gem value table (d20, 10 gp–50,000 gp) with named examples per value tier
- Jewelry value table (d10) with type and material vocabulary
- Magic item roll: potions, scrolls, swords, armor, and miscellaneous magic
- Hiding location chosen from room features or a default set of dungeon hiding spots
- Compound treasure types (`Q+R`, `C+1000gp`) parsed and rolled independently

#### Stocking logic (`stocking.py`)
- OSE d6 contents roll: 1–2 empty, 3–4 monster, 5 special, 6 monster with treasure
- Unguarded treasure sub-roll (1-in-6) on empty results, matching Moldvay's intent
- Trap table with 6 types: pit, spear, gas, falling block, magic, alarm
- Atmosphere: 4 categories (smell, sound, light, temperature); 2 random categories shown per room
- Feature selection weighted per theme; spiral-from-center placement; no overlaps with exits or other features
- Small canvas caps feature count at 3; medium at 5; large at 7

#### ASCII map renderer (`renderer.py`)
- Room walls: `#`, floor: `.`, exits: `+` / `/` / `=` / `^` / `v`, entry: `@`
- Compass directional labels (N/S/E/W) printed outside the map
- Color mode: ANSI highlighting by glyph category (walls, doors, features, special)
- No-color mode: all box-drawing characters replaced with ASCII equivalents
- Legend printed below the map showing only glyphs present in the current room
- Stat block sections: MONSTER, TREASURE, SPECIAL/TRAP, FEATURES, EXITS, ATMOSPHERE
- Seed printed at header and footer; reproducibility note included

#### JSON output
- Structured JSON with all generated data: seed, theme, level, room name, size, contents type, monster, treasure, trap, features, exits, atmosphere, entry direction
- Suitable for piping into session-logging tools or external processors

#### Data model (`models.py`)
- `Room`, `Monster`, `MonsterStats`, `Treasure`, `TreasureItem`, `Feature`, `Exit`, `Trap` dataclasses
- All fields typed; `Optional` used where a room may lack a given component

#### Packaging
- Installable as a standalone command via `pip install -e .`
- `pyproject.toml` with `setuptools` build backend
- Dependencies: `colorama>=0.4.6` (all data files are JSON; no YAML dependency)
- Python 3.10+ required
- UTF-8 stdout forced on Windows terminals that default to CP1252

#### Tests (`tests/`)
- 40 tests across three test modules; all passing under `pytest`
- `test_generator.py` — determinism, all themes × level bands, forced exits, entry direction, triggered flag, room dimension bounds
- `test_renderer.py` — no-color output, seed in output, JSON validity, map walls, legend correctness, small-canvas feature cap
- `test_stocking.py` — contents type distribution (within ±10% of B/X ratios over 1,000 runs), dice roller, all trap types reachable, feature cap, no duplicate glyphs

### Known Limitations (v1.0)

- Room geometry is always rectangular; L-shapes and irregular caverns are deferred to v2.
- Dungeon level cap is 6; the spec allows 1–10 but the monster tables cover only bands 1–2, 3–4, 5–6. Levels 7–10 use the 5–6 band without crashing but are not distinctly stocked.
- Text wrapping in the stat block can split a word across lines in narrow canvases.
- Multi-room level generation, room graphs, and session state tracking are out of scope for v1.0.
- No web or GUI interface.

---

[Unreleased]: https://github.com/example/dungeonroom/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/example/dungeonroom/releases/tag/v1.0.0
