"""OSE stocking logic: contents rolls, treasure, traps, monsters."""
from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Optional

import yaml

from models import Exit, Feature, Monster, MonsterStats, NonCombatEncounter, Trap, Treasure, TreasureItem

_DATA = Path(__file__).parent / "data"


def _load_yaml(name: str) -> dict:
    with open(_DATA / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


_MONSTERS: dict = {}
_TREASURES: dict = {}
_NON_COMBAT: dict = {}


def _monsters() -> dict:
    global _MONSTERS
    if not _MONSTERS:
        _MONSTERS = _load_yaml("monsters.yaml")
    return _MONSTERS


def _treasures() -> dict:
    global _TREASURES
    if not _TREASURES:
        _TREASURES = _load_yaml("treasures.yaml")
    return _TREASURES


def _non_combat_data() -> dict:
    global _NON_COMBAT
    if not _NON_COMBAT:
        _NON_COMBAT = _load_yaml("non_combat_encounters.yaml")
    return _NON_COMBAT


# ─── Dice ─────────────────────────────────────────────────────────────────────

def roll_dice(expr: str, rng: random.Random) -> int:
    """Parse and roll NdM[+/-K] or NdM*K expressions."""
    expr = expr.strip().replace(" ", "")
    # Handle multiply: e.g. "1d6*1000"
    if "*" in expr:
        left, right = expr.split("*", 1)
        return roll_dice(left, rng) * int(right)
    # Handle plus/minus at the end: e.g. "1d8+1"
    modifier = 0
    if "+" in expr[1:]:
        idx = expr.rindex("+")
        modifier = int(expr[idx + 1:])
        expr = expr[:idx]
    elif "-" in expr[1:]:
        idx = expr.rindex("-")
        modifier = -int(expr[idx + 1:])
        expr = expr[:idx]
    # Handle plain integer
    if "d" not in expr:
        return int(expr) + modifier
    n, m = expr.split("d")
    n = int(n) if n else 1
    m = int(m)
    return sum(rng.randint(1, m) for _ in range(n)) + modifier


# ─── Contents Roll ─────────────────────────────────────────────────────────────

def roll_contents_type(rng: random.Random) -> str:
    d6 = rng.randint(1, 6)
    if d6 <= 2:
        contents = "empty"
    elif d6 <= 4:
        contents = "monster"
    elif d6 == 5:
        contents = "special"
    else:
        contents = "monster_with_treasure"

    # Unguarded treasure: 1-in-6 for empty rooms (Moldvay)
    if contents == "empty" and rng.randint(1, 6) == 1:
        contents = "unguarded_treasure"

    return contents


# ─── Level Band ───────────────────────────────────────────────────────────────

def _level_band(level: int) -> str:
    if level <= 2:
        return "levels_1_2"
    elif level <= 4:
        return "levels_3_4"
    else:
        return "levels_5_6"


# ─── Monster ──────────────────────────────────────────────────────────────────

def roll_monster(theme: str, level: int, rng: random.Random) -> Monster:
    monsters = _monsters()
    band = _level_band(level)
    table = monsters.get(theme, {}).get(band, {})
    if not table:
        # Fallback: use undead_crypt level band
        table = monsters["undead_crypt"][band]

    entry_key = rng.randint(1, 6)
    entry = table.get(entry_key, table[list(table.keys())[0]])

    stats = MonsterStats(
        name=entry["name"],
        hd=str(entry["hd"]),
        ac=entry["ac"],
        attacks=entry["attacks"],
        damage=entry["damage"],
        save=entry["save"],
        morale=entry["morale"],
        xp=entry["xp"],
        special=entry.get("special", ""),
        treasure_type=entry.get("treasure_type", ""),
    )

    count_expr = entry.get("count", "1d4")
    base_count = roll_dice(count_expr, rng)
    count = _scale_count(base_count, level)

    behaviors = entry.get("behaviors", ["Lurking."])
    behavior = rng.choice(behaviors)

    return Monster(stats=stats, count=count, behavior=behavior)


def _scale_count(base: int, level: int) -> int:
    if level >= 7:
        return max(1, math.ceil(base * 2))
    elif level >= 4:
        return max(1, math.ceil(base * 1.5))
    return max(1, base)


# ─── Treasure ─────────────────────────────────────────────────────────────────

def _parse_treasure_types(treasure_type_str: str) -> list[str]:
    """Split compound treasure types like 'Q+R' or 'C+1000gp'."""
    parts = treasure_type_str.replace(" ", "").split("+")
    types = []
    bonuses = []
    for p in parts:
        if p.endswith("gp") and p[:-2].isdigit():
            bonuses.append(int(p[:-2]))
        elif p:
            types.append(p)
    return types, bonuses


def roll_treasure(treasure_type_str: str, rng: random.Random,
                  hiding_location: str = "") -> Optional[Treasure]:
    if not treasure_type_str:
        return None

    treasures = _treasures()
    types, gp_bonuses = _parse_treasure_types(treasure_type_str)
    items: list[TreasureItem] = []
    total_gp = 0

    for ttype in types:
        tdata = treasures.get(ttype)
        if not tdata:
            continue
        items.extend(_roll_type(tdata, rng))

    for bonus_gp in gp_bonuses:
        items.append(TreasureItem(description=f"{bonus_gp} gp (flat bonus)"))
        total_gp += bonus_gp

    if not items:
        return None

    # Set hiding location on all items
    for item in items:
        if hiding_location:
            item.hiding_location = hiding_location

    total_gp += _estimate_gp(items)
    return Treasure(items=items, total_gp_value=total_gp)


def _roll_type(tdata: dict, rng: random.Random) -> list[TreasureItem]:
    items: list[TreasureItem] = []
    treasures = _treasures()

    # Coins
    for coin in ("cp", "sp", "ep", "gp", "pp"):
        entry = tdata.get(coin, {})
        chance = entry.get("chance", 0)
        amount_expr = entry.get("amount", "0")
        if chance and rng.randint(1, 100) <= chance:
            amount = roll_dice(amount_expr, rng)
            if amount > 0:
                items.append(TreasureItem(description=f"{amount:,} {coin}"))

    # Gems
    gem_entry = tdata.get("gems", {})
    gem_chance = gem_entry.get("chance", 0)
    if gem_chance and rng.randint(1, 100) <= gem_chance:
        gem_count = roll_dice(gem_entry.get("amount", "1"), rng)
        gem_vals = treasures.get("gem_values", {})
        for _ in range(gem_count):
            d20 = min(20, max(1, rng.randint(1, 20)))
            gval = gem_vals.get(d20, gem_vals.get("1"))
            value = gval["value"]
            examples = gval.get("examples", ["gem"])
            name = rng.choice(examples)
            items.append(TreasureItem(description=f"1 gem ({value} gp, {name.lower()})"))

    # Jewelry
    jewelry_entry = tdata.get("jewelry", {})
    jewelry_chance = jewelry_entry.get("chance", 0)
    if jewelry_chance and rng.randint(1, 100) <= jewelry_chance:
        j_count = roll_dice(jewelry_entry.get("amount", "1"), rng)
        j_vals = treasures.get("jewelry_values", {})
        j_types = treasures.get("jewelry_types", ["ring"])
        j_mats = treasures.get("jewelry_materials", ["silver"])
        for _ in range(j_count):
            d10 = rng.randint(1, 10)
            jval = j_vals.get(d10, j_vals.get(1))
            vr = jval["value_range"]
            mult = jval["multiplier"]
            value = rng.randint(vr[0], vr[1]) * mult
            jtype = rng.choice(j_types)
            jmat = rng.choice(j_mats)
            items.append(TreasureItem(
                description=f"1 {jmat} {jtype} ({value:,} gp)"
            ))

    # Magic items — just note them (no full magic item table expansion yet)
    magic_entry = tdata.get("magic", {})
    magic_chance = magic_entry.get("chance", 0)
    magic_rolls = magic_entry.get("rolls", 0)
    if magic_chance and magic_rolls and rng.randint(1, 100) <= magic_chance:
        for _ in range(magic_rolls):
            items.append(TreasureItem(description=_roll_magic_item(rng, treasures)))

    return items


def _roll_magic_item(rng: random.Random, treasures: dict) -> str:
    d100 = rng.randint(1, 100)
    if d100 <= 30:
        potions = treasures.get("potion_table", {})
        if potions:
            key = rng.choice(list(potions.keys()))
            return potions[key]
        return "Potion (random)"
    elif d100 <= 45:
        scrolls = treasures.get("scroll_table", {})
        if scrolls:
            key = rng.choice(list(scrolls.keys()))
            return scrolls[key]
        return "Scroll (random)"
    elif d100 <= 60:
        return rng.choice([
            "Sword +1", "Sword +1, +2 vs. magic-users",
            "Sword +1, +3 vs. undead", "Sword +2",
        ])
    elif d100 <= 75:
        return rng.choice([
            "Armor +1", "Shield +1", "Armor +1 and Shield +1",
        ])
    else:
        return rng.choice([
            "Ring of Protection +1", "Ring of Fire Resistance",
            "Wand of Magic Detection (2d10 charges)",
            "Staff of Healing (1d10 charges)",
            "Bag of Holding",
            "Cloak of Elvenkind",
            "Boots of Elvenkind",
        ])


def _estimate_gp(items: list[TreasureItem]) -> int:
    total = 0
    for item in items:
        desc = item.description
        # Try to parse trailing "(NNN gp)" pattern
        if "gp)" in desc or desc.endswith("gp"):
            parts = desc.replace(",", "").split()
            for i, p in enumerate(parts):
                if "gp" in p and i > 0:
                    try:
                        total += int(parts[i - 1].replace(",", ""))
                    except ValueError:
                        pass
    return total


# ─── Non-Combat Encounter ─────────────────────────────────────────────────────

def roll_non_combat_encounter(rng: random.Random) -> NonCombatEncounter:
    data = _non_combat_data()
    key = rng.randint(1, 6)
    entry = data.get(key, data[1])
    description = rng.choice(entry["descriptions"])
    return NonCombatEncounter(
        encounter_type=entry["type"],
        name=entry["name"],
        description=description,
        interactions=list(entry.get("interactions", [])),
    )


# ─── Trap ─────────────────────────────────────────────────────────────────────

def roll_trap(rng: random.Random) -> Trap:
    treasures = _treasures()
    trap_table = treasures.get("trap_table", {})
    key = rng.randint(1, 6)
    entry = trap_table.get(key, trap_table[1])
    return Trap(
        trap_type=entry["type"],
        name=entry["name"],
        trigger=entry["trigger"],
        effect=entry["effect"],
    )


# ─── Feature Selection ────────────────────────────────────────────────────────

FEATURE_NAMES = {
    "A": "Altar",
    "B": "Barrel",
    "C": "Chest",
    "c": "Coffin",
    "D": "Debris pile",
    "F": "Fountain / pool",
    "I": "Iron cage",
    "P": "Pillar",
    "S": "Sarcophagus",
    "T": "Table / workbench",
    "t": "Throne",
    "W": "Weapon rack",
    "X": "Trap (triggered)",
    "~": "Water",
    "*": "Magical effect",
    "?": "Unknown feature",
}

FEATURE_DESCRIPTIONS: dict[str, list[str]] = {
    "A": [
        "Stone altar, black-stained. Disturbing it triggers a morale check for nearby undead.",
        "Low altar carved with forgotten symbols. Still bears old offerings.",
        "Raised stone dais with sacrificial channels. Rust-red stains.",
    ],
    "B": [
        "Barrel, sealed. Contains salted meat, foul water, or trade goods.",
        "Cluster of barrels, some broken. Smells of sour wine.",
        "Large cask, iron-banded. Liquid inside — roll to identify.",
    ],
    "C": [
        "Chest, iron-bound. Roll: 1-3 locked, 4-5 unlocked, 6 trapped.",
        "Small chest, carved wood. Hinges corroded but lid opens.",
        "Heavy chest, embedded in the floor. Requires a Str check to shift.",
    ],
    "c": [
        "Coffin, closed. Contents unknown until opened.",
        "Empty coffin. Lid is ajar — drag marks on the floor suggest recent use.",
        "Coffin, nailed shut. Something inside shifts when you approach.",
    ],
    "D": [
        "Debris pile: broken furniture, shattered stone, old rags. Searching takes a turn.",
        "Rubble from a partial collapse. Something glints underneath.",
        "Pile of old bones, equipment scraps, and refuse.",
    ],
    "F": [
        "Stone fountain, dry or trickling with murky water.",
        "Pool of still water. Depth unknown. Reflection looks wrong.",
        "Carved basin, water faintly luminescent. Possibly magical.",
    ],
    "I": [
        "Iron cage, heavy lock. Empty — or is it?",
        "Cage containing a prisoner (roll: 1-3 dead, 4-5 unconscious, 6 alive and aware).",
        "Cage door bent outward. Whatever was inside left in a hurry.",
    ],
    "P": [
        "Stone pillar, load-bearing. Carved with old reliefs.",
        "Column, cracked near the base. Structurally suspect.",
        "Pillar cluster. Space between them is tight.",
    ],
    "S": [
        "Sarcophagus, sealed with mortar. Heavy lid requires Str check to shift.",
        "Ornate sarcophagus, gold-leaf faded. Name plate unreadable.",
        "Plain stone sarcophagus, already opened. Contents unknown.",
    ],
    "T": [
        "Heavy table, laden with equipment, papers, or alchemical apparatus.",
        "Workbench, tools scattered. Whatever was being made is unfinished.",
        "Long table, benches on either side. Signs of recent occupation.",
    ],
    "t": [
        "Stone throne, imposing. Sitting in it feels unwise.",
        "Carved wooden chair, larger than it should be. For someone important.",
        "Throne of corroded iron, draped with rotted cloth.",
    ],
    "W": [
        "Weapon rack, partially stocked. Remaining weapons are mundane but usable.",
        "Empty weapon rack, brackets show outline of what was here.",
        "Rack holding spears, swords, and shields. Roll condition: 1-3 poor, 4-6 serviceable.",
    ],
    "X": [
        "Triggered trap — mechanism visible and spent.",
    ],
    "~": [
        "Shallow water covering the floor. Movement is halved.",
        "Underground pool, edges uncertain. Depth: 1d6×2 ft.",
        "Runoff channel, water knee-deep and cold.",
    ],
    "*": [
        "Magical effect: runes glow faintly on the floor. Touching them is not advised.",
        "Summoning circle, drawn in silver dust. Still active.",
        "Floating motes of light. They track motion.",
    ],
    "?": [
        "Something is here — shape unclear in the dark.",
    ],
}


def select_features(theme_data: dict, contents_type: str,
                    cap: int, rng: random.Random) -> list[Feature]:
    weights = theme_data.get("feature_weights", {})
    # Build weighted pool
    pool: list[str] = []
    for glyph, weight in weights.items():
        if isinstance(weight, int) and weight > 0:
            pool.extend([glyph] * weight)

    if not pool:
        return []

    # How many features: d4-1 (0-3), capped by size
    count = min(rng.randint(0, 3), cap)
    if contents_type in ("monster", "monster_with_treasure"):
        # Ensure at least 1 feature for flavour in stocked rooms
        count = max(count, 1)
    count = min(count, cap)

    chosen: list[Feature] = []
    used_glyphs: set[str] = set()
    attempts = 0
    while len(chosen) < count and attempts < 30:
        attempts += 1
        g = rng.choice(pool)
        if g in used_glyphs:
            continue
        used_glyphs.add(g)
        name = FEATURE_NAMES.get(g, "Feature")
        descs = FEATURE_DESCRIPTIONS.get(g, ["Unknown feature."])
        desc = rng.choice(descs)
        chosen.append(Feature(glyph=g, name=name, description=desc))

    return chosen


# ─── Exit Rolling ─────────────────────────────────────────────────────────────

def roll_exits(theme_data: dict, level: int, forced_count: Optional[int],
               entry_direction: str, rng: random.Random) -> list[Exit]:
    # Number of exits
    if forced_count is not None:
        n_exits = max(1, min(4, forced_count))
    else:
        d6 = rng.randint(1, 6)
        if d6 <= 2:
            n_exits = 1
        elif d6 <= 4:
            n_exits = 2
        elif d6 == 5:
            n_exits = 3
        else:
            n_exits = 4

    directions = ["north", "south", "east", "west"]
    # Entry direction is always included
    chosen_directions = [entry_direction]
    remaining = [d for d in directions if d != entry_direction]
    rng.shuffle(remaining)
    chosen_directions.extend(remaining[: n_exits - 1])

    exits: list[Exit] = []
    exit_flavor = theme_data.get("exit_flavor", {})

    for direction in chosen_directions:
        if direction == entry_direction:
            door_type = "archway"
            flavor = "Entry (where you came from)"
        else:
            door_type, flavor = _roll_door_type(exit_flavor, level, direction, rng)
        exits.append(Exit(direction=direction, door_type=door_type, flavor=flavor))

    return exits


def _roll_door_type(exit_flavor: dict, level: int, direction: str,
                    rng: random.Random) -> tuple[str, str]:
    d6 = rng.randint(1, 6)
    if d6 <= 2:
        key = "archway"
        door_type = "archway"
    elif d6 <= 4:
        key = "door_wood"
        door_type = "door_wood"
    elif d6 == 5:
        key = "door_iron"
        door_type = "door_iron"
    else:
        # Special: stuck/locked/secret
        sub = rng.randint(1, 3)
        if sub == 1:
            key = "door_stuck"
            door_type = "door_stuck"
        elif sub == 2:
            key = "door_locked"
            door_type = "door_locked"
        else:
            key = "door_secret"
            door_type = "door_secret"

    options = exit_flavor.get(key, [])
    if options:
        flavor = rng.choice(options)
    else:
        flavor = key.replace("_", " ").capitalize()

    return door_type, flavor


# ─── Atmosphere ───────────────────────────────────────────────────────────────

def roll_atmosphere(theme_data: dict, rng: random.Random) -> dict[str, str]:
    atmo_data = theme_data.get("atmosphere", {})
    categories = list(atmo_data.keys())
    rng.shuffle(categories)
    # Pick 2 random categories
    chosen = categories[:2]
    result: dict[str, str] = {}
    for cat in chosen:
        options = atmo_data[cat]
        result[cat] = rng.choice(options)
    return result


# ─── Hiding Locations ─────────────────────────────────────────────────────────

_HIDING_LOCATIONS = {
    "A": "Concealed beneath the altar stone",
    "B": "Hidden inside a barrel (false bottom)",
    "C": "Inside the chest",
    "c": "Inside the coffin",
    "D": "Buried under the debris",
    "F": "Submerged in the pool",
    "I": "Under the cage floor",
    "P": "Behind a loose section of pillar",
    "S": "Inside the sarcophagus",
    "T": "In a hidden drawer under the table",
    "t": "Beneath the throne seat",
    "W": "Hidden behind the weapon rack",
    "~": "Waterproofed pouch in the pool",
}

DEFAULT_HIDING = [
    "Loose stones in the wall (Search to find)",
    "Hidden in a crack in the ceiling",
    "False floor panel (Search to find)",
    "Inside a hollow pillar base",
    "Behind old tapestry or wall hanging",
]


def pick_hiding_location(features: list[Feature], rng: random.Random) -> str:
    for feature in features:
        loc = _HIDING_LOCATIONS.get(feature.glyph)
        if loc:
            return loc
    return rng.choice(DEFAULT_HIDING)
