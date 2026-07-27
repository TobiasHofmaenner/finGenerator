# finGenerator

Parametric surfboard fin generator: rider data in (weight, board, wave speed, surf style),
3D-printable fin set out (STEP / STL).

## Architecture

The project is built around one principle: **the fin engine is a library, not a website.**
Everything else — the web app, the CFD loop, the optimizer — is a consumer of that library.

This public repository is the **geometry library plus the tier-0 (analytic) optimizer**. The
CFD / compute-and-verification layer is maintained separately in a private repo.

Planned components:

- **`fingen`** (current focus) — pure-Python parametric fin geometry: outline curves, foil
  sections, spanwise loft, STEP/STL export via the OCCT kernel. Flat base for now; fin-box
  tab systems (FCS II, Futures) come later.
- **Sizing model** — maps rider weight, board, wave speed and surf style onto fin parameters,
  anchored in published hydrodynamics (see `docs/SOURCES.md`).
- **Hydro models** — fast XFOIL/vortex-lattice estimates first; automated OpenFOAM RANS and
  surrogate-based parametric optimization later.
- **Web app** — Python API + HTMX frontend, built as a container image, deployed to
  Kubernetes with Flux image automation.

## Documentation

- [docs/PHYSICS.md](docs/PHYSICS.md) — the math the generator implements, every formula cited
- [docs/SOURCES.md](docs/SOURCES.md) — verified annotated bibliography (65 sources found,
  each URL/metadata-checked; near-duplicates merged)

## 3D printing

Field-tested so far with **PET-CF** and **PAHT-CF**, both structurally usable. The generator
will treat printing material as an input and enforce material-appropriate minimums
(trailing-edge thickness, foil thickness scaling).

## License

Apache-2.0 — see [LICENSE](LICENSE). The core is and will remain open source.
