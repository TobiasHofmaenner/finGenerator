"""CalculiX result viewer: dark FEM inspection panels for the FSI approval gate.

Minimal, dependency-free readers for the two CalculiX text formats — the input
deck (*NODE / *ELEMENT / *NSET / *BOUNDARY / *DLOAD, with *INCLUDE) and the
.frd result file (nodal block 2C, nodal result blocks -4 DISP / -4 STRESS) —
in the spirit of cfd.viz's _Surface. The .frd is a fixed-column format
(adjacent negative values touch, "…E+00-1.23456E-01"), so parsing is by
column slice, never split().

fem_report() renders two PNGs from a solved static case: the inspection sheet
(undeformed vs deformed overlay in side x-z and front y-z views, the fixed
node set marked, the loaded faces and load direction shown, a displacement-
magnitude map, and the numbers against the sizing.py material allowable) and
a von Mises map on the deformed shape. Units are the fingen deck convention
mm-N-MPa: displacements read in mm, stresses in MPa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from fingen.sizing import _MATERIAL_ALLOW_MPA

# T-FINS dark instrument palette (shared instrument look across the viz modules).
_BG = "#0b0e11"
_TEXT = "#e8e8e8"
_MUTED = "#8f8f8f"
_GRID = (1.0, 1.0, 1.0, 0.14)
_CYAN = "#7fd4e0"
_ORANGE = "#f2a154"
_LOAD = "#e58b8b"

# CalculiX C3D4/C3D10 face numbering over the four corner nodes (ccx docs
# §"Eight-node brick element" neighbourhood; tets: face 1 = 1-2-3,
# 2 = 1-4-2, 3 = 2-4-3, 4 = 3-4-1). Used both to WRITE *DLOAD face labels
# and to draw the loaded faces back from a parsed deck.
TET_FACES = {1: (0, 1, 2), 2: (0, 3, 1), 3: (1, 3, 2), 4: (2, 3, 0)}


# ---------------------------------------------------------------------------
# .frd parsing
# ---------------------------------------------------------------------------

@dataclass
class FrdResult:
    """Nodal coordinates plus the nodal result blocks of a CalculiX .frd."""

    node_ids: np.ndarray  # (n,) int, file order
    coords: np.ndarray  # (n, 3)
    blocks: dict[str, np.ndarray]  # name ("DISP", "STRESS", …) -> (n, ncomp)

    @property
    def displacement(self) -> np.ndarray:
        """(n, 3) displacements, row-aligned with node_ids."""
        return self.blocks["DISP"]

    @property
    def stress(self) -> np.ndarray:
        """(n, 6) nodal stresses SXX SYY SZZ SXY SYZ SZX."""
        return self.blocks["STRESS"]


def _row_values(line: str, start: int, want: int) -> list[float]:
    """Up to `want` fixed-width (12-char) floats from `line` at `start`."""
    out = []
    for i in range(start, start + 12 * want, 12):
        chunk = line[i:i + 12].strip()
        if not chunk:
            break
        out.append(float(chunk))
    return out


def parse_frd_text(text: str) -> FrdResult:
    """Parse .frd content: the 2C nodal block and every -4 nodal result block.

    Fixed-column records (ccx long format): data lines are " -1" + node id in
    10 columns + values in 12-column E-format fields; " -2" continuation lines
    carry further values from column 3; " -3" ends a block. Components flagged
    as calculated (iexist = 1, e.g. DISP's ALL) are declared but not stored.
    """
    lines = text.splitlines()
    node_ids: list[int] = []
    coords: list[list[float]] = []
    raw_blocks: dict[str, dict[int, list[float]]] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line[:6].strip() == "2C":  # nodal coordinate block
            i += 1
            while i < len(lines) and lines[i][:3].strip() != "-3":
                row = lines[i]
                if row[:3].strip() == "-1":
                    node_ids.append(int(row[3:13]))
                    coords.append(_row_values(row, 13, 3))
                i += 1
        elif line[:3].strip() == "-4":  # nodal result block
            name = line[5:13].strip()
            i += 1
            stored = 0
            while i < len(lines) and lines[i][:3].strip() == "-5":
                iexist = (lines[i][33:38].strip() or "0")
                stored += iexist == "0"
                i += 1
            data = raw_blocks.setdefault(name, {})
            nid = None
            while i < len(lines) and lines[i][:3].strip() != "-3":
                row = lines[i]
                code = row[:3].strip()
                if code == "-1":
                    nid = int(row[3:13])
                    data[nid] = _row_values(row, 13, min(stored, 6))
                elif code == "-2" and nid is not None:  # continuation
                    data[nid] += _row_values(row, 3, stored - len(data[nid]))
                i += 1
        i += 1

    ids = np.asarray(node_ids, dtype=int)
    index = {nid: k for k, nid in enumerate(ids)}
    blocks = {}
    for name, data in raw_blocks.items():
        ncomp = max(len(v) for v in data.values())
        arr = np.zeros((len(ids), ncomp))
        for nid, vals in data.items():
            arr[index[nid], :len(vals)] = vals
        blocks[name] = arr
    return FrdResult(ids, np.asarray(coords, dtype=float), blocks)


def parse_frd(path: str | Path) -> FrdResult:
    """Read and parse a .frd file."""
    return parse_frd_text(Path(path).read_text())


def von_mises(stress: np.ndarray) -> np.ndarray:
    """Von Mises equivalent of (n, 6) stress rows SXX SYY SZZ SXY SYZ SZX."""
    sxx, syy, szz, sxy, syz, szx = np.asarray(stress).T
    return np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                   + 3.0 * (sxy**2 + syz**2 + szx**2))


# ---------------------------------------------------------------------------
# .inp parsing
# ---------------------------------------------------------------------------

@dataclass
class CcxModel:
    """The parts of a ccx deck the viewer (and the demo mesher) needs."""

    nodes: dict[int, np.ndarray] = field(default_factory=dict)
    elements: dict[int, tuple[int, ...]] = field(default_factory=dict)  # C3D10
    nsets: dict[str, list[int]] = field(default_factory=dict)
    boundaries: list[tuple[str, int, int]] = field(default_factory=list)
    dloads: list[tuple[int, int, float]] = field(default_factory=list)
    elastic: tuple[float, float] | None = None  # (E, nu)

    def fixed_node_ids(self) -> list[int]:
        """Node ids referenced by *BOUNDARY entries (set names expanded)."""
        out: list[int] = []
        for target, _first, _last in self.boundaries:
            out += self.nsets.get(target.upper(), []) if not target.isdigit() \
                else [int(target)]
        return out


def _keyword(line: str) -> tuple[str, dict[str, str]]:
    parts = [p.strip() for p in line.split(",")]
    params = {}
    for p in parts[1:]:
        k, _, v = p.partition("=")
        params[k.strip().upper()] = v.strip()
    return parts[0].lstrip("*").upper(), params


def read_inp(path: str | Path) -> CcxModel:
    """Parse a ccx input deck (nodes, C3D10 elements, nsets, boundaries,
    dloads, elastic constants), following *INCLUDE references."""
    model = CcxModel()
    _read_inp_into(Path(path), model)
    return model


def _read_inp_into(path: Path, model: CcxModel) -> None:
    mode: str | None = None
    target = ""
    buf: list[int] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("**"):
            continue
        if line.startswith("*"):
            key, params = _keyword(line)
            mode, buf = None, []
            if key == "INCLUDE":
                _read_inp_into(path.parent / params["INPUT"], model)
            elif key == "NODE":
                mode = "node"
            elif key == "ELEMENT" and params.get("TYPE", "").upper().startswith("C3D10"):
                mode = "element"
            elif key == "NSET":
                target = params["NSET"].upper()
                model.nsets.setdefault(target, [])
                mode = "nset"
            elif key in ("BOUNDARY", "DLOAD", "ELASTIC"):
                mode = key.lower()
            continue
        parts = [p for p in (s.strip() for s in line.split(",")) if p]
        if mode == "node":
            model.nodes[int(parts[0])] = np.array([float(v) for v in parts[1:4]])
        elif mode == "element":
            buf += [int(v) for v in parts]
            if len(buf) >= 11:
                model.elements[buf[0]] = tuple(buf[1:11])
                buf = []
        elif mode == "nset":
            model.nsets[target] += [int(v) for v in parts]
        elif mode == "boundary":
            first = int(parts[1])
            last = int(parts[2]) if len(parts) > 2 else first
            model.boundaries.append((parts[0], first, last))
        elif mode == "dload":
            model.dloads.append((int(parts[0]), int(parts[1][1:]), float(parts[2])))
        elif mode == "elastic" and model.elastic is None:
            model.elastic = (float(parts[0]), float(parts[1]))


def boundary_faces(model: CcxModel) -> list[tuple[int, int, tuple[int, int, int]]]:
    """(element id, ccx face number, corner-node triple) for every exterior
    face of the C3D10 mesh, the triple oriented so its right-hand normal
    points OUT of the body (fixed geometrically against the opposite corner,
    independent of any node-ordering convention)."""
    seen: dict[frozenset, tuple[int, int, tuple[int, int, int]] | None] = {}
    for eid, conn in model.elements.items():
        for fno, idx in TET_FACES.items():
            tri = (conn[idx[0]], conn[idx[1]], conn[idx[2]])
            key = frozenset(tri)
            seen[key] = None if key in seen else (eid, fno, tri)
    faces = []
    for entry in seen.values():
        if entry is None:
            continue
        eid, fno, tri = entry
        conn = model.elements[eid]
        opposite = next(n for n in conn[:4] if n not in tri)
        a, b, c = (model.nodes[n] for n in tri)
        if np.dot(np.cross(b - a, c - a), model.nodes[opposite] - a) > 0.0:
            tri = (tri[0], tri[2], tri[1])
        faces.append((eid, fno, tri))
    return faces


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _nice_factor(x: float) -> float:
    """Round an exaggeration factor to a headline-friendly value."""
    if x >= 10.0:
        return max(5.0, round(x / 5.0) * 5.0)
    if x >= 3.0:
        return float(round(x))
    return max(0.1, round(x, 1))


def _style(ax, title: str) -> None:
    ax.set_facecolor(_BG)
    for spine in ax.spines.values():
        spine.set_color(_GRID)
    ax.tick_params(colors=_MUTED, labelsize=8)
    ax.set_title(title, color=_TEXT, fontsize=10)
    ax.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)


def _edges(tris: np.ndarray) -> np.ndarray:
    """Unique node-index pairs of a triangle soup's edges."""
    e = np.vstack([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    return np.unique(np.sort(e, axis=1), axis=0)


def _wire(ax, pts2d: np.ndarray, edges: np.ndarray, color, lw: float, alpha: float,
          label: str | None = None):
    from matplotlib.collections import LineCollection

    lc = LineCollection(pts2d[edges], colors=color, linewidths=lw, alpha=alpha,
                        label=label)
    ax.add_collection(lc)
    return lc


def _shaded(ax, pts2d: np.ndarray, tris: np.ndarray, values: np.ndarray,
            depth: np.ndarray, cmap, norm):
    """Painter-sorted flat-shaded triangles colored by per-node values."""
    from matplotlib.collections import PolyCollection

    order = np.argsort(depth)
    tri_vals = values[tris].mean(axis=1)
    pc = PolyCollection(pts2d[tris[order]], edgecolor="none",
                        facecolors=cmap(norm(tri_vals[order])))
    ax.add_collection(pc)
    return pc


def _colorbar(fig, ax, cmap, norm, label: str):
    import matplotlib.pyplot as plt

    cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax,
                        shrink=0.85, pad=0.03)
    cbar.set_label(label, color=_MUTED, fontsize=8)
    cbar.ax.tick_params(colors=_MUTED, labelsize=7)
    cbar.outline.set_edgecolor(_GRID)
    return cbar


def fem_report(frd_path: str | Path, inp_path: str | Path, out_png: str | Path,
               stress_png: str | Path | None = None,
               material: str = "pet-cf") -> dict:
    """Render the FEM inspection sheet (out_png) and the von Mises map
    (stress_png, default: out_png stem + "-stress.png").

    Returns {"png", "stress_png", "u_max_mm", "vm_max_mpa", "allow_mpa",
    "safety_factor", "exaggeration", "force_n"}.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_png = Path(out_png)
    stress_png = (Path(stress_png) if stress_png is not None
                  else out_png.with_name(out_png.stem + "-stress.png"))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    stress_png.parent.mkdir(parents=True, exist_ok=True)

    model = read_inp(inp_path)
    frd = parse_frd(frd_path)
    index = {nid: k for k, nid in enumerate(frd.node_ids)}
    xyz = frd.coords
    u = frd.displacement
    umag = np.linalg.norm(u, axis=1)
    vm = von_mises(frd.stress)

    faces = boundary_faces(model)
    tris = np.array([[index[a], index[b], index[c]] for _, _, tri in faces
                     for a, b, c in [tri]])
    edges = _edges(tris)
    loaded_keys = {(eid, fno) for eid, fno, _ in model.dloads}
    loaded = np.array([(eid, fno) in loaded_keys for eid, fno, _ in faces])
    fixed_rows = np.array(sorted({index[n] for n in model.fixed_node_ids()
                                  if n in index}), dtype=int)

    span = float(xyz[:, 2].max() - xyz[:, 2].min())
    u_max = float(umag.max())
    exag = _nice_factor(0.15 * span / max(u_max, 1e-12))
    dxyz = xyz + exag * u

    # Load resultant from the loaded faces' outward normals (mm² · MPa = N).
    force = np.zeros(3)
    pressures = dict(((eid, fno), p) for eid, fno, p in model.dloads)
    for eid, fno, tri in faces:
        p = pressures.get((eid, fno))
        if p is not None:
            a, b, c = (model.nodes[n] for n in tri)
            force -= p * 0.5 * np.cross(b - a, c - a)  # +p pushes inward
    e_mpa, nu = model.elastic if model.elastic else (float("nan"), float("nan"))
    allow = _MATERIAL_ALLOW_MPA[material]
    vm_max = float(vm.max())
    sf = allow / vm_max

    side, front = [0, 2], [1, 2]  # (x,z) and (y,z) projections
    depth_side, depth_front = dxyz[tris][:, :, 1].mean(axis=1), \
        -dxyz[tris][:, :, 0].mean(axis=1)

    # ---------------- sheet 1: inspection panels -------------------------
    fig, axes = plt.subplots(
        1, 4, figsize=(16.5, 6.6), facecolor=_BG, layout="constrained",
        gridspec_kw={"width_ratios": [1.35, 0.75, 1.35, 1.0]})
    ax_side, ax_front, ax_umap, ax_txt = axes

    _style(ax_side, "side view x-z · undeformed vs deformed")
    from matplotlib.collections import PolyCollection

    _wire(ax_side, xyz[:, side], edges, "#ffffff", 0.35, 0.22, "undeformed")
    _wire(ax_side, dxyz[:, side], edges, _CYAN, 0.45, 0.55, f"deformed ×{exag:g}")
    if loaded.any():
        ax_side.add_collection(PolyCollection(
            xyz[tris[loaded]][:, :, side], facecolor=_LOAD, alpha=0.20,
            edgecolor="none", label="loaded faces (outer, toward viewer)"))
    ax_side.plot(xyz[fixed_rows, 0], xyz[fixed_rows, 2], ".", color=_ORANGE,
                 ms=2.5, label="fixed (all DOF)")
    ax_side.text(0.97, 0.065, "bend is out of plane here — see front view",
                 transform=ax_side.transAxes, color=_MUTED, fontsize=7.5,
                 ha="right", style="italic")
    ax_side.set_xlabel("x [mm]", color=_MUTED)
    ax_side.set_ylabel("z [mm]", color=_MUTED)

    _style(ax_front, "front view y-z · the bend")
    _wire(ax_front, xyz[:, front], edges, "#ffffff", 0.35, 0.22)
    _wire(ax_front, dxyz[:, front], edges, _CYAN, 0.45, 0.55)
    ax_front.plot(xyz[fixed_rows, 1], xyz[fixed_rows, 2], ".", color=_ORANGE,
                  ms=2.5)
    if loaded.any():  # pressure arrows onto the outer face, spread over span
        cyz = xyz[tris[loaded]].mean(axis=1)
        picks = cyz[np.argsort(cyz[:, 2])][::max(1, loaded.sum() // 11)]
        alen = 0.09 * span
        for _, cy, cz in picks:
            ax_front.annotate(
                "", xy=(cy, cz), xytext=(cy + alen, cz),
                arrowprops={"arrowstyle": "-|>", "color": _LOAD, "lw": 1.3})
        ax_front.text(picks[-1][1] + alen, xyz[:, 2].max() + 0.04 * span,
                      "10 kPa" if abs(force[1]) else "pressure", color=_LOAD,
                      fontsize=9, ha="left")
    ax_front.text(xyz[fixed_rows, 1].mean(), -0.06 * span, "fixed (all DOF)",
                  color=_ORANGE, fontsize=9, ha="center", va="top")
    ax_front.set_xlabel("y [mm]", color=_MUTED)

    _style(ax_umap, f"|u| on the deformed shape (×{exag:g})")
    cmap_u = plt.get_cmap("cividis")
    norm_u = plt.Normalize(0.0, u_max)
    _shaded(ax_umap, dxyz[:, side], tris, umag, depth_side, cmap_u, norm_u)
    ax_umap.plot(xyz[fixed_rows, 0], xyz[fixed_rows, 2], ".", color=_ORANGE,
                 ms=2.0)
    _colorbar(fig, ax_umap, cmap_u, norm_u, "|u| [mm]  (true, not exaggerated)")
    ax_umap.set_xlabel("x [mm]", color=_MUTED)

    for ax in (ax_side, ax_front, ax_umap):
        ax.autoscale_view()
        ax.set_aspect("equal", adjustable="datalim")
        ax.margins(0.08)
    leg = ax_side.legend(facecolor=_BG, edgecolor=_GRID, labelcolor=_TEXT,
                         fontsize=7.5, loc="upper right")
    leg.get_frame().set_linewidth(0.8)
    ax_front.text(0.5, 1.075, f"deformation × {exag:g}", color=_CYAN,
                  fontsize=13, ha="center", transform=ax_front.transAxes,
                  family="monospace", weight="bold")

    ax_txt.set_axis_off()
    fdir = "xyz"[int(np.argmax(np.abs(force)))] if np.any(force) else "-"
    fsign = "-" if force[int(np.argmax(np.abs(force)))] < 0 else "+"
    ax_txt.text(
        0.02, 0.97,
        "\n".join([
            "CalculiX static · C3D10 · mm-N-MPa",
            "",
            f"nodes       {len(frd.node_ids):,}",
            f"elements    {len(model.elements):,}",
            f"fixed       {len(fixed_rows):,} base nodes, all DOF",
            f"load        {abs(pressures[next(iter(pressures))]) * 1e3:g} kPa "
            f"on {int(loaded.sum())} outer faces" if pressures else "load        none",
            f"resultant   {np.linalg.norm(force):.0f} N  ({fsign}{fdir})",
            f"E, nu       {e_mpa:g} MPa, {nu:g}",
            "",
            f"max |u|     {u_max:.2f} mm   (true)",
            f"max s_vM    {vm_max:.1f} MPa  (nodal)",
            f"allowable   {allow:.1f} MPa  ({material}, sizing.py)",
            f"safety      {sf:.2f}",
            "",
            f"drawn deformation ×{exag:g}",
        ]),
        transform=ax_txt.transAxes, color=_TEXT, fontsize=10.5, va="top",
        family="monospace", linespacing=1.55)

    fig.suptitle("FEM inspection · fixed base + outer-face pressure",
                 color=_TEXT, fontsize=12, family="monospace")
    fig.savefig(out_png, dpi=150, facecolor=_BG)
    plt.close(fig)

    # ---------------- sheet 2: von Mises map -----------------------------
    fig2, (bx1, bx2) = plt.subplots(
        1, 2, figsize=(12.0, 6.4), facecolor=_BG, layout="constrained",
        gridspec_kw={"width_ratios": [1.6, 0.8]})
    cmap_s = plt.get_cmap("magma")
    vcap = float(np.percentile(vm, 99.0))
    norm_s = plt.Normalize(0.0, vcap)
    _style(bx1, f"von Mises · side view (deformed ×{exag:g})")
    _shaded(bx1, dxyz[:, side], tris, vm, depth_side, cmap_s, norm_s)
    bx1.plot(xyz[fixed_rows, 0], xyz[fixed_rows, 2], ".", color=_ORANGE, ms=2.0)
    bx1.text(0.02, 0.04, "fixed (all DOF)", transform=bx1.transAxes,
             color=_ORANGE, fontsize=9)
    bx1.set_xlabel("x [mm]", color=_MUTED)
    bx1.set_ylabel("z [mm]", color=_MUTED)
    _style(bx2, "front view y-z")
    _shaded(bx2, dxyz[:, front], tris, vm, depth_front, cmap_s, norm_s)
    bx2.set_xlabel("y [mm]", color=_MUTED)
    _colorbar(fig2, bx2, cmap_s, norm_s,
              f"von Mises [MPa]  (color capped at p99 = {vcap:.1f})")
    for bx in (bx1, bx2):
        bx.autoscale_view()
        bx.set_aspect("equal", adjustable="datalim")
        bx.margins(0.08)
    bx2.text(0.03, 0.97,
             f"max {vm_max:.1f} MPa\nallow {allow:.1f} MPa\nSF {sf:.2f}",
             transform=bx2.transAxes, color=_TEXT, fontsize=10, va="top",
             family="monospace", linespacing=1.5)
    fig2.suptitle("von Mises stress on the deformed shape", color=_TEXT,
                  fontsize=12, family="monospace")
    fig2.savefig(stress_png, dpi=150, facecolor=_BG)
    plt.close(fig2)

    return {"png": out_png, "stress_png": stress_png, "u_max_mm": u_max,
            "vm_max_mpa": vm_max, "allow_mpa": allow, "safety_factor": sf,
            "exaggeration": exag, "force_n": float(np.linalg.norm(force))}
