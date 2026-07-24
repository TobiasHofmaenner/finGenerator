"""Command-line interface: `fingen`."""

from __future__ import annotations

import argparse
from pathlib import Path

from fingen import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fingen", description="Parametric surfboard fin generator"
    )
    parser.add_argument("--version", action="version", version=f"fingen {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser(
        "demo", help="export a placeholder lofted solid to validate the CAD stack"
    )
    demo.add_argument("output", type=Path, nargs="?", default=Path("out/demo.step"))

    args = parser.parse_args(argv)

    if args.command == "demo":
        # Deferred import: build123d/OCCT takes seconds to load, keep --help fast.
        from fingen.demo import demo_solid
        from fingen.export import to_step, to_stl

        part = demo_solid()
        writer = to_stl if args.output.suffix.lower() == ".stl" else to_step
        written = writer(part, args.output)
        print(f"wrote {written} ({written.stat().st_size} bytes)")
    return 0
