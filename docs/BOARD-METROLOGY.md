# Board metrology: recovering cluster geometry from photos

**Status: design note. Not implemented.** Captured 2026-07-28.

## The problem

A fin's own polar is placement-independent — a blade's lift curve does not care
where it is bolted. **Interference is not.** Front-to-rear spacing, lateral
offset, toe and cant all move the per-fin load split ([Falk20] exists precisely
because moving the fins changes the forces). So the moment we model a *set*
rather than a *blade*, the answer is conditioned on a cluster geometry we
currently do not know.

Today `FinSetParams` carries production-convention defaults (toe 3.5°, cant 8.0°,
side_x −195 mm, side_y 118 mm) — good representative numbers, but **not any
specific board**. Every set-level result is therefore about *a* thruster, not
*this rider's* thruster.

Worse, these are not values we can design our way out of: with FCS II (and FCS /
Futures generally) **toe and cant are glassed into the board**, not built into
the fin. The boxes set them; the fin clicks in. They are an input to be
*measured*, never an output to be chosen.

Asking a rider to measure toe and cant with a protractor is a non-starter. Hence:

## The idea

Print a **measurement jig** that clicks into the fin boxes and carries fiducial
markers (AprilTag / ArUco). The rider takes a handful of photos from different
angles with an ordinary phone and uploads them. We solve for each jig's pose and
read the cluster geometry straight off.

Because **we** print the jig, its geometry is known to print tolerance. That
solves the hard problem in uncalibrated photogrammetry — *scale*. A tag of known
edge length in a known 3D layout gives metric scale directly; no reference
object, no calibration target, no user diligence required.

And the jig's tab mates with the box, so **the jig's pose IS the box's pose.**
We are not inferring the fin's geometry, we are measuring the mount.

## Why an uncalibrated camera is probably good enough

The rider's camera is unknown and uncalibrated. That matters less than it sounds:

- **Scale comes from the jig, not the camera.** Known tag size + known tag
  layout ⇒ metric.
- **Focal length is recoverable.** Phone EXIF carries focal length and sensor
  size (a solid initialization); with enough known 3D↔2D correspondences the
  focal length can be refined in the solve itself (camera resection / bundle
  adjustment). Multiple views make it well-conditioned.
- **We want RELATIVE quantities.** Toe and cant are angles *between* the boxes
  and the board centerline; spacing is a *difference* of positions. Systematic
  errors that affect all jigs identically largely cancel.
- **Multi-view averaging beats single-shot pose.** Single-tag pose from one view
  is the weak case (the classic planar-target ambiguity near fronto-parallel).
  Several tags per jig, several jigs per photo, several photos ⇒ heavily
  over-determined.

## Defining the board frame (the neat part)

Angles must be expressed against the **stringer** (board centerline), not just
jig-to-jig. Two independent ways to recover it, which cross-check each other:

1. **The center box.** By convention the center fin rides the stringer at
   toe = cant = 0 (`fingen.assembly.fin_set` places it exactly so). The center
   jig therefore *defines* the reference frame for a thruster / 2+1 / single.
2. **Side-pair symmetry.** The two side boxes are mirror-symmetric about the
   stringer, so the perpendicular bisector of the front pair recovers the
   centerline. This is the only route for a twin/quad (no center box) and a free
   consistency check where a center exists.

The board's bottom surface near the cluster gives the plane cant is measured
against; three or more jig bases already span it (it is curved — see Limitations).

## What comes out

Exactly the fields `FinSetParams` needs, and nothing else:

| Output | From |
|---|---|
| `side_y`, `rear_y` | jig base-centre lateral offset from the recovered stringer |
| `side_x`, `rear_x` | jig base-centre fore/aft offset |
| `toe`, `rear_toe` | jig yaw about the board normal, relative to the stringer |
| `cant`, `rear_cant` | jig roll about the fore/aft axis, relative to the local bottom plane |
| `config` | how many jigs were found, and where |

These drop straight into a set-polar CFD job (`fin_set` already serializes
placement, and placement is part of the corpus dedup key) — so a rider's real
board geometry becomes a first-class, versioned input.

## Accuracy target

Toe and cant live in a 0–8° band, so **±0.5° is the useful bar**; spacing wants
roughly ±2 mm. Published AprilTag pose accuracy at phone resolutions is in that
neighbourhood *per view*, and we get many views plus a rigid known layout — so
the target looks reachable, but this is the number the prototype has to prove
before anything downstream trusts it.

Sensitivity should be checked the honest way round: run the set CFD at toe ±0.5°
and cant ±1° and see how much the per-fin split actually moves. If interference
is insensitive at that scale, cheap photos are plenty; if it is sensitive, the
jig has to be good — and we will know *before* building it.

## Jig design sketch

- **Mates like a fin**: the existing `fingen.tabs` geometry (CLICK_TAB / DUAL_TAB
  / SINGLE_TAB) is already parametric — the jig is a tab base with a marker
  plate instead of a blade. Reuse, don't reinvent.
- **Zero play** is the dominant error source: box tolerance ⇒ jig rock ⇒ angle
  error. Wants a snug tab, ideally a light preload (and FCS II's cam screw
  helps). Worth a printed test in two tolerances.
- **Markers visible from many angles**: a single flat plate is weak near
  edge-on. A small faceted head (two or three non-coplanar faces) or a short
  post with tags on multiple sides makes pose well-conditioned from any
  reasonable viewpoint.
- **Distinct tag IDs per slot** so the solver knows which jig is the centre and
  which rail is which without asking the user.
- **Print in a stiff, dimensionally-stable material** and keep it small — this
  is a metrology tool, its own warp is systematic error. (PET-CF over PLA.)

## Rider flow

1. Order/print the jig (three for a thruster).
2. Click them into the boxes.
3. Take ~8–12 photos, walking around the tail, both rails, some high and some
   low. No instructions beyond "get all three markers in frame often".
4. Upload. We solve, show the recovered numbers **with uncertainties**, and ask
   for a sanity confirmation.
5. The board geometry is stored against the rider's profile and used for every
   subsequent set-level design and CFD run.

## Limitations / open questions

- **Board bottom is curved** (vee, concave). "The bottom plane" near the cluster
  is an approximation; cant is genuinely measured against a local tangent plane.
  Needs a defined convention or it becomes a silent bias.
- **Box play** may dominate the error budget (see above) — measure it first.
- **A jig per tab system** (FCS II, FCS, Futures) is three prints, not one.
- **Not all riders will do this.** The defaults must stay a sane fallback, and
  any result computed from defaults must be *labelled* as generic — never
  silently presented as being about the rider's board.
- **Is it worth it?** Gated on the sensitivity study above. If ±0.5° toe barely
  moves the per-fin split, this is a beautiful solution to a non-problem.

## Why it is attractive beyond the physics

It turns an unanswerable question ("what's your toe and cant?") into a task a
rider can actually complete, with a printed part *we already know how to make*.
It is also a natural onboarding artefact for the product, and every submission
enriches a dataset of real production cluster geometries — which is exactly the
distribution the multi-fin model should be validated over.

## Related

- `fingen.params.FinSetParams` — the fields this recovers.
- `fingen.optimize.fin_set_to_dict` — placement already crosses the wire.
- `fingen.tabs` — the mating geometry the jig reuses.
- `docs/TAB-SYSTEMS.md` — per-system tab dimensions.
- The multi-fin CFD (`fincfd.setcase`) — the consumer that makes this matter.
