# Sources used

## Primary (everything in this package derives from it)

**Zarruk, Brandner, Pearce & Phillips (2014)** — "Experimental study of the steady
fluid-structure interaction of flexible hydrofoils", Journal of Fluids and Structures
51:326-343. doi:10.1016/j.jfluidstructs.2014.10.009

- Local file: `zarruk2014-original.pdf` — 29-page author-accepted manuscript / preprint
  (TeX output dated 1 Sep 2014), supplied by the user. Access status: user-supplied copy of
  the accepted manuscript; the journal version of record is paywalled (Elsevier). The data
  extracted here (geometry values, measured data points, uncertainty statements) are facts,
  digitized for internal validation use; page/figure numbers cited throughout refer to this
  preprint (printed page = PDF page).
- Contributed: complete geometry spec (geometry.md), all digitized curves (measured/*.csv),
  tunnel/uncertainty statements.
- Text extraction: `zarruk2014.txt` (pdftotext -layout).
- Figure renders: `pages/hr13-13.png` (Fig 8), `hr14-14.png` (Fig 9), `hr23-23.png`
  (Figs 18-19), `hr26-26.png` (Fig 22), all 600 dpi; `pages/p*.png` at 300 dpi.
- Verification overlays (digitized points plotted back onto source figures):
  `pages/verify_fig8.png`, `pages/verify_fig9.png`, `pages/verify_f18.png`,
  `pages/verify_f19.png`.

## Secondary (attempted, not needed after the original became available)

- Cambridge Core free PDF of Smith et al. (2020) JFM "The influence of fluid-structure
  interaction on cloud cavitation about a stiff hydrofoil. Part 1" — download returned an
  HTML challenge page (Cloudflare); not pursued further per no-bypass policy. Would only
  have served as a geometry cross-check.
- mdolab.engin.umich.edu/publications — fetched (802 kB HTML, 24 hydrofoil hits) but not
  mined further after the pivot to the original manuscript.
- api.semanticscholar.org — rate-limited (HTTP 429) on first query; abandoned.

## Digitization toolchain (audit trail, all in this directory)

- `digitize_forces3.py` — final force-polar digitizer (Figs 8/9): color segmentation per Re
  series; cyan squares via 5x5-erosion component analysis with geometric deblending of
  merged blobs; green/red (+/*) markers via vertical-stroke (11x1) erosion after 3x3
  closing; blue via column clustering; branch assignment by predictive tracking. Outputs
  `measured/*_raw3.csv` (kept as audit trail; `_raw.csv`/`_raw2.csv` are earlier iterations).
- `export_final.py` — converts raw3 to final `measured/forces_*.csv` with quality grades
  and occlusion pruning.
- `digitize_defl2.py` -> `measured/defl_candidates.csv` -> `deflection_dimensionless_metal.csv`.
- `digitize_twist2.py` -> `measured/twist_raw.csv` -> `twist_CFRP_Fig22.csv`.
- Calibration checks: axis frames vs in-figure dashed alpha=0 / CL=0 lines (<1 px);
  deflection axis vs caption-stated mean lines (0.204/0.227 reproduced to +/-0.0004);
  twist axis vs caption anchors (+0.6/-2.2 deg reproduced as +0.59/-2.19).
