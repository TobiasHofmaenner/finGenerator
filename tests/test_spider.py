"""Spider axes must reproduce the fleet's surf-shop truths (tier-0 backing)."""

from fingen.spider import AXES, normalized_scores, reference_fleet


def test_fleet_scores_match_surf_intuition():
    fleet = reference_fleet()
    scores = {name: normalized_scores(fin) for name, fin in fleet.items()}
    for s in scores.values():
        assert set(s) == set(AXES)
        assert all(0.0 <= v <= 100.0 for v in s.values())
    # Keels hold and forgive (low-AR vortex lift); high-aspect blades drive.
    assert scores["fish-keel"]["hold"] > scores["thruster-side"]["hold"]
    assert scores["fish-keel"]["forgiveness"] >= 80.0
    assert scores["hi-aspect"]["drive"] == max(s["drive"] for s in scores.values())
    # The raked gun releases; the compact quad-rear pivots and runs clean.
    assert scores["gun-rake"]["release"] >= 80.0
    assert scores["quad-rear"]["speed"] >= 80.0
