# Web-Shooter

A wrist-worn device that sprays Beacon Fabri-Tac fabric adhesive to produce a
Spider-Man-style strand. Visual effect only — **it bears no load**.

> **Status: unbuilt, untested, and currently failing its own independent audit.**
> This is a design-in-progress published for reference. Nothing here has been printed,
> assembled, or fired. See [Known failures](#known-failures-mk4) before doing anything else.

## Safety — read before building

This device stores mechanical energy in a compressed spring and uses it to eject a jet of
acetone-thinned contact adhesive at several metres per second.

- **Acetone and Fabri-Tac vapour are flammable.** The mixture is a skin, eye and
  respiratory hazard, and Fabri-Tac bonds to skin. Mix and fire only with strong
  ventilation, away from all ignition sources, wearing sealed goggles, solvent-rated
  (butyl/nitrile) gloves and an organic-vapour respirator.
- **There is no mechanical safety and no firmware in this repo.** The Mk4 sear is
  self-holding; the only thing between the cocked spring and a discharge is a hobby servo
  horn. A servo power-up twitch, brownout, reset, or loose lead can fire it. Any build
  must add a physical sear block or trigger disconnect that is removed by hand, and must
  keep the battery disconnected whenever the spring is cocked and not about to be fired.
  A naively written firmware will fire on boot.
- **Never cock, load, or fire the device while it is on an arm.** Cock with two hands,
  off the arm, muzzle pointed at a disposable backstop. Peak cocking force is ~16 N on a
  4 mm printed tab that sits in the carriage path: if your thumb slips before the sear
  engages, the carriage snaps forward onto your fingers.
- Never point it at a person, animal, face, flame, vehicle or property. Store it uncocked
  (PETG creeps under sustained load and is **not** acetone-resistant; the sear is a
  life-safety part and its layer orientation matters).
- The LiPo has no retention in Mk4. Do not strap an unretained pouch cell against a
  moving carriage and a solvent reservoir; relocate or pocket it.

**No warranty.** This is an experimental personal project published for reference only.
It is not a product, has never been built or bench-tested, and has not been reviewed for
safety by anyone qualified. It is provided "AS IS", without warranty of any kind (see
`LICENSE`). You build, modify, or operate it entirely at your own risk, and the author
accepts no liability for any injury, damage, or loss.

## Layout

Everything lives in `mk2/` (the folder name is historical; it holds Mk3 and Mk4).

| File | What it is |
|---|---|
| `webshooter_mk4.py` | **Current.** Parameterized CadQuery model; exports STEP/STL + `mk4_params.json` |
| `webshooter_mk2.py` | Previous Mk3 model (filename retained from the rebuild target) |
| `verify_independent.py` | Audit harness not written by the geometry author; reprobes the exported solids |
| `mk4_indep.json`, `indep_quick.json` | Independent-audit output for Mk4 / Mk3 — including the failures |
| `DESIGN_NOTES.md` | Design decisions, force and velocity arithmetic, unverified values |
| `BOM_DELTA.md` | What must be bought |
| `*_BRIEF.md` | Design/rebuild briefs written for and with AI coding agents during development; kept for provenance |
| `bl.py`, `build_mk4_viz.py`, `build_blender_viz.py` | Blender scene builder + headless CLI |
| `printed_parts/`, `assembly_stl/`, `mk4_*.stl/step` | Generated geometry |

## Mk4 (current)

Open frame: a curved baseplate strapped to the forearm with components mounted exposed
on top, and a muzzle extending over the back of the hand. A 5 mL syringe acts as
reservoir, pump and seal in one part. A hand-cocked spring is held by a self-holding sear
and released by a hobby servo. Mk4 cut the Luer fitting, the cocking lever and its pins.

**Targets:** ≤25 mm wrist profile · ≥1.5 mL per shot · ≤6 printed parts · ≥1.5 m throw.

### Known failures (Mk4)

`verify_independent.py` on the committed Mk4 geometry reports these; none are fixed yet:

- `baseplate <> switch_pod` overlap 255.95 mm³; `baseplate <> sear` 150.00 mm³;
  `baseplate <> outlet_adapter` 85.88 mm³; `baseplate <> carriage` 18.90 mm³
- carriage → baseplate: 18.90 mm³ interference **at 0.00 mm of travel** (it jams before it moves)
- unsupported islands on baseplate (50.7 mm²), carriage (21.5), outlet_adapter (50.8), switch_pod (60.0)
- with the real 8 ga needle (ID 3.429 mm) the shot needs 0.1705 J but the spring stores 0.1335 J
  — **the design does not have the energy to fire as specified**

Unmodelled and known-doubtful: syringe seal breakaway friction (can consume the whole spring
force), a linear spring that falls below the 5.6 N plunger force at ~11 of 16 mm of stroke
(only ~1.3 mL of 2 mL leaves at pressure), and a 0.5 Pa·s viscosity guess for thinned,
non-Newtonian adhesive. All range figures are indicative only.

## Reproduce

```bash
pip install cadquery                              # Python 3.12 required
python mk2/webshooter_mk4.py                      # writes STEP/STL + mk4_params.json
python mk2/verify_independent.py --quick          # independent audit (defaults to Mk4)
python mk2/verify_independent.py --model webshooter_mk2   # audit the Mk3 model
blender -b --python mk2/build_mk4_viz.py          # Blender 5.2 scene
```

The verifier exits via `os._exit` because CadQuery/OCCT can segfault at interpreter teardown.

## Design history

Mk1 was an enclosure around a 10 mL fragrance pump. Three independent audits found it
over-packed (96% cabin fill), geometrically broken in three parts, and functionally
doubtful — a 0.1 mL dose cannot form a strand. Scrapped and removed from the tree.

Mk2 replaced it with an open frame and a syringe, hitting the size and volume targets,
but audits found the chosen linear actuator was ~100× too slow: for a positive-displacement
pump, exit velocity is fixed by kinematics alone, and a 210:1 gearbox and a jet are
mutually exclusive. Mk3 replaced the drive with a spring and sear; its self-check passed
while the independent harness found jams and overlaps. Mk4 is the response, and still fails.

**Lessons worth keeping:** compute exit velocity and range, not just shot volume; size the
spring on force at end of stroke, not stored energy; do not trust a model's own self-check.

## Requirements

- Python 3.12 + CadQuery 2.8 (`pip install cadquery`)
- Blender 5.2 for visualization (`bl.py` looks for it at the default Windows install path;
  edit `DEFAULT_BLENDER` otherwise)
- CQ-editor for interactive viewing (`pip install cq-editor`), optional

Print in PETG for load-bearing parts (creep resistance; it is not acetone-proof — keep the
solvent path off the printed parts); PLA is fine for fit-test coupons only.

## `bl.py` — Blender scene CLI

Drives a `.blend` headlessly (defaults to the Mk3 visualization; pass `--blend
mk2/webshooter_mk4.blend` for Mk4). Note that `show/hide/isolate/reset` save the file.

```bash
python mk2/bl.py stats                  # counts, bounds, frame range, markers, cameras
python mk2/bl.py ls                     # every object: collection, dims, location
python mk2/bl.py tree                   # collection hierarchy
python mk2/bl.py info sear              # full dump for matching objects
python mk2/bl.py measure syringe sear   # min vertex gap + bbox gap + centre distance
python mk2/bl.py isolate baseplate      # show only these
python mk2/bl.py render --cam hero --frame 46 --res 1920x1280
python mk2/bl.py shot --az 135 --el 20  # render from an arbitrary angle
python mk2/bl.py turntable --frames 24  # orbit sequence
python mk2/bl.py export --fmt glb --only printed
```

Names match loosely: case-insensitive, punctuation-insensitive substrings, and
collection names work anywhere an object name does. `--dry` prints the generated
Blender script instead of running it.

## License

MIT — see `LICENSE`. The disclaimer above applies to the hardware design as well as the code.
