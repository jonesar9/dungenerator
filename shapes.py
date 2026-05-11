"""Floor mask generators for room shape types.

A mask is an rh×rw grid of bools: True = floor cell, False = wall.
Coordinates are interior-space (0-indexed), matching the renderer's
interior dimensions (room_w × room_h in character cells).
"""
from __future__ import annotations

import random


def make_floor_mask(shape_type: str, rw: int, rh: int, seed: int) -> list[list[bool]]:
    """Return an rh×rw bool mask; True = floor, False = wall."""
    rng = random.Random(seed ^ 0xCA7E)
    if shape_type == "l_shape":
        return _l_shape(rng, rw, rh)
    if shape_type == "organic":
        return _organic(rng, rw, rh)
    return [[True] * rw for _ in range(rh)]  # rect / fallback


def _l_shape(rng: random.Random, rw: int, rh: int) -> list[list[bool]]:
    """Rectangle with one corner quadrant removed."""
    mask = [[True] * rw for _ in range(rh)]
    corner = rng.choice(("NW", "NE", "SW", "SE"))

    # Cut 35–55% of each dimension, but never so deep that the opposite wall
    # face loses all valid exit positions (drift range is col/row 2..dim-2).
    cut_h = max(1, min(rng.randint(rh * 35 // 100, rh * 55 // 100), rh - 3))
    cut_w = max(1, min(rng.randint(rw * 35 // 100, rw * 55 // 100), rw - 3))

    r0, r1 = (0, cut_h)      if "N" in corner else (rh - cut_h, rh)
    c0, c1 = (0, cut_w)      if "W" in corner else (rw - cut_w, rw)
    for r in range(r0, r1):
        for c in range(c0, c1):
            mask[r][c] = False
    return mask


def _organic(rng: random.Random, rw: int, rh: int) -> list[list[bool]]:
    """Cellular-automata cave erosion."""
    mask = [[True] * rw for _ in range(rh)]

    # Seed: outer ring 50% wall probability, second ring 20%
    for r in range(rh):
        for c in range(rw):
            dist = min(r, rh - 1 - r, c, rw - 1 - c)
            if dist == 0 and rng.random() < 0.50:
                mask[r][c] = False
            elif dist == 1 and rng.random() < 0.20:
                mask[r][c] = False

    # Smooth twice: cell becomes floor if ≥ half its Moore neighbourhood is floor
    for _ in range(2):
        new_mask = [[False] * rw for _ in range(rh)]
        for r in range(rh):
            for c in range(rw):
                total = count = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rh and 0 <= nc < rw:
                            total += mask[nr][nc]
                            count += 1
                new_mask[r][c] = total * 2 >= count
        mask = new_mask

    # Flood fill from centre; disconnect isolated islands → wall
    cr, cc = rh // 2, rw // 2
    mask[cr][cc] = True
    connected: set[tuple[int, int]] = set()
    queue = [(cr, cc)]
    while queue:
        r, c = queue.pop()
        if (r, c) in connected:
            continue
        connected.add((r, c))
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rh and 0 <= nc < rw and mask[nr][nc] and (nr, nc) not in connected:
                queue.append((nr, nc))
    for r in range(rh):
        for c in range(rw):
            if (r, c) not in connected:
                mask[r][c] = False

    # Guarantee one floor cell adjacent to each wall face (exit connectivity anchor)
    mask[0][rw // 2] = True
    mask[rh - 1][rw // 2] = True
    mask[rh // 2][0] = True
    mask[rh // 2][rw - 1] = True

    return mask
