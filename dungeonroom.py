"""dungeonroom — OSE Solo Dungeon Room Generator. CLI entry point."""
from __future__ import annotations

import argparse
import sys

from generator import get_theme_ids, SIZE_PRESETS, generate_room
from renderer import Renderer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dungeonroom",
        description="OSE Solo Dungeon Room Generator — generates one dungeon room per invocation.",
    )
    p.add_argument("-t", "--theme", default="random",
                   help=f"Dungeon theme: {', '.join(get_theme_ids())}, or 'random' (default: random)")
    p.add_argument("-l", "--level", type=int, default=1, metavar="1-6",
                   help="Dungeon level 1-6 (default: 1)")
    p.add_argument("-s", "--size", default="medium",
                   choices=["small", "medium", "large"],
                   help="Canvas size preset (default: medium)")
    p.add_argument("-W", "--width", type=int, default=None,
                   help="Override canvas width (30-120 chars)")
    p.add_argument("-H", "--height", type=int, default=None,
                   help="Override canvas height (15-50 chars)")
    p.add_argument("-e", "--exits", type=int, default=None, metavar="1-4",
                   help="Force number of exits 1-4 (default: random)")
    p.add_argument("-S", "--seed", type=int, default=None,
                   help="RNG seed for reproducible output")
    p.add_argument("-f", "--format", default="ascii",
                   choices=["ascii", "json", "both"],
                   help="Output format (default: ascii)")
    p.add_argument("--no-color", action="store_true",
                   help="Suppress ANSI color codes")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Include OSE stocking rationale in output")
    p.add_argument("--entry", default="south",
                   choices=["north", "south", "east", "west"],
                   help="Entry wall direction (default: south)")
    p.add_argument("--triggered", action="store_true",
                   help="Reveal triggered traps on the ASCII map")
    return p


def validate_args(args: argparse.Namespace) -> None:
    if not 1 <= args.level <= 6:
        print(f"Error: --level must be 1-6, got {args.level}", file=sys.stderr)
        sys.exit(1)
    if args.exits is not None and not 1 <= args.exits <= 4:
        print(f"Error: --exits must be 1-4, got {args.exits}", file=sys.stderr)
        sys.exit(1)
    if args.width is not None and not 30 <= args.width <= 120:
        print(f"Error: --width must be 30-120, got {args.width}", file=sys.stderr)
        sys.exit(1)
    if args.height is not None and not 15 <= args.height <= 50:
        print(f"Error: --height must be 15-50, got {args.height}", file=sys.stderr)
        sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    # Ensure UTF-8 output on Windows terminals that default to CP1252
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(args)

    # colorama init for Windows ANSI support
    if not args.no_color:
        try:
            import colorama
            colorama.init()
        except ImportError:
            pass

    try:
        room = generate_room(
            theme=args.theme,
            level=args.level,
            size=args.size,
            canvas_w=args.width,
            canvas_h=args.height,
            exits=args.exits,
            seed=args.seed,
            entry=args.entry,
            triggered=args.triggered,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    renderer = Renderer(
        room=room,
        size=args.size,
        canvas_w=args.width,
        canvas_h=args.height,
        color=not args.no_color,
        verbose=args.verbose,
    )

    fmt = args.format
    if fmt in ("ascii", "both"):
        print(renderer.render_ascii())
    if fmt in ("json", "both"):
        if fmt == "both":
            print()
        print(renderer.render_json())


if __name__ == "__main__":
    main()
