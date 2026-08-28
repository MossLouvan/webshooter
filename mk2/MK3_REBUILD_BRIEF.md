# Web-Shooter Mk3 — REBUILD BRIEF

**To:** Codex (full access)
**Model:** `mk2/webshooter_mk2.py`
**Status:** three independent audits ran probes against your Mk2. All three returned BROKEN.
The open-frame concept, the zones, the bridge, the syringe-as-reservoir idea and the electronics
stack all survive. **The drive does not.**

---

## 1. THE FATAL FINDING — the drive is ~100× too slow, and it is kinematic

For a positive-displacement pump, exit velocity is fixed by geometry alone:

```
v_exit = v_plunger × (A_plunger / A_orifice) = v_plunger × 98.8   (15.9 mm bore, 1.6 mm orifice)
```

At the L12-210's **no-load 6.5 mm/s** — an unreachable ceiling — `v_exit = 0.64 m/s`, ballistic
range **4 cm**. At the actual operating point it is **0.078 m/s** and the charge falls out of the
barrel. **This cannot be fixed by thinning the fluid, opening the orifice, or buying more force.**
A 210:1 gearbox and a jet are mutually exclusive.

A 3 m throw needs ~5.4 m/s exit → 55 mm/s plunger → **21× the L12's no-load speed at 808 N**. The
whole 2 mL charge must leave in **~180 ms**.

**DESIGN_NOTES never computed an exit velocity or a range. That omission is why Mk2 passed its own
review. Every future revision must compute and report both.**

### Two further inputs that were wrong

**Fabri-Tac's viscosity is published and you used a value 5.3× low.** Beacon's SDS gives
**8,000 cps (8.0 Pa·s)**, 60 wt% volatiles, acetone 65–85 wt%:
https://beaconadhesives.com/cdn/shop/files/BEACON_FabriTac_SDS_2023_657ad5d7-a700-4d92-b5dd-1491e6f14541.pdf
At the true value the L12 needs **70.2 N for 12.6 s** — past its 62 N peak-power point, i.e.
**negative margin**, not the claimed 1.31×.

**The "do not dilute" rule in the Mk2 brief was wrong, and it was mine.** Stringing is *extensional*
elasticity set by polymer molecular weight, not shear viscosity. Thinning 1:1 drops shear viscosity
~16× while preserving filament behaviour, and acetone flash-off re-concentrates the strand in
flight. **Dilution to 1:1 is now permitted and encouraged.**

---

## 2. THE NEW DRIVE — spring + sear

Adopt the impulsive architecture. Sized for 2 mL, 3 mm orifice, 1:1 thinned fluid:

```
~72 kPa (10 psi),  ~14 N plunger force,  ~0.14 J stored
0.5 s shot,  ~0.8 m/s exit,  ~1.5-2 m throw
```

0.14 J is a modest compression spring. **Cock it by hand** through a lever, and fire it with a
**sear tripped by one of the two owned Corona DS239MG servos** — releasing a sear takes a few N·cm,
which is the job that servo is actually good at.

This deletes the Actuonix L12, the Pololu U3V70F6 and the DRV8833. It removes both specialty
vendor orders, saves ~$110, reuses an owned servo, and is the only variant that throws.

**Constraints:**
- Orifice **3 mm** (8–10 ga blunt needle). Force scales 1/r⁴ — this is why the numbers collapse.
- One shot per cock is acceptable. A second shot must be geometrically possible after re-cocking.
- The cocking lever must be operable one-handed, on the arm, and must not require tools.
- Spring energy is small; **do not** design a device that stores enough energy to injure.

If you judge a different impulsive mechanism better (over-centre toggle, elastic band, gas), take
it — but it must deliver ≥2 mL in ≤250 ms and you must show the velocity arithmetic.

---

## 3. MUST-FIX DEFECTS (every one was measured, not inferred)

### Will not print
| # | Where | Defect |
|---|---|---|
| 3.1 | `make_baseplate` L149–258 | **First layer is 35.1 mm² in 2 pieces** — two 0.29 mm strips holding 49 g of PETG. Modeled as a vault, concave face down, crown floating 8.58 mm. **7,841 mm² of down-facing surface below 45°**, including the entire 6,801 mm² skin-contact underside. No orientation fixes it. Make it a shallow chord, split it, or separate the soft interface. |
| 3.2 | `make_baseplate` L227–230 | Boost clip rail is a **floating island**, 771 mm³ attached by a single **13.5 mm²** butt face. Root cause: `add_support` L179–180 clamps `sample_y` into ±27.8, so anything outboard gets a bottom_z as if it sat on the plate edge. **Four of eight board rails and two of four LiPo posts are outboard.** |
| 3.3 | `make_baseplate` L201–205 | Both M3 insert pockets **break out of the +X end face** — Ø5.2 at x=116 needs x≤118.6, plate ends at 118. C-shaped, open pockets; inserts will not retain. |
| 3.4 | `make_bridge` L276–299 | Cross-section from x=10.5 to 29.5 is **4.50 mm² total — two 0.750 × 3.0 mm ligaments.** Strap slot and syringe lane eat the deck from both sides. Both barrel towers hang off this; a 5 N flick ≈ 700 MPa. |
| 3.5 | `make_switch_pod` L341–355 | The strap tunnel is **wider than the part**, so it deletes the floor; the pocket overshoots the top. What remains is a bare 18×18 open ring. No floor, no tunnel, no retention — the switch falls through. Also floats 9 mm from the hand, touching nothing. |

### Prints but will not work
| # | Where | Defect |
|---|---|---|
| 3.6 | stroke | **Jams at exactly 5.0 mm.** Yoke sweeps into the TP4056 clip rail (x=76) and the +Y syringe guide (x=80), and through the TP4056 itself: at 10 mm, 18.4 mm³ into the baseplate and **49.8 mm³ into the module.** Real shot = **0.99 mL**, half the requirement. `verify_model` only ever checked the retracted pose. |
| 3.7 | actuator mount | **The actuator is fastened to nothing.** Two 2 mm side fins, 0.45 mm clear, floating 3.2 mm above the shell, no rear abutment, no fastener. Swept 20 mm rearward with zero contact. The primary load path does not close. |
| 3.8 | `make_pusher_yoke` L324–338 | 3 × 6 mm web spanning a 17 mm offset → **σ ≈ 89 MPa** vs ~50 MPa PETG. ~2× over. Its only constraints are a pivot pin and a flat unguided face; it will rotate and cam off. No anti-rotation, no guide. |
| 3.9 | fluid path | **Does not connect.** Luer at (177.3, 0, 20.85); live barrel inlet at (178.0, **−6**, 21.6) — 6.09 mm off-axis. **0.2 mm ahead of the Luer is the blank flank of the barrel tower** — the syringe outlet is aimed at a solid wall. The `ptfe_line_owned` mockup sits 25–27 mm from both and was placed to pass the interference check. |
| 3.10 | syringe restraint | No axial reaction feature. Located by 2 mm side fins with 0.5 mm clearance; the finger flange is **not in the mockup at all**. First forward contact is the Luer tip crashing into the tower. The EPDM retainer claimed in the notes has no groove or notch on either side. |
| 3.11 | zero-clearance | Interference = 0.0 mm³ is hiding **tangency**: baseplate↔LiPo **0.050 mm** (notes say never clamp the pouch), baseplate↔switch **0.000**, baseplate↔actuator **0.000**, baseplate↔boost **0.000**. No board is captive — every one is a slot with no floor and nothing above. |
| 3.12 | bridge joint | Designed **0.30 mm air gap** between pad and bridge; two M3s clamping across a gap rock rather than clamp. 78 mm bridge, 6 mm overlap, barrels at the tip, through the 3.4 ligaments. |

### Wrong numbers / hygiene
- **Epsilon lifts** `+0.06`, `+0.01`, `+0.001` (L258, L321, L338) exist only to satisfy `z_min > -1e-6`
  and break tangency so volumes read 0.0. **Delete them and fix the checks instead.**
- `BOOST_SIZE` is 32 mm; the real U3V70F6 is **40.6 mm** — the true envelope collides 416 mm³ with the
  XIAO. The zero-interference result depended on an undersized proxy. (Moot if the boost is deleted.)
- `BARREL_OD = 2.4` is not a 14 ga needle (**2.11 mm**); the hub won't pass the 2.9 bore; a 1" needle
  leaves 25.4 mm where 26 is needed.
- Duplicated coordinate literals between `clip_specs` and `make_mockups`: (61,−28.5), (94,−31),
  (3,−27), (76,11.5), (56,28). `BARREL_GLOBAL_START_X = 178.0` silently encodes a sum of three other
  constants. `BRIDGE_FASTENER_X = 116` and the pad at `FOREARM_PLATE_LENGTH − 12.0` drift apart —
  that drift already produced 3.3.
- Docs vs geometry: barrel clearance is 0.5 mm not 0.25; the print gap is 0.30 not 0.35; foam is
  0.715 mm not 0.8 and non-uniform; "perforated towers" are solid blocks; "two forearm slot pairs"
  is a one-element loop.

---

## 4. THE VERIFICATION HARNESS MUST CHANGE

Mk2's suite passed all five Rank-1 defects. Rebuild it to include:

1. **Stroke sweep**, not one pose — check interference at every 0.5 mm through full travel.
2. **Minimum-gap check** as well as interference. Tangency (0.000 mm) must FAIL, not pass. Assert a
   real clearance for every non-contact pair and an explicit, justified contact list for the rest.
3. `abs(z_min) < tol`, not `z_min > -tol`.
4. **Connectivity / thin-feature check** — solid count cannot see a 13.5 mm² butt joint or a 0.75 mm
   ligament. Section each part and flag any cross-section under ~2 mm² or any ligament under 1.2 mm.
5. **First-layer footprint** check with a minimum area threshold.
6. **Overhang-angle** check on real sampled normals, reporting total area below 45°.
7. **Exit velocity and ballistic range** computed and printed, with the shot time.
8. Assert every mockup uses a **real, sourced** envelope, and print the source for each.

---

## 5. DELIVER

Same folder. Repaired model + assembly + `assembly_stl/` **including mockups** (Mk2 exported only
the 4 printed parts, so nothing could be rendered). Updated `DESIGN_NOTES.md` with the velocity
arithmetic front and centre. Updated `BOM_DELTA.md`.

**The cart has already been updated** — the builder now has, or is buying: 10 mL Luer-lock syringes
(30-pack), an 8/10/12/14 ga blunt needle assortment, a compression spring assortment, PETG and PLA
filament, 1" hook-and-loop strapping, closed-cell neoprene foam, and a multimeter. He already owns
the XIAO, TP4056, LiPo, both DS239MG servos, MT3608 boosts, tactile switches, wire, JST-PH, M3
screws, M3 heat-set inserts (5.0 × 4.0), EPDM O-rings, PTFE tube, Fabri-Tac and acetone.
**Design to that inventory.** If you need something else, it goes in BOM_DELTA with a reason.

Targets unchanged: **≤25 mm wrist profile, ≥1.5 mL per shot, ≤6 printed parts** — plus the new one:
**≥1.5 m throw, which means ≥2 mL in ≤250 ms.**

Three auditors will run again and will keep running until they have no substantive findings.
Work autonomously; do not stop to ask questions.
