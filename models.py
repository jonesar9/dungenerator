from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class MonsterStats:
    name: str
    hd: str          # e.g. "1", "1+1", "2"
    ac: int
    attacks: str     # e.g. "1 weapon"
    damage: str      # e.g. "1d6"
    save: str        # e.g. "F1"
    morale: int
    xp: int
    special: str = ""
    treasure_type: str = ""


@dataclass
class Monster:
    stats: MonsterStats
    count: int
    behavior: str
    location_note: str = ""  # e.g. "Guarding the sarcophagus"


@dataclass
class TreasureItem:
    description: str   # e.g. "35 sp", "1 gem (10 gp, cracked quartz)"
    hidden: bool = False
    hiding_location: str = ""  # e.g. "Hidden in sarcophagus"


@dataclass
class Treasure:
    items: list[TreasureItem] = field(default_factory=list)
    total_gp_value: int = 0


@dataclass
class Feature:
    glyph: str
    name: str
    description: str
    col: int = 0
    row: int = 0


@dataclass
class Exit:
    direction: str        # "north", "south", "east", "west"
    door_type: str        # "archway", "door_wood", "door_iron", "door_stuck", "door_locked", "door_secret", "stairs_down", "stairs_up"
    flavor: str           # e.g. "Closed wooden door (stuck, Str check)"
    leads_to: str = ""    # e.g. "To Level 2"


@dataclass
class NonCombatEncounter:
    encounter_type: str   # "neutral_npc", "trick", "puzzle", "sanctuary", "omen", "hazard"
    name: str
    description: str
    interactions: List[str] = field(default_factory=list)


@dataclass
class Trap:
    trap_type: str        # "pit", "spear", "gas", "falling_block", "magic", "alarm"
    name: str
    trigger: str
    effect: str
    col: int = 0
    row: int = 0
    triggered: bool = False


@dataclass
class Room:
    name: str
    theme: str
    level: int
    seed: int

    # Geometry (in 10-ft squares, inner dimensions)
    width_sq: int = 3
    height_sq: int = 3

    # Stocking
    contents_type: str = "empty"   # "empty", "monster", "monster_with_treasure", "unguarded_treasure", "trap", "non_combat_encounter"
    monster: Optional[Monster] = None
    treasure: Optional[Treasure] = None
    trap: Optional[Trap] = None
    non_combat_encounter: Optional[NonCombatEncounter] = None
    features: list[Feature] = field(default_factory=list)
    exits: list[Exit] = field(default_factory=list)
    entry_direction: str = "south"

    # Atmosphere
    atmosphere: dict[str, str] = field(default_factory=dict)  # e.g. {"smell": "...", "sound": "..."}
