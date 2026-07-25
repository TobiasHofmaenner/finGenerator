# Fin mounting systems: geometry & legal status

Research verified 2026-07-24 (find + adversarial verify passes; every load-bearing number
re-fetched or re-measured). **No official dimensional drawing exists for any system** — all
three are proprietary; geometry below comes from convergent community measurement, patents,
and official installation manuals. Confidence is stated per item. Names: we use the generic
terms **dual-tab** (FCS-compatible), **click-tab** (FCS II-compatible), **single-tab**
(Futures-compatible) — descriptive compatibility statements only, no brand styling
(nominative use; "FCS" is a registered trademark of Fin Control Systems Pty Ltd / SHI).

## Dual-tab (original FCS) — HIGH confidence, off-patent

Two rectangular tabs, secured by grub screws in round plugs. Sources: Swaylocks caliper
measurements of production fins, the open-source `hrobeers/finbases` OpenSCAD generator,
and patent US5464359A (qualitative: plain rectangular tabs, no draft).

| Feature | Value | Agreement |
|---|---|---|
| Tab length (each) | 20.0–20.5 mm | 2 sources ±0.5 |
| Tab depth below base | 13.5–14 mm | 2 sources ±0.5 |
| Tab thickness | 6.0–6.35 mm (nominal slot 1/4″; print ~6.2–6.3) | 4 sources |
| **Center-to-center spacing** | **53–53.5 mm** | 2 precise sources; plug slots have ~1.25 mm fore-aft play |
| Gap between tabs | 33 mm | exact agreement |
| Overall span | 73–74 mm | ±1 mm |
| Corner round | 2 mm on lower corners | 1 source + patent (rectangular) |
| Grub screw | 10-24 UNC × 5/16″, 3/32″ hex; bears on tab side face | corroborated |
| Plug hole depth | 15.9 mm (5/8″) — tabs leave clearance | 1 source |

Variants use *more* identical tabs (3-tab longboard/keel), never different ones.

## Click-tab (FCS II) — HIGH footprint / MEDIUM fine features, plug patents active to ~2033

Tool-less: long front tab with a leading-edge hook notch + shorter rear tab with side
retention indents that an acetal barrel on a titanium rod snaps into (~12 kg). Two
independent reverse-engineered CAD models (a STEP and a FreeCAD source) were downloaded
and re-measured with this project's own OCCT during research; footprints agree ≤0.5 mm.
Key datum: FCS II plugs accept original dual-tab fins under grub screws, so slot width
(~6.35), depth (~14) and the legacy tab stations are preserved inside the FCS II slots —
one base-datum module can serve both systems.

| Feature | Value | Agreement |
|---|---|---|
| Overall insert span | 98.0 mm | exact (both models) |
| Front tab length | 44.5–45.0 mm | ±0.5 |
| Rear tab length | 33.0 mm | exact |
| Gap | 20.0–20.5 mm | ±0.5 |
| Thickness | 6.2 mm (variants 6.2/6.4 for box fit) | both |
| Depth | 13.5–14.0 mm | ±0.5 |
| Front hook notch | ~4 mm tall (4–8 mm below surface), 4–5 mm deep, R2 root | both, ±1 |
| Rear side indents (both faces) | ~15 long × 5–8 tall × 0.8–1.0 deep, top ~3 mm below surface | length agrees; height/depth differ (reverse-engineered) |
| TE rake of tabs | ~20°; 1.5 mm × 45° chamfers | single source (STEP) |
| Plug envelope (official) | 110 × 37.5 mm | official |

3D-print practice: printed indents work but deform after several insert/remove cycles
(PETG); the plug's two grub screws are the standard fallback. Expose indent depth as a
parameter.

## Single-tab (Futures) — MEDIUM-HIGH box envelope, two knowns missing

One blade-length tab, angled front, one vertical grub screw at the box front. Best hard
numbers come from patent US20150239532A1's measured box channel, the official Futures
installation manual (PDF), and Swaylocks caliper threads.

| Feature | Value | Agreement |
|---|---|---|
| Box channel length | 4.40″ (patent) vs 4.5″ slot (caliper) = 111.8–114.3 mm — parametrize | 2 sources, definition差 |
| Channel width (max tab thickness) | 7.19 mm (0.283″); print ~7.0 | patent; consistent w/ 6.3 mm community fins |
| Channel depth, 3/4″ side boxes | 17.7 mm; tab 17.3–17.8 | patent + official manual |
| Channel depth, 1/2″ center/quad-rear boxes | tab 12.7–15.2 mm | patent + manual |
| Front tab angle | 6° — **single community source, LOW confidence**; do NOT confuse with the 6° side-fin CANT (official manual) | 1 source |
| Grub screw | newer boxes 10-24 UNC, older M5, ~12 mm; **exact fore-aft offset unpublished** — parameter + trial fit | caliper, 2 confirmations |
| Longboard boxes | 8″ and 10.75″ variants exist | community templates |

Print practice (community consensus): start tabs ~0.2 mm undersize, trial-fit per
printer/filament; CF-reinforced filament over PLA.

## Legal status (facts with sources — NOT legal advice)

- **Original FCS: expired.** US5464359A (priority 1992) expired 2013 ("Expired -
  Lifetime" on Google Patents). Stronger still: *Surfco Hawaii v. Fin Control Systems*,
  264 F.3d 1062 (Fed. Cir. 2001) held that third-party replacement fins for the FCS
  system were permissible repair **even while the plug patents were in force** (full text:
  law.resource.org). A large compatible-fin market exists (DORSAL sells "FCS Compatible"
  by name; Captain Fin uses neutral "Twin Tab").
- **FCS II: plug-side patents active.** US9688365B2 (expires ~2033-07) and US9957021B2
  (~2033-12) — claim 1 covers the **plug's** biasing-rod retention mechanism, not the fin
  tab shape (tabs appear only in dependent claims/description). Third parties ship
  "FCS 2 compatible" fins; the AU application was initially rejected for lack of
  inventive step (Swellnet, 2016). Practical read: fins are the safer side of the
  interface; do not generate FCS II *plugs/boxes*; review claim 1 before *selling*
  click-tab fins with the retention indent.
- **Futures: no interface patent found.** Todos Santos Surf's verified IP covers
  manufacturing methods (US9566729B2), not the tab/box interface; multiple sources state
  Futures deliberately kept the system open. (Unprovable negative — treat as strong
  consensus.)
- **Trademarks:** use "compatible with X" phrasing, generic feature names, no logos.

## Implementation plan

1. `single-tab` (Futures) and `dual-tab` (FCS classic) first: simple prisms, unencumbered,
   HIGH-confidence dims. Unknowns (Futures screw offset + front angle) become parameters.
2. `click-tab` (FCS II) second: shared base datum with dual-tab; indent depth
   parameterized; grub-screw fallback documented.
3. Every system ships with a **test-fit coupon** (tab-only, minutes to print) with a
   `fit_offset` parameter — the user's boxes are the ground truth, not internet numbers.


## Tab positioning (v0.4.0)

`TabParams.x_offset` slides the whole tab set along the base chord
(feasibility-checked at build time: the set must stay on the base with 1 mm
margins); `y_offset` shifts it across the section thickness. The thickness
anchor is family-aware: **flat-inside fins carry the tab's inner face flush
with the y = 0 flat plane**, so blade and tabs print flat on the bed with no
supports — commercial flat-foiled fins sit in their boxes exactly this way,
and slot clearance absorbs the ~1–2 mm lateral shift. Symmetric/cambered
fins keep the tab centered on the base section's mid-thickness. The fit
coupon ignores both offsets (it tests the box interface, not placement).
Note: large |y_offset| on rear tabs can outrun the thin aft section — the
geometry checker refuses the degenerate union rather than exporting it.
