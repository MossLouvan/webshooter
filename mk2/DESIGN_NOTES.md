# Web-Shooter Mk2 design notes

## Result

Mk2 is an open frame, not an enclosure. A 3.2 mm nominal curved forearm plate carries exposed hardware; a narrow separate bridge runs over the back of the hand and carries two visible barrels. There is no shell, lid, box, cuff, or hidden pump.

- Printed parts: **4** (`baseplate`, `barrel_bridge`, `pusher_yoke`, `palm_switch_pod`).
- Shot: **1.986 mL** from 10.0 mm plunger travel in the selected 15.9 mm-bore syringe.
- Wrist profile: **21.725 mm above the modeled skin crown** over x = 90–120 mm; target is <= 25 mm.
- Baseplate underside: 50 mm forearm crown-radius proxy plus an assumed 0.8 mm foam gap.
- Barrels: lower-Y barrel live; upper-Y barrel capped/dummy. One live outlet preserves one strong 1.986 mL strand and avoids splitting the dose and doubling outlet area. The second barrel is retained for worn symmetry.
- Refill: lift the syringe out of the open side guides, pull the plunger back, command actuator retract, and drop the syringe back in. An owned EPDM loop around the guide posts is the removable retainer. No printed part is disassembled.

The design is deliberately one shot per fill. That makes the complete shot a factory-limited 10 mm actuator stroke, eliminates a ratchet/indexing mechanism, and keeps the frame low.

## Actuator decision

### Required volume and plunger travel

The selected syringe is the rubber-free, two-part 10 mL NORM-JECT geometry. Published cylinder dimensions are 15.9 mm ID, 17.3 mm OD and 85.3 mm cylinder length. It is PP/PE and contains no rubber or silicone oil. The CAD values come from the [Restek NORM-JECT specification table](https://www.restek.com/p/22775).

Plunger area:

```text
A = pi d^2 / 4
  = pi (0.0159 m)^2 / 4
  = 1.9856e-4 m^2
```

Ten millimetres of travel gives:

```text
V = A x = (1.9856e-4)(0.010)
  = 1.9856e-6 m^3
  = 1.986 mL
```

### Fluid-force estimate

Fabri-Tac has no published viscosity in the manufacturer data found, so viscosity is the largest unverified input. The first-pass estimate uses:

- dynamic viscosity `mu = 1.5 Pa*s` (1,500 cP), with a 2x sensitivity case;
- one 14 ga / 1.6 mm-ID live flow path, radius `r = 0.0008 m`;
- `L = 0.040 m` effective restriction length (short connector plus live needle);
- 8 N dry syringe seal/guide allowance;
- laminar Hagen-Poiseuille flow. Fabri-Tac is not guaranteed Newtonian, so this is a sizing calculation, not a substitute for a force test.

With actuator speed `v` expressed in mm/s, `Q = A v` and:

```text
DeltaP = 8 mu L Q / (pi r^4)
F_hyd  = DeltaP A
       = 14.706 v  N
F_total = 8 + 14.706 v  N
```

For a deliberately conservative actuator-line approximation between 80 N at zero speed and 6.5 mm/s at zero load:

```text
F_act = 80 (1 - v / 6.5)

8 + 14.706v = 80(1 - v/6.5)
v = 2.665 mm/s
F = 47.20 N
shot time = 10 / 2.665 = 3.75 s
```

At twice the assumed viscosity, the same arithmetic gives 58.76 N at 1.726 mm/s and a 5.79 s shot.

### Why the owned Corona DS239MG is rejected

The published DS239MG figures are 4.6 kg*cm stall torque at 6 V and 40 degrees travel to each side. Those specifications are listed by [HobbyKing](https://hobbyking.com/corona-ds-239mg-digital-slim-wing-servo-metal-gear-4-6kg-0-15sec-22g.html).

```text
T_stall = 4.6 kgf*cm x 9.80665 x 0.01 = 0.451 N*m

For a 10 mm chord over an 80 degree total sweep:
r = 10 mm / (2 sin 40 degrees) = 7.779 mm

Ideal stall force = T/r = 0.451/0.007779 = 57.99 N
1/3-stall working force = 19.33 N
```

The estimate requires 47.20 N. The DS239MG has only a 1.23x ideal **stall** ratio and only 0.41x of the required force at a conservative one-third-stall working point. Link-angle loss, syringe side load, startup friction, and the fact that the owned 1S battery cannot supply its rated 6 V make that worse. A force-gaining lever would reduce the already-required travel. For a multi-shot 50 mm stroke, the required crank radius becomes 38.9 mm and stall force falls to about 11.6 N.

**Plain conclusion: the DS239MG cannot do this job with an acceptable margin. Do not build the syringe drive around it.**

### Selected actuator and margin

Use the actually sold **Actuonix L12-10-210-6-S**: 10 mm stroke, 210:1 gearing, 6 V, internal end limit switches. The manufacturer's listing gives 80 N maximum load, 45 N backdrive force and 6.5 mm/s no-load speed. The datasheet also gives a 62 N at 3.2 mm/s peak-power point, 460 mA stall current and 20% maximum duty cycle: [Actuonix product page](https://www.actuonix.com/l12-10-210-6-s), [L12 datasheet](https://www.actuonix.com/assets/images/datasheets/ActuonixL12Datasheet.pdf).

Nominal estimated-load margin:

```text
to 62 N peak-power load: 62 - 47.20 = 14.80 N; ratio 1.31
to 80 N maximum load:    80 - 47.20 = 32.80 N; ratio 1.69
```

At the 2x-viscosity sensitivity point, margin is 3.24 N to the 62 N point and 21.24 N to maximum. This is adequate for a prototype only if the real force test passes. The controller should drive one full extension per shot, then remain off; respect the actuator's 20% duty cycle.

The `-S` actuator is reversed by a DRV8833 H-bridge. Its internal end switches terminate extension/retraction. The 1S LiPo therefore requires a regulated 6 V rail. This actuator choice **does force a boost converter back into the design**, but it is a fixed Pololu U3V70F6 rather than an MT3608. The protected battery feeds the required power switch, then the 6 V regulator, actuator and motor driver. All logic shares ground.

## Mechanical architecture

- `baseplate`: curved forearm shell segment, two 25 mm forearm-strap slots, exposed actuator/syringe guides, board clips, power-switch saddle and two M3 insert pockets.
- `barrel_bridge`: raised narrow hand plate with a locally widened two-screw rear interface, palm strap slots, an open syringe lane and perforated twin-barrel towers.
- `pusher_yoke`: pinned to the actuator clevis with an owned M3 screw and bears on the syringe thumb flange.
- `palm_switch_pod`: open frame on the palm strap for the owned 12 x 12 mm tactile switch.

The base and bridge mating holes are driven from `BRIDGE_FASTENER_X`, `BRIDGE_FASTENER_Y`, `M3_CLEARANCE_DIAMETER`, `M3_INSERT_OD` and `M3_INSERT_LENGTH`. Barrel OD and guide clearance, strap thickness and slot width, actuator pin diameter, syringe OD and guide clearance are likewise shared named values rather than duplicated mating literals.

The XIAO and TP4056 USB-C ends remain exposed. Use GPIO4 for the palm switch (GPIO8 and GPIO9 are reserved/avoided), configure an internal pull-up, and recognize a double tap whose second falling edge arrives within 400 ms. Firmware is intentionally outside this CAD deliverable.

## Interference and geometry verification

`python webshooter_mk2.py` regenerates all exports and `verification_report.json`. The verification run checks:

- every printed item has exactly one solid;
- every printed item is valid;
- every printed item has local `z_min >= 0` (within a 1e-6 mm kernel tolerance);
- shot volume and printed-part limits;
- wrist profile;
- every unordered pair across all printed parts and all mockups, with no skip list and no allow-list.

Latest result: **PASS**, 4 printed solids, 1.986 mL, 21.725 mm wrist profile, **300/300 pair volumes exactly 0.0 mm^3**.

Functional contacts are explicitly represented with clearance or tangent faces, so none requires an interference exception:

| Interface | Purpose | CAD intersection |
|---|---|---:|
| Yoke face / syringe thumb flange | Transfers shot force | 0.0 mm^3 |
| M3 clevis pin / actuator and yoke bores | Joins actuator to yoke | 0.0 mm^3 |
| Bridge screws / clearance holes / insert bores | Clamps bridge to base | 0.0 mm^3 |
| Base / bridge interface | 0.35 mm print/assembly gap before screw clamp | 0.0 mm^3 |
| Syringe / guide posts | 0.50 mm radial removal clearance | 0.0 mm^3 |
| Barrels / tower bores | 0.25 mm diametral clearance | 0.0 mm^3 |
| Boards / clip rails | Captive exposed mounting | 0.0 mm^3 |
| Strap tabs / printed slots | Represents routed 25 mm webbing | 0.0 mm^3 |
| Base / forearm reference | 0.8 mm foam allowance | 0.0 mm^3 |

`assembly_stl/` contains each printed part after its explicit assembly transform. `printed_parts/` contains local-coordinate STEP and STL exports. `webshooter_mk2_assembly.step` is exported from the real `cadquery.Assembly`; mockups remain non-printable dictionary/assembly members.

## Proxies and measure-before-printing

High confidence: NORM-JECT cylinder ID/OD/length, actuator stroke/load/speed envelope, 25 mm webbing width, owned item names, M3 hardware nominal dimensions.

Proxy or unverified: Fabri-Tac viscosity/rheology, actual syringe breakaway force and flange size, exact L12 body/clevis envelope, EEMB pouch swelling envelope, individual board/USB connector envelopes, regulator/driver carrier outlines, switch body, wearer anatomy, webbing thickness and purchased needle ID.

Measure or test before committing a full print:

1. Put the actual syringe, shortest proposed connector and live needle on a scale; push at roughly 2–3 mm/s with undiluted Fabri-Tac. Required peak must stay below 62 N. If it does not, shorten/widen the flow path before changing adhesive concentration. Do not exceed 1:0.5 thinning.
2. Confirm the purchased needle has at least 1.6 mm clear ID. A smaller ID changes force with `1/r^4` and invalidates the margin.
3. Measure syringe OD, cylinder length, thumb flange, Luer location and breakaway force; update the named constants.
4. Measure actuator body, clevis and pin location from the purchased unit/STEP file.
5. Measure the actual LiPo, XIAO, TP4056, boost, DRV8833 and switch—including solder joints and USB plugs. Allow for LiPo swelling; never clamp the pouch.
6. Measure the wearer's forearm crown and neutral-wrist bridge height. Print 20 mm-long strap/curvature coupons first.
7. Verify the boost holds 6.0 V during actuator startup and that the power switch has a genuine >= 1 A DC rating at 6 V.
8. Bench-test with water first, then adhesive, outdoors or with strong ventilation and the owned eye/respiratory protection. Never aim at a person, face, flame or ignition source.

