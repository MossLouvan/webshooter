# Web-Shooter

A wrist-worn device that sprays Beacon Fabri-Tac fabric adhesive to produce a
Spider-Man-style strand. Visual effect only — **it bears no load**.

## Layout

| Path | What it is |
|---|---|
| `mk2/` | **Current work.** Mk2/Mk3 open-frame design in CadQuery. |
| `archive_mk1/` | Superseded Mk1 enclosure design, kept for history. |

## Mk3 (current)

Open frame: a curved baseplate strapped to the forearm with components mounted
exposed on top, and barrels extending over the back of the hand. A syringe acts as
reservoir, pump and seal in one part. A hand-cocked spring is released by a sear
tripped by a hobby servo.

**Targets:** ≤25 mm wrist profile · ≥1.5 mL per shot · ≤6 printed parts · ≥1.5 m throw.

Key files in `mk2/`:
- `webshooter_mk2.py` — parameterized CadQuery model, exports STEP/STL + assembly
- `DESIGN_NOTES.md` — design decisions, force and velocity arithmetic, unverified values
- `BOM_DELTA.md` — what must be bought
- `MK3_REBUILD_BRIEF.md` — the audit findings driving the current revision
- `assembly_stl/` — parts and purchased-component mockups at assembly positions

## Design history

Mk1 was an enclosure around a 10 mL fragrance pump. Three independent audits found it
over-packed (96% cabin fill), geometrically broken in three parts, and functionally
doubtful — a 0.1 mL dose cannot form a strand. Scrapped.

Mk2 replaced it with an open frame and a syringe, hitting the size and volume targets,
but audits found the chosen linear actuator was ~100× too slow: for a positive-displacement
pump, exit velocity is fixed by kinematics alone, and a 210:1 gearbox and a jet are
mutually exclusive. Mk3 replaces the drive with a spring and sear.

**Lesson worth keeping:** compute exit velocity and range, not just shot volume.

## Requirements

- Python 3.12 + CadQuery 2.8 (`pip install cadquery`)
- Blender 5.2 for visualization
- CQ-editor for interactive viewing (`pip install cq-editor`)

Print in PETG for load-bearing parts (acetone resistance and creep); PLA is fine for
fit-test coupons only.
