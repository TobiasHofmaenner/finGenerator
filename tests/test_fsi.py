"""Fast unit tests for the two FSI interface operators (scripts/fsi_loop.py).

The pressure map (CFD surface -> FEM faces) and the STL warp (FEM displacement
field -> foil vertices) are the load-bearing transfers; both are exercised on
tiny synthetic cases with a known answer. No CFD/FEM here — no heavy marker.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fsi_loop import map_pressure, warp_vertices  # noqa: E402


def test_map_pressure_nearest_face():
    # Four FEM face centroids; four CFD triangle centroids sit a hair off each
    # (plus two decoys further away). Every face must inherit the pressure of
    # its own nearest CFD centroid, and the error norm is the RMS offset.
    faces = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0],
                      [0.0, 10.0, 0.0], [10.0, 10.0, 0.0]])
    src = np.array([[0.1, 0.0, 0.0], [10.0, 0.1, 0.0],
                    [0.0, 9.9, 0.0], [9.9, 10.0, 0.0],
                    [50.0, 50.0, 0.0], [-50.0, -50.0, 0.0]])
    src_p = np.array([1.0, 2.0, 3.0, 4.0, -9.0, -9.0])
    p, err = map_pressure(faces, src, src_p)
    np.testing.assert_allclose(p, [1.0, 2.0, 3.0, 4.0])
    np.testing.assert_allclose(err, 0.1)  # RMS of the four 0.1 offsets


def test_warp_vertices_linear_field_exact():
    # Linear interpolation of a LINEAR displacement field is exact. Source
    # nodes: a 3x3x3 lattice over [-1, 2]^3 (a proper 3D hull). Query: the unit
    # cube's eight vertices (strictly inside) displaced by d(x) = A x + b.
    g = np.linspace(-1.0, 2.0, 3)
    nodes = np.array([[x, y, z] for x in g for y in g for z in g], dtype=float)
    rng = np.random.default_rng(0)
    a = rng.normal(size=(3, 3))
    b = rng.normal(size=3)
    node_disp = nodes @ a.T + b

    cube = np.array([[x, y, z] for x in (0.0, 1.0) for y in (0.0, 1.0)
                     for z in (0.0, 1.0)])
    warped = warp_vertices(cube, nodes, node_disp)
    expected = cube + (cube @ a.T + b)
    np.testing.assert_allclose(warped, expected, atol=1e-10)


def test_warp_vertices_zero_field_is_identity():
    g = np.linspace(-1.0, 2.0, 3)
    nodes = np.array([[x, y, z] for x in g for y in g for z in g], dtype=float)
    cube = np.array([[0.2, 0.3, 0.4], [0.9, 0.1, 0.7]])
    warped = warp_vertices(cube, nodes, np.zeros_like(nodes))
    np.testing.assert_allclose(warped, cube, atol=1e-12)
