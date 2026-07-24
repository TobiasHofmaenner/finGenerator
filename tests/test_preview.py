from fingen.params import FinParams, GenSettings
from fingen.preview import render_preview

COARSE = GenSettings(n_stations=11, n_foil_points=60)


def test_preview_renders_png_without_lofting(tmp_path):
    out = render_preview(FinParams(), tmp_path / "fin.png", COARSE)
    assert out.exists()
    assert out.stat().st_size > 20_000


def test_preview_with_solid_panel(tmp_path):
    out = render_preview(FinParams(), tmp_path / "fin3d.png", COARSE, show_solid=True)
    assert out.exists()
    assert out.stat().st_size > 30_000
