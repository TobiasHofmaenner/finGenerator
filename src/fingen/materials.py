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
Bambu PAHT-CF analog [PAHTCF], which is kept as `"bambu-paht-cf"`). `"ppa-cf"`
is the user's Siraya Tech Fibreheart PPA-CF **Core** ([SirPPACore26]), also
APPROXIMATED — a 25% carbon-fibre core-shell filament and the stiffest card
here (8700 MPa dry X-Y bending); the plain 15% grade is kept as
`"siraya-ppa-cf"` for comparison, and note that BOTH are sold under the
"PAHT-CF" trade name while being PPA-based rather than the PA12-CF that name
denotes on the `"paht-cf"` cards. `"pla"` is Bambu PLA Basic ([PLA]), a
low-stiffness reference only. The DRY X-Y bending
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
    # Conditioned (wet, in-service) retention of the DRY datasheet strength for a
    # submerged part. 1.0 = the resin is indifferent to water. This was a
    # module-level dict in fingen.sizing keyed by material NAME, which silently
    # returned 1.0 — no derate at all — for any name not spelled in it, so a new
    # polyamide card or a registry ALIAS of an existing one was designed as if
    # water did not exist. It is a property of the polymer; it belongs here with
    # the other per-material factors. Applied to strength by
    # sizing._design_allowable_mpa; the matching stiffness conditioning is baked
    # into e_mpa (with the dry value kept in e_mpa_dry).
    wet_retention: float = 1.0
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
_SIRAYA_PPACF_URL = ("https://sirayatech.myshopify.com/pages/"
                     "siraya-tech-fibreheart-paht-cf-ppa-based-tds")
_SIRAYA_PPACF_CORE_URL = ("https://sirayatech.myshopify.com/pages/"
                          "siraya-tech-fibreheart-ppa-cf-core-tds")
# PPA-CF conditioned/wet retention. The TDS reports 1.37% water absorption
# (ISO 62) — 2.6x the Fiberon PET-CF (0.53%, treated as water-indifferent) and
# above PA12's <1% (retention 0.85 [3DXPA]). The trend puts this resin BELOW
# PA12, so 0.80 is the central estimate, honest band 0.70-0.90. The name "PPA"
# would argue the other way — a true polyphthalamide is semi-aromatic and takes
# up less water than an aliphatic PA — but this TDS's own thermal numbers do not
# describe one: Tm 232 °C and Tg 80 °C against a classic PPA's Tm ~310-325 °C
# and Tg 90-125 °C. The melt point sits between PA6 (220 °C) and PA66 (260 °C),
# so the aliphatic content is high and the plasticization behaviour should be
# read as PA-like, which is what the 1.37% uptake already says. Test G (seawater
# soak, docs/BENCH-PROTOCOL.md) replaces this estimate with a measurement.
_PPA_WET_RETENTION = 0.80
# PPA-CF **Core** conditioned/wet retention. Its TDS reports 1.09% uptake
# (ISO 62) against the 15% grade's 1.37% — but most of that drop is fibre
# dilution, not a drier polymer: carbon does not absorb water, so going 15% ->
# 25% CF removes ~12% of the absorbing phase by itself. MATRIX-NORMALISED the
# two grades are close, 1.09/0.75 = 1.45% against 1.37/0.85 = 1.61%, so the
# resin around the fibres still conditions nearly as wet and PA-like plasticiz-
# ation still applies. Two effects nonetheless push retention slightly ABOVE the
# 15% grade's 0.80: the matrix is a little drier, and with 25% CF a larger share
# of the composite stiffness rides on fibre, which is indifferent to water — the
# same matrix softening moves the composite less. 0.82 is the central estimate,
# honest band 0.72-0.92, still below PA12's 0.85 [3DXPA] because the matrix is
# wetter than PA12's <1%. Test G (seawater soak) replaces it with a measurement.
_PPA_CORE_WET_RETENTION = 0.82

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
    wet_retention=_PA12_WET_RETENTION,   # was sizing._MOISTURE_RETENTION["paht-cf"]
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
    wet_retention=_PA12_WET_RETENTION,   # PA12-CF, same as the Elegoo card
)

# Secondary ppa-cf option: Siraya Tech Fibreheart PPA-CF, 15% carbon fibre — the
# plain grade, kept for filament comparison against the Core the user actually
# runs. Sold as "PAHT-CF" but it is NOT the PA12-CF the paht-cf cards describe,
# so PPA takes its own slot rather than shadowing one — X-Y bending modulus 6800
# MPa against Elegoo's 5089, a different material with a colliding trade name.
#
# UNANNEALED numbers are the card. The TDS reports both states but publishes no
# anneal schedule (no temperature, no time), so the annealed column is not
# reproducible. It is also the worse trade for a fin: annealing buys +8% bending
# modulus (6800 -> 7350) and NOTHING on bending strength (145 both ways), while
# costing 43% of the Charpy impact toughness (11 -> 6.3 kJ/m^2). A fin takes
# impact loads — reef, sand, the other board — and toughness is the property you
# want there. The HDT gain (82.5 -> 119 °C at 1.8 MPa) is irrelevant in water.
_SIRAYA_PPA_CF = MaterialCard(
    name="siraya-ppa-cf",
    e_mpa=round(6800.0 * _PPA_WET_RETENTION, 1),  # =5440.0 MPa, conditioned/wet
    e_z_mpa=2926.0,          # analog: 6800 x Bambu PAHT-CF Z/XY modulus (1820/4230)
    strength_xy_mpa=145.0,   # ISO 178 bending strength X-Y, unannealed (dry)
    strength_z_mpa=22.6,     # 145 x 0.156, the MEASURED process ratio (see below)
    density_kg_m3=1200.0,    # ISO 1183, 1.2 g/cm³
    source=("Siraya Tech Fibreheart PPA-CF TDS [SirPPA26] (ISO 178 bending, "
            "ISO 527 tensile, ISO 1183 density, ISO 62 water uptake), UNANNEALED "
            f"column; Z data and wet conditioning derived; {_SIRAYA_PPACF_URL}"),
    accessed="2026-08-07",
    provenance="approximated",
    annealed=False,          # TDS publishes no anneal schedule; see above
    e_mpa_dry=6800.0,        # ISO 178 X-Y bending modulus, unannealed (dry)
    wet_retention=_PPA_WET_RETENTION,
    derivation=(
        "SIRAYA's own (X-Y, unannealed, dry): bending modulus 6800 MPa (-> "
        "e_mpa_dry), bending strength 145 MPa (-> strength_xy_mpa), tensile "
        "95 MPa, Young's 7800 MPa, elongation 2%, Charpy 11 kJ/m2, density 1.2 "
        "g/cm3, water absorption 1.37%, Tg 80 C, Tm 232 C, HDT/A 82.5 C, 15% "
        "CF, nozzle 280-320 C, bed 70-90 C [SirPPA26]. THE TDS REPORTS NO Z / "
        "INTERLAYER DATA AT ALL, so both through-layer fields are derived. "
        "e_z_mpa: X-Y modulus x the Bambu PAHT-CF Z/XY modulus ratio 1820/4230 "
        "= 0.430, the nearest CF-filled polyamide with full X-Y/Z data "
        "[PAHTCF]; good to about +-20-30%. strength_z_mpa does NOT use that "
        "datasheet ratio (0.488): the user's own 4x4 mm coupons on the same "
        "printer put Elegoo PAHT-CF at Z/XY 0.156 where the cross-brand "
        "datasheet analogy predicted 0.49 — 3x optimistic [ELPAHT-COUPON]. "
        "Interlayer strength is a property of the PROCESS, not the polymer, so "
        "the measured process ratio carries across to another CF-filled "
        "polyamide on that printer far better than a second vendor's lab "
        "specimens: 145 x 0.156 = 22.6 MPa. That may be PESSIMISTIC here, "
        "since PPA extrudes at 280-320 C against PA12's ~260-290 C and hotter "
        "welds bond better; it is also nearly free, because the exporter prints "
        "blades FLAT and the Z allowable only binds on an upright print. "
        "CONDITIONED: e_mpa = 6800 x 0.80 (_PPA_WET_RETENTION, see the constant "
        "for why 0.80 and not PA12's 0.85) = 5440 MPa, the in-service default. "
        "as_printed_retention is the INHERITED 0.85 measured on Elegoo PAHT-CF "
        "coupons, not a measurement of this filament — per sizing's book-the-"
        "uncertainty-once rule an untested card inherits rather than inventing "
        "a lower number, and the residual rides in STRUCTURAL_SF. Test E "
        "(coupons) and Test G (seawater soak) in docs/BENCH-PROTOCOL.md are the "
        "decision-grade replacements for strength_z, as_printed_retention and "
        "the wet conditioning respectively."),
)

# PRIMARY ppa-cf: the user's actual filament, Siraya Tech Fibreheart PPA-CF
# **Core** — 25% carbon fibre, and a CORE-SHELL filament: fibre-loaded core
# inside a pure-resin skin. It is a different material from the plain 15% grade
# above, not a revision of it, so it takes the ppa-cf slot as its own card and
# the 15% one stays for comparison. Every structural number is higher: X-Y
# bending 8700/178 MPa against 6800/145, Young's 9300 against 7800, and — unlike
# the usual stiffness-for-toughness trade — Charpy is UP too, 13.1 against
# 11 kJ/m². At 8700 MPa dry it is the stiffest card in the registry by a wide
# margin (1.8x the Fiberon PET-CF the fin defaults to).
#
# UNANNEALED numbers again, for the same two reasons as the 15% card: the TDS
# publishes no anneal schedule (no temperature, no time), so the annealed column
# is not reproducible; and it is the worse trade for a fin, buying +9.5% bending
# modulus (8700 -> 9510) and +4% bending strength (178 -> 185) for 44% of the
# Charpy impact toughness (13.1 -> 7.3 kJ/m^2). A fin meets reef, sand and the
# other board, so impact toughness is the property to keep. The HDT gain
# (84 -> 126 °C at 1.8 MPa) is irrelevant in water.
_SIRAYA_PPA_CF_CORE = MaterialCard(
    name="siraya-ppa-cf-core",
    e_mpa=round(8700.0 * _PPA_CORE_WET_RETENTION, 1),  # =7134.0 MPa, conditioned/wet
    e_z_mpa=3743.3,          # analog: 8700 x Bambu PAHT-CF Z/XY modulus (1820/4230)
    strength_xy_mpa=178.0,   # ISO 178 bending strength X-Y, unannealed (dry)
    strength_z_mpa=27.8,     # 178 x 0.156, the MEASURED process ratio (see below)
    density_kg_m3=1230.0,    # ISO 1183, 1.23 g/cm³
    source=("Siraya Tech Fibreheart PPA-CF Core TDS [SirPPACore26] (ISO 178 "
            "bending, ASTM D638 tensile, ISO 1183 density, ISO 62 water uptake), "
            f"UNANNEALED column; Z data and wet conditioning derived; "
            f"{_SIRAYA_PPACF_CORE_URL}"),
    accessed="2026-08-17",
    provenance="approximated",
    annealed=False,          # TDS publishes no anneal schedule; see above
    e_mpa_dry=8700.0,        # ISO 178 X-Y bending modulus, unannealed (dry)
    wet_retention=_PPA_CORE_WET_RETENTION,
    derivation=(
        "SIRAYA's own (X-Y, unannealed, dry): bending modulus 8700 MPa (-> "
        "e_mpa_dry), bending strength 178 MPa (-> strength_xy_mpa), tensile at "
        "break 112 MPa, Young's 9300 MPa, elongation 2.25%, Charpy 13.1 kJ/m2, "
        "density 1.23 g/cm3, water absorption 1.09%, Tg 80 C, Tm 239 C, Vicat "
        "238 C, HDT/A 84 C, 25% CF, core-shell, nozzle 280-320 C, bed 80 C "
        "[SirPPACore26]. LIKE THE 15% GRADE, THE TDS REPORTS NO Z / INTERLAYER "
        "PROPERTY AT ALL, so both through-layer fields are derived. e_z_mpa: "
        "X-Y modulus x the Bambu PAHT-CF Z/XY modulus ratio 1820/4230 = 0.430, "
        "the nearest CF-filled polyamide with full X-Y/Z data [PAHTCF]; good to "
        "about +-20-30%, and the core-shell construction adds unquantified "
        "scatter in BOTH directions here (resin-rich weld zones are more "
        "compliant than the filled core, but they weld better). strength_z_mpa "
        "does NOT use that datasheet ratio: the user's own 4x4 mm coupons on "
        "the same printer put Elegoo PAHT-CF at Z/XY 0.156 where the cross-"
        "brand datasheet analogy predicted 0.49 — 3x optimistic [ELPAHT-"
        "COUPON]. Interlayer strength is a property of the PROCESS, so the "
        "measured process ratio carries better than a second vendor's lab "
        "specimens: 178 x 0.156 = 27.8 MPa. That is probably MORE pessimistic "
        "here than on any other card, because the whole point of a core-shell "
        "filament is that the surface meeting the previous layer is UNFILLED "
        "resin, and fibre at the weld interface is exactly what disrupts inter-"
        "road bonding; the hot 280-320 C melt argues the same way. It is left "
        "pessimistic deliberately: the vendor quantifies none of that, raising "
        "an allowable on an unquantified construction claim is the unsafe "
        "direction, and it is nearly free because the exporter prints blades "
        "FLAT — the Z allowable only binds on an upright print. CONDITIONED: "
        "e_mpa = 8700 x 0.82 (_PPA_CORE_WET_RETENTION, see the constant for why "
        "0.82 and not the 15% grade's 0.80) = 7134 MPa, the in-service default. "
        "as_printed_retention is the INHERITED 0.85 measured on Elegoo PAHT-CF "
        "coupons, not a measurement of this filament — per sizing's book-the-"
        "uncertainty-once rule an untested card inherits rather than inventing "
        "a lower number, and the residual rides in STRUCTURAL_SF. Test E "
        "(coupons) and Test G (seawater soak) in docs/BENCH-PROTOCOL.md are the "
        "decision-grade replacements for strength_z, as_printed_retention and "
        "the wet conditioning respectively."),
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
        _FIBERON_PET_CF17, _BAMBU_PET_CF, _ELEGOO_PAHT_CF, _BAMBU_PAHT_CF,
        _SIRAYA_PPA_CF, _SIRAYA_PPA_CF_CORE, _PLA)
}
CARDS["pet-cf"] = _FIBERON_PET_CF17       # user's filament is the pet-cf default
CARDS["ppa-cf"] = _SIRAYA_PPA_CF_CORE     # ...and the Core is the ppa-cf default
# ("paht-cf" is already _ELEGOO_PAHT_CF via its own name; "bambu-paht-cf" is the
#  analog. Both pet-cf and paht-cf slots hold the user's actual filaments.)
# NOTE the Siraya filament is SOLD as "PAHT-CF" but is PPA-based, not the PA12
# the paht-cf slot holds — it is deliberately NOT aliased there.


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
