from fingen.params import FinParams, GenSettings
from fingen.preview import render_preview


def test_preview_renders_png(tmp_path):
    out = render_preview(FinParams(), tmp_path / "fin.png",
                         GenSettings(n_stations=11, n_foil_points=60))
    assert out.exists()
    assert out.stat().st_size > 20_000
