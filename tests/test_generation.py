"""fingen.generation: results carry the model generation that scored them."""
import json

from fingen import generation
from fingen.generation import GENERATIONS, MODEL_GENERATION, stamp


def test_current_generation_is_described():
    assert MODEL_GENERATION in GENERATIONS
    assert len(GENERATIONS[MODEL_GENERATION]) > 80   # a real description, not a stub
    assert set(GENERATIONS) == set(range(1, MODEL_GENERATION + 1))   # no gaps


def test_stamp_shape_and_version_not_stale():
    s = stamp()
    assert s["model"] == MODEL_GENERATION
    assert s["fingen"] not in ("0.6.0", "", None)     # the literal that had gone stale
    assert "git" in s and "dirty" in s
    json.dumps(s)                                      # JSON-safe


def test_result_json_carries_the_stamp():
    from fingen.optimize import RiderSpec, optimize, result_to_dict
    from fingen.params import FinConfig
    from fingen.sizing import Skill
    r = optimize(RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE,
                           config=FinConfig.THRUSTER), budget_evals=60, seed=0)
    d = result_to_dict(r)
    assert d["generation"]["model"] == MODEL_GENERATION


def test_git_probe_never_raises(monkeypatch):
    """A container image has no .git; the stamp must degrade to None, not fail."""
    generation._git.cache_clear()
    monkeypatch.setattr(generation.subprocess, "run",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("no git")))
    assert generation._git() == (None, None)
    generation._git.cache_clear()
