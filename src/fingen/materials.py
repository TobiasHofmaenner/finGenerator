"""Printed-material property cards — datasheet defaults, measured shadows.

Tier-0 flex (fingen.flex) and the sizing gate (fingen.sizing) hinge on one
number above all others: how stiff a printed blade is in the direction it
actually bends. A flat surfboard fin is printed lying on the bed — span and
chord in the machine X-Y plane, the deposited roads running spanwise, and the
layers stacking through the blade THICKNESS (the print Z). Under a side load
the blade bends about its chordwise axis, so the extreme fibres that carry the
bending stress run spanwise, IN-PLANE, along whole deposited roads. The
governing stiffness is therefore the **in-plane flexural (bending) modulus**,
ISO 178 X-Y:

- *Flexural, not tensile* — the load case is bending, and the datasheet's own
  three/four-point-bend coupon (ISO 178) is a closer analogue of a bending
  blade than the ISO 527 tensile dogbone (CF-filled prints read differently in
  bend than in pure tension).
- *X-Y, not Z* — the layers lie in the bending plane; a flat-printed blade
  never loads the weak inter-layer Z bond in primary bending. `e_z_mpa` (ISO
  178 Z) is carried only as the anisotropy handle and the print-on-EDGE
  warning: it is markedly softer and is what the SAME blade would show if
  someone printed it on its edge. See [Fis23] for the ~factor-2 orientation
  split this encodes.

ANNEALING CAVEAT. Every datasheet card here reports ANNEALED coupons (the
`annealed` field is True; the anneal schedule is in each card's `source`).
Polymaker Fiberon PET-CF17 in particular is characterised only after
120 °C / 10 h — its own TDS says so. AS-PRINTED parts test LOWER, the Z
direction most of all, because annealing is what heals the inter-layer bond
and relieves print stress. So these cards are the *annealed ceiling*; treat
them as optimistic for a part straight off the bed. The load-cell rig
(docs/BENCH-PROTOCOL.md) measures the REAL state — build the bench blade in the
state you ship (as-printed or annealed) and let the measured card, tagged with
its own `annealed` flag, shadow the datasheet default.

Cards default to PUBLISHED datasheet numbers (provenance "datasheet") so the
whole model is usable ~a month before that rig yields measured cards — the rig
is then an accuracy UPGRADE, not a blocker. A measured card (provenance
"measured") is built from a bench_intake material-card JSON by
`load_measured_card()` and shadows its datasheet namesake via `register_card()`;
it replaces the effective modulus while inheriting datasheet strength/density
(the bench measures stiffness, not strength — that waits on Test E).

MOISTURE CAVEAT (nylon only). PA absorbs water and softens: high-uptake PA6/66
loses ~30-50% stiffness dry→conditioned. The user's `"paht-cf"` is Elegoo
PAHT-CF, a PA12-CF — PA12 absorbs <1% and largely holds stiffness with humidity
([3DXPA]), so its card carries only a modest ~15% wet derate, NOT the PA6
figure. Datasheets quote DRY, but a submerged fin runs CONDITIONED, so the
PAHT card's default e_mpa is the conditioned estimate with the dry value in
e_mpa_dry (Test G, docs/BENCH-PROTOCOL.md, is decision-grade and replaces the
estimate). By contrast the `"pet-cf"` Fiberon card needs no split: ≈0.53%
equilibrium uptake makes it near seawater-indifferent — a real product
differentiator, noted in both cards' comments.

The registry default `"pet-cf"` is the user's actual filament, Polymaker
Fiberon PET-CF17 ([FibPET26]); the Bambu PET-CF card is kept as
`"bambu-pet-cf"` for filament comparison. `"paht-cf"` is the user's Elegoo
PAHT-CF as an APPROXIMATED card ([ELPAHT26], structural gaps filled from the
Bambu PAHT-CF analog [PAHTCF], which is kept as `"bambu-paht-cf"`); `"pla"` is
Bambu PLA Basic ([PLA]), a low-stiffness reference only. The DRY X-Y bending
STRENGTHS here (`strength_xy_mpa`) are the inputs fingen.sizing knocks down
(print + moisture) into its design allowables; that module cross-references
this one.

Production finish: fins are impregnated with DIAMANT dichtol AM
(capillary sealant) — moisture-uptake figures here are upper bounds for
sealed production parts, and sealed surfaces approach the hydraulically
smooth walls the CFD bench assumes (bare FDM roughness is transitional
at fin Reynolds numbers). Test specimens should carry the same finish.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class MaterialCard:
    """Printed-material properties for one resin at one provenance.

    e_mpa is the OPERATING in-plane (ISO-178 X-Y) FLEXURAL modulus — the
    span-bending stiffness of a flat-printed blade, and the right default for
    fingen.flex (see the module header for why flexural-X-Y, not tensile and
    not Z). For a moisture-sensitive nylon (PA) card e_mpa is the CONDITIONED
    (wet, in-service) value and `e_mpa_dry` carries the dry datasheet reference;
    for a low-uptake resin the two are equal (e_mpa_dry left None). e_z_mpa is
    the through-layer (ISO-178 Z) bending modulus. The strength fields are the
    DRY ISO-178 bending strengths as reported (fingen.sizing applies the print
    and moisture knockdowns). `annealed` records whether the numbers describe
    annealed specimens; `provenance` is "datasheet" | "measured" |
    "approximated"; `derivation` documents cross-brand/analog approximations and
    their uncertainty. Geometry-free: pure material data.
    """

    name: str
    e_mpa: float            # operating in-plane flexural modulus (ISO 178 X-Y), MPa
    e_z_mpa: float          # through-layer flexural modulus (ISO 178 Z), MPa
    strength_xy_mpa: float  # in-plane bending strength (ISO 178 X-Y), dry, MPa
    strength_z_mpa: float   # through-layer bending strength (ISO 178 Z), dry, MPa
    density_kg_m3: float
    source: str
    accessed: str
    nu: float = 0.35               # short-CF thermoplastic Poisson ratio (flex.POISSON)
    provenance: str = "datasheet"  # "datasheet" | "measured" | "approximated"
    annealed: bool = True          # True = numbers are for annealed specimens
    e_mpa_dry: float | None = None  # dry-state X-Y flexural modulus when e_mpa is conditioned
    # As-printed IN-PLANE strength retention: the fraction of the datasheet X-Y
    # strength a real printed part reaches. NOT derivable from a datasheet — it
    # is a property of the print (nozzle, layer height, temperature, bonding),
    # not of the polymer — so it has to be measured per material AND per
    # process. Defaults to the one value we have measured; a card that has not
    # been coupon-tested inherits it, and the extra uncertainty is carried by
    # the provenance-scaled structural SF rather than smeared in here (see
    # fingen.sizing._design_allowable_mpa: uncertainty is booked ONCE).
    as_printed_retention: float = 0.85
    derivation: str = ""            # note: which numbers are measured vs analog-derived

    @property
    def interlaminar_ratio(self) -> float:
        """Z/XY strength ratio — the through-layer knockdown, DERIVED.

        This used to be a module-level constant in fingen.sizing fitted to
        paht-cf (22/138 = 0.159) and applied to every material. It is 2.3x to
        4.9x too pessimistic for the others — PLA is 0.776, nearly isotropic —
        and it duplicated data the card already carried. Read it from the card.
        """
        return self.strength_z_mpa / max(self.strength_xy_mpa, 1e-9)


# Access date for the datasheet cards below (TDS PDFs re-pulled and
# text-extracted from the official servers on this date; see docs/SOURCES.md).
_ACCESSED = "2026-07-26"

_FIBERON_URL = "https://3d.nice-cdn.com/upload/file/TDS_FIBERON-PET-CF17_V1.0_EN.pdf"
_BAMBU_PETCF_URL = ("https://wiki.bambulab.com/filament-acc/petcf-ppacf/"
                    "07689de83afd4cc480f136c7697e6de3.pdf")
_BAMBU_PAHTCF_URL = ("https://wiki.bambulab.com/filament-acc/asacf-pahtcf/"
                     "65f1b18a6d6142d794a1a6a00f1496ef.pdf")
_ELEGOO_PAHTCF_URL = "https://us.elegoo.com/products/paht-cf-filament-1-75mm-colored-1kg"
# PA12-CF conditioned/wet in-plane modulus retention. PA12 absorbs <1% and holds
# stiffness with humidity [3DXPA] (contrast PA6-CF, ~24% dry→conditioned loss);
# a submerged fin still runs wetter than 50% RH and Elegoo's exact grade is
# unproven, so a conservative 15% derate (retention 0.85) is the central
# estimate, honest band ~10-20%. Test G on the actual filament is decisive.
_PA12_WET_RETENTION = 0.85
_PLA_URL = ("https://store.bblcdn.com/s1/default/"
            "58b85d0f3db94878854a28fdb8a0006e/Bambu_PLA_Basic_Technical_Data_Sheet.pdf")

# PRIMARY pet-cf: the user's actual filament. Polymaker Fiberon PET-CF17 TDS
# V1.0 (ISO 178 bending, ISO 527 tensile, ISO 1183 density). ALL mechanical
# values are for specimens annealed 120 °C / 10 h (stated on the TDS).
# Product-relevant: equilibrium water absorption ≈0.53% at 70% RH, Tg 79.3 °C,
# HDT 105 °C @1.8 MPa — low uptake makes it near-indifferent to humid/seawater
# service, the reason it beats plain PET for a fin. (Seawater soak is Test G.)
_FIBERON_PET_CF17 = MaterialCard(
    name="fiberon-pet-cf17",
    e_mpa=4744.4, e_z_mpa=2768.2,               # ISO 178 bending modulus X-Y / Z
    strength_xy_mpa=109.3, strength_z_mpa=43.4,  # ISO 178 bending strength X-Y / Z
    density_kg_m3=1340.0,                        # ISO 1183, 1.34 g/cm³ at 23 °C
    source=("Polymaker Fiberon PET-CF17 TDS V1.0 [FibPET26], specimens "
            f"annealed 120 °C/10 h; {_FIBERON_URL}"),
    accessed=_ACCESSED,
)

# Secondary pet-cf option, kept for filament comparison. Bambu Lab PET-CF TDS
# V3.0 (specimens annealed/dried 80 °C/12 h).
_BAMBU_PET_CF = MaterialCard(
    name="bambu-pet-cf",
    e_mpa=5320.0, e_z_mpa=2210.0,
    strength_xy_mpa=131.0, strength_z_mpa=49.0,
    density_kg_m3=1290.0,                        # ISO 1183, 1.29 g/cm³
    source=("Bambu Lab PET-CF TDS V3.0 [PETCF], specimens annealed 80 °C/12 h; "
            f"{_BAMBU_PETCF_URL}"),
    accessed=_ACCESSED,
)

# PRIMARY paht-cf: the user's actual filament, Elegoo PAHT-CF (PA12-CF).
# APPROXIMATED card — Elegoo publishes only a few X-Y numbers and no thorough
# TDS, so structural gaps are filled from the Bambu PAHT-CF analog (both are
# PA12+CF). e_mpa is the CONDITIONED/wet operating modulus (Elegoo dry X-Y
# flexural 5089 MPa × _PA12_WET_RETENTION); e_mpa_dry keeps the Elegoo dry
# value. Strengths are DRY-reported (sizing applies the knockdowns).
_ELEGOO_PAHT_CF = MaterialCard(
    name="paht-cf",
    e_mpa=round(5089.0 * _PA12_WET_RETENTION, 1),  # ≈4325.7 MPa, conditioned/wet
    e_z_mpa=2190.0,          # DRY, analog: Elegoo X-Y 5089 × Bambu Z/XY (1820/4230)
    strength_xy_mpa=138.0,   # Elegoo flexural strength X-Y (dry)
    strength_z_mpa=22.0,     # MEASURED ratio: 138 × 0.156 (4x4 coupon, see below)
    density_kg_m3=1060.0,    # analog: PA12+CF, Bambu PAHT-CF 1.06 g/cm³ (Elegoo unstated)
    source=("Elegoo PAHT-CF (PA12-CF) [ELPAHT26], structural gaps from the Bambu "
            f"PAHT-CF analog [PAHTCF]; {_ELEGOO_PAHTCF_URL}"),
    accessed=_ACCESSED,
    provenance="approximated",
    annealed=False,          # Elegoo states no anneal schedule
    e_mpa_dry=5089.0,        # Elegoo published X-Y flexural modulus (dry)
    derivation=(
        "ELEGOO's own (X-Y, dry): flexural modulus 5089 MPa (-> e_mpa_dry), "
        "flexural strength 138 MPa (-> strength_xy_mpa), tensile strength 87 "
        "MPa, elongation 14.2%, base PA12-CF [ELPAHT26]. ANALOG-DERIVED from "
        "Bambu PAHT-CF [PAHTCF] (same PA12+CF class): e_z_mpa via the Z/XY "
        "modulus ratio 1820/4230, density 1.06 g/cm3. strength_z is NO LONGER "
        "that analogy: as-printed 4x4 mm coupons broke at 121.8 kgf X-Y vs "
        "19.0 kgf Z = 74.7 / 11.7 MPa tensile, a Z/XY of 0.156 against the "
        "analogy's 0.49 — the cross-brand guess was 3x optimistic, so "
        "strength_z = 138 x 0.156 = 22 MPa. The same coupons put as-printed "
        "X-Y at 0.86 of the published tensile, which is why the design "
        "knockdown is now orientation-split (sizing.PRINT_KNOCKDOWN_*). "
        "CONDITIONED: e_mpa = 5089 x 0.85 (PA12-CF wet retention [3DXPA]) = "
        "4326 MPa, the in-service default. UNCERTAINTY: cross-brand analogy is "
        "good to about +-20-30% on modulus and the wet retention to about +-10 "
        "points; Test G (seawater soak, docs/BENCH-PROTOCOL.md) is decision-"
        "grade and replaces the conditioned estimate with a measurement."),
)

# Secondary paht-cf option / the analog behind the Elegoo approximation. Bambu
# Lab PAHT-CF TDS V3.0 — tougher, wet-stable PA12+CF, thorough X-Y/Z data.
_BAMBU_PAHT_CF = MaterialCard(
    name="bambu-paht-cf",
    e_mpa=4230.0, e_z_mpa=1820.0,
    strength_xy_mpa=125.0, strength_z_mpa=61.0,
    density_kg_m3=1060.0,                        # ISO 1183, 1.06 g/cm³
    source=("Bambu Lab PAHT-CF TDS V3.0 [PAHTCF], specimens annealed 80 °C/12 h; "
            f"{_BAMBU_PAHTCF_URL}"),
    accessed=_ACCESSED,
)

# Generic reference resin — NOT a seawater candidate (cheap, brittle, low HDT),
# kept as the low-stiffness anchor for card wiring and comparisons. Bambu Lab
# PLA Basic TDS V3.0.
_PLA = MaterialCard(
    name="pla",
    e_mpa=2750.0, e_z_mpa=2370.0,
    strength_xy_mpa=76.0, strength_z_mpa=59.0,
    density_kg_m3=1240.0,                        # ISO 1183, 1.24 g/cm³
    source=f"Bambu Lab PLA Basic TDS V3.0 [PLA]; {_PLA_URL}",
    accessed=_ACCESSED,
)

# Registry: each card under its own name, plus the short alias the sizing/flex
# layer addresses (material="pet-cf"). The alias points at the CURRENT primary
# card for that slot; a measured card registered under the alias shadows it.
CARDS: dict[str, MaterialCard] = {
    c.name: c for c in (
        _FIBERON_PET_CF17, _BAMBU_PET_CF, _ELEGOO_PAHT_CF, _BAMBU_PAHT_CF, _PLA)
}
CARDS["pet-cf"] = _FIBERON_PET_CF17  # user's filament is the pet-cf default
# ("paht-cf" is already _ELEGOO_PAHT_CF via its own name; "bambu-paht-cf" is the
#  analog. Both pet-cf and paht-cf slots hold the user's actual filaments.)


def get_card(name: str) -> MaterialCard:
    """The material card for `name`, or a clear error listing what's available.

    Reads the live registry, so a measured card installed with register_card()
    shadows its datasheet namesake here.
    """
    try:
        return CARDS[name]
    except KeyError:
        raise KeyError(
            f"no material card {name!r}; available: {sorted(CARDS)}"
        ) from None


def register_card(card: MaterialCard) -> MaterialCard:
    """Install `card` in the registry under its own name, shadowing any
    existing (e.g. datasheet) card for that material. Returns the card."""
    CARDS[card.name] = card
    return card


def load_measured_card(json_path: str | Path, *,
                       annealed: bool | None = None,
                       accessed: str | None = None) -> MaterialCard:
    """Build a measured MaterialCard from a bench_intake material-card JSON.

    scripts/bench_intake.py (docs/BENCH-PROTOCOL.md) writes a card with, among
    other keys, {"material", "E_eff_mpa", "provenance": {"source_csv", ...}}.
    The rig measures STIFFNESS, not strength, so the inverted `E_eff_mpa`
    replaces `e_mpa` while the through-layer modulus, both bending strengths,
    density and Poisson ratio are inherited from the datasheet card for the
    same resin (until Test E supplies a measured strength). Provenance is
    stamped "measured", and the card keeps the bench card's `material` name so
    it shadows the slot the sizing/flex layer reads (e.g. "pet-cf").

    `annealed` records the state of the tested blade (the bench card does not
    yet carry it): pass True/False explicitly, else it falls back to an
    "annealed" key in the JSON, else it inherits the datasheet card's flag —
    so record it honestly, since an as-printed blade reads lower than the
    annealed datasheet.

    The card is NOT auto-registered — call `register_card()` on the result to
    let it shadow the datasheet entry.
    """
    data = json.loads(Path(json_path).read_text())
    name = data.get("material")
    if not name:
        raise ValueError(f"{json_path}: bench card has no 'material' field")
    e_eff = data.get("E_eff_mpa")
    if e_eff is None:
        raise ValueError(
            f"{json_path}: bench card has no E_eff_mpa (only K was measured) — "
            "re-run bench_intake.py with --fin-json so the tier-0 inversion "
            "fills in the effective modulus")
    base = CARDS.get(name)
    if base is None:
        raise KeyError(
            f"measured card resin {name!r} has no datasheet card to inherit "
            f"strength/density from; available: {sorted(CARDS)}")
    prov = data.get("provenance") or {}
    origin = prov.get("source_csv") or data.get("fin_id") or str(json_path)
    if annealed is None:
        annealed = data.get("annealed", base.annealed)
    # A measurement supersedes the datasheet/analog estimates: e_eff is the real
    # (conditioned-as-tested) modulus, so drop the dry-split and the approximation
    # note inherited from the base card.
    return replace(
        base,
        name=name,
        e_mpa=float(e_eff),
        source=f"bench: {origin}",
        accessed=accessed or date.today().isoformat(),
        provenance="measured",
        annealed=bool(annealed),
        e_mpa_dry=None,
        derivation="",
    )
