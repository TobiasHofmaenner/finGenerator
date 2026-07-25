"""femviz parsers: fixed-column .frd reading and inp/boundary-face utilities."""

import numpy as np
import pytest

from fingen.femviz import boundary_faces, parse_frd_text, read_inp, von_mises

# Hand-written .frd exactly in ccx's long ascii format: " -1" + node id in 10
# columns + 12-column E-format values. Node 4 exercises the fixed-column trap:
# adjacent negative values touch with no separating whitespace.
FRD = """\
    1C
    1UUSER
    2C                             4                                     1
 -1         1 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 1.00000E+01 0.00000E+00 0.00000E+00
 -1         3 0.00000E+00 1.00000E+01 0.00000E+00
 -1         4-1.00000E+00-2.00000E+00 5.00000E+00
 -3
  100CL  101 1.00000E+00           4                     0    1           1
 -4  DISP        4    1
 -5  D1          1    2    1    0
 -5  D2          1    2    2    0
 -5  D3          1    2    3    0
 -5  ALL         1    2    0    0    1ALL
 -1         1 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 1.50000E+00-2.50000E-01 0.00000E+00
 -1         3 0.00000E+00 1.00000E-03-1.00000E-03
 -1         4-1.23400E+00-5.00000E-01 2.00000E+00
 -3
  100CL  101 1.00000E+00           4                     0    1           1
 -4  STRESS      6    1
 -5  SXX         1    4    1    1
 -5  SYY         1    4    2    2
 -5  SZZ         1    4    3    3
 -5  SXY         1    4    1    2
 -5  SYZ         1    4    2    3
 -5  SZX         1    4    3    1
 -1         1 1.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2-3.00000E+00-3.00000E+00-3.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         3 0.00000E+00 0.00000E+00 0.00000E+00 2.00000E+00 0.00000E+00 0.00000E+00
 -1         4 1.00000E+01-1.00000E+01 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -3
 9999
"""

# One C3D10 tet (corners 1-4, midside 5-10 in ccx ordering) split across a
# *INCLUDE'd mesh file, the way the fem_demo deck is written.
MESH_INP = """\
*NODE, NSET=NALL
1, 0., 0., 0.
2, 1., 0., 0.
3, 0., 1., 0.
4, 0., 0., 1.
5, 0.5, 0., 0.
6, 0.5, 0.5, 0.
7, 0., 0.5, 0.
8, 0., 0., 0.5
9, 0.5, 0., 0.5
10, 0., 0.5, 0.5
*ELEMENT, TYPE=C3D10, ELSET=EALL
1, 1, 2, 3, 4, 5,
6, 7, 8, 9, 10
"""

JOB_INP = """\
** demo deck
*INCLUDE, INPUT=mesh.inp
*NSET, NSET=BASE
1, 2,
3
*MATERIAL, NAME=PETCF
*ELASTIC
7000., 0.35
*SOLID SECTION, ELSET=EALL, MATERIAL=PETCF
*BOUNDARY
BASE, 1, 3
*STEP
*STATIC
*DLOAD
1, P1, 0.01
*NODE FILE
U
*END STEP
"""


def test_frd_nodes_fixed_column():
    frd = parse_frd_text(FRD)
    assert frd.node_ids.tolist() == [1, 2, 3, 4]
    np.testing.assert_allclose(frd.coords[1], [10.0, 0.0, 0.0])
    # The touching "-1.00000E+00-2.00000E+00" pair must split on columns.
    np.testing.assert_allclose(frd.coords[3], [-1.0, -2.0, 5.0])


def test_frd_displacement_block():
    frd = parse_frd_text(FRD)
    disp = frd.displacement
    assert disp.shape == (4, 3)  # the calculated ALL component is not stored
    np.testing.assert_allclose(disp[1], [1.5, -0.25, 0.0])
    np.testing.assert_allclose(disp[3], [-1.234, -0.5, 2.0])


def test_frd_stress_and_von_mises():
    frd = parse_frd_text(FRD)
    assert frd.stress.shape == (4, 6)
    np.testing.assert_allclose(frd.stress[2], [0, 0, 0, 2.0, 0, 0])
    vm = von_mises(frd.stress)
    expected = [1.0,  # uniaxial
                0.0,  # hydrostatic
                2.0 * np.sqrt(3.0),  # pure shear
                np.sqrt(300.0)]  # sxx = +10, syy = -10
    np.testing.assert_allclose(vm, expected, atol=1e-12)


@pytest.fixture
def model(tmp_path):
    (tmp_path / "mesh.inp").write_text(MESH_INP)
    (tmp_path / "job.inp").write_text(JOB_INP)
    return read_inp(tmp_path / "job.inp")


def test_inp_include_and_sets(model):
    assert len(model.nodes) == 10
    np.testing.assert_allclose(model.nodes[9], [0.5, 0.0, 0.5])
    assert model.elements[1] == (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)  # continuation
    assert model.nsets["BASE"] == [1, 2, 3]
    assert model.boundaries == [("BASE", 1, 3)]
    assert model.fixed_node_ids() == [1, 2, 3]
    assert model.dloads == [(1, 1, 0.01)]
    assert model.elastic == (7000.0, 0.35)


def test_boundary_faces_outward(model):
    faces = boundary_faces(model)
    assert len(faces) == 4  # a lone tet: every face is exterior
    assert {fno for _, fno, _ in faces} == {1, 2, 3, 4}
    centroid = np.mean([model.nodes[n] for n in (1, 2, 3, 4)], axis=0)
    for _, _, tri in faces:
        a, b, c = (model.nodes[n] for n in tri)
        outward = np.cross(b - a, c - a)
        assert np.dot(outward, (a + b + c) / 3.0 - centroid) > 0.0
