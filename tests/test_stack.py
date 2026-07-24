"""End-to-end smoke test of the CAD stack: loft a solid, export STEP and STL."""

from fingen.demo import demo_solid
from fingen.export import to_step, to_stl


def test_demo_loft_and_export(tmp_path):
    part = demo_solid()
    assert part.volume > 1000  # mm^3 — a real solid, not a degenerate shell

    step = to_step(part, tmp_path / "demo.step")
    assert step.read_text().startswith("ISO-10303-21")

    stl = to_stl(part, tmp_path / "demo.stl")
    assert stl.stat().st_size > 1000
