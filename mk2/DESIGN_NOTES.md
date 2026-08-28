# Web-Shooter Mk3 design notes

## Exit velocity and range — governing calculation

Mk3 uses a hand-cocked compression spring, a positive sear, and an owned Corona DS239MG servo only to release the sear. The Actuonix L12, Pololu U3V70F6 and DRV8833 are deleted.

For any positive-displacement syringe, force and viscosity do not set the kinematic ceiling. Plunger speed and area ratio do:

```text
10 mL syringe bore               d_p = 15.9 mm
plunger area                     A_p = pi d_p^2 / 4 = 198.556 mm2
3.0 mm effective outlet area     A_o = pi (3.0)^2 / 4 = 7.069 mm2
area ratio                       A_p/A_o = 28.080

2.000 mL stroke                  x = 2000 / 198.556 = 10.073 mm
selected shot time               t = 0.069 s
mean plunger speed               v_p = x/t = 0.14599 m/s
exit velocity                    v_exit = v_p(A_p/A_o) = 4.101 m/s
ideal level 45 degree range      R = v_exit^2/g = 1.715 m
```

The 69 ms shot is deliberate. The rebuild brief's illustrative 0.5 s shot would give only 0.566 m/s and an ideal ballistic range of 0.033 m. Even the final 250 ms limit gives only 1.13 m/s and 0.13 m ideal range. Therefore the explicit **>=1.5 m ballistic target** governs and requires no more than about 74 ms for 2 mL through a 3 mm outlet. Mk3 carries 14.3% ideal-range margin and 181 ms time margin to the hard limits.

The range value is the drag-free 45 degree upper bound, not a promise for adhesive in air. Real strand range must be measured outdoors into a safe backstop. The calculation is printed on every generator run and stored in `verification_report.json` so a slow drive can never pass silently again.

## Fluid and spring sizing

Beacon's Fabri-Tac SDS publishes 8,000 cP (8.0 Pa·s) for the neat adhesive. Mk3 uses the permitted **1:1 Fabri-Tac/acetone starting mixture**. The brief's measured guidance is that this reduces shear viscosity about 16x, to roughly 0.5 Pa·s, while polymer extensional elasticity preserves stringing and acetone flash-off reconcentrates the strand.

The source spring is selected from the owned/buying compression-spring assortment by measurement, not by color or appearance:

```text
maximum OD                     10.0 mm
free length                    39.7 mm
spring rate                    1.94 N/mm
fired installed length         35.6 mm
cocked installed length        25.53 mm
fired preload                  7.95 N
cocked force                   27.50 N
releasable energy              0.179 J
lever mechanical advantage     2.06:1
maximum ideal hand force       13.35 N
```

The releasable energy is below the verifier's 0.25 J safety ceiling. It is enough for the short, wide 8 ga/Luer path only after 1:1 thinning; it is not permission to install a stiffer spring. Bench-select the spring with the multimeter-sized scale/force fixture described below, then confirm 2 mL discharge in <=69 ms with high-frame-rate video. If the measured shot is slower, reduce restriction and seal friction before changing spring energy.

The live nozzle mockup uses the real nominal 8 ga OD of 4.19 mm and a conservative 3.0 mm effective outlet. The capped upper nozzle is visual symmetry only. The syringe Luer, live hub, metal nozzle, and both bridge bores share the named axis `(y=-6.0, z=12.5)`; the verification report asserts 0.000 mm axis and axial connection error.

## Mechanical architecture

Six printed parts are generated:

1. `baseplate` — flat-printing 2.8 mm shallow chord with a continuous perimeter, broad device floors, two forearm strap pairs, spring reaction wall, 24 mm-wide carriage way, open electronics anchors, syringe cradle, and bridge bosses.
2. `barrel_bridge` — continuous 32 mm deck with a 74 mm open syringe/Luer lane, 60 mm rear joint wing, outboard palm strap slots, forward syringe guide, and two bored barrel towers.
3. `spring_carriage` — broad anti-rotation tappet guided on both sides, with spring seat, full plunger pad, closed cocking-pin lug, and sear shoulder.
4. `cocking_lever` — one-hand lever with a 55 mm hand arm and closed M3 drive eye. Its deployed arc retracts the carriage through the full 10.073 mm stroke; the sear holds the load while the lever returns to the stowed position.
5. `servo_sear` — M3-pivoted, thickened around the pivot. The spring load closes into the base boss; the DS239MG horn only trips the unloaded tail.
6. `palm_switch_pod` — 2 mm floor under the owned 12 mm tactile switch, two bounded 26 mm strap slots, and lead-retention holes. It is held by the palm strap rather than floating from the hand.

The baseplate prints flat on its 7,435.6 mm² first layer. It is not a concave shell. Closed-cell neoprene supplies the conformal skin interface. The bridge joint has direct boss-to-deck contact at z=6.2 mm and two M3 heat-set inserts centered at x=112 mm, 6 mm inboard of the base end; no insert pocket breaks out and there is no clamped air gap.

The bridge lane leaves two 6.75 x 3.0 mm continuous side rails through the syringe zone: 40.5 mm² total section before the wider wings and tower roots. This replaces Mk2's two 0.75 mm ligaments. The rear and forward syringe guides have 0.60 mm radial clearance and explicit EPDM retainer geometry. A low rear flange stop reacts the syringe body below the elevated carriage sweep. The complete finger flange is present in the syringe mockup.

The electronics stack is now only the owned 1S LiPo, XIAO ESP32C3, TP4056/DW01 charger, DS239MG servo, hard switch, and wiring. The pouch has a 0.60 mm floor gap, low corner keepers, and no top clamp. Each board rests 0.60 mm above a real floor and is held under an EPDM U-band in broad grooved anchors; USB ends stay open.

## Verification harness

`python webshooter_mk2.py` regenerates the part STEP/STL files, full assembly STEP, every assembly STL mockup, and `verification_report.json`. A passing run performs all of the following:

- prints exit velocity, ideal 45 degree ballistic range, volume, and shot time;
- checks exactly 2.000 mL, <=69 ms, >=1.5 m ideal range, <=0.25 J spring release energy, <=6 printed parts, and <=25 mm wrist profile;
- sweeps the carriage every 0.5 mm through 10.0 mm and at the exact 10.073 mm endpoint;
- checks both intersection volume and true minimum distance for every unordered assembly pair;
- rejects tangency for non-contact pairs and documents every allowed functional contact;
- requires `abs(z_min) < 0.0001 mm` in the real print orientation—there are no epsilon lifts;
- computes first-layer footprint from a real 0.20 mm slab;
- sections every part along X, Y, and Z at nine stations and rejects sampled areas below 2 mm² or sampled ligaments below 1.2 mm;
- tessellates each part, samples actual triangle normals, and reports down-facing area below 45 degrees above the build layer;
- checks straight fluid-path connectivity and tower-bore alignment;
- asserts a named source and envelope for every assembly mockup.

Latest clean audit values are written to the JSON rather than copied as untracked claims. The generated model has 6 valid single-solid parts, a 24.3 mm wrist-zone profile, a 0.400 mm worst-case swept static gap, and zero failures **from its own self-check**. The independent harness (`verify_independent.py --model webshooter_mk2`, output in `indep_quick.json`) disagrees and reports jams and overlaps; that disagreement is what drove Mk4, which still has open failures — see the README.

## Assembly and operation

1. Print the base, bridge, carriage, lever, sear, and switch pod in PETG using their exported local orientations. Do not rotate the base onto its old curved underside.
2. Heat-set the two bridge inserts; install the bridge with direct face contact. Confirm the live Luer/nozzle axis by sight before fitting adhesive.
3. Select and measure the spring. Reject any spring above 10 mm OD, 2.0 N/mm measured rate, 28 N cocked force, or 0.20 J measured release energy.
4. Fit the carriage between the two open rails, install the M3 cocking and pivot pins, and verify the carriage moves the full 10.073 mm by hand with the spring removed.
5. Fit the syringe under the EPDM guide retainer with its finger flange behind the low axial stop. The syringe must lift out after the retainer is released, allowing a second fill/shot after re-cocking.
6. Mount the DS239MG in its M3 cradle. Adjust the horn so it clears the sear except during a commanded trip. The servo must never hold spring load.
7. Route both forearm straps and the palm strap through all modeled slot pairs. The palm strap retains the switch pod.
8. Mix only a small 1:1 charge, away from ignition sources, with strong ventilation and eye protection. Acetone and Fabri-Tac vapors are flammable. Never aim the device at a person, animal, face, flame, vehicle, or property.

## Mandatory bench gates

- With the nozzle removed, confirm carriage travel is >=10.073 mm and no contact occurs at any intermediate position.
- With water, confirm 2.00 mL leaves in <=69 ms. Then repeat with a very small 1:1 adhesive charge into a safe disposable backstop.
- Measure spring force at fired and cocked lengths. Do not exceed the limits above.
- Confirm the LiPo cannot be compressed by straps or retainers and has clearance for swelling.
- Measure the actual owned TP4056, LiPo, switch, EPDM bands, spring and syringe flanges. Items marked `MEASURE` in the report must fit their conservative envelopes before printing the full base.
- Treat 1.715 m as an ideal ballistic ceiling. Record actual strand range and stop if atomization, splashback, clogging, frame cracking, sear bounce, or accidental release occurs.
