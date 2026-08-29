#!/usr/bin/env python3
"""
Web-Shooter Mk5 (in progress, still in the mk4 module name) — parametric CadQuery model.

MK5 STATUS — ROUND 4 OF 5 COMPLETE. READ THIS BEFORE EDITING.
-------------------------------------------------------------
ROUND 4 DREW THE RECOCK ACTUATOR AND MADE THE HARNESS MEASURE IT.

Until this round the headline requirement rested on a 1.804 mm lever arm that no
part possessed. `N_BITES = 2` and

    WINCH_RADIUS_MM = PLUNGER_STROKE / (RECOCK_SWEEP_RAD * N_BITES)

produced a number, check_recock_budget divided the same three constants back out
of it, and the gate reported 2.24x on a mechanism whose only reach toward the
carriage was an 0.850 mm sliver of bounding-box corner. Two bites also demanded a
half-cock hold that nothing in the model provides (defect 12).

DELETED: N_BITES, WINCH_RADIUS_MM, RECOCK_PEAK_TORQUE_N_MM, the rocker, its pin,
the hand-lever hex stub (architecture C's free fallback goes with it, and that is
a real loss), the winch servo's horn and pushrod.

DRAWN INSTEAD, all of it geometry:
  * winch_drum     a PROFILED SCROLL on the winch servo's output shaft. Radius
                   falls from 7.00 to 1.98 mm through the sweep, so the torque is
                   flat instead of ramping with the spring. Solved from
                   ds/dphi = T/F(s), capped at R_max over the first phi0 radians,
                   phi0 by bisection. Machined aluminium, not printed - the waist
                   is 1.7 mm from the axis and only exists because the hub is in
                   a different y band from the cable groove.
  * winch_shaft    the servo's own spline, so "the drum is on a shaft" is a
                   measurable statement rather than a caption.
  * recock_cable   Ø0.6 UHMWPE, tangent to the drum groove and swaged over
  * recock_anchor_pin  a Ø2 dowel through
  * a FORK on the carriage's rear face, full height so it prints, with 4.3 mm of
                   pin journalled in material. That number replaces 0.850 mm of
                   bounding-box corner.
  * a winch servo CRADLE on the baseplate, at located-fit clearance.

MEASURED RESULT (harness, not this file): radius read off the drawn drum at 33
angles; peak 97.0 N.mm at the servo shaft against 150 usable, 1.55x, flat to
within 0.5% across the sweep; one sweep draws 10.468 mm against a 10.073 mm
stroke; drum turns a full revolution clear of every other body.

WHAT IT COST
  * THE SWEEP IS NOW 170 deg, not 160. At 160 the solved profile is 1.45x and no
    choice of R_max recovers it. This is the single bench measurement the whole
    architecture hangs on - servodatabase says the DS239MG turns 40 deg.
  * THE LIPO MOVED FORWARD 86 mm, because the tail is where the drum has to be.
  * The hand-cock fallback is gone.
  * The drum is CANTILEVERED on the servo's output shaft: 37 N at ~5 mm is
    ~190 N.mm of bending on a bushing that was not designed for it, and there is
    nowhere to put an outboard bearing (the push-rod occupies y = -19..-13 at
    exactly the shaft height). UNRESOLVED - see the round 4 notes.

ROUND 3 WAS A GEOMETRY ROUND, AND THE DEVICE NOW FIRES FIVE TIMES.

Rounds 1 and 2 built the instrument and left the part untouched; the harness
consequently got better at describing a machine that could not fire once. Round
3 changed no check. The whole diff is drawn geometry, and the number it moved is
the one that matters:

    shot 1  10.07 of 10.07 mm  ->  2.00 mL      (was 3.00 mm -> 0.60 mL)
    shot 2  10.07 of 10.07 mm  ->  2.00 mL      after a re-cock to the same X
    shots 3-5 likewise; 10.00 mL total, stopped by nothing

WHAT WAS DRAWN
  * THE FRAME GREW REARWARD, 64.0 mm of it, and FRAME_X0 is now DERIVED from the
    push-rod's tail rather than assumed to be 0. The frame is 238 mm along the
    forearm against Mk4's 174. That is the largest single cost this design
    carries and it is a length, not a height.
  * THE STATION MAP WAS RE-ROOTED AT THE SYRINGE. The old chain grew forward
    from SPRING_X0 = 8.0 and could therefore never give the stroke room that has
    to come out of the back; the 7.028 mm deficit was arithmetic, not spacing.
    GRIP_SPAN_DEFICIT_MM is now -0.350 and asserted <= 0.
  * THE CARRIAGE IS BORED ON THE ROD - spring counterbore, rod bore, drive-plate
    pocket, return-spring pocket - so the three purchased bodies that were drawn
    inside solid material (338.23 + 138.56 + 85.42 mm3) now have the pockets
    they always needed. Push pad and thumb tab deleted: both served a mechanism
    Mk5 does not have.
  * THE ANTI-RETURN PLATE HAS AN ABUTMENT. It carried 37 N into air 2.10 mm from
    anything solid. It is now Ø18 against the drive plate's Ø14 and beds on an
    annulus of a bored wall on the baseplate, so the Ø14 drive plate passes
    through the middle at full stroke while the reaction lands on printed
    material.
  * THE WINCH ROCKER LEFT THE CARRIAGE LANE, into the pocket the shortened rails
    vacate behind the cocked carriage, on printed pin bearings.

WHAT IT COST, STATED RATHER THAN ABSORBED
  A carriage that CONTAINS the rod is taller than one that shoves a flange:
  carriage top 16.40 -> 17.95 mm, and since SEAR_CONTACT_Z derives from it, the
  pawl, tower and stack all rise with it. Wrist profile 35.50 -> 37.05 mm
  against a 25 mm target. The tower alone is 32 of those millimetres, so the
  profile is a sear-architecture problem for round 4/5, not a spring-placement
  one.

WHAT ROUND 3 DID NOT TOUCH (deliberately - these are round 4/5)
  * check_grip_release's return sweep starts from the COCKED pose and retracts a
    further full stroke into a spring drawn at its cocked length. The carriage's
    cocked pose IS its rearmost; the return stroke runs fired -> cocked, which
    check_multishot's own stepper walks successfully five times. The check is
    posed wrong, and repairing checks was reserved for round 4.
  * push_rod <> grip_plate_* "overlap 0.07 mm3" is the BITE - the design
    requires 0.10 mm of diametral interference - reported as a clearance defect.
  * the servo cannot open the sear (240 vs 150 N.mm): architecture B.
  * servo mounts, horns, cradle screws and the outlet adapter are step 4/7/8.

DONE:
  1. HARNESS BEFORE MODEL. check_spring_buckling, check_servo_torque,
     check_one_way_grip, check_multishot, check_recock_budget,
     check_wrist_profile and check_piston_containment were added to
     verify_independent.py and run against the UNCHANGED Mk4 first. All seven
     fired, and their numbers independently reproduced the brief's hand
     arithmetic: 642 N.mm to release the sear against 150 available, shot 2
     delivering 0.79 mL, slenderness 6.48 with a 32% pilot. A check written
     after the fix has never been seen to fail; these were.
  2. PHYSICS. TARGET_RANGE_M 1.5 -> 1.60 (off the knife edge against the
     harness's own >= 1.5 gate); OUTLET_BORE is now DEFINED AS CANNULA_ID_MM,
     so the design bore and the sizing bore are one number and cannot drift
     apart again; cartridge 5 mL -> 10 mL for five 2 mL shots.
  3. MOCKUPS. 7 bodies -> 26. Barrel is a tube, finger flange an annulus, and
     the piston, push-rod, both grip plates, two servos, two horns, two
     pushrods, the rocker and its pin, the hex hand-lever stub, the sear
     torsion spring, the cannula, hub and O-ring, and the cradle screws are all
     present. Failure count rose 21 -> 42, which is the point.

NOT DONE — steps 4 to 9, in this order:
  4. fluid spine: front abutment, split cradle, cannula collar, muzzle cap
  5. push-rod, grip plates, rear abutment, spring, tail shroud
  6. carriage bored on the rod, carrying the rack
  7. sear and trip servo  (do this BEFORE the winch: never leave the build able
     to cock but not certifiably hold a compressed 37 N spring on a wrist)
  8. cocking winch
  9. edge treatment

ONE MEASURED CONSEQUENCE ROUND 1 SURFACED AND DID NOT SOLVE:
  the push-rod's tail reaches x = -48.4 while the baseplate starts at x = 0.
  Five shots from a 10 mL cartridge require FILL_LEN = 50.4 mm of rod behind
  the spring seat, or the spring loses its pilot on the last shots. The frame
  must grow rearward by ~52 mm, or the mechanism shift forward, or the shot
  count drop. That is a length along the forearm, not a height on the wrist,
  but it is a real cost of the cartridge choice and it is not yet paid.

WHY MK4 EXISTED
---------------

WHY MK4 EXISTS
--------------
Mk3 had three independent mechanism failures and an energy shortfall, all found by
independent audit after its own harness reported `failures: []`:

  * the sear was inverted — the load line sat 5.9 mm below the pivot, so the spring
    torqued it toward release. It fired itself the instant it was cocked.
  * the sear also sat in the carriage's path — 60 mm3 of interference mid-stroke.
  * the cocking lever was over-constrained (round pin in round hole, no slot) and
    achieved 0.096 mm of the 10.07 mm it needed.
  * the drive was energy-starved: 0.179 J stored against 0.276 J needed just to
    push the charge through the syringe's own Luer taper.

Mk4 does not patch those. It removes the conditions that created them:

  1. THE LUER TAPER IS CUT OFF and replaced by a bonded 4 mm x 12 mm outlet.
     Work falls from 0.276 J to 0.092 J — half the stored energy, with margin.
  2. A 5 mL SYRINGE replaces the 10 mL. Same 2 mL shot (bore does not affect exit
     velocity: v = V/(t*A_o), the bore cancels), but the longer stroke drops peak
     spring force to 11.2 N.
  3. the peak spring force (16.3 N, see mk4_params.json) is a thumb pull, so the cocking lever and its two pins are deleted.
     A broken mechanism removed rather than repaired.
  4. THE SEAR ENGAGES THE CARRIAGE'S REAR FACE. Firing moves the carriage away
     from the sear, so a stroke jam is not geometrically possible. The pivot sits
     above and behind the contact so the spring load torques the tooth deeper into
     engagement — verified numerically in `sear_moment_check()`, not asserted.

Every part is prismatic and extruded from its own bed plane, which is also what
fixes Mk3's unsupported islands and undersized first layers.

Run:  python webshooter_mk4.py          # exports STEP + STL per part
Check: python verify_independent.py --model webshooter_mk4
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from typing import Dict

import cadquery as cq

OUT = os.path.dirname(os.path.abspath(__file__))

# =============================================================== fluid physics
# All derived, none declared. These drive the geometry below.
FLUID_VISCOSITY_PA_S = 0.50      # 1:1 thinned Fabri-Tac (SDS 8000 cP neat)
SHOT_VOLUME_ML = 2.0

# (Mk5) TARGET_RANGE_M 1.5 -> 1.60.
# The harness fails the design when the range at the REAL cannula drops under
# 1.5 m. Targeting exactly 1.5 put the design on a floating-point knife edge
# against its own acceptance gate: a rounding step in either direction is the
# difference between pass and fail, and three revisions have been decided by
# that last decimal. 1.60 is the same design with the gate off the edge.
TARGET_RANGE_M = 1.60
G = 9.81

EXIT_VELOCITY_M_S = math.sqrt(TARGET_RANGE_M * G)        # 3.962 m/s

# (Mk5) THE DESIGN BORE AND THE SIZING BORE ARE NOW ONE NUMBER.
# Mk4 drew a 4.00 mm outlet and then sized the spring against a 3.429 mm
# cannula, so every derived quantity in the file existed in two versions and
# the discrepancy - 0.0921 J against 0.1705 J - has been rediscovered by an
# independent reviewer in three consecutive revisions. There is no bonded 4 mm
# adapter in Mk5 (defect 10: no bonded joint anywhere in the fluid path), so
# the only bore the fluid ever sees is the replaceable cannula's. Declare that
# once and derive everything from it; the two numbers cannot drift apart
# because there is only one of them.
CANNULA_ID_MM = 3.429                                    # real 8 ga blunt tip
OUTLET_BORE = CANNULA_ID_MM
OUTLET_LENGTH = 12.0                                     # mm of wetted bore

_r = OUTLET_BORE / 2000.0
_V = SHOT_VOLUME_ML * 1e-6
OUTLET_DP_PA = 8 * FLUID_VISCOSITY_PA_S * (OUTLET_LENGTH / 1000.0) * EXIT_VELOCITY_M_S / (_r * _r)
FLOW_WORK_J = OUTLET_DP_PA * _V
SHOT_TIME_S = _V / (EXIT_VELOCITY_M_S * math.pi * _r * _r)   # derived
BALLISTIC_RANGE_M = EXIT_VELOCITY_M_S ** 2 / G

# ------------------------------------------------------------------ cartridge
# (Mk5) 10 mL NORM-JECT, back from Mk4's 5 mL.
#
# Mk4 went 10 -> 5 mL to cut peak spring force and stack height. With a ratchet
# doing the recocking the force argument is gone - the servo does that work, and
# it does it in N small bites rather than one pull. What the 10 mL buys is the
# headline requirement: 5 shots of 2 mL per fill against the 5 mL's 2.5.
#
# It costs stack height, and that cost is not hidden: the barrel is 3.30 mm
# fatter than the 5 mL, which is a straight 3.30 mm onto the wrist profile.
# check_wrist_profile measures the whole assembly against the 25 mm target and
# will say so.
#
# BENCH FIRST: these are catalogue figures for a 10 mL NORM-JECT and the brief's
# step 0 requires the actual barrel to be measured with calipers before anything
# is cut. Bore, OD and length are all parametric on these three lines.
SYRINGE_BORE = 15.90            # UNVERIFIED - measure the real barrel
SYRINGE_WALL = 0.55             # UNVERIFIED - measure the real barrel
SYRINGE_OD = SYRINGE_BORE + 2 * SYRINGE_WALL             # 17.00
SYRINGE_BARREL_LEN = 88.0       # UNVERIFIED - measure the real barrel
SYRINGE_FLANGE_OD = 26.0        # UNVERIFIED
SYRINGE_FLANGE_T = 2.5          # UNVERIFIED
SYRINGE_CAPACITY_ML = 10.0
SHOTS_PER_FILL = int(SYRINGE_CAPACITY_ML // SHOT_VOLUME_ML)      # 5

_A_p = math.pi * (SYRINGE_BORE / 2000.0) ** 2
PLUNGER_STROKE = _V / _A_p * 1000.0                      # 16.43 mm
PLUNGER_FORCE_N = OUTLET_DP_PA * _A_p                    # 5.60 N
PLUNGER_ROD_OD = 6.0
PLUNGER_THUMB_OD = 18.0
PLUNGER_THUMB_T = 2.5

# ----------------------------------------------------- the sizing restriction
# (Mk5) THERE IS NO LONGER A DISCREPANCY TO RESOLVE HERE.
#
# Mk4 drew a 4.00 mm adapter bore and sized the spring against the 3.429 mm
# cannula that would actually be fitted, so the file carried two sets of every
# derived number and three consecutive independent reviews rediscovered the gap
# between them. Mk5 deletes the bonded adapter entirely (defect 10 wants a
# serviceable joint, not a glued one), so the cannula IS the outlet and
# OUTLET_BORE is defined as CANNULA_ID_MM above. FLOW_WORK_J and CANNULA_WORK_J
# are therefore the same computation on the same number, and SIZING_WORK_J is
# not a max over a disagreement - it is a max over an identity. The assert
# below is what keeps it that way if anyone re-opens the bore.
_rc = CANNULA_ID_MM / 2000.0
FLOW_RATE_M3_S = EXIT_VELOCITY_M_S * math.pi * _r * _r
CANNULA_DP_PA = (8 * FLUID_VISCOSITY_PA_S * (OUTLET_LENGTH / 1000.0)
                 * FLOW_RATE_M3_S / (math.pi * _rc ** 4))
CANNULA_WORK_J = CANNULA_DP_PA * _V
SIZING_WORK_J = max(FLOW_WORK_J, CANNULA_WORK_J)
assert abs(FLOW_WORK_J - CANNULA_WORK_J) < 1e-9, (
    "the design bore and the sizing bore have drifted apart again: "
    f"{FLOW_WORK_J:.6f} J vs {CANNULA_WORK_J:.6f} J")

# --------------------------------------------------------------------- spring
# Sized from the derived sizing work with margin, not chosen then justified.
SPRING_MARGIN = 1.45
SPRING_ENERGY_J = SIZING_WORK_J * SPRING_MARGIN
SPRING_PEAK_N = 2.0 * SPRING_ENERGY_J / (PLUNGER_STROKE / 1000.0)
SPRING_RATE_N_MM = SPRING_PEAK_N / PLUNGER_STROKE
SPRING_OD = 8.0
SPRING_WIRE = 0.9
# (Mk5) The 10 mL bore cuts the stroke from 16.43 mm to 10.07 mm, so the spring
# gets shorter as well. Free length is set from the stroke plus solid height
# plus a working margin rather than left at Mk4's 46 mm, which would now be
# 4.6 coil diameters of unused length sitting on the wrist.
SPRING_SOLID_LEN = 9.0                                   # ~10 active coils
SPRING_FREE_LEN = 34.0
SPRING_COCKED_LEN = SPRING_FREE_LEN - PLUNGER_STROKE
assert SPRING_COCKED_LEN > SPRING_SOLID_LEN, "spring goes solid before full cock"


# ============================================== (Mk5) THE ACTUATORS AND THE WINCH
# Defect 3: `grep servo` across Mk4 found only comments. There was no mount, no
# horn, no pushrod and no linkage, and BOM_DELTA.md said "servo mounting as
# shown" while nothing was shown. Every number a servo check could possibly want
# is declared here, in one place, with its provenance.
#
# BENCH FIRST, NOTHING CUT. Step 0 of the build order requires six measurements
# before any of this is trusted. The two that decide the architecture are marked
# BENCH: servodatabase lists the DS239MG's sweep as 40 deg and its body as
# 30 x 10 x 34.5 mm, and a 10 mm width on a 22 g servo is internally implausible.
# Defect 3 exists because nobody ever held the part.
SERVO_STALL_N_MM = 4.6 * 98.07        # 4.6 kg.cm at 6 V, DS239MG   BENCH: stall
SERVO_HORN_R_MM = 9.0                 # horn pin radius on the output shaft
SERVO_L, SERVO_W, SERVO_H = 30.0, 13.0, 34.5   # BENCH: measure the real body
SERVO_MOUNT_T = 3.0                   # printed mount wall the body sits in
SERVO_SHAFT_DX = 9.0                  # shaft offset along the body from its end

# =========================== (Mk5 round 4) SINGLE-SWEEP SCROLL WINCH
#
# WHAT WAS DELETED AND WHY. Rounds 1-3 carried `N_BITES = 2` and a
# rocker-and-pawl winch that drew the stroke in two equal bites. Two bites is
# what forced
#       WINCH_RADIUS_MM = PLUNGER_STROKE / (sweep * N_BITES) = 1.8035 mm
# and 1.8035 mm was a NUMBER, not a feature: no part in the file had a radius,
# a pin, a groove or a face at 1.8 mm from any shaft, and the rocker's only
# reach toward the carriage was an 0.850 mm corner sliver of bounding-box
# overlap. Worse, two bites needs the carriage HELD at half cock between them,
# and nothing in the model holds it - defect 12, which the brief already lists.
# So N_BITES, WINCH_RADIUS_MM and the rocker are gone, and with them the
# hand-lever hex stub (architecture C's free fallback): there is no longer a
# rocker shaft to put it on, and the drum sits in a pocket a lever cannot reach.
# That is a real loss and it is stated rather than absorbed.
#
# WHAT REPLACES IT. One sweep. A profiled scroll drum on the winch servo's
# output shaft winds a UHMWPE cable that ends on an anchor pin through a fork on
# the carriage's rear face, and one 160 deg sweep draws the whole 10.073 mm and
# lets the sear catch at full cock.
#
# THE ARITHMETIC, AND WHY THE DRUM IS PROFILED RATHER THAN ROUND.
# A CONSTANT radius closes the energy balance and fails the instant:
#       r_const   = stroke / sweep            = 3.607 mm
#       peak      = F_cocked * r_const        = 134 N.mm at the servo
# against 150 N.mm usable - 1.12x at the worst instant of the cycle. Raising the
# radius makes the peak worse; lowering it makes the sweep too short to draw the
# stroke. The fix is SHAPE. The spring's resistance rises linearly with the
# draw, so the drum's radius is made to FALL as the draw proceeds: the cable
# leaves at a large radius while the spring is soft and at a small one while it
# is stiff, and the torque is flat instead of ramping. The schedule below is
# solved, not fitted: constant torque T against F(s) = k*s + drag gives
#       ds/dphi = R = T / F(s)   ->   (k/2)s^2 + drag*s = T*(phi - phi0) + const
# capped at WINCH_R_MAX_EFF over the first phi0 radians, because the true
# constant-torque profile needs an infinite radius where the force is zero.
# phi0 is then the root that makes the cap and the constant-torque arc draw
# exactly PLUNGER_STROKE between them, found by bisection below.
# THE SWEEP IS 170 DEG AND THAT IS A DECISION, NOT A ROUNDING.
# At 160 deg the solved profile peaks at 104 N.mm against 150 usable - 1.45x,
# under the 1.5x gate - and no choice of WINCH_R_MAX_EFF recovers it: the peak
# is set by the sweep and the over-travel, and R_max moves it by under 2%.
# 170 deg gives 1.55x, 180 deg gives 1.65x. The brief's own table says the same
# thing (160 -> 1.4x, 180 -> 1.5x, before the drag term this model carries).
# THIS IS THE SINGLE BENCH MEASUREMENT THE WHOLE ARCHITECTURE HANGS ON:
# servodatabase lists the DS239MG's rotation as 40 deg, which if true kills the
# one-sweep winch outright and the fallback is a bigger drum on a geared servo,
# not a tweak to this profile. Measure it over 500-2500 us before cutting.
RECOCK_SWEEP_DEG = 170.0              # BENCH: measure over 500-2500 us PWM
RECOCK_SWEEP_RAD = math.radians(RECOCK_SWEEP_DEG)

# The load the drum works against. NOT just the spring: the drive plate's
# return spring is being squared and the carriage is sliding in its rails, and
# a recock budget that pretends those are zero is a budget with a free lunch in
# it. 3.0 N is the drive plate's own return spring taken at full value plus
# nothing for rail friction - BENCH: drag the cocked carriage on a scale.
RECOCK_DRAG_N = 3.0
WINCH_EFFICIENCY = 0.85               # cable stiffness over the drum + bearing

WINCH_CABLE_D = 0.6                   # Ø0.6 UHMWPE braid, ~200 N break vs 37 N
WINCH_R_MAX_EFF = 7.0                 # cable PITCH radius at the start of sweep
WINCH_GROOVE_DEPTH = 0.35             # groove floor sits this far under the rim
WINCH_GROOVE_W = 0.8                  # groove width, y

# OVER-TRAVEL. The sweep must not draw EXACTLY the stroke. The sear tooth has
# to have somewhere to drop into once the lug has passed under it, cable braid
# creeps a few tenths under load, and a profile solved to the stroke to the last
# micron fails an integration of its own drawn radius by rounding. 0.40 mm is
# the tooth's own gap over the lug (SEAR_TOOTH_GAP is 0.8; half of it is enough
# to catch) and it is drawn into the drum, not asserted about it.
WINCH_OVERDRAW_MM = 0.40

_WK = SPRING_RATE_N_MM                # N/mm, from the spring the model draws
_WS = PLUNGER_STROKE + WINCH_OVERDRAW_MM
_WTH = RECOCK_SWEEP_RAD


def _winch_torque_for_phi0(phi0: float) -> float:
    """Constant-torque value implied by a cap of WINCH_R_MAX_EFF over phi0."""
    s0 = WINCH_R_MAX_EFF * phi0
    return (_WK * s0 + RECOCK_DRAG_N) * WINCH_R_MAX_EFF


def _winch_draw_at_sweep(phi0: float) -> float:
    """Cable drawn over the whole sweep for a given cap angle phi0."""
    T = _winch_torque_for_phi0(phi0)
    s0 = WINCH_R_MAX_EFF * phi0
    if phi0 >= _WTH:
        return WINCH_R_MAX_EFF * _WTH
    # (k/2)s^2 + drag*s = T*(phi-phi0) + (k/2)s0^2 + drag*s0
    rhs = T * (_WTH - phi0) + 0.5 * _WK * s0 * s0 + RECOCK_DRAG_N * s0
    a, b, c = 0.5 * _WK, RECOCK_DRAG_N, -rhs
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)


def _solve_winch_phi0() -> float:
    # the draw rises monotonically with phi0: a longer capped arc both winds
    # more cable directly and raises the constant torque that follows it.
    lo, hi = 0.0, _WTH
    if _winch_draw_at_sweep(hi) < _WS:
        raise ValueError("even a drum at WINCH_R_MAX_EFF for the whole sweep "
                         "cannot draw PLUNGER_STROKE: raise R_max or the sweep")
    if _winch_draw_at_sweep(lo) > _WS:
        raise ValueError("WINCH_R_MAX_EFF is larger than the profile needs; the "
                         "cap never binds and phi0 has no root")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _winch_draw_at_sweep(mid) < _WS:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


WINCH_PHI0_RAD = _solve_winch_phi0()
WINCH_TORQUE_N_MM = _winch_torque_for_phi0(WINCH_PHI0_RAD)     # at the cable
WINCH_SERVO_TORQUE_N_MM = WINCH_TORQUE_N_MM / WINCH_EFFICIENCY  # at the shaft


def winch_draw_at(phi: float) -> float:
    """Cable drawn in, mm, after `phi` radians of the sweep. phi = 0 is the
    fired pose; phi = RECOCK_SWEEP_RAD is full cock."""
    phi = max(0.0, min(phi, _WTH))
    if phi <= WINCH_PHI0_RAD:
        return WINCH_R_MAX_EFF * phi
    s0 = WINCH_R_MAX_EFF * WINCH_PHI0_RAD
    rhs = (WINCH_TORQUE_N_MM * (phi - WINCH_PHI0_RAD)
           + 0.5 * _WK * s0 * s0 + RECOCK_DRAG_N * s0)
    a, b, c = 0.5 * _WK, RECOCK_DRAG_N, -rhs
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)


def winch_pitch_radius(phi: float) -> float:
    """Cable pitch radius (drum groove floor + cable radius) at sweep angle phi.

    THIS is what the drum is drawn from, and the harness re-measures it off the
    drawn solid rather than calling this function."""
    phi = max(0.0, min(phi, _WTH))
    if phi <= WINCH_PHI0_RAD:
        return WINCH_R_MAX_EFF
    return WINCH_TORQUE_N_MM / (_WK * winch_draw_at(phi) + RECOCK_DRAG_N)


WINCH_R_MIN_EFF = winch_pitch_radius(_WTH)
RECOCK_WORK_N_MM = 0.5 * SPRING_PEAK_N * PLUNGER_STROKE + RECOCK_DRAG_N * PLUNGER_STROKE
assert winch_draw_at(_WTH) > PLUNGER_STROKE + 0.9 * WINCH_OVERDRAW_MM, (
    "the drum profile does not draw the stroke plus its over-travel")

# ================================================ (Mk5) THE ONE-WAY PLUNGER GRIP
# The caulk-gun pair: two tilting steel plates on a ground stainless push-rod.
# The syringe's own plunger rod is DISCARDED - cut off behind the piston - which
# deletes defects 4 and 5 outright instead of accommodating them, and replaces a
# ribbed polypropylene rod (which no tilting plate can bite) with the round
# hardened rod a tilting plate needs.
#
# GEOMETRY OF THE BITE, SOLVED RATHER THAN APPROXIMATED.
# A plate of thickness t with a bore D, tilted by alpha on a rod of diameter d,
# presents a projected aperture
#       A(a) = D*cos(a) - t*sin(a) = R*cos(a + phi),
#       R = hypot(D, t),   phi = atan(t/D)
# across the rod, and it bites when A(a) falls to d. The closed-form root is
#       a_root = acos(d/R) - phi
# and for D=6.3, t=1.5, d=6.0 that is 8.715 deg.
#
# Mk5 round 1 wrote `atan((D-d)/t)` here, which is 11.310 deg. That expression is
# the small-angle stand-in for the same root - it ignores the cos(a) thinning of
# the bore - and it is 30% high. The number itself was harmless (too much tilt
# still bites). The DAMAGE was that the harness checked the declared tilt against
# THE SAME atan expression the model had used to choose it, so `got >= need` was
# `x >= x`: a gate with no failing state, on the mechanism the whole multi-shot
# claim rests on. The root below is the real one; GRIP_TILT_DEG is now an
# INDEPENDENT declared number with a stated margin over it, so the gate can fail.
GRIP_BORE_D = 6.3
PUSH_ROD_OD = 6.0                     # h9 stainless, ground - a wear part
GRIP_PLATE_T = 1.5                    # hardened spring steel

_GRIP_R = math.hypot(GRIP_BORE_D, GRIP_PLATE_T)
_GRIP_PHI = math.atan2(GRIP_PLATE_T, GRIP_BORE_D)

def grip_aperture_mm(tilt_deg: float) -> float:
    """Projected aperture of the tilted bore across the rod. The ONE definition;
    the harness re-derives it from D, t and the tilt rather than reading it."""
    return _GRIP_R * math.cos(math.radians(tilt_deg) + _GRIP_PHI)

# The angle at which the aperture is exactly the rod diameter: line contact, zero
# interference, zero bite force. A grip AT this angle does not grip - it touches.
GRIP_BITE_ROOT_DEG = math.degrees(math.acos(PUSH_ROD_OD / _GRIP_R) - _GRIP_PHI)

# HOW MUCH PAST THE ROOT, AND WHY. The bite is an interference fit made by
# tilting: the plate has to be forced onto an aperture SMALLER than the rod so
# the two bore edges are pressed into it before any load is applied. 0.10 mm on
# diameter is the smallest interference that survives the tolerance stack - a
# +0.05 h9 rod against a bore that a stamping holds to about +/-0.03 - with
# contact left over. It is a stated requirement, not a fitted result.
GRIP_BITE_INTERFERENCE_MM = 0.10
GRIP_BITE_MIN_DEG = math.degrees(
    math.acos((PUSH_ROD_OD - GRIP_BITE_INTERFERENCE_MM) / _GRIP_R) - _GRIP_PHI)

# THE DECLARED TILT. Chosen, not computed from the gate it has to pass: 12 deg is
# a round number a stamping tool can hold, it clears the 10.958 deg interference
# requirement by 1.10x and the bare 8.715 deg bite root by 1.38x, and it is low
# enough that the plate still swings square (see GRIP_SQUARE_DEG) inside a 1.5 mm
# pocket. Raising it costs axial length: the plate's x-envelope grows as
# OD/2*sin(a), and axial length between the plates is the scarcest thing here.
GRIP_TILT_DEG = 12.0

# (Mk5 round 3) THE TWO PLATES ARE NO LONGER THE SAME DIAMETER, AND THE REASON
# IS THE ABUTMENT THE ANTI-RETURN PLATE HAS NEVER HAD.
#
# The anti-return plate carries the return reaction and its nearest solid was
# 2.10 mm away - it was floating. The reaction is REARWARD (the rod tries to
# follow the retreating carriage), so the face that takes it must sit BEHIND the
# plate. But behind the plate is exactly where the drive plate arrives at the end
# of the stroke, so a plain wall there is a wall the stroke runs into: that is
# the same 7 mm the frame was short of, re-created one part further forward.
#
# The way out is radial, not axial. Make the anti-return plate LARGER than the
# drive plate and take its reaction on an ANNULUS outside the drive plate's
# swept radius. The drive plate (r 7.0) then passes clean through a r 7.4 mouth
# in the abutment while the anti-return plate (r 9.0) beds on the r 7.4..11 ring
# around it. Nothing about the bite changes - the bite is a bore-edge effect and
# both plates keep GRIP_BORE_D - and the reaction finally lands on printed
# material instead of on air.
GRIP_DRIVE_OD = 14.0
GRIP_ANTIRETURN_OD = 18.0
GRIP_PLATE_OD = GRIP_DRIVE_OD          # the plate the release moment acts on


def grip_plate_half_x(od: float, tilt_deg: float = GRIP_TILT_DEG) -> float:
    """Half the axial envelope of a tilted disc: od/2*sin(a) + t/2*cos(a)."""
    a = math.radians(tilt_deg)
    return od / 2.0 * math.sin(a) + GRIP_PLATE_T / 2.0 * math.cos(a)


GRIP_DRIVE_HALF_X = grip_plate_half_x(GRIP_DRIVE_OD)          # 2.189
GRIP_ANTIRETURN_HALF_X = grip_plate_half_x(GRIP_ANTIRETURN_OD)  # 2.604
GRIP_PLATE_HALF_X = GRIP_DRIVE_HALF_X                          # back-compat
GRIP_PLATE_CLEARANCE = 0.15      # the harness's own tangency gate
# ...and this much again on top of it, so the stroke is not certified by a gap
# the size of the gate. A stroke that ends exactly on MIN_CLEARANCE is a stroke
# one rounding step from failing, which is the knife-edge TARGET_RANGE_M was
# moved off in round 1 for the same reason.
GRIP_SPAN_MARGIN = 0.35

GRIP_TILT_MARGIN = GRIP_TILT_DEG / GRIP_BITE_ROOT_DEG          # 1.377
GRIP_BITE_APERTURE_MM = grip_aperture_mm(GRIP_TILT_DEG)        # 5.851
GRIP_BITE_INTERFERENCE_ACTUAL_MM = PUSH_ROD_OD - GRIP_BITE_APERTURE_MM

# THE RELEASE HALF OF THE CYCLE - the half that was never drawn.
# Both plates were modelled RIGID at their bite angle. A drive plate rigid at its
# bite angle does not let go: it holds the rod on the return stroke and drags the
# piston back out, and the caulk-gun load path never closes. In a real caulk gun
# the tilt is LOAD-INDUCED - the plate is loose on the rod at rest (aperture D =
# 6.30 on a 6.00 rod, 0.30 mm of diametral clearance) and the forward drive force
# is what cocks it into the bite. Take the force away and a light return spring
# squares it, and it slides freely back over the rod.
#
# So the drive plate has TWO poses, and both are now checked:
#   BITE   at GRIP_TILT_DEG    aperture 5.851 < 6.00 -> interference, holds 37 N
#   SQUARE at GRIP_SQUARE_DEG  aperture 6.300 > 6.00 -> 0.30 mm clear, slides
GRIP_SQUARE_DEG = 0.0
GRIP_SQUARE_APERTURE_MM = grip_aperture_mm(GRIP_SQUARE_DEG)    # = GRIP_BORE_D
GRIP_SQUARE_CLEARANCE_MM = GRIP_SQUARE_APERTURE_MM - PUSH_ROD_OD

# WHAT IS STILL PUSHING ON THE PLATE WHEN THE SHOT ENDS.
# The first draft of the return spring was specified at 0.3 N on the reasoning
# that "the load is gone, so it only has to move a washer". The load is not
# gone. A syringe piston has seal drag whether or not anything is driving it,
# and that drag is axial on the rod, so it goes through the same wedge that
# makes the plate grip: the plate stays bitten on exactly the force that is
# supposed to have disappeared. Assuming it zero is what would make the release
# check unfailable, so it is declared here as a quantity with a bench task
# against it.
#
# 4.0 N is the middle of the published sustained-glide band for a 10 mL
# polypropylene barrel with a rubber-tipped piston (typically 2-6 N; breakaway
# is higher). BENCH: push a filled cartridge by hand through a 5 kg scale and
# read the plateau. If it measures above 6.6 N the return spring below is
# undersized and has to grow with it.
PISTON_SEAL_DRAG_N = 4.0

# THE SPRING THAT SQUARES THE PLATE, SIZED TO THE MOMENT IT HAS TO BEAT.
# Squaring is a rotation, so the balance is of moments about the plate's rocking
# axis, not of forces. The model's own account of the bite is that axial
# equilibrium puts f = F/2 of friction at each of two bore edges, so a residual
# axial F resists squaring with
#       M_resist = F * GRIP_BORE_D/2      = 4.0 * 3.15  = 12.6 N.mm
# and a spring bearing at the plate's outer radius supplies
#       M_spring = F_s * GRIP_PLATE_OD/2  = F_s * 7.0
# so F_s must exceed 1.80 N. 3.0 N is the next standard rate up and leaves
# 1.67x. It is a light coil, but it is an order of magnitude more than the
# 0.3 N first specified, and the difference between the two is the difference
# between a mechanism that lets go and one that drags the piston back out.
GRIP_RETURN_SPRING_N = 3.0
GRIP_RETURN_SPRING_LEN = 4.0
GRIP_RETURN_SPRING_OD = 9.0

# WHY THE PLATES MUST BE HARDENED AND THE ROD MUST BE STAINLESS.
# Axial equilibrium on a tilted plate gives friction f = F/2 at each of two edge
# contacts, and the wedge supplies whatever normal force that needs - so the
# limit is contact stress, not slip. Hertz line contact at F/2 over the bore
# edge on a 0.2 mm edge radius runs to about 1.3 GPa. That is above any printed
# plastic and above mild steel; it is why this pair is purchased, not printed.
GRIP_EDGE_RADIUS_MM = 0.2
GRIP_LINE_LOAD_N_MM = SPRING_PEAK_N / 2.0 / (math.pi * PUSH_ROD_OD / 4.0)


# ------------------------------------------------------------------- envelope
PLATE_T = 3.0
PLATE_W = 64.0

# Wrist curve. Mk3's baseplate was a full vault and printed on two hairline
# edges (35 mm2 first layer). Here the curve is a shallow relief cut into the
# UNDERSIDE only: the outer rim stays flat so the part still has a wide contact
# band on the bed, and the relief is what cups the arm. WRIST_RADIUS is large on
# purpose - the arm's dorsal crown is ~50 mm, but a 50 mm cup would need a 9 mm
# sagitta and no rim would survive. RELIEF_DEPTH is the honest limit.
WRIST_RADIUS = 95.0             # mm, cylindrical relief radius
RELIEF_DEPTH = 2.2              # mm at the centreline - the sagitta we allow
RELIEF_RIM = 7.0                # mm of flat rim left on each edge for bed contact
WALL = 2.4
RAIL_H = 9.0
RAIL_T = 2.4

CLEAR = 0.25                    # located fit, per side
BORE_CLEAR = 0.30
M3_CLEAR = 3.6                  # printed, at the bed
INSERT_PILOT = 4.5              # 5.0 x 4.0 knurled inserts
INSERT_BOSS_OD = 10.0

# lanes: fluid on -Y, electronics on +Y
FLUID_Y = -16.0
ELEC_Y = 13.0

# =========================================== (Mk5 round 3) THE STATION MAP,
# ============================================ RE-ROOTED AT THE FLUID END
#
# WHY THE CHAIN NOW RUNS BACKWARDS, AND WHAT THAT PAID FOR.
#
# Every revision up to here declared SPRING_X0 = 8.0 at the back of a plate that
# started at x = 0, and then derived the carriage, the syringe and the plate
# length FORWARD from it. Under that chain the gap between the carriage front and
# the syringe was a hard-coded 2.0 mm, so the axial room the drive plate had to
# travel in was
#       PLUNGER_STROKE - SYRINGE_FLANGE_T - 2*half_x  =  3.194 mm
# for a stroke that needs 10.222 mm. The deficit - 7.028 mm, measured by round
# 2's stepper and confirmed to three decimals - was not a spacing mistake. It was
# the arithmetic of a chain rooted at the wrong end: the front of the machine is
# fixed by the barrel and the wrist, so the room for the stroke has to be taken
# out of the BACK, and a chain that grows forward can never take it.
#
# So the root moves to SYRINGE_X0 and everything upstream is DERIVED from the
# clearance the stroke actually requires. The frame then grows rearward by
# whatever that arithmetic asks for, which is the debt round 2 stated and did not
# pay. GRIP_SPAN_DEFICIT_MM is still computed below, from the drawn geometry, and
# is now <= 0 by construction rather than by hope.
SYRINGE_X0 = 54.0                       # ROOT: barrel mouth end of the cradle
SYRINGE_X1 = SYRINGE_X0 + SYRINGE_BARREL_LEN
OUTLET_X0 = SYRINGE_X1
OUTLET_X1 = OUTLET_X0 + OUTLET_LENGTH
MUZZLE_LEN = 14.0
PLATE_L = OUTLET_X1 + MUZZLE_LEN + 6.0  # front edge of the frame, unchanged

SYRINGE_AXIS_Z = PLATE_T + SYRINGE_OD / 2.0 + 0.6
CARRIAGE_Z0 = PLATE_T

# --- the anti-return plate and the abutment that finally carries it ---------
GRIP_ANTIRETURN_X = SYRINGE_X0 - SYRINGE_FLANGE_T - 4.0        # 47.50
GRIP_ANTIRETURN_REAR_X = GRIP_ANTIRETURN_X - GRIP_ANTIRETURN_HALF_X   # 44.896
ANTIRETURN_POST_T = 3.0          # x thickness of the reaction wall
ANTIRETURN_MOUTH_R = GRIP_DRIVE_OD / 2.0 + 0.4   # 7.4: the drive plate's door
ANTIRETURN_POST_X1 = GRIP_ANTIRETURN_REAR_X      # the bearing face itself
ANTIRETURN_POST_X0 = ANTIRETURN_POST_X1 - ANTIRETURN_POST_T
ANTIRETURN_W = 24.0              # y span: clear of the pawl's swept leg

# --- the carriage, sized and placed from the stroke it has to make ----------
# The carriage BODY may not enter the abutment mouth (it is 17.7 x 14.6 and the
# mouth is 14.8 across), so its front face stops CARRIAGE_NOSE_CLEAR short of
# the abutment at full stroke and only the drive plate goes through.
CARRIAGE_LEN = 22.0
CARRIAGE_NOSE_CLEAR = 0.5
CARRIAGE_FRONT_AT_FIRED = ANTIRETURN_POST_X0 - CARRIAGE_NOSE_CLEAR
CARRIAGE_X_FIRED = CARRIAGE_FRONT_AT_FIRED - CARRIAGE_LEN
CARRIAGE_X_COCKED = CARRIAGE_X_FIRED - PLUNGER_STROKE

# The drive plate's front face at full stroke, set by the clearance it must keep
# from the anti-return plate's rear face. This is the number the whole round is
# about: it is DECLARED here as a clearance and the carriage position follows
# from it, instead of being whatever fell out of a forward chain.
GRIP_DRIVE_FRONT_AT_FIRED = (GRIP_ANTIRETURN_REAR_X
                             - GRIP_PLATE_CLEARANCE - GRIP_SPAN_MARGIN)
GRIP_DRIVE_X = (GRIP_DRIVE_FRONT_AT_FIRED - GRIP_DRIVE_HALF_X
                - PLUNGER_STROKE)       # plate centre, carriage COCKED

# --- the spring, and the seat the frame has to grow to reach ----------------
# The spring's front end no longer butts the carriage's rear FACE: it sits in a
# counterbore, and its front seat is that bore's FLOOR. Drawing it against a
# face meant the harness's stepper saw the carriage drive into a rigid spring
# 0.25 mm into the stroke; a spring inside a bore recedes from its own floor as
# the carriage advances, which is what a real spring does.
SPRING_BORE_DEPTH = 5.0
SPRING_FRONT_SEAT_X = CARRIAGE_X_COCKED + SPRING_BORE_DEPTH
SPRING_SEAT_X = SPRING_FRONT_SEAT_X - SPRING_COCKED_LEN   # rear abutment face
SPRING_X0 = SPRING_SEAT_X
SPRING_ABUT_T = 4.0                     # rear abutment wall, reacts 37 N
# Width of the two tail-lane bulkheads (rear abutment, tail rod pillar). Sized
# to clear the battery lane rather than to the rail span: the rails do not reach
# back here, so a bulkhead as wide as them was 27.8 mm of wall whose only
# achievement was 190 mm3 shared with the LiPo.
TAIL_W = 21.0

# --- the rod tail, and therefore the back edge of the frame -----------------
# FILL_LEN is defined further down (it needs SHOTS_PER_FILL), but the frame's
# rear edge is a geometry number and has to exist before make_baseplate runs, so
# the same product is spelled out here and asserted equal to FILL_LEN below.
_FILL_LEN = SHOTS_PER_FILL * PLUNGER_STROKE
ROD_X0 = SPRING_SEAT_X - _FILL_LEN
FRAME_TAIL_CLEAR = 4.0
FRAME_X0 = ROD_X0 - FRAME_TAIL_CLEAR    # rear edge of the baseplate
FRAME_LEN = PLATE_L - FRAME_X0

# (round 4) THE LIPO MOVED FORWARD 86 mm. The tail is where the winch servo
# now lives - it is the only station from which a drum reaches the carriage -
# and 54 mm of battery plus 30 mm of servo do not both fit in 60 mm of tail.
# The pack goes to the mid-forearm stretch of the electronics lane, which was
# empty from x = 19 to x = 60. It is a length along the arm, not a height.
BATT_X0 = 22.0                          # LiPo 54 x 34 x 10, mid-forearm
BATT_X1 = BATT_X0 + 54.0

# --- the single-sweep scroll winch, placed against measured neighbours ------
# Every one of these numbers was chosen against a bounding box printed out of
# the assembly, not against a round number:
#   * the drum lives in the pocket between the spring's rear abutment
#     (x <= -9.605) and the carriage's anchor fork at full cock (x >= 6.32).
#   * its groove plane sits at y = -9.5: outboard of the +Y carriage rail
#     (y = -5.7..-3.3) and inboard of the compression spring's outer coil
#     (y = -20..-12), which is the only 6 mm of Y in the tail that is clear of
#     both the coil and the push-rod (y = -19..-13).
#   * the servo lies flat with its output shaft along +Y, so the drum turns in
#     the XZ plane and the cable pulls straight down the carriage's axis of
#     travel. Its body runs FORWARD from the shaft into the electronics lane,
#     which is why the LiPo moves forward 41 mm (see make_mockups).
WINCH_AXIS_X = -2.2
WINCH_SERVO_Z0 = PLATE_T + 2.0          # sits on a printed cradle, not the plate
WINCH_AXIS_Z = WINCH_SERVO_Z0 + SERVO_W / 2.0
WINCH_SERVO_X0 = WINCH_AXIS_X - SERVO_SHAFT_DX
WINCH_SERVO_Y0 = -2.9                   # shaft face; body runs +Y from here
WINCH_CABLE_Y = -9.5                    # groove plane and cable plane, one number
WINCH_SHAFT_D = 4.8                     # servo spline OD, BENCH: DS239MG

# =========== (Mk5 round 5) LOCK 2: THE DRUM COMES OFF THE SERVO SHAFT ========
#
# THE DEFECT. The recock cable is inextensible, taut, wrapped on a drum, and the
# drum was SPLINED TO THE SERVO SHAFT. The servo is a position servo: it holds.
# So at the instant the sear releases, the carriage's 37.4 N reflected through
# the drawn moment arm (WINCH_R_MIN_EFF + cable radius = 2.276 mm) as 85 N.mm
# against a 451 N.mm stall - the servo wins by 5x and the carriage does not
# move. Four revisions drew that and reported multishot_working.
#
# WHAT WAS PRICED FIRST, AND WHY IT LOST. The brief's preferred fix is for the
# winch servo to return to zero after cocking and pay the cable out, with the
# sear holding full cock. It works, and it costs slack management: the free span
# from the drum's tangent to the anchor pin is 8.72 mm and the slack to be
# swallowed is PLUNGER_STROKE + WINCH_OVERDRAW = 10.47 mm, MORE THAN THE SPAN
# ITSELF. A bow cannot absorb that (the cable folds); a sprung take-up idler can,
# at a deflection of 0.5*sqrt(dL^2 + 2*S*dL) = 8.62 mm, which needs a Ø5 pulley
# on a guided post travelling 8.6 mm in the column directly behind the cocked
# carriage - a new moving envelope on the wrist, a pulley, a pin, a slot and a
# spring, and a drum drawn at a different rotation from the one every winch
# radius in this file is measured at.
#
# THE LOST-MOTION SLOT LOSES OUTRIGHT, and the arithmetic is short. Put the pin
# in a slot in the carriage: to pull the carriage back the pin must bear on the
# slot's REAR wall, so cocking ENDS with the pin on that wall; firing then walks
# the pin to the slot's front. To cock again the pin must reach the rear wall,
# which is now a slot-length BEHIND it, so the winch must pay out a slot length
# and wind in a slot length plus the stroke - 2x the draw at the same 170 deg
# sweep, i.e. 2x the drum radius and 2x the torque. It blows the recock budget.
#
# SO: A ONE-WAY CLUTCH, which the brief explicitly allows. The drum is no longer
# splined to the shaft. It runs on a wrap-spring one-way clutch pressed into its
# hub: the servo DRIVES it in the wind-in direction and OVERRUNS it in the
# pay-out direction. During the shot the carriage pulls the cable, the drum
# free-spools, and the only thing reflected to the carriage is the rewind
# spring's torque plus the clutch's overrun drag - measured below, and checked
# against the geometry in check_release_resistance.
#
# WHAT THIS GIVES UP, STATED PLAINLY:
#   1. Two purchased bodies instead of a splined bore - the clutch and a light
#      rewind spring that keeps the braid seated in an 0.8 mm groove and stops
#      the drum overrunning at the end of the shot and throwing a loop.
#   2. The drum's angle is no longer the servo's angle, so the recock sweep can
#      no longer be pure open-loop position: the servo winds until the carriage
#      seats on the sear and the current rises. The scroll's constant-torque
#      schedule still holds, because drum and servo traverse the same 170 deg
#      every cycle - the clutch only ever slips on the servo's return.
#   3. The drum's inertia is no longer decoupled from the shot by the servo's
#      gear train, it is decoupled by the clutch instead: I/R^2 at the cocked
#      radius is ~9.8 g of effective mass added to the carriage at the start of
#      the stroke, falling to ~1 g by the end as the pitch radius grows.
# NEGATIVE CONTROLS, RUN, NOT ASSERTED. check_release_resistance was driven
# through four mutations of this model and had to fail on three of them:
#   0  as drawn ......................... 0 [release] failures, 4.25x margin
#   1  WINCH_FREESPOOL = False .......... FAILS: "recock_cable is HOLDING the
#      (the round-4 tether, unchanged      carriage ... reflects the full 37.3 N
#       in every other respect)            as 74 N.mm at the shaft"
#   2  clutch body deleted from mockups .. FAILS the same way
#   3  rewind-spring body deleted ........ FAILS the same way
#   4  RECOCK_DRAG_N = 40 ................ FAILS gate 2 at 0.81x
# A flag with no body behind it buys nothing, which is controls 2 and 3.
WINCH_FREESPOOL = True                  # the drum overruns the shaft on pay-out
WINCH_CLUTCH_OD = 8.0                   # wrap-spring one-way clutch, Ø4.8 bore
WINCH_CLUTCH_LEN = 3.0
WINCH_CLUTCH_RETAIN_GAP = 0.20          # retaining-compound joint into the hub
WINCH_CLUTCH_RUN_GAP = 0.20             # coil-to-shaft standoff while overrunning
WINCH_CLUTCH_OVERRUN_N_MM = 1.5         # drag while it slips - BENCH: measure
WINCH_REWIND_TORQUE_N_MM = 2.0          # the rewind spring at full cock

# The hub is bored for the CLUTCH now, not for the spline, so it grows: the bore
# goes 5.30 -> 8.40 and the hub radius 5.00 -> 6.50 to keep a 2.30 mm wall, and
# the hub band widens from 2.0 to 4.6 mm to hold a 4.0 mm clutch. The scroll
# gives up 2.6 mm of that band and takes 1.6 mm back on its outboard face, so
# the drum as a whole is a LARGER body than the one it replaces, not a smaller.
WINCH_HUB_R = 6.5
WINCH_HUB_BORE_D = WINCH_CLUTCH_OD + 2 * WINCH_CLUTCH_RETAIN_GAP
WINCH_HUB_Y1 = WINCH_SERVO_Y0 - 0.2     # 0.2 clear of the servo body face
WINCH_HUB_Y0 = WINCH_HUB_Y1 - (WINCH_CLUTCH_LEN + 0.6)
WINCH_SCROLL_Y0 = WINCH_CABLE_Y - 1.4   # scroll plate band
WINCH_SCROLL_Y1 = WINCH_HUB_Y0
WINCH_CLUTCH_Y0 = WINCH_HUB_Y0 + 0.3    # centred in the hub band
# THE REWIND SPRING: a flat clock spring wound on the HUB'S OUTSIDE DIAMETER,
# inner end on the hub, outer end hooked to a post on the plate. It is what
# keeps D0.6 braid seated in an 0.8 mm groove when the cable tension goes to
# zero and what stops the drum overrunning at the end of the shot and throwing
# a loop. It is drawn because a spring that is only a number cannot be checked
# for fit.
#
# WHY IT IS NOT COAXIAL ON A SPINDLE STUB, which is where a first draft put it.
# The whole outboard side of this drum is already spoken for: the Ø6 push rod
# occupies y -19.00..-13.00 and the Ø8.5 compression spring on it occupies
# -20.25..-11.75, and the drum's disc shares their X and Z everywhere, so only Y
# separates them. The harness measured the result exactly - 38.79 mm3 of drum
# inside the rod, 30.49 mm3 of spring, then 10.35 and 6.65 mm3 against the coil
# when the stub was pulled back. There are 0.85 mm of clear Y outboard of the
# scroll and a 1.7 mm spring does not fit in them. The hub band, on the servo
# side, has room and nothing else is in it.
#
# ITS OUTER RADIUS IS SET BY THE SPRING ABUTMENT BEHIND IT, not chosen. The
# drum lives in the pocket between the compression spring's rear abutment
# (whose face is SPRING_SEAT_X = -9.605) and the carriage, and the winch axis
# stands 7.405 mm forward of that face; a first draft at OR 8.2 put 3.77 mm3 of
# clock spring inside the abutment wall. What is left is a 0.56 mm band - which
# is a real clock spring, 0.4 mm strip with clearance, and it is the whole
# reason the rewind torque is 2 N.mm and not 20.
WINCH_REWIND_IR = WINCH_HUB_R + 0.2     # 0.20 mm clear of the hub it winds on
WINCH_REWIND_OR = min(WINCH_REWIND_IR + 1.5,
                      WINCH_AXIS_X - SPRING_SEAT_X - 0.15)
assert WINCH_REWIND_OR > WINCH_REWIND_IR + 0.4, (
    "no room for a clock spring between the hub and the rear abutment")
WINCH_REWIND_LEN = 2.0
WINCH_REWIND_Y0 = WINCH_HUB_Y0 + 0.2    # 0.20 mm clear of the scroll's flange
assert WINCH_AXIS_Z - WINCH_REWIND_OR >= PLATE_T + 0.15, (
    "the rewind spring is inside the baseplate")
WINCH_GROOVE_Y0 = WINCH_CABLE_Y - WINCH_GROOVE_W / 2.0
WINCH_GROOVE_Y1 = WINCH_CABLE_Y + WINCH_GROOVE_W / 2.0
# The cable leaves the drum straight up, so its centreline sits R_eff above the
# shaft axis and its moment arm about the shaft IS the pitch radius, whatever
# direction it then runs. WINCH_DEPARTURE_DEG is measured in the XZ plane from
# +X toward +Z; the drum is DRAWN at full cock, so the profile angle that is at
# the departure position after `u` of the sweep is DEPARTURE + (1-u)*SWEEP.
WINCH_DEPARTURE_DEG = 90.0
WINCH_CABLE_Z = WINCH_AXIS_Z + WINCH_R_MIN_EFF

# WHAT THE TETHER STILL COSTS THE SHOT, at the worst instant - the drawn full
# cock pose, where the pitch radius is at its MINIMUM and therefore the torque
# the cable has to overcome converts into the LARGEST cable tension.
WINCH_R_AT_COCK = WINCH_R_MIN_EFF + WINCH_CABLE_D / 2.0
WINCH_HOLDBACK_N = ((WINCH_REWIND_TORQUE_N_MM + WINCH_CLUTCH_OVERRUN_N_MM)
                    / WINCH_R_AT_COCK)

# --- the anchor: a fork on the carriage's rear face, and a pin through it ---
# The rocker it replaces reached the carriage with 0.850 mm of bounding-box
# corner. This pin is 4.3 mm long inside a 4.3 mm fork, all of it inside the
# carriage's own y span, so the load path has a bearing width and not a sliver.
# SIZED AGAINST THE CHECK'S OWN PROBE, NOT AGAINST A ROUND NUMBER. The harness
# measures journalled length by asking whether carriage material surrounds the
# pin at bore radius + 0.3 mm, in eight directions, at every station along the
# pin. A 3.0 mm fork on a Ø2 pin puts the +/-X probes 1.55 mm from the pin axis
# against 1.50 mm of fork, so the first draft scored 3.10 mm against a 3.0 mm
# gate - passing on rounding. The fork is 3.6 long and the slot 1.0 wide, which
# is 0.2 mm of clearance each side of a Ø0.6 cable and 3.6 mm of ear.
ANCHOR_FORK_LEN = 3.6                   # how far the fork stands off the rear face
ANCHOR_FORK_Y0 = -11.8                  # 0.2 clear of the compression spring
ANCHOR_FORK_Y1 = -7.2                   # inboard of the carriage's own +Y face
ANCHOR_SLOT_W = 1.0                     # the cable's lane through the fork
ANCHOR_PIN_D = 2.0
ANCHOR_PIN_LEN = 4.4
ANCHOR_PIN_X = CARRIAGE_X_COCKED - ANCHOR_FORK_LEN / 2.0   # world x at full cock
ANCHOR_PIN_Z = WINCH_CABLE_Z
ANCHOR_FORK_Z0 = ANCHOR_PIN_Z - 2.6
ANCHOR_FORK_Z1 = ANCHOR_PIN_Z + 2.6
ANCHOR_SLOT_Y0 = WINCH_CABLE_Y - ANCHOR_SLOT_W / 2.0
ANCHOR_SLOT_Y1 = WINCH_CABLE_Y + ANCHOR_SLOT_W / 2.0
# The cable's dead end is a swaged eye over the pin, so the eye's outer radius
# has to live inside the fork slot - that is what sets the slot's height.
CABLE_EYE_R = ANCHOR_PIN_D / 2.0 + WINCH_CABLE_D / 2.0

# The cradle screw offset has to exist before make_baseplate drills the rib for
# it; the rest of the cradle-screw block still lives with the mockups.
_CRADLE_SCREW_DY = SYRINGE_OD / 2.0 + 2.0

# ----------------------------------------------------------------------- sear
# Pivot ABOVE and FORWARD of the contact so the +X spring load torques the tooth
# down into engagement. Sign is verified in sear_moment_check().
# Vertical-axis pawl. The pivot sits FORWARD of the contact so the carriage's
# +X load rotates the tooth inboard, deeper into engagement (see
# sear_moment_check). Behind the contact it would unlatch itself - which is
# exactly the inversion Mk3 shipped.
# LIFTING pawl, pivoting about Y. A vertical-axis pawl cannot work here: its arm
# crosses the carriage lane at lug height, and the carriage travels ALONG that
# lane, so no rotation about Z ever leaves the swept volume (check_sear_release
# proved it - no angle under 90 deg cleared).
#
# Self-holding condition, from M_y = r_z*F_x and dz = -dtheta*r_x:
#   the tooth moves DOWN under load iff r_x and r_z share a sign.
# So the tooth sits BELOW and BEHIND the pivot. Lifting it releases.
# ENGAGEMENT HEIGHT (Mk4.1). The tooth used to sit at 0.6 mm above the carriage
# body top - which is also where the plunger push pad and the cocking tab live,
# so 109 mm3 of the tooth was inside the pad. The contact plane is now DERIVED
# from the tallest non-lug carriage feature, so it cannot silently sink back in:
# every carriage station declares its height, _CARRIAGE_TOP takes the max, and
# the tooth clears it by SEAR_TOOTH_GAP. The lug is then made tall enough to
# reach up to the tooth, instead of the tooth being dropped down to the lug.
CARRIAGE_LUG_X = 8.0                              # local, from the carriage rear
CARRIAGE_LUG_Y = -4.0                             # local, inboard on the top face
CARRIAGE_LUG_L = 4.0                              # lug length in X at full height
CARRIAGE_LUG_W = 6.0                              # lug width in Y
CARRIAGE_LIFT = 0.4                               # ride height above the plate

# (Mk5 round 3) THE CARRIAGE IS NOW BORED ON THE ROD, AND THAT SETS ITS HEIGHT.
#
# Mk4's carriage was an 8 mm block between the rails with a 12.1 mm push pad on
# the front, because all it had to do was shove a thumb flange. Mk5's carriage
# has to CONTAIN three coaxial things on the fluid axis at z = 12.10: the spring
# in a counterbore, the rod in a bore (which is also defect 9's vertical
# retention, since a carriage threaded on a Ø6 rod cannot lift 3.25 mm off its
# rails), and the drive plate in a pocket. A wall over the Ø8.5 spring bore of
# 1.60 mm - four perimeters at 0.4 - fixes the body height:
#       SYRINGE_AXIS_Z + 8.5/2 + 1.60 - (CARRIAGE_Z0 + CARRIAGE_LIFT)
# THIS IS A HEIGHT INCREASE AND IT IS NOT ABSORBED QUIETLY: the carriage top
# rises 16.40 -> 18.00 mm, and because SEAR_CONTACT_Z is derived from it the
# pawl, the tower and the stack all rise the same 1.60 mm. The wrist profile,
# already 35.50 against a 25 mm target, becomes ~37.1. The 25 mm target is a
# sear-tower problem (the tower alone is 32 of those millimetres) and is round
# 4/5's to solve; what this round owes is the number, which is +1.60 mm.
SPRING_BORE_D = SPRING_OD + 0.5                   # 8.50, coil clearance
CARRIAGE_ROD_BORE_D = PUSH_ROD_OD + 2 * CLEAR     # 6.50
CARRIAGE_CROWN_T = 1.60                           # wall over the spring bore
CARRIAGE_BODY_H = (SYRINGE_AXIS_Z + SPRING_BORE_D / 2.0 + CARRIAGE_CROWN_T
                   - (CARRIAGE_Z0 + CARRIAGE_LIFT))          # 14.55

# The push pad and the thumb tab are DELETED, not shrunk. The pad pushed a
# thumb flange that Mk5 cuts off the syringe, and the tab hand-cocked a carriage
# that the rocker's hex stub now hand-cocks with a proper lever. Both were
# features of a mechanism that no longer exists; keeping them would be keeping
# height on the wrist for nothing.
#
# tallest carriage feature that is NOT the sear lug, in world Z
_CARRIAGE_TOP = CARRIAGE_Z0 + CARRIAGE_LIFT + CARRIAGE_BODY_H

SEAR_TOOTH_H = 4.0                                # engaged height of the tooth
SEAR_TOOTH_L = 4.0                                # tooth length in X
SEAR_TOOTH_GAP = 0.8                              # tooth underside over the pad

_LUG_FRONT = (CARRIAGE_X_FIRED - PLUNGER_STROKE
              + CARRIAGE_LUG_X + CARRIAGE_LUG_L)

SEAR_CONTACT_X = _LUG_FRONT                       # tooth blocks the lug's front face
SEAR_CONTACT_Y = FLUID_Y + CARRIAGE_LUG_Y
SEAR_CONTACT_Z = _CARRIAGE_TOP + SEAR_TOOTH_GAP   # tooth underside, above the pad

# the lug must reach the tooth and overtop it, so the abutting faces are the
# lug FRONT and the tooth REAR - never a tooth top against a lug top.
CARRIAGE_LUG_H = ((SEAR_CONTACT_Z + SEAR_TOOTH_H + 0.4)
                  - (CARRIAGE_Z0 + CARRIAGE_LIFT + CARRIAGE_BODY_H))
_LUG_TOP = CARRIAGE_Z0 + CARRIAGE_LIFT + CARRIAGE_BODY_H + CARRIAGE_LUG_H

SEAR_PIVOT_X = SEAR_CONTACT_X + 9.0               # forward of the tooth
# (round 5) -31.00 -> -31.45. At pivot height the TAIL sweeps down through the
# rails' own Z band, and the sear slab's inboard face at -28.50 overlapped the
# outboard rail's outboard face at -28.70 by 0.20 mm: measured 0.006 mm3 at
# 18 deg of release rotation growing to 7.01 mm3 at 45 deg, i.e. inside the
# 31 deg the release actually needs. Moving the pivot 0.45 mm outboard puts the
# slab face at -28.95, 0.25 mm clear of the rail, and the first contact with
# anything moves from 18 deg to the angle at which the tail dips below the
# plate's top face - about 57 deg, past every angle the mechanism uses.
SEAR_PIVOT_Y = -31.45                             # outboard, clear of the lane

# ============ (Mk5 round 5) ARCHITECTURE B: THE CONTACT MOVES ONTO THE PIVOT LINE
#
# LOCK 1. Four revisions shipped with the pivot 13.40 mm ABOVE the tooth, and
# every one of them reported the same arithmetic: |r_z|*F = 13.40 x 37.25 =
# 499 N.mm of holding moment alone, 639 N.mm with friction and pin drag, against
# 150 N.mm of honest servo. The device fired ZERO times under power. Being
# strongly self-holding and being openable are the same axis and Mk4 maximised
# the wrong end of it.
#
# The brief's architecture B is a GEOMETRIC change, not a note: put the contact
# on the pivot line. The holding moment is r_z * F and nothing else, so driving
# r_z to 1.20 mm drives the holding moment to 44.7 N.mm - a factor of 11 - and
# what is left is friction, which is what a real sear releases against.
#
# WHY 1.20 AND NOT 0.00. At exactly r_z = 0 the tooth is neutral: the load
# neither closes nor opens it, and the ONLY thing holding it is the spring. A
# small negative r_z keeps sear_moment_check()'s sign (tooth below AND behind
# the pivot => load drives it deeper) so a spring failure still leaves the sear
# closing rather than opening, at a holding moment the servo can beat five times
# over. 1.20 mm is the smallest offset that survives the 0.25 mm print
# tolerance stack on the pin bore and the tooth seat with margin.
#
# WHAT THIS COSTS, STATED: the sear is no longer self-holding enough to stay
# engaged on its own against vibration and the cocking impact, so it needs the
# light engagement spring below - exactly what every real firearm sear has.
# One purchased body, drawn in make_mockups() as sear_torsion_spring, with a
# declared rate and preload that check_servo_torque adds to the release moment.
SEAR_PIVOT_RISE = 1.20                            # pivot above the contact, mm
SEAR_PIVOT_Z = SEAR_CONTACT_Z + SEAR_PIVOT_RISE
assert SEAR_PIVOT_RISE <= 1.5, "architecture B needs |r_z| <= 1.5 mm"
SEAR_W = 5.0                                      # slab thickness, measured in Y
SEAR_TAIL_LEN = 24.0
SEAR_POST_R = 3.0
SEAR_BACK = SEAR_PIVOT_X - SEAR_CONTACT_X         # tooth is this far behind
SEAR_DROP = SEAR_PIVOT_Z - SEAR_CONTACT_Z         # and this far below

# THE ENGAGEMENT SPRING that architecture B requires, with real numbers.
# A torsion spring on the pivot pin, one leg on the tower, one on the sear's
# tail, winding the tooth DOWN into the lug. It is sized by the two jobs it has
# and by nothing else:
#   (a) hold the tooth seated against the pawl's own weight and against the
#       cocking impact. The pawl masses ~2.2 g of PETG with its centre of mass
#       ~8 mm from the pivot, i.e. ~0.17 N.mm of gravity moment; 12 N.mm of
#       preload is a 70x margin on that and still only 8% of the friction the
#       servo already has to beat.
#   (b) re-close the tooth after the cocking ramp has cammed it open, against
#       pin drag at zero load - which is microscopic once the spring is off.
# Rate is deliberately low so the wind-up over the release sweep stays small:
# at the certified release angle the spring adds RATE * angle on top of PRELOAD,
# and check_servo_torque charges the servo for the value at FULL release, not at
# first movement.
SEAR_SPRING_PRELOAD_N_MM = 8.0                    # at the engaged (0 deg) pose
SEAR_SPRING_RATE_N_MM_PER_DEG = 0.25              # torsion rate, wound up on release

# WHERE THE TAIL ENDS, AND WHY IT IS SHORTER THAN MK4'S.
# The tail is the servo's moment arm, so longer is cheaper - but it is also the
# part of the pawl that sweeps FORWARD AND DOWN through the release rotation,
# and at pivot height that arc now reaches into the cartridge. Measured: the
# Mk4 tail (tip 27.0 mm out) put 4.65 mm3 into the syringe's finger flange at
# 19 deg of release - inside the working sweep, not past it. The flange's rear
# face stands at x = 51.50, the pivot at SEAR_PIVOT_X, so the tip radius is
# capped by the DISTANCE TO THE CARTRIDGE and the arm is what is left over.
SEAR_TAIL_TIP_X = 20.0                            # local x of the tail's tip
SEAR_ACTUATION_ARM_MM = SEAR_TAIL_TIP_X           # servo pushrod lands on the tip
_SEAR_TAIL_SWEPT_R = math.hypot(SEAR_TAIL_TIP_X, 4.0 - 2.0)
assert SEAR_PIVOT_X + _SEAR_TAIL_SWEPT_R <= SYRINGE_X0 - SYRINGE_FLANGE_T - 0.5, (
    "the sear tail's swept circle reaches the cartridge's finger flange")

# ==================================================== THE RE-COCKING RAMP
# Mk4 up to this revision fired exactly once. The tooth's cocking-side face and
# the lug's rear face were both square walls at right angles to the travel axis,
# so pushing the carriage back drove a flat into a flat: the carriage stopped
# dead and re-cocking meant holding the pawl's tail up with a second hand. That
# is not a mechanism, it is a single-shot prop, and no check in the harness had
# ever looked at the return stroke.
#
# The fix is a matched pair of ramps - the tooth's front (cocking-side) face and
# the lug's rear face - so the returning lug lifts the pawl itself and the pawl
# drops back in behind it: a one-way ratchet. The FIRING-side faces (tooth rear,
# lug front) stay exactly square and exactly abutting; they are what carries the
# spring, and nothing below touches them.
#
# THE RAMP ANGLE IS DERIVED, NOT PICKED.
# Measure it as the angle between the contact normal and the travel axis, which
# is what the harness measures: 0 deg is the wall this replaces.
#
# A block pushed against a ramp slides up it instead of jamming when the driving
# component beats friction: sin(g) * F > mu * cos(g) * F, i.e. tan(g) > mu. That
# is the bare slip condition. Two things make the bare condition not enough:
#
#   1. the pawl is not a free block, it is a lever on a pin, and the pin's own
#      friction resists. The cam force reacts at the pivot, so it drags a torque
#      mu * N * SEAR_PIN_R against a lifting torque N * (ramp term) * R_CAM,
#      where R_CAM is the pawl's OWN moment arm from the pivot to the contact.
#      That is exactly an increase of the effective friction coefficient by the
#      arm ratio SEAR_PIN_R / R_CAM - the sear's own geometry, not a fudge.
#   2. mu itself is a printed-plastic estimate, so the ramp is required to beat
#      it by RAMP_CAM_MARGIN, not to merely equal it.
RAMP_MU = 0.35              # PETG on PETG, dry, as-printed faces
RAMP_CAM_MARGIN = 1.5       # required tan(ramp) / mu before it is self-camming
SEAR_PIN_R = 1.75           # the pawl's pivot bore radius - where pin drag acts

# moment arm from the pivot to the cocking contact, measured on the tooth's
# FRONT face (the face the lug actually meets), before the ramp shortens it -
# the shorter arm is the pessimistic one, so the ramp comes out steeper.
_R_CAM = math.hypot(SEAR_BACK - SEAR_TOOTH_L, SEAR_DROP)
RAMP_MU_EFF = RAMP_MU * (1.0 + SEAR_PIN_R / _R_CAM)
RAMP_NORMAL_DEG = math.degrees(math.atan(RAMP_MU_EFF * RAMP_CAM_MARGIN))
RAMP_TAN = math.tan(math.radians(RAMP_NORMAL_DEG))
assert RAMP_TAN > RAMP_MU * RAMP_CAM_MARGIN, "ramp does not cam against mu"

# HOW FAR THE RAMPS RUN.
# The two surfaces have to be ramped over every height at which they can meet,
# or the lug finds the leftover square face and the cam angle collapses to 0
# there. The sear side must be ramped from the tooth's underside up past the lug
# top; the lug side from its top down past the tooth's underside.
_RAMP_TOP_Z = _LUG_TOP + 0.4                       # a hair over the lug top
SEAR_RAMP_BAND = _RAMP_TOP_Z - SEAR_CONTACT_Z      # sear-side ramped height
SEAR_RAMP_RUN = SEAR_RAMP_BAND * RAMP_TAN
_LUG_RAMP_BOT_Z = SEAR_CONTACT_Z - 0.2             # a hair under the tooth
LUG_RAMP_BAND = _LUG_TOP - _LUG_RAMP_BOT_Z         # lug-side ramped height
LUG_RAMP_RUN = LUG_RAMP_BAND * RAMP_TAN

# THE LUG IS LENGTHENED REARWARD BY ITS OWN RAMP RUN, so that chamfering the
# rear does not eat the lug: the full-length top still spans CARRIAGE_LUG_L and
# the FRONT face - the bearing face - does not move by a micron.
CARRIAGE_LUG_X0 = CARRIAGE_LUG_X - LUG_RAMP_RUN

# ================================== HOW WIDE THE TOOTH HAS TO BE, IN Y
# The lug is a sliding block between two rails and the fit clearance the rails
# are drawn with is real travel. Clear span between the rails is
# (2*inner - RAIL_T) and the carriage body is (2*inner - 2*RAIL_T - 2*CLEAR)
# wide, so the block can wander RAIL_T + 2*CLEAR side to side - the `inner`
# terms cancel, which is why this is exact and not a measurement.
#
# At nominal the lug sat fully on the tooth. Half a millimetre of that wander
# walked the lug off the tooth's inboard end and dropped the bearing patch to
# 16 mm2, under the harness's own 20 mm2 floor, with the spring still on it. So
# the tooth is sized to CAPTURE the lug across the whole play band with margin,
# rather than to meet it at nominal.
CARRIAGE_Y_PLAY = (RAIL_T + 2 * CLEAR) / 2.0       # +/- 1.45 mm, derived
TOOTH_CAPTURE_MARGIN = 0.5                         # mm of tooth beyond the band
_LUG_Y_INBOARD = FLUID_Y + CARRIAGE_LUG_Y + CARRIAGE_LUG_W / 2.0
_LUG_Y_OUTBOARD = FLUID_Y + CARRIAGE_LUG_Y - CARRIAGE_LUG_W / 2.0

# =========== (Mk5 round 5) THE LANE LINE - WHAT ARCHITECTURE B MADE NECESSARY
# With the pivot 13.40 mm above the tooth, every member of the pawl except the
# tooth itself sat above everything the carriage owns, so their Y extents were
# free. At pivot height they are level with the carriage body top, and the ONE
# rule that keeps the pawl out of the carriage is: below the lug top, sear
# material exists only outboard of SEAR_LANE_Y.
#
# SEAR_LANE_Y is the carriage's OUTBOARD-MOST reachable face - its drawn face
# taken out by the full lateral play the rails permit - expressed in the pivot's
# own Y frame. It is derived from the same `inner` and RAIL_T that build the
# rails and the carriage body, so it cannot drift out of step with them.
_CARRIAGE_BODY_W = 2 * (SYRINGE_OD / 2.0 + 3.0) - 2 * RAIL_T - 2 * CLEAR
SEAR_LANE_Y = ((FLUID_Y - _CARRIAGE_BODY_W / 2.0 - CARRIAGE_Y_PLAY)
               - SEAR_PIVOT_Y)                     # 4.70 local
SEAR_JOG_Y = SEAR_LANE_Y - 1.10                    # 3.60, the jog stops here
SEAR_TOOTH_Y0 = SEAR_W / 2.0 + 0.30                # 2.80, tooth root inside the jog
SEAR_RAMP_Y0 = SEAR_W / 2.0                        # 2.50, the slab's outboard face
assert SEAR_TOOTH_Y0 < SEAR_JOG_Y, "tooth root does not overlap the jog in Y"
assert SEAR_JOG_Y < SEAR_LANE_Y, "the jog reaches into the carriage lane"
assert SEAR_RAMP_Y0 <= SEAR_TOOTH_Y0, "the tooth has an unramped root face"

# The pivot is a CLEVIS: the tower is slotted and the sear hub journals inside
# it. The slot was previously cut 5.5 mm wide out of a 6 mm tower, leaving two
# 0.25 mm walls that the hub and cross-arm passed straight through (17 mm3).
# Size the tower FROM the slot instead, so real walls are guaranteed.
SEAR_SLOT_W = SEAR_W + 2 * CLEAR                  # 5.50 mm
TOWER_WALL = 2.5                                  # each cheek of the clevis
TOWER_W = SEAR_SLOT_W + 2 * TOWER_WALL            # 10.50 mm
SEAR_HUB_R = 3.4
TOWER_TOP_Z = SEAR_PIVOT_Z + 3.0                  # 3 mm of cheek over the pin bore
TOWER_BASE_Z = PLATE_T                            # the footing pad's top face

# (Mk4.2) THE CLEVIS SLOT IS A THROUGH-SLOT, NOT A POCKET.
# It used to be a 3*SEAR_POST_R = 9 mm tall box starting 1.5*SEAR_POST_R below
# the pivot, so it bottomed at z = 26.10. The sear's swept envelope inside the
# tower's X band reaches z = 26.16 at 30 deg, 24.77 at 45 and 21.40 at 60 - the
# tail root swings straight into the pocket floor (measured: 0.0278 mm3 at 30,
# 4.56 at 45, 31.9 at 60). A floor sized from that envelope would be a number
# tuned to one sweep limit and would fail the moment the servo overtravelled,
# so the floor is removed instead: the slot runs the full height of the tower,
# from the footing pad up past the tower top. The slab band then has no tower
# material at ANY z, which is a property of the shape rather than of a limit.

# (Mk4.3) INBOARD FACE, CHEEK RELIEF, AND A DEFINED REST POSE.
#
# Mk4.2 kept the jog and the leg out of the inboard cheek by pushing their rear
# faces OUT to radius hypot(SEAR_POST_R + CLEAR, 3 + CLEAR) = 4.596 mm. That paid
# for clearance with the pawl's own geometry, and it left the pawl with no rest
# pose at all: nothing stopped its forward rotation until the LEG fouled the
# cheek's rear face at -6.70 deg (measured: the shared volume appears at local
# x = -3.000, z = -13.9..-8.0, i.e. the cheek's rear face, y 2.75..5.25). At that
# drooped angle the tooth met the lug on a 2.38 mm2 corner after 1.16 mm of free
# creep - numbers from check_sear_rest_pose, not from this comment.
#
# So the face goes back to x = -4.000 and the CHEEK gives way instead.
SEAR_INBOARD_X = 4.0        # local x of the jog's and the leg's rear/front face

# WHY THE CHEEK CAN GIVE WAY, AND EXACTLY HOW MUCH.
# Work in the pivot's own polar frame (r, phi) in the XZ plane; release rotation
# decreases phi, so every inboard feature sweeps an arc of constant r. The
# inboard cheek is the box x in [-SEAR_POST_R, +SEAR_POST_R], z <= +3, so its
# outer radius as a function of phi is 3/|sin phi| where the top face bounds it
# and 3/|cos phi| where the rear face does. The sweeping face sits at x = -4.0,
# so at the SAME phi it is at 4/|cos phi| - a factor 4/3 further out than the
# cheek everywhere the rear face is the binding surface (phi in 180..270). The
# only place the cheek reaches further than the face is around its top-rear
# corner, (x, z) = (-SEAR_POST_R, +(TOWER_TOP_Z - SEAR_PIVOT_Z)), radius
# CHEEK_CORNER_R = 4.2426 > 4.0. That corner, and only that corner, is what the
# Mk4.2 setback was buying clearance from - and the cheek only has to carry the
# pin, so the corner is expendable.
#
# Relieve it on an ARC ABOUT THE PIVOT, at the radius the sweeping face reaches
# minus CLEAR. Then the deepest cheek material anywhere in the upper-rear
# quadrant is CHEEK_RELIEF_R and the nearest sear material is SEAR_INBOARD_X, at
# every angle at once - a property of the arc, not of a sampled sweep.
CHEEK_CORNER_R = math.hypot(SEAR_POST_R, TOWER_TOP_Z - SEAR_PIVOT_Z)   # 4.2426
CHEEK_RELIEF_R = SEAR_INBOARD_X - CLEAR                                # 3.750
assert CHEEK_RELIEF_R + CLEAR <= SEAR_INBOARD_X, "relief is inside the sweep"
assert CHEEK_RELIEF_R < CHEEK_CORNER_R, "relief never reaches the corner"

# THE FORWARD ROTATION STOP.
# The rest pose must be a designed abutment, not whichever face fouls first. The
# stop is a PAD on the tower's rear face whose own rear face is COPLANAR with the
# sear's inboard face at 0 deg, so the leg and the lower jog bottom on it flat
# (~40 mm2) with zero shared volume.
#
# It is a vertical face and not a ledge under the jog because there is nowhere to
# put a ledge: in the inboard cheek's Y band the LEG already occupies the space
# directly under the jog, and the only band where the jog overhangs nothing is
# y in [0, 2.5] - inside the clevis slot, where a floor is precisely what Mk4.2
# had to delete.
#
# It cannot re-enter the swept envelope. A point of the sear's inboard face at
# height z0 travels x(theta) = -SEAR_INBOARD_X*cos(theta) + z0*sin(theta); for
# z0 < 0 that leaves the pad immediately, and solving x = -SEAR_INBOARD_X again
# gives z = +|z0|. So the face only returns to the pad's plane ABOVE the pivot,
# and any pad capped at or below z = 0 is out of reach for every theta > 0.
SEAR_STOP_TOP = -1.0        # local z of the pad's top face
assert SEAR_STOP_TOP <= 0.0, "a stop above the pivot re-enters the sweep"

# =============================================================== small helpers
def _box(l, w, h, x=0.0, y=0.0, z=0.0):
    return (cq.Workplane("XY").box(l, w, h, centered=(False, True, False))
            .translate((x, y, z)).val())


def _cyl_x(length, r, x, y, z):
    return (cq.Workplane("YZ").circle(r).extrude(length)
            .translate((x, y, z)).val())


def _cyl_z(height, r, x, y, z):
    return (cq.Workplane("XY").circle(r).extrude(height)
            .translate((x, y, z)).val())


def _cyl_y(length, r, x, y, z):
    """Cylinder whose axis is +Y, starting at y and running `length` in +Y.

    Built from makeCylinder rather than a named workplane: cq.Workplane("XZ")
    extrudes along -Y, which is how the old pivot-pin cut started at y=-38 and
    ran AWAY from the tower it was meant to drill.
    """
    return cq.Solid.makeCylinder(r, length, cq.Vector(x, y, z), cq.Vector(0, 1, 0))


def _fuse(*shapes):
    out = shapes[0]
    for s in shapes[1:]:
        out = out.fuse(s)
    return out.clean()


def _ground(shape):
    """Drop a part so its own minimum Z sits at 0 — how it meets the bed."""
    b = shape.BoundingBox()
    return shape.moved(cq.Location(cq.Vector(0, 0, -b.zmin)))


@dataclass
class Placed:
    shape: cq.Shape
    location: cq.Location

    def world(self) -> cq.Shape:
        return self.shape.moved(self.location)


# ==================================================================== part 1/5
def make_baseplate() -> cq.Shape:
    """Flat plate with two rails. Flat because a vaulted plate gave Mk3 a 35 mm2
    first layer; the arm curve is taken up by foam, not by the print."""
    # (Mk5 round 3) THE FRAME GROWS REARWARD. It starts at FRAME_X0, not 0.
    # FRAME_X0 is derived, not chosen: it is the rod's tail at full charge plus
    # a clearance. Two debts are paid by the one extension - the stroke needs
    # the rear abutment behind x = 0, and the push-rod's tail was previously
    # standing 48 mm off the back of the frame in mid-air and driving 67.86 mm3
    # of itself straight through the abutment wall.
    plate = _box(FRAME_LEN, PLATE_W, PLATE_T, FRAME_X0, 0.0, 0.0)

    # Shallow cylindrical relief in the underside, inboard of a flat rim.
    # The cylinder sits BELOW the plate so its top surface is highest on the
    # centreline - that is what cups the arm. (Centring it above hollows the
    # edges instead, which is the opposite of a wrist curve.)
    relief_w = PLATE_W - 2 * RELIEF_RIM
    cyl_z = RELIEF_DEPTH - WRIST_RADIUS
    cutter = (cq.Workplane("YZ").circle(WRIST_RADIUS).extrude(FRAME_LEN + 20.0)
              .val().moved(cq.Location(cq.Vector(FRAME_X0 - 10.0, 0.0, cyl_z))))
    keep = _box(FRAME_LEN + 20.0, relief_w, PLATE_T + 6.0,
                FRAME_X0 - 10.0, 0.0, -3.0)
    plate = plate.cut(cutter.intersect(keep))

    # carriage ways: two rails either side of the fluid lane. They now start
    # just behind the COCKED carriage rather than at a hard-coded x, and stop
    # short of the syringe: the length between those two is the only length
    # they were ever guiding.
    inner = SYRINGE_OD / 2.0 + 3.0
    rail_x0 = CARRIAGE_X_COCKED - 0.4
    rail_len = (SYRINGE_X0 - SYRINGE_FLANGE_T - CLEAR - 0.5) - rail_x0
    for sgn in (-1, 1):
        y = FLUID_Y + sgn * inner
        plate = _fuse(plate, _box(rail_len, RAIL_T, RAIL_H, rail_x0, y, PLATE_T))

    # spring rear abutment - reacts the full spring force into the plate. Its
    # FRONT face is SPRING_SEAT_X by construction (see the assert on
    # SPRING_TRUE_COCKED_N), and it is BORED for the rod: the tail passes
    # through it on every shot and used to occupy 67.86 mm3 of it.
    abut = _box(SPRING_ABUT_T, TAIL_W, RAIL_H + 6.0,
                SPRING_SEAT_X - SPRING_ABUT_T, FLUID_Y, PLATE_T)
    abut = abut.cut(_cyl_x(SPRING_ABUT_T + 4.0, CARRIAGE_ROD_BORE_D / 2.0,
                           SPRING_SEAT_X - SPRING_ABUT_T - 2.0,
                           FLUID_Y, SYRINGE_AXIS_Z))
    plate = _fuse(plate, abut)

    # TAIL ROD SUPPORT. The rod's tail cantilevers ~50 mm behind the abutment at
    # full charge; one bored pillar near the back of the extension carries it,
    # and the rod withdraws through the pillar as the cartridge empties.
    tail_pillar_x = FRAME_X0 + 6.0
    pil = _box(6.0, TAIL_W, SYRINGE_AXIS_Z + 5.0,
               tail_pillar_x, FLUID_Y, PLATE_T)
    pil = pil.cut(_cyl_x(10.0, CARRIAGE_ROD_BORE_D / 2.0, tail_pillar_x - 2.0,
                         FLUID_Y, SYRINGE_AXIS_Z))
    # witness slot: the protruding tail is the charge gauge, and it has to be
    # visible, so the pillar is a yoke and not a wall.
    pil = pil.cut(_box(10.0, TAIL_W - 9.0, 6.0,
                       tail_pillar_x - 2.0, FLUID_Y, SYRINGE_AXIS_Z + 4.0))
    plate = _fuse(plate, pil)

    # ANTI-RETURN ABUTMENT (round 3 constraint 1). The anti-return plate carries
    # the whole 37 N return reaction and its nearest solid was 2.10 mm away. The
    # bearing face is this wall's FRONT face, at GRIP_ANTIRETURN_REAR_X, and the
    # mouth through it is ANTIRETURN_MOUTH_R = 7.40 - large enough that the
    # Ø14 drive plate passes through at full stroke and small enough that the
    # Ø18 anti-return plate beds on a 7.40..11 mm annulus of it.
    # Width: the pawl's leg sweeps down the outboard side at y = -28.50, so the
    # wall stops at -28.00. Sized to the sweep it has to miss, measured, not to
    # the rail span it does not need.
    ar = _box(ANTIRETURN_POST_T, ANTIRETURN_W,
              SYRINGE_AXIS_Z + 11.0, ANTIRETURN_POST_X0, FLUID_Y, PLATE_T)
    ar = ar.cut(_cyl_x(ANTIRETURN_POST_T + 4.0, ANTIRETURN_MOUTH_R,
                       ANTIRETURN_POST_X0 - 2.0, FLUID_Y, SYRINGE_AXIS_Z))
    plate = _fuse(plate, ar)

    # WINCH SERVO CRADLE. Defect 3 was "no servo interface exists anywhere"; the
    # rocker pin bearings this replaces carried a rocker that no longer exists.
    # Two pads under the servo's ends hold it CLEAR of the plate by exactly the
    # located-fit clearance - it is screwed down through its own ears, it does
    # not rest on printed plastic - and two walls locate it in X so the drum
    # cannot walk into the abutment behind it or the carriage in front.
    _wsy = WINCH_SERVO_Y0 + SERVO_H / 2.0
    for px in (WINCH_SERVO_X0, WINCH_SERVO_X0 + SERVO_L - 3.0):
        plate = _fuse(plate, _box(3.0, SERVO_H, WINCH_SERVO_Z0 - CLEAR - PLATE_T,
                                  px, _wsy, PLATE_T))
    for wx in (WINCH_SERVO_X0 - CLEAR - 2.25, WINCH_SERVO_X0 + SERVO_L + CLEAR):
        plate = _fuse(plate, _box(2.25, SERVO_H, 11.0, wx, _wsy, PLATE_T))

    # syringe cradle: a trough plus two ribs that capture the barrel
    cradle_r = SYRINGE_OD / 2.0 + BORE_CLEAR
    for cx in (SYRINGE_X0 + 6.0, SYRINGE_X1 - 12.0):
        rib = _box(6.0, SYRINGE_OD + 2 * 4.0, SYRINGE_AXIS_Z + 2.0, cx, FLUID_Y, PLATE_T)
        rib = rib.cut(_cyl_x(8.0, cradle_r, cx - 1.0, FLUID_Y, SYRINGE_AXIS_Z))
        # open the top so the cartridge drops in
        rib = rib.cut(_box(8.0, 2 * cradle_r * 0.72, 20.0,
                           cx - 1.0, FLUID_Y, SYRINGE_AXIS_Z))
        # (round 4) THE SCREWS NOW LAND IN THE RIB, SO THE RIB IS DRILLED.
        # While CRADLE_SCREW_DY put them 1 mm outside the rib they had nothing
        # to pass through and the harness saw no interface at all; moving them
        # into material is what makes the missing hole visible.
        for sy in (FLUID_Y + _CRADLE_SCREW_DY, FLUID_Y - _CRADLE_SCREW_DY):
            rib = rib.cut(_cyl_z(SYRINGE_AXIS_Z + 6.0, M3_CLEAR / 2.0,
                                 cx + 3.0, sy, PLATE_T - 1.0))
        plate = _fuse(plate, rib)

    # forward thrust face — the barrel is driven +X at ~5.6 N and must react here
    stop = _box(WALL + 1.0, SYRINGE_OD + 8.0, SYRINGE_AXIS_Z + 4.0,
                SYRINGE_X1 + 0.5, FLUID_Y, PLATE_T)
    stop = stop.cut(_cyl_x(10.0, SYRINGE_OD / 2.0 + 2.2 + BORE_CLEAR,
                       SYRINGE_X1 - 1.0, FLUID_Y, SYRINGE_AXIS_Z))
    plate = _fuse(plate, stop)

    # sear pivot tower: a CLEVIS rising outboard of the lane, carrying a
    # transverse Y pin. Its width is derived from the slot (TOWER_W), so the
    # cheeks are TOWER_WALL thick by construction; sizing the tower first and
    # cutting the slot second is what left 0.25 mm cheeks for the hub to pass
    # through. It also needs a footing: at SEAR_PIVOT_Y the plate edge is at
    # -PLATE_W/2, so the outboard cheek would otherwise start in mid-air.
    plate = _fuse(plate, _box(2 * SEAR_POST_R + 8.0, TOWER_W + 2.0, PLATE_T,
                              SEAR_PIVOT_X - SEAR_POST_R - 4.0,
                              SEAR_PIVOT_Y, 0.0))
    tower = _box(2 * SEAR_POST_R, TOWER_W, TOWER_TOP_Z - TOWER_BASE_Z,
                 SEAR_PIVOT_X - SEAR_POST_R, SEAR_PIVOT_Y, TOWER_BASE_Z)
    plate = _fuse(plate, tower)
    # FORWARD ROTATION STOP: a pad on the tower's rear face, running from the
    # footing up to SEAR_STOP_TOP, whose rear face sits at the sear's own
    # inboard plane. Fused BEFORE the slot cut, so the slot opens its middle and
    # what remains is a stop face on each cheek; only the inboard one is reached.
    plate = _fuse(plate, _box(
        SEAR_INBOARD_X - SEAR_POST_R, TOWER_W,
        (SEAR_PIVOT_Z + SEAR_STOP_TOP) - TOWER_BASE_Z,
        SEAR_PIVOT_X - SEAR_INBOARD_X, SEAR_PIVOT_Y, TOWER_BASE_Z))
    # THROUGH-SLOT, not a pocket: full height of the tower, from the footing pad
    # top up past the tower top, and past the tower in X at both ends. There is
    # therefore no tower material anywhere in the slab band, at any Z, so no
    # rotation of the pawl can bottom out on a slot floor. The two cheeks stay
    # joined through the footing pad, which the slot does not reach.
    plate = plate.cut(_box(3 * SEAR_POST_R, SEAR_SLOT_W,
                           (TOWER_TOP_Z + 3.0) - TOWER_BASE_Z,
                           SEAR_PIVOT_X - 1.5 * SEAR_POST_R, SEAR_PIVOT_Y,
                           TOWER_BASE_Z))
    # CHEEK CORNER RELIEF. Take the upper-rear quadrant of the tower (the only
    # quadrant where the cheek reaches further from the pivot than the sear's
    # inboard face does) and remove everything in it that stands outside
    # CHEEK_RELIEF_R. What is left is an arc concentric with the pivot, so the
    # clearance to the sweeping face is CLEAR at every angle rather than at the
    # angles a sweep happened to sample. The pin bore keeps a full
    # CHEEK_RELIEF_R - (SEAR_PIN_R + CLEAR) = 1.75 mm collar all the way round.
    quad = _box(SEAR_POST_R + 1.0, TOWER_W + 2.0,
                (TOWER_TOP_Z - SEAR_PIVOT_Z) + 1.0,
                SEAR_PIVOT_X - SEAR_POST_R - 1.0, SEAR_PIVOT_Y, SEAR_PIVOT_Z)
    plate = plate.cut(quad.cut(_cyl_y(
        TOWER_W + 8.0, CHEEK_RELIEF_R, SEAR_PIVOT_X,
        SEAR_PIVOT_Y - TOWER_W / 2.0 - 4.0, SEAR_PIVOT_Z)))

    # pivot pin bore, on the Y axis, through BOTH cheeks
    # (round 5) BORED FOR A SLIP FIT, not for the pin's own radius. At 1.70 the
    # bore and the Ø3.40 dowel were the same size to the micron, so the drawn
    # gap was 0.000 mm - a press fit in a printed hole, which is how a pivot pin
    # ends up either loose or split. SEAR_PIN_R + CLEAR leaves 0.30 mm on the
    # radius and the pin is retained by an E-clip on its outboard stub.
    plate = plate.cut(_cyl_y(TOWER_W + 12.0, SEAR_PIN_R + CLEAR, SEAR_PIVOT_X,
                             SEAR_PIVOT_Y - TOWER_W / 2.0 - 6.0, SEAR_PIVOT_Z))

    # electronics shelf ribs (open, so nothing prints in mid-air)
    for cx in (BATT_X1 + 6.0, BATT_X1 + 16.0):
        plate = _fuse(plate, _box(4.0, 26.0, 6.0, cx, ELEC_Y, PLATE_T))

    # FINGER-FLANGE RELIEF (defect 5's residue). The Ø26 collar on the barrel
    # reaches z = -0.90, i.e. 3.90 mm into a 3 mm plate: 125.63 mm3 of it was
    # inside the baseplate. The cartridge has to drop in from above, so the
    # plate is relieved for the collar rather than the collar being wished away.
    plate = plate.cut(_box(SYRINGE_FLANGE_T + 2 * CLEAR, SYRINGE_FLANGE_OD + 1.0,
                           PLATE_T + 2.0, SYRINGE_X0 - SYRINGE_FLANGE_T - CLEAR,
                           FLUID_Y, -1.0))

    # strap slots — 25 mm webbing, three stations now the frame is longer
    for sx in (FRAME_X0 + 16.0, 16.0, PLATE_L - 26.0):
        plate = plate.cut(_box(4.0, 27.0, PLATE_T + 2, sx, 0.0, -1.0))

    # bridge inserts. bx was PLATE_L-12 = 159.8, which put the -26 boss (r 5)
    # straight inside the outlet adapter's barrel (45 mm3). The adapter ends at
    # OUTLET_X1 + 8; put the bosses forward of that, still on the plate.
    for y in (-26.0, 26.0):
        bx = PLATE_L - 6.0
        boss = _cyl_z(6.0, INSERT_BOSS_OD / 2.0, bx, y, PLATE_T)
        plate = _fuse(plate, boss)
        plate = plate.cut(_cyl_z(6.5, INSERT_PILOT / 2.0, bx, y, PLATE_T + 6.0 - 5.0))
    return _ground(plate)


# ==================================================================== part 2/5
def make_carriage() -> cq.Shape:
    """Threaded on the push-rod: spring behind, drive grip plate in front.

    (Mk5 round 3) THIS IS THE PART THE CAULK-GUN ARCHITECTURE ALWAYS NEEDED AND
    NEVER HAD. Mk4's carriage was a blind block that shoved a thumb flange, and
    three purchased bodies were consequently drawn inside solid material:
    push_rod 338.23 mm3, grip_plate_drive 138.56 mm3, grip_return_spring
    85.42 mm3. None of those is a clearance error - each is a POCKET the part
    does not have. They are cut here, at the positions the mockups already
    occupy, so the fix is the pocket and not a moved body.

    Three coaxial features on the fluid axis, back to front:
      0 .. SPRING_BORE_DEPTH        Ø8.50  spring counterbore; its FLOOR is the
                                           spring's front seat, so the spring
                                           recedes from it as the carriage runs
                                           instead of being driven into
      .. pocket B rear              Ø6.50  rod bore - and defect 9's vertical
                                           retention, since a carriage threaded
                                           on the rod cannot lift off its rails
      pocket B                      9.80   the drive plate's return spring
      pocket A                      15.00  the tilted drive plate

    Pockets A and B are cut as top-open slots, not bores. A Ø15 bore on an axis
    12.10 above the plate would need a body 20 mm tall - 5 mm of pure wrist
    profile to roof over a plate that has to be dropped in from above anyway.
    The step between them is the DRIVE FACE: ~109 mm2 of shoulder at 37 N is
    0.34 MPa, and it is what pushes the plate, so the 3 N return spring is never
    in the load path.
    """
    inner = SYRINGE_OD / 2.0 + 3.0
    body_w = 2 * inner - 2 * RAIL_T - 2 * CLEAR   # clear span, not centres
    body = _box(CARRIAGE_LEN, body_w, CARRIAGE_BODY_H, 0.0, 0.0, 0.0)

    axis_z = SYRINGE_AXIS_Z - (CARRIAGE_Z0 + CARRIAGE_LIFT)   # local rod axis
    # pocket A: the drive plate, open at the top, through the front face
    pa_x0 = (GRIP_DRIVE_X - GRIP_DRIVE_HALF_X - 0.3) - CARRIAGE_X_COCKED
    pa_w = GRIP_DRIVE_OD + 1.0
    body = body.cut(_box(CARRIAGE_LEN - pa_x0 + 2.0, pa_w,
                         CARRIAGE_BODY_H + 4.0, pa_x0, 0.0, axis_z - pa_w / 2.0))
    # pocket B: the drive plate's return spring, also top-open
    pb_w = GRIP_RETURN_SPRING_OD + 0.8
    pb_x0 = pa_x0 - GRIP_RETURN_SPRING_LEN - 0.5
    body = body.cut(_box(pa_x0 - pb_x0, pb_w, CARRIAGE_BODY_H + 4.0,
                         pb_x0, 0.0, axis_z - pb_w / 2.0))
    # the rod bore, from the spring counterbore floor to pocket B
    body = body.cut(_cyl_x(pb_x0 - SPRING_BORE_DEPTH + 0.2,
                           CARRIAGE_ROD_BORE_D / 2.0,
                           SPRING_BORE_DEPTH - 0.1, 0.0, axis_z))
    # the spring counterbore, from the rear face
    body = body.cut(_cyl_x(SPRING_BORE_DEPTH + 0.5, SPRING_BORE_D / 2.0,
                           -0.5, 0.0, axis_z))

    # sear lug: the pawl bears on its FORWARD face, so the spring load is
    # carried by the pawl and never by the servo. It stands proud of every
    # other feature so the tooth can reach it without entering the pad.
    # It runs from CARRIAGE_LUG_X0 (rearward by its own ramp run) to
    # CARRIAGE_LUG_X + CARRIAGE_LUG_L; the front face is the bearing face and
    # is untouched by anything below.
    lug = _box((CARRIAGE_LUG_X + CARRIAGE_LUG_L) - CARRIAGE_LUG_X0,
               CARRIAGE_LUG_W, CARRIAGE_LUG_H,
               CARRIAGE_LUG_X0, CARRIAGE_LUG_Y, CARRIAGE_BODY_H)
    body = _fuse(body, lug)

    # THE COCKING RAMP on the lug's REAR. Remove everything behind the ramp
    # line over the band the tooth can reach, so the rear presents a face
    # leaning forward as it rises - a doorstop the returning stroke drives
    # under the pawl. Below the band the rear stays square, and the tooth never
    # gets down there (the band bottom is under the tooth's underside).
    z_top = _LUG_TOP - (CARRIAGE_Z0 + CARRIAGE_LIFT)          # local
    z_bot = _LUG_RAMP_BOT_Z - (CARRIAGE_Z0 + CARRIAGE_LIFT)
    far = CARRIAGE_LUG_X0 - 20.0
    ramp = (cq.Workplane("XZ")
            .polyline([(far, z_bot), (CARRIAGE_LUG_X0, z_bot),
                       (CARRIAGE_LUG_X, z_top), (far, z_top)])
            .close().extrude(CARRIAGE_LUG_W + 20.0).val()
            .moved(cq.Location(cq.Vector(0.0,
                                         CARRIAGE_LUG_Y + CARRIAGE_LUG_W / 2.0
                                         + 10.0, 0.0))))
    body = body.cut(ramp)

    # THE RECOCK ANCHOR FORK (Mk5 round 4). The recock load has to enter the
    # carriage somewhere, and until this round it entered nowhere: the rocker's
    # pawl "reached 1.3 mm forward to the carriage's rear face" and in fact
    # shared 0.850 mm of bounding-box corner with it, in Y, which is not a
    # bearing - it is two boxes that happen to touch at an edge.
    #
    # This is a clevis standing off the rear face, split by a slot the cable
    # runs in, with a transverse bore for the anchor pin. The pin is what the
    # cable's swaged eye pulls on and the fork's two ears are what the pin
    # bears in, so the whole 37 N + 3 N goes pin -> ears -> carriage body
    # through 4.3 mm of engaged Y.
    fy0 = ANCHOR_FORK_Y0 - FLUID_Y
    fy1 = ANCHOR_FORK_Y1 - FLUID_Y
    fz0 = ANCHOR_FORK_Z0 - (CARRIAGE_Z0 + CARRIAGE_LIFT)
    fz1 = ANCHOR_FORK_Z1 - (CARRIAGE_Z0 + CARRIAGE_LIFT)
    #
    # It runs the FULL HEIGHT of the carriage rather than hanging off the rear
    # face at pin height. A 3 x 4.3 mm tongue starting 7.5 mm up a part that
    # prints standing on its z = 0 face is 12.9 mm2 of material begun in mid
    # air, which is exactly the unsupported island check_printability exists to
    # catch; taking it to the bed costs nothing and buttresses the pin.
    fork = _box(ANCHOR_FORK_LEN, fy1 - fy0, fz1,
                -ANCHOR_FORK_LEN, (fy0 + fy1) / 2.0, 0.0)
    body = _fuse(body, fork)
    # the cable's lane, cut right through into the body so the ears are ears
    body = body.cut(_box(ANCHOR_FORK_LEN + 0.8, ANCHOR_SLOT_W, fz1 - fz0 + 1.0,
                         -ANCHOR_FORK_LEN - 0.5,
                         (ANCHOR_SLOT_Y0 + ANCHOR_SLOT_Y1) / 2.0 - FLUID_Y,
                         fz0 - 0.5))
    # the pin bore, through both ears
    body = body.cut(_cyl_y(fy1 - fy0 + 2.0, ANCHOR_PIN_D / 2.0 + CLEAR,
                           ANCHOR_PIN_X - CARRIAGE_X_COCKED, fy0 - 1.0,
                           ANCHOR_PIN_Z - (CARRIAGE_Z0 + CARRIAGE_LIFT)))
    return _ground(body)


# ==================================================================== part 3/5
def _sear_raw() -> cq.Shape:
    """Lifting pawl, in ASSEMBLY orientation with the pivot at the origin.

    (Mk5 round 5) ARCHITECTURE B. The pivot is now 1.20 mm above the contact
    instead of 13.40, and that deletes a member: there is no LEG any more,
    because there is nothing left to climb down. The pawl is a flat lever -
    hub, cross-arm and tail in the SEAR_W slab; a jog carrying the slab outboard
    of the carriage lane; and the tooth cantilevering inboard off the jog at
    the same height as the pivot.

    THE ONE THING THAT GOT HARDER. With the pivot 13.4 mm up, every member of
    the pawl except the tooth was above everything the carriage owns, so their Y
    extents did not matter. At pivot height they are level with the carriage
    body top (local z = -2.00) and the lug (local y 8.00..14.00, up to local
    z +3.20). So the part is now built to one rule, and every member is placed
    by it: BELOW the lug top, sear material may only exist OUTBOARD of
    SEAR_LANE_Y - and SEAR_LANE_Y is derived from the carriage's own worst-case
    lateral excursion, not from where the carriage is drawn.

    Load still pushes the tooth +X and r_x*r_z is still positive, so the load
    still rotates it DOWN into the lug (sear_moment_check) - just 11x more
    weakly, which is the entire point and is why SEAR_SPRING_PRELOAD_N_MM now
    exists.
    """
    back = SEAR_BACK                              # tooth is this far behind
    drop = SEAR_DROP                              # and this far below

    # HUB, CROSS-ARM and TAIL live inside a SEAR_W slab centred on the pivot,
    # because that slab is all the clevis slot gives them. The old cross-arm was
    # abs(lat)+5 = 16 mm wide and the hub was a cylinder about X (6.8 mm in Y),
    # so both ran through the tower cheeks. Only the JOG and the TOOTH step
    # inboard, and both do so where the tower has no material in X.
    hub = _cyl_y(SEAR_W, SEAR_HUB_R, 0.0, -SEAR_W / 2.0, 0.0)
    # The cross-arm and jog start at the hub's UNDERSIDE, not 2.5 mm above it.
    # A hub bottomed below them leaves its lowest 0.9 mm printing in mid-air -
    # a 10.8 mm2 island the 1.0 mm --quick layer step steps straight over, and
    # which the full 0.4 mm scan does catch.
    arm_z0 = -SEAR_HUB_R
    arm_h = SEAR_HUB_R + 2.5
    cross = _box(back + 8.0, SEAR_W, arm_h, -(back + 5.0), 0.0, arm_z0)

    # THE JOG carries the slab outboard-to-inboard, and it STOPS at SEAR_JOG_Y.
    # Its front face sits at SEAR_INBOARD_X and does two jobs: it is the surface
    # that sweeps past the relieved cheek corner (CHEEK_RELIEF_R, above), and at
    # 0 deg it is the surface that bottoms flat on the baseplate's rotation stop
    # pad, which is why the two are built from the same number.
    jog = _box((back + 5.0) - SEAR_INBOARD_X, SEAR_JOG_Y + SEAR_W / 2.0, arm_h,
               -(back + 5.0), (SEAR_JOG_Y - SEAR_W / 2.0) / 2.0, arm_z0)
    # The tooth's REAR face abuts the lug's FRONT face and nothing else: it is
    # SEAR_TOOTH_H tall, seated SEAR_TOOTH_GAP above the carriage's tallest
    # non-lug feature and finishing below the lug top, so the only coincident
    # surface in the pair is that one vertical face.
    #
    # ITS WIDTH IS DERIVED FROM THE LUG'S SWEPT Y BAND, not from the lug's
    # nominal position: it starts inside the jog and runs inboard far enough to
    # still overlap the whole lug when the carriage is at either limit of the
    # lateral play the rails permit, plus margin.
    tooth_y0 = SEAR_TOOTH_Y0
    tooth_y1 = ((_LUG_Y_INBOARD + CARRIAGE_Y_PLAY + TOOTH_CAPTURE_MARGIN)
                - SEAR_PIVOT_Y)
    assert (SEAR_PIVOT_Y + tooth_y0
            <= _LUG_Y_OUTBOARD - CARRIAGE_Y_PLAY - TOOTH_CAPTURE_MARGIN), \
        "tooth does not reach outboard past the lug's play band"
    lat = tooth_y1 - tooth_y0
    tooth = _box(SEAR_TOOTH_L, lat, SEAR_TOOTH_H, -back,
                 tooth_y0 + lat / 2.0, -drop)
    tail = _box(SEAR_TAIL_TIP_X + 3.0, SEAR_W, 4.0, -3.0, 0.0, -2.0)
    body = _fuse(hub, cross, jog, tooth, tail)

    # THE COCKING RAMP on the sear's FRONT, cut across every millimetre of Y the
    # lug can reach and one millimetre more. Mk4 cut it across the FULL width
    # because the LEG's square front stood 1 mm proud of the tooth's; with the
    # leg gone the cut is bounded at SEAR_RAMP_Y0 instead, for a reason that is
    # geometric and not cosmetic: at pivot height the wedge would otherwise eat
    # the hub and the pin bore with it - the ramp band now runs from local
    # z = -1.20 to +3.60 and the hub spans -3.40 to +3.40.
    #
    # SEAR_RAMP_Y0 is the cross-arm's own outboard face, so the cut takes no
    # sliver off the slab, and it is SEAR_LANE_Y - SEAR_RAMP_Y0 = 2.20 mm
    # outboard of anything the lug can reach at its worst lateral excursion.
    # Everything the lug CAN touch is ramped; nothing it cannot is.
    far = -back + SEAR_TOOTH_L + 20.0
    _prism = (cq.Workplane("XZ")
              .polyline([(-back + SEAR_TOOTH_L - SEAR_RAMP_RUN, -drop),
                         (far, -drop),
                         (far, -drop + SEAR_RAMP_BAND),
                         (-back + SEAR_TOOTH_L, -drop + SEAR_RAMP_BAND)])
              .close().extrude(tooth_y1 + 20.0 - SEAR_RAMP_Y0).val())
    # place by MEASUREMENT, not by trusting the extrude direction of an XZ
    # workplane: the prism's own ymin is put on SEAR_RAMP_Y0.
    ramp = _prism.moved(cq.Location(
        cq.Vector(0.0, SEAR_RAMP_Y0 - _prism.BoundingBox().ymin, 0.0)))
    body = body.cut(ramp)
    # pivot bore on the Y axis - the axis check_sear_release actually rotates about
    body = body.cut(_cyl_y(SEAR_W + 4.0, SEAR_PIN_R, 0.0, -SEAR_W / 2.0 - 2.0, 0.0))
    return body


# THE PAWL IS PRINTED ON ITS SIDE - AND NOW ACTUALLY IS.
# The docstring used to say "printed lying on its side so the whole profile
# meets the bed" while printed_parts placed it with a pure translation, so the
# print frame WAS the assembly frame: the part stood on the undersides of the
# tooth and leg, 46.5 mm2 of bed contact, and once the cocking ramp cut those
# undersides back to a wedge tip it fell to 15.7 mm2. A 1.5 kg-cm servo load on
# a part held to the bed by 16 mm2 comes off the bed.
#
# So the part is now genuinely rotated 90 deg about X for printing: the slab
# face (hub, cross-arm and tail, which span the full SEAR_W) lies flat on the
# bed and the whole lever profile is the first layer. The assembly transform
# below UNDOES that rotation and the grounding, composed rather than
# re-guessed - changing a part's print frame without changing its assembly
# transform is exactly how Mk3 ended up with a sear buried in its own post.
_SEAR_PRINT_ROT = cq.Location(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90.0)
_SEAR_RAW = _sear_raw()
_SEAR_LAID = _SEAR_RAW.moved(_SEAR_PRINT_ROT)
_SEAR_PRINT_DZ = -_SEAR_LAID.BoundingBox().zmin


def make_sear() -> cq.Shape:
    """The pawl as it reaches the bed: laid on its slab face and grounded."""
    return _SEAR_LAID.moved(cq.Location(cq.Vector(0, 0, _SEAR_PRINT_DZ)))


# ==================================================================== part 4/5
def make_outlet() -> cq.Shape:
    """Bonds to the syringe barrel after its Luer taper is cut off. This single
    part is what closes the energy gap: 4 mm bore instead of the Luer's ~2 mm."""
    body = _cyl_x(OUTLET_LENGTH + 10.0, SYRINGE_OD / 2.0 + 2.2, 0.0, 0.0, 0.0)
    # socket for the cut barrel
    body = body.cut(_cyl_x(10.0, SYRINGE_OD / 2.0 + 0.15, -0.1, 0.0, 0.0))
    # the working bore
    body = body.cut(_cyl_x(OUTLET_LENGTH + 12.0, OUTLET_BORE / 2.0, -1.0, 0.0, 0.0))
    # flat so it prints without support
    body = body.cut(_box(OUTLET_LENGTH + 12.0, SYRINGE_OD + 8.0, 3.0,
                         -1.0, 0.0, -(SYRINGE_OD / 2.0 + 2.2)))
    return _ground(body)


# ==================================================================== part 5/5
def make_switch_pod() -> cq.Shape:
    """Palm trigger housing. Canonical web-shooters fire from a pad in the palm
    struck by the middle two fingers; this is that pad."""
    pod = _box(24.0, 20.0, 7.0)
    pod = pod.cut(_box(13.0, 13.0, 5.0, 5.5, 0.0, 2.0))     # switch pocket, floored
    pod = pod.cut(_cyl_z(3.0, 5.0, 12.0, 0.0, 6.0))          # cap clearance
    for sx in (1.5, 20.0):                                    # strap tunnels, floored
        pod = pod.cut(_box(2.5, 27.0, 3.4, sx, 0.0, 2.0))
    return _ground(pod)


PARTS = {
    "baseplate": make_baseplate,
    "carriage": make_carriage,
    "sear": make_sear,
    "outlet_adapter": make_outlet,
    "switch_pod": make_switch_pod,
}

# Assembly transforms. The sear is MODELLED flat for printing (5 mm in Z) and
# rotated upright here — changing a part's print frame without changing its
# assembly transform is exactly how it ended up buried in its own post.
printed_parts: Dict[str, Placed] = {
    "baseplate": Placed(make_baseplate(), cq.Location()),
    "carriage": Placed(make_carriage(), cq.Location(cq.Vector(
        CARRIAGE_X_FIRED - PLUNGER_STROKE, FLUID_Y, CARRIAGE_Z0 + CARRIAGE_LIFT))),
    # make_sear() is the LAID-DOWN, GROUNDED part. The assembly transform is
    # the exact inverse of the two operations that produced it, composed in
    # reverse order, then the move to the pivot - so the hub lands on the real
    # pivot by construction and not by a subtraction that has to be kept in
    # step by hand. Asserted below.
    "sear": Placed(make_sear(),
                   cq.Location(cq.Vector(SEAR_PIVOT_X, SEAR_PIVOT_Y, SEAR_PIVOT_Z))
                   * cq.Location(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90.0)
                   * cq.Location(cq.Vector(0, 0, -_SEAR_PRINT_DZ))),
    "outlet_adapter": Placed(make_outlet(), cq.Location(cq.Vector(
        OUTLET_X0 - 2.0, FLUID_Y, SYRINGE_AXIS_Z - (SYRINGE_OD / 2.0 + 2.2) + 3.0))),
    # palm pod rides its own strap, clear of the plate entirely
    "switch_pod": Placed(make_switch_pod(), cq.Location(cq.Vector(
        PLATE_L - 30.0, -PLATE_W / 2.0 - 24.0, 0.0))),
}


# The composed transform must put the raw part back exactly where it was.
_placed_sear = printed_parts["sear"].world()
_want = _SEAR_RAW.moved(cq.Location(cq.Vector(SEAR_PIVOT_X, SEAR_PIVOT_Y,
                                              SEAR_PIVOT_Z)))
_b1, _b2 = _placed_sear.BoundingBox(), _want.BoundingBox()
for _a, _v1, _v2 in (("xmin", _b1.xmin, _b2.xmin), ("xmax", _b1.xmax, _b2.xmax),
                     ("ymin", _b1.ymin, _b2.ymin), ("ymax", _b1.ymax, _b2.ymax),
                     ("zmin", _b1.zmin, _b2.zmin), ("zmax", _b1.zmax, _b2.zmax)):
    assert abs(_v1 - _v2) < 1e-6, f"sear assembly transform: {_a} {_v1} vs {_v2}"



# ============================================================ purchased parts
# THE MOST IMPORTANT BLOCK IN THIS FILE.
#
# Two independent acceptance reviews found every blocking defect at a
# printed-to-purchased interface, and both traced it to the same cause: Mk4
# defined no `mockups`, so verify_independent.py's `if hasattr(M, "mockups")`
# guard silently skipped and `bodies` held only the five printed parts. The
# syringe, plunger, spring, servo and pins were in no check at all.
#
# One reviewer's phrasing: "the harness was not gamed by editing - it was
# starved by the model."
#
# Every body the machine touches now goes in here, so the checks can see them.
# Dimensions carry their source; where a number is unverified it says so, and
# an unverified number must never be quietly trusted by a check.

# ================================ (Mk5) THE COAXIAL STATION MAP, ON ONE AXIS
# Mk4 ran the spring in one lane, the plunger in a second and the sear in a
# third, and every defect at a printed-to-purchased interface lived where two
# lanes met. Mk5 puts the spring, the carriage, both grip plates, the push-rod
# and the piston on ONE axis - the fluid axis - so the rod is simultaneously the
# spring's full-length pilot (defect 11), the carriage's vertical constraint
# (defect 9) and the caulk-gun rod (defect 1).

# (round 3) The stations themselves now live in the envelope block above,
# because make_baseplate has to draw the frame that reaches them. What remains
# here is the arithmetic THAT CHECKS THEM, computed from the drawn numbers.

SPRING_TRUE_COCKED_LEN = SPRING_FRONT_SEAT_X - SPRING_SEAT_X
SPRING_TRUE_COCKED_N = (SPRING_FREE_LEN - SPRING_TRUE_COCKED_LEN) * SPRING_RATE_N_MM
# Defect 6 was a 24% force error caused by the spring seating on a face 2 mm
# from where the arithmetic assumed. The seat is still DERIVED from the cocked
# length, but the front seat is now the counterbore FLOOR rather than the
# carriage's rear face, so the two ends of this subtraction are the two surfaces
# the coil actually touches. The assert is what keeps them that way.
assert abs(SPRING_TRUE_COCKED_N - SPRING_PEAK_N) < 1e-6, (
    "the drawn spring seat and the sizing arithmetic disagree again: "
    f"{SPRING_TRUE_COCKED_N:.3f} N drawn vs {SPRING_PEAK_N:.3f} N sized")

# --- the fluid end, no bonded joint anywhere -----------------------------
CANNULA_OD = 4.2                   # 8 ga blunt tip, ID = CANNULA_ID_MM
CANNULA_HUB_OD, CANNULA_HUB_LEN = 9.0, 12.0    # Luer hub
ORING_CS = 1.8                     # O-ring cross-section holding the hub

# --- the fluid column and the piston -------------------------------------
FILL_LEN = SHOTS_PER_FILL * PLUNGER_STROKE               # 50.36 mm of column
assert abs(FILL_LEN - _FILL_LEN) < 1e-9, "the frame and the fill disagree"
PISTON_LEN = 10.0
# (round 3) THE COLUMN ENDS AT THE HUB, NOT AT THE BARREL MOUTH.
# With the stroke unblocked for the first time, the stepper got far enough to
# find the next thing in the way: the piston reached the cannula hub - which
# plugs into the last CANNULA_HUB_LEN of the barrel - on shot 4, and shots 4 and
# 5 delivered 1.59 and 0.00 mL. The fluid column a cartridge actually holds is
# bounded by the hub's rear face, so that is what FILL_LEN is measured back
# from. The barrel is 88 mm long and the column is 50.4, so this costs nothing
# but the arithmetic being right.
COLUMN_FRONT_X = OUTLET_X0 - CANNULA_HUB_LEN
PISTON_X0 = COLUMN_FRONT_X - FILL_LEN - PISTON_LEN       # rear face, full charge

# --- the push-rod ---------------------------------------------------------
# HOW LONG THE ROD HAS TO BE, DERIVED RATHER THAN CHOSEN.
# The rod's front end is the piston's rear face and travels FILL_LEN forward
# over the life of a cartridge. Its rear end must STILL be behind the spring's
# rear seat when the cartridge is empty, or the spring loses its pilot in the
# last shots - so the rod's rear end at full charge sits FILL_LEN behind that
# seat. That protruding tail is not waste: it is the charge gauge, 50 mm of rod
# showing at full and none at empty, read through the witness slot in the tail
# pillar.
#
# (round 3) THE DEBT IS PAID. ROD_X0 is now the number FRAME_X0 is derived FROM
# rather than a number stated and left standing in mid-air: the baseplate starts
# FRAME_TAIL_CLEAR behind the tail, the tail pillar carries it, and the rear
# abutment is bored for it instead of sharing 67.86 mm3 with it. What that costs
# is stated in FRAME_LEN and reported: the frame is now ~238 mm along the
# forearm against Mk4's 174. That is the price of five 2 mL shots from a 10 mL
# cartridge with a rod-piloted spring, it is a length and not a height, and it
# is the largest single cost this design carries.
ROD_LEN = PISTON_X0 - ROD_X0
ROD_TAIL_AT_EMPTY_X = ROD_X0 + FILL_LEN

# --- the two tilting grip plates -----------------------------------------
GRIP_ENGAGE_MM = 12.0                                    # rod left in the bore
GRIP_RELEASE_RESIST_N_MM = PISTON_SEAL_DRAG_N * GRIP_BORE_D / 2.0
GRIP_RELEASE_DRIVE_N_MM = GRIP_RETURN_SPRING_N * GRIP_PLATE_OD / 2.0
GRIP_RELEASE_MARGIN = GRIP_RELEASE_DRIVE_N_MM / GRIP_RELEASE_RESIST_N_MM

# ---- THE AXIAL BUDGET BETWEEN THE PLATES, MEASURED FROM THE DRAWN GEOMETRY --
# A tilted disc of diameter OD and thickness t occupies, along x,
#       half_x = OD/2*sin(a) + t/2*cos(a)
# either side of its centre. The drive plate has to travel a whole
# PLUNGER_STROKE before its FRONT face reaches the anti-return plate's REAR
# face, or the shot is cut off wherever the two meet.
#
# Round 2 measured that span at 3.194 mm against 10.222 mm needed and reported
# the 7.028 mm deficit as frame length owed. Round 3 grew the frame and re-rooted
# the chain at the syringe, so the same subtraction is now positive. It is still
# a SUBTRACTION OF DRAWN NUMBERS - GRIP_DRIVE_X and GRIP_ANTIRETURN_X are what
# make_mockups places the plates at - so if either moves, this says so.
GRIP_DRIVE_FRONT_X = GRIP_DRIVE_X + GRIP_DRIVE_HALF_X
GRIP_CLEAR_SPAN_MM = GRIP_ANTIRETURN_REAR_X - GRIP_DRIVE_FRONT_X
GRIP_SPAN_NEEDED_MM = PLUNGER_STROKE + GRIP_PLATE_CLEARANCE
GRIP_SPAN_DEFICIT_MM = GRIP_SPAN_NEEDED_MM - GRIP_CLEAR_SPAN_MM
assert GRIP_SPAN_DEFICIT_MM <= 0.0, (
    f"one full stroke still does not fit between the plates: "
    f"{GRIP_CLEAR_SPAN_MM:.3f} mm clear against {GRIP_SPAN_NEEDED_MM:.3f} needed")

GRIP_SPAN_FRAME_GROWTH_MM = max(0.0, GRIP_SPAN_DEFICIT_MM)

# --- the two servos, both lying flat -------------------------------------
# Output shafts along +Y, horns sweeping in the XZ plane. Lying flat is what
# keeps them off the wrist profile: the body's 13 mm thickness is the only
# dimension standing up, and the 34.5 mm height lies across the plate instead.
SERVO_Y = 12.0                     # centre of the body in Y (electronics lane)
SERVO_Z = PLATE_T                  # sits on the plate
SERVO_HORN_T = 2.5
SERVO_PUSHROD_LEN = 30.0
SERVO_TRIP_X = 98.0

# --- the sear ------------------------------------------------------------
# (Mk5 round 5) THE ENGAGEMENT SPRING HAD TO MOVE OUTBOARD, and this is why.
# It was drawn on the pin's INBOARD stub, which was legal only while the pivot
# stood 13.40 mm above everything. At pivot height a Ø8 coil on that stub spans
# z 15.95..23.95 and y -25.5..-19.5 - straight through the carriage body and
# through the sear lug's own swept lane. It now sits on the OUTBOARD stub,
# 0.30 mm clear of the tower's outboard cheek, where the only thing at its Y is
# air. The pin grows to carry it and is drawn from END COORDINATES rather than
# centred on the pivot, so neither end can drift into the lane again.
SEAR_TORSION_OD = 8.0
SEAR_TORSION_LEN = 4.0
# The bore is a WINDING CLEARANCE, not a fit: a torsion spring that is a press
# fit on its own pin cannot wind. 0.20 mm on the radius is the smallest gap
# that is still a gap after the pin's h9 tolerance.
SEAR_TORSION_BORE_R = SEAR_PIN_R + 0.20
SEAR_TORSION_Y1 = SEAR_PIVOT_Y - TOWER_W / 2.0 - 0.30
SEAR_TORSION_Y0 = SEAR_TORSION_Y1 - SEAR_TORSION_LEN
SEAR_PIN_Y0 = SEAR_TORSION_Y0 - 0.5              # 0.5 mm of stub past the coil
SEAR_PIN_Y1 = SEAR_PIVOT_Y + TOWER_W / 2.0 - 0.5  # recessed inside the cheek
SEAR_PIN_LEN = SEAR_PIN_Y1 - SEAR_PIN_Y0
assert SEAR_PIN_Y1 <= FLUID_Y - _CARRIAGE_BODY_W / 2.0 - 0.15, \
    "the pivot pin protrudes into the carriage lane"


# --- the split cradle ----------------------------------------------------
# (round 4) ON THE RIB CENTRES. SYRINGE_X1 - 14.0 put the forward screw at
# x = 128, i.e. 126.5..129.5, against a rib that starts at 130: it missed its
# own rib by 0.5 mm in X as well as by 1 mm in Y, and passed through the trip
# servo instead. Both screws are now on the centreline of the rib they clamp.
CRADLE_SCREW_X = (SYRINGE_X0 + 9.0, SYRINGE_X1 - 9.0)
# (round 4) 5.0 put the screws at y = -2.5 and -29.5, which is OUTSIDE the
# cradle rib they are supposed to go through (the rib spans -28.5..-3.5): two
# M3 screws standing in air, 1 mm clear of any material. 2.0 lands them in the
# 4 mm band of rib that is outside the Ø17 barrel and inside the rib's edge.
CRADLE_SCREW_DY = _CRADLE_SCREW_DY
M3_SCREW_LEN = 14.0
# The screws run DOWN from the removable cap into heat-set inserts in the
# base, alongside the barrel - not up from the fluid axis, which is where a
# first draft of this put them, 26.1 mm into the air above a 25 mm target.
CRADLE_SCREW_Z0 = PLATE_T

# Sear release torque, the check neither the model nor the harness ever ran.
_SEAR_R_X = SEAR_CONTACT_X - SEAR_PIVOT_X
_SEAR_R_Z = SEAR_CONTACT_Z - SEAR_PIVOT_Z
SEAR_HOLD_MOMENT_N_MM = abs(_SEAR_R_Z) * SPRING_TRUE_COCKED_N
SEAR_FRICTION_MU = 0.35                          # PETG on PETG, dry - ESTIMATE
# (Mk5 round 5) THE ENGAGEMENT SPRING IS PART OF THE RELEASE MOMENT, charged at
# FULL release rather than at first movement: SEAR_RELEASE_SWEEP_DEG is the
# angle the tooth has to rise through to clear the lug top, from the geometry.
SEAR_RELEASE_SWEEP_DEG = math.degrees(
    math.asin(min(1.0, (_LUG_TOP - SEAR_CONTACT_Z + abs(_SEAR_R_Z))
                  / math.hypot(_SEAR_R_X, _SEAR_R_Z)))) + math.degrees(
    math.atan2(abs(_SEAR_R_Z), abs(_SEAR_R_X)))
SEAR_SPRING_MOMENT_N_MM = (SEAR_SPRING_PRELOAD_N_MM
                           + SEAR_SPRING_RATE_N_MM_PER_DEG * SEAR_RELEASE_SWEEP_DEG)
SEAR_RELEASE_MOMENT_N_MM = (SEAR_HOLD_MOMENT_N_MM
                            + SEAR_FRICTION_MU * SPRING_TRUE_COCKED_N * abs(_SEAR_R_X)
                            + SEAR_FRICTION_MU * SPRING_TRUE_COCKED_N * SEAR_PIN_R
                            + SEAR_SPRING_MOMENT_N_MM)
SERVO_STALL_N_MM = 4.6 * 98.07                   # DS239MG 4.6 kg.cm at 6 V
SERVO_USABLE_N_MM = SERVO_STALL_N_MM / 3.0       # a third of stall is the honest ceiling
SEAR_TAIL_ADVANTAGE = SEAR_TAIL_LEN / max(1e-6, abs(_SEAR_R_X))


MOCKUP_BODY_COUNT_FLOOR = 26    # round 4 shipped 26; round 5 adds the clutch and
                                # its rewind spring. It may grow; it may not shrink.


def make_mockups() -> Dict[str, Placed]:
    """Purchased bodies at their assembly positions, so the harness can see them.

    (Mk5) THE COUNT GOES UP, NOT DOWN - AND TWO CHANGES HERE NEEDED CARE.

    1. THE BARREL IS NOW A TUBE, not a solid cylinder. That is correct - a
       syringe barrel is a tube - but it also makes two of Mk4's overlap
       failures disappear on their own, because a plunger inside a hollow
       barrel no longer intersects it. Removing failures by hollowing a mockup
       is indistinguishable, from the outside, from the starving that got Mk4
       rejected. So check_piston_containment lands in the same commit: it does
       not ask whether the piston FAILS TO OVERLAP the barrel, it proves the
       piston is INSIDE the bore, radially and axially, at every shot. The
       hollow barrel is only legal because a stricter check replaced the
       accidental one.

    2. THE SYRINGE'S OWN PLUNGER ROD AND THUMB FLANGE ARE GONE. This is not
       hiding them: the Mk5 design CUTS THE ROD OFF behind the piston and drives
       the piston with a Ø6 stainless push-rod instead. Defects 4 and 5 - the
       Ø18 thumb flange fouling a 14.90 mm rail span, and the finger flange
       buried 115.60 mm3 into the plate - are deleted rather than accommodated,
       and the ribbed polypropylene rod that no tilting plate could ever bite is
       replaced by the round hardened rod the grip needs. A body the machine no
       longer touches is not a body the harness needs to see. What replaces them
       - piston, push-rod, both grip plates - is strictly harder to satisfy:
       check_multishot falls through from the thumb flange to the piston and
       keeps simulating, and check_piston_containment did not exist before.

    The assert at the bottom is the guard: this dictionary may not shrink.
    """
    m: Dict[str, Placed] = {}
    L = cq.Location()

    def add(name, shape):
        m[name] = Placed(shape, L)

    # ---------------------------------------------------------- the cartridge
    # 10 mL NORM-JECT. A TUBE: ID = SYRINGE_BORE, wall = SYRINGE_WALL.
    barrel = _cyl_x(SYRINGE_BARREL_LEN, SYRINGE_OD / 2.0,
                    SYRINGE_X0, FLUID_Y, SYRINGE_AXIS_Z)
    barrel = barrel.cut(_cyl_x(SYRINGE_BARREL_LEN + 2.0, SYRINGE_BORE / 2.0,
                               SYRINGE_X0 - 1.0, FLUID_Y, SYRINGE_AXIS_Z))
    add("syringe_barrel", barrel)

    # The finger flange is an ANNULUS, not a disc: it is a collar on the barrel,
    # and drawing it solid put 115.60 mm3 of it through the plate for reasons
    # that were an artefact of the mockup rather than of the part.
    fl = _cyl_x(SYRINGE_FLANGE_T, SYRINGE_FLANGE_OD / 2.0,
                SYRINGE_X0 - SYRINGE_FLANGE_T, FLUID_Y, SYRINGE_AXIS_Z)
    fl = fl.cut(_cyl_x(SYRINGE_FLANGE_T + 2.0, SYRINGE_BORE / 2.0,
                       SYRINGE_X0 - SYRINGE_FLANGE_T - 1.0, FLUID_Y, SYRINGE_AXIS_Z))
    add("syringe_finger_flange", fl)

    # THE PISTON, at full charge. The fluid column behind the outlet is
    # SHOTS_PER_FILL strokes long, so a full cartridge puts the piston's front
    # face exactly that far back from the barrel mouth. After five shots it
    # arrives at the mouth - which check_piston_containment verifies rather
    # than assumes.
    add("piston", _cyl_x(PISTON_LEN, SYRINGE_BORE / 2.0,
                         PISTON_X0, FLUID_Y, SYRINGE_AXIS_Z))

    # ------------------------------------------------ the coaxial push-rod line
    # ONE AXIS INSTEAD OF THREE LANES. The Ø6.0 h9 stainless rod is the spring's
    # full-length pilot (defect 11), the carriage's vertical constraint
    # (defect 9) and the caulk-gun rod (defect 1), all at once.
    add("push_rod", _cyl_x(ROD_LEN, PUSH_ROD_OD / 2.0,
                           ROD_X0, FLUID_Y, SYRINGE_AXIS_Z))

    # The spring, COAXIAL ON THE ROD at its cocked length. Modelled as the
    # annulus the coil actually occupies so the pilot inside it is visible to
    # check_spring_buckling as clear bore rather than as spring material.
    spr = _cyl_x(SPRING_COCKED_LEN, SPRING_OD / 2.0,
                 SPRING_SEAT_X, FLUID_Y, SYRINGE_AXIS_Z)
    spr = spr.cut(_cyl_x(SPRING_COCKED_LEN + 2.0, SPRING_OD / 2.0 - SPRING_WIRE,
                         SPRING_SEAT_X - 1.0, FLUID_Y, SYRINGE_AXIS_Z))
    add("compression_spring", spr)

    # THE TWO TILTING GRIP PLATES, at their bite angles.
    # Both are washers of GRIP_PLATE_T on the rod, rotated about +Y by
    # GRIP_TILT_DEG so their bore edges dig into it.
    #   drive plate      on the carriage, carries the full spring force forward
    #   anti-return plate anchored to the front abutment, blocks rearward motion
    #                    while the carriage returns; it carries only residual
    #                    drag, because back-pressure decays to zero after the shot
    def _tilted_plate(x, tilt, od):
        w = _cyl_x(GRIP_PLATE_T, od / 2.0, -GRIP_PLATE_T / 2.0, 0.0, 0.0)
        w = w.cut(_cyl_x(GRIP_PLATE_T + 2.0, GRIP_BORE_D / 2.0,
                         -GRIP_PLATE_T / 2.0 - 1.0, 0.0, 0.0))
        w = w.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), tilt)
        return w.moved(cq.Location(cq.Vector(x, FLUID_Y, SYRINGE_AXIS_Z)))

    # (round 3) The anti-return plate is Ø18 against the drive plate's Ø14, so
    # its reaction lands on the abutment annulus outside the drive plate's
    # swept radius. See GRIP_ANTIRETURN_OD.
    add("grip_plate_drive",
        _tilted_plate(GRIP_DRIVE_X, GRIP_TILT_DEG, GRIP_DRIVE_OD))
    add("grip_plate_antireturn",
        _tilted_plate(GRIP_ANTIRETURN_X, -GRIP_TILT_DEG, GRIP_ANTIRETURN_OD))

    # THE DRIVE PLATE'S RETURN SPRING - the release half of the cycle.
    # Without it the drive plate is rigid at its bite angle, holds the rod on the
    # return stroke and drags the piston back out: the caulk-gun load path never
    # closes and "re-cock and shoot again" is not a thing the mechanism does.
    # This light coil is what squares the plate the moment the 37 N goes away.
    #
    # IT IS DRAWN WHERE IT HAS TO ACT - coaxial on the rod, bearing on the
    # plate's rear face - and that is presently INSIDE the solid carriage, so the
    # harness will report it overlapping printed/carriage. That overlap is the
    # honest statement of a pocket the carriage does not have yet. Round 2 does
    # not draw printed geometry; putting the spring somewhere it does not
    # interfere would be moving the body to suit the check, which is the exact
    # move that got four revisions rejected.
    grs = _cyl_x(GRIP_RETURN_SPRING_LEN, GRIP_RETURN_SPRING_OD / 2.0,
                 GRIP_DRIVE_X - GRIP_PLATE_HALF_X - GRIP_RETURN_SPRING_LEN,
                 FLUID_Y, SYRINGE_AXIS_Z)
    grs = grs.cut(_cyl_x(GRIP_RETURN_SPRING_LEN + 2.0, PUSH_ROD_OD / 2.0 + 0.2,
                         GRIP_DRIVE_X - GRIP_PLATE_HALF_X
                         - GRIP_RETURN_SPRING_LEN - 1.0,
                         FLUID_Y, SYRINGE_AXIS_Z))
    add("grip_return_spring", grs)

    # ------------------------------------------------------------ the actuators
    # TWO DS239MG SERVOS, BOTH LYING FLAT, output shafts along +Y so the horns
    # sweep in the XZ plane. Lying flat is what keeps them off the profile: the
    # body's 13 mm thickness is the only dimension that stands up.
    #   servo #1  the cocking winch, carrying the scroll drum on its own shaft
    #   servo #2  the trip, lifting the sear off the rack
    #
    # (round 4) THE WINCH SERVO MOVED. It used to sit at x = 64 in the +Y lane
    # with a Ø18 horn that shared 53.51 mm3 with the baseplate and 2.30 mm3 with
    # its own pushrod, 60 mm forward of anything it could pull. It now sits
    # directly behind the cocked carriage with its shaft face at y = -2.9, which
    # is the only station in the tail from which a drum can reach the carriage
    # without crossing the push-rod, the coil or the +Y rail. Its horn and
    # pushrod are DELETED because a drum is not driven by a pushrod - they are
    # replaced by winch_drum below, which is a larger body, not a smaller one.
    add("servo_trip", _box(SERVO_L, SERVO_H, SERVO_W,
                           SERVO_TRIP_X, SERVO_Y, SERVO_Z))
    _tsy = SERVO_Y + SERVO_H / 2.0
    add("horn_trip", _cyl_y(SERVO_HORN_T, SERVO_HORN_R_MM,
                            SERVO_TRIP_X + SERVO_SHAFT_DX, _tsy,
                            SERVO_Z + SERVO_W / 2.0))
    add("pushrod_trip", _cyl_x(SERVO_PUSHROD_LEN, 0.8,
                               SERVO_TRIP_X + SERVO_SHAFT_DX,
                               _tsy + SERVO_HORN_T / 2.0,
                               SERVO_Z + SERVO_W / 2.0 + SERVO_HORN_R_MM))
    add("servo_winch", _box(SERVO_L, SERVO_H, SERVO_W, WINCH_SERVO_X0,
                            WINCH_SERVO_Y0 + SERVO_H / 2.0, WINCH_SERVO_Z0))

    # ------------------------------------------------- the single-sweep winch
    # THE SCROLL DRUM, DRAWN FROM winch_pitch_radius() RATHER THAN DECLARED.
    #
    # The profile is a closed polyline swept about the shaft axis in the XZ
    # plane. Over the 160 deg the cable occupies, the rim radius is the solved
    # constant-torque schedule; over the remaining 200 deg it is the flat
    # WINCH_R_MAX_EFF arc, which is also the web that carries the waist. The
    # waist is 1.7 mm from the axis - smaller than the servo's own spline - and
    # that is only buildable because the HUB IS IN A DIFFERENT PLANE: the drum
    # is a stepped plate, splined to the shaft on the band nearest the servo and
    # necking down to the scroll on the band the cable runs in. A drum with its
    # bore in the cable's plane could not have this profile at all, which is the
    # geometric reason the two-bite ratchet's 1.804 mm radius never appeared as
    # a feature anywhere.
    #
    # MATERIAL: this is the one machined part in the build - 2024 aluminium or
    # a laser-cut steel plate, not PETG. At the waist the section carries
    # 37 N of cable tension on a 1.7 mm arm.
    def _scroll_poly(offset: float):
        pts = []
        n = 240
        for i in range(n + 1):
            a = math.radians(WINCH_DEPARTURE_DEG) + 2.0 * math.pi * i / n
            # the drum is drawn at FULL COCK, so the profile angle standing at
            # the departure position after fraction u of the sweep is
            # DEPARTURE + (1-u)*SWEEP: walking +a from DEPARTURE walks the sweep
            # backwards, from full cock toward the fired pose.
            da = 2.0 * math.pi * i / n
            if da <= RECOCK_SWEEP_RAD:
                r = winch_pitch_radius(RECOCK_SWEEP_RAD - da) - WINCH_CABLE_D / 2.0
            elif da <= math.pi:
                # the dead-end ledge: the cable's fixed end is swaged into this
                # step, which is why it is at full radius and 180 deg from the
                # departure point rather than anywhere convenient
                r = WINCH_R_MAX_EFF - WINCH_CABLE_D / 2.0
            else:
                # THE RELIEF, and it is not cosmetic. The cable leaves the drum
                # straight up at WINCH_CABLE_Z and then runs +X to the anchor.
                # Anything on that side of the drum standing higher than the
                # departure radius is material the cable would have to pass
                # through - the first draft of this profile carried R_MAX right
                # up to the departure point and put a 6.7 mm wall directly in
                # front of the cable. Everything from the bottom of the drum
                # round to the departure is cut back to the departure radius, so
                # the free span is tangent at 90 deg and clear everywhere after.
                r = winch_pitch_radius(RECOCK_SWEEP_RAD) - WINCH_CABLE_D / 2.0
            r += offset
            pts.append((WINCH_AXIS_X + r * math.cos(a),
                        WINCH_AXIS_Z + r * math.sin(a)))
        return pts

    def _scroll_solid(offset: float, y0: float, y1: float):
        return (cq.Workplane("XZ").polyline(_scroll_poly(offset)).close()
                .extrude(-(y1 - y0)).val()
                .moved(cq.Location(cq.Vector(0.0, y0, 0.0))))

    drum = _scroll_solid(WINCH_GROOVE_DEPTH, WINCH_SCROLL_Y0, WINCH_SCROLL_Y1)
    # the cable groove: a channel WINCH_GROOVE_DEPTH deep, so the floor the
    # cable rides on is exactly winch_pitch_radius() - cable radius
    groove = _scroll_solid(WINCH_GROOVE_DEPTH, WINCH_GROOVE_Y0, WINCH_GROOVE_Y1)
    groove = groove.cut(_scroll_solid(0.0, WINCH_GROOVE_Y0, WINCH_GROOVE_Y1))
    drum = drum.cut(groove)
    # the hub band, on the servo's spline, in its own plane clear of the cable
    hub = _cyl_y(WINCH_HUB_Y1 - WINCH_HUB_Y0, WINCH_HUB_R,
                 WINCH_AXIS_X, WINCH_HUB_Y0, WINCH_AXIS_Z)
    hub = hub.cut(_cyl_y(WINCH_HUB_Y1 - WINCH_HUB_Y0 + 2.0, WINCH_HUB_BORE_D / 2.0,
                         WINCH_AXIS_X, WINCH_HUB_Y0 - 1.0, WINCH_AXIS_Z))
    add("winch_drum", _fuse(drum, hub))

    # THE ONE-WAY CLUTCH (LOCK 2). A wrap-spring clutch: Ø4.8 bore on the servo
    # spline, Ø8.0 body retained in the drum's hub. It DRIVES the drum in the
    # wind-in direction and OVERRUNS it in the pay-out direction, which is the
    # only reason the cable does not hold the carriage at the instant of
    # release. Drawn, not noted - check_release_resistance will not credit a
    # free-spool it cannot find a body for.
    clutch = _cyl_y(WINCH_CLUTCH_LEN, WINCH_CLUTCH_OD / 2.0,
                    WINCH_AXIS_X, WINCH_CLUTCH_Y0, WINCH_AXIS_Z)
    # The bore is drawn at the OVERRUNNING clearance, not at the shaft OD: what
    # grips the shaft is the wrap spring's coil, which stands off the shaft
    # everywhere except at the instant it tightens. A bore drawn on the shaft
    # diameter would state a permanent 0.000 mm interference and say the drum
    # can never free-spool, which is the opposite of what this part is for.
    clutch = clutch.cut(_cyl_y(WINCH_CLUTCH_LEN + 2.0,
                               WINCH_SHAFT_D / 2.0 + WINCH_CLUTCH_RUN_GAP,
                               WINCH_AXIS_X, WINCH_CLUTCH_Y0 - 1.0, WINCH_AXIS_Z))
    add("winch_clutch", clutch)

    # THE REWIND SPRING, on the stub, reacting to a post on the plate. Its job
    # is to keep D0.6 braid seated in an 0.8 mm groove when cable tension is
    # zero and to stop the drum overrunning at the end of the shot. It is the
    # ONLY thing besides clutch drag that the carriage tows, and both are
    # charged against it in check_release_resistance.
    rew = _cyl_y(WINCH_REWIND_LEN, WINCH_REWIND_OR,
                 WINCH_AXIS_X, WINCH_REWIND_Y0, WINCH_AXIS_Z)
    rew = rew.cut(_cyl_y(WINCH_REWIND_LEN + 2.0, WINCH_REWIND_IR,
                         WINCH_AXIS_X, WINCH_REWIND_Y0 - 1.0, WINCH_AXIS_Z))
    add("winch_rewind_spring", rew)

    # THE OUTPUT SHAFT ITSELF. Drawn because the drum has to be ON something,
    # and because "the drum is 0.2 mm off the servo case" is a statement about
    # a gap while "the drum's hub is engaged 2.0 mm on the shaft" is a statement
    # about a drive.
    add("winch_shaft", _cyl_y(WINCH_SERVO_Y0 - WINCH_HUB_Y0, WINCH_SHAFT_D / 2.0,
                              WINCH_AXIS_X, WINCH_HUB_Y0, WINCH_AXIS_Z))

    # THE ANCHOR PIN, through the carriage's fork. Ø2 hardened dowel.
    add("recock_anchor_pin",
        _cyl_y(ANCHOR_PIN_LEN, ANCHOR_PIN_D / 2.0, ANCHOR_PIN_X,
               (ANCHOR_FORK_Y0 + ANCHOR_FORK_Y1) / 2.0 - ANCHOR_PIN_LEN / 2.0,
               ANCHOR_PIN_Z))

    # THE CABLE, drawn at full cock: the free span from the drum's tangent point
    # to the pin, plus the swaged eye that closes the load path onto the pin.
    # The free span leaves the drum straight up at WINCH_CABLE_Z, so its
    # perpendicular distance from the shaft axis is WINCH_R_MIN_EFF by
    # construction - and check_recock_actuator re-measures that off these two
    # bodies rather than believing it.
    _cab_x0 = WINCH_AXIS_X
    _cab_x1 = ANCHOR_PIN_X - ANCHOR_PIN_D / 2.0
    cable = _cyl_x(_cab_x1 - _cab_x0, WINCH_CABLE_D / 2.0,
                   _cab_x0, WINCH_CABLE_Y, WINCH_CABLE_Z)
    eye = cq.Solid.makeTorus(CABLE_EYE_R, WINCH_CABLE_D / 2.0,
                             cq.Vector(ANCHOR_PIN_X, WINCH_CABLE_Y, ANCHOR_PIN_Z),
                             cq.Vector(0, 1, 0))
    add("recock_cable", _fuse(cable, eye))

    # ------------------------------------------------------------- the sear
    add("sear_pivot_pin", _cyl_y(SEAR_PIN_LEN, SEAR_PIN_R - 0.05,
                                 SEAR_PIVOT_X, SEAR_PIN_Y0, SEAR_PIVOT_Z))
    # THE SEAR RETURN SPRING. Architecture B is not self-holding - that is the
    # whole point of moving the contact onto the pivot line - so a light torsion
    # spring is what keeps it engaged, exactly as every real firearm sear has.
    # It is a body on the wrist and it belongs in the count.
    tors = _cyl_y(SEAR_TORSION_LEN, SEAR_TORSION_OD / 2.0,
                  SEAR_PIVOT_X, SEAR_TORSION_Y0, SEAR_PIVOT_Z)
    tors = tors.cut(_cyl_y(SEAR_TORSION_LEN + 2.0, SEAR_TORSION_BORE_R,
                           SEAR_PIVOT_X, SEAR_TORSION_Y0 - 1.0, SEAR_PIVOT_Z))
    add("sear_torsion_spring", tors)

    # ------------------------------------------------------------ the fluid end
    # NO BONDED JOINT ANYWHERE IN THE FLUID PATH (defect 10). The cannula is a
    # replaceable Luer-hub 8 ga blunt tip held in a collar by an O-ring, so a
    # cured plug is cleared by swapping a consumable rather than by pushing
    # 151 N through 30 N of spring.
    add("cannula", _cyl_x(OUTLET_LENGTH, CANNULA_OD / 2.0,
                          OUTLET_X0, FLUID_Y, SYRINGE_AXIS_Z))
    add("cannula_hub", _cyl_x(CANNULA_HUB_LEN, CANNULA_HUB_OD / 2.0,
                              OUTLET_X0 - CANNULA_HUB_LEN, FLUID_Y, SYRINGE_AXIS_Z))
    # The O-ring is coaxial with the hub it seals, i.e. an annulus about the
    # FLUID axis. Extruding it in Z made a flat washer lying across the bore.
    _or_x = OUTLET_X0 - CANNULA_HUB_LEN / 2.0
    oring = _cyl_x(ORING_CS, CANNULA_HUB_OD / 2.0 + ORING_CS,
                   _or_x, FLUID_Y, SYRINGE_AXIS_Z)
    oring = oring.cut(_cyl_x(ORING_CS + 2.0, CANNULA_HUB_OD / 2.0,
                             _or_x - 1.0, FLUID_Y, SYRINGE_AXIS_Z))
    add("cannula_oring", oring)

    # ------------------------------------------------------------- fasteners
    # The cradle is split - printed base plus a removable cap on two M3 screws
    # into heat-set inserts - so the drop-in opening is unrestricted and the
    # 13.70-into-10.30 impossibility of defect 7 cannot recur at 17.00.
    for i, sx in enumerate(CRADLE_SCREW_X):
        add(f"cradle_screw_{i}",
            _cyl_z(M3_SCREW_LEN, 1.5, sx, FLUID_Y + CRADLE_SCREW_DY,
                   CRADLE_SCREW_Z0))
        add(f"cradle_screw_{i}b",
            _cyl_z(M3_SCREW_LEN, 1.5, sx, FLUID_Y - CRADLE_SCREW_DY,
                   CRADLE_SCREW_Z0))

    # y is ELEC_Y + 1.3, not + 1.0: at +1.0 the pack's -Y face lands on
    # y = -3.000 and the syringe's finger flange reaches y = -3.000 as well.
    # A true solid-to-solid distance says 0.000 mm there; min_gap() samples
    # vertices and would not have said anything, which is why it was measured
    # with BRepExtrema rather than trusted.
    add("lipo_2000mah", _box(54.0, 34.0, 10.0, BATT_X0, ELEC_Y + 1.3, PLATE_T))

    assert len(m) >= MOCKUP_BODY_COUNT_FLOOR, (
        f"make_mockups() has shrunk to {len(m)} bodies (floor "
        f"{MOCKUP_BODY_COUNT_FLOOR}). Mk4 was rejected because this dictionary "
        f"was empty and the harness saw only printed parts; it may grow, and it "
        f"may not shrink to make a failure disappear.")
    return m


mockups: Dict[str, Placed] = make_mockups()


def sear_moment_check() -> dict:
    """Does the spring load hold the sear closed, or open it?

    Mk3 failed here and asserted the opposite in prose. Compute it.
    Contact force on the tooth is +X (the carriage pushing forward).
    Moment about the pivot, in the XZ plane, about +Y:
        M_y = r_z * F_x - r_x * F_z ,  with F_z = 0  ->  M_y = r_z * F_x
    r_z = tooth_z - pivot_z is negative (tooth below pivot), so M_y is negative:
    a rotation that drives the tooth further into the notch. Engagement is stable.

    (Mk5 round 5) THE SIGN IS UNCHANGED AND THE MAGNITUDE IS NOT. Architecture B
    put the contact on the pivot line, so r_z is -1.20 mm instead of -13.40 and
    the holding moment is 44.7 N.mm instead of 499. Still self-holding, still by
    the same sign - but weakly enough that SEAR_SPRING_PRELOAD_N_MM, not the
    load, is what actually keeps the tooth seated between shots.
    """
    r_x = SEAR_CONTACT_X - SEAR_PIVOT_X          # negative: tooth behind pivot
    r_z = SEAR_CONTACT_Z - SEAR_PIVOT_Z          # negative: tooth below pivot
    F = SPRING_PEAK_N                             # carriage pushes the tooth +X
    m_y = r_z * F                                 # M_y = r_z*F_x - r_x*F_z, F_z=0
    # dz = -dtheta * r_x, and dtheta follows the sign of m_y (= sign of r_z).
    # So dz has the sign of -r_z*r_x: the tooth moves DOWN iff r_x and r_z share
    # a sign. Below-and-behind satisfies it; below-and-forward unlatches.
    engages = (r_x * r_z) > 0
    # Release lift: the tooth must rise from its seat to above the lug top, and
    # a rotation dtheta about the pivot raises it by |r_x|*sin(dtheta) - NOT
    # |r_z|, which is the arm for the holding moment, not for the lift.
    lift_mm = _LUG_TOP - SEAR_CONTACT_Z
    lift_needed_deg = math.degrees(math.asin(
        min(1.0, lift_mm / max(1e-6, abs(r_x)))))
    return dict(r_x_mm=r_x, r_z_mm=r_z, force_N=F, moment_N_mm=m_y,
                lift_mm=lift_mm,
                self_holding=engages, lift_to_release_deg=lift_needed_deg,
                note="tooth below AND behind the pivot: load drives it down")


def report() -> dict:
    sm = sear_moment_check()
    return {
        "exit_velocity_m_s": EXIT_VELOCITY_M_S,
        "ballistic_range_m": BALLISTIC_RANGE_M,
        "shot_volume_ml": SHOT_VOLUME_ML,
        "shot_time_s": SHOT_TIME_S,
        "outlet_bore_mm": OUTLET_BORE,
        "outlet_dp_kPa": OUTLET_DP_PA / 1000.0,
        "flow_work_J": FLOW_WORK_J,
        "cannula_id_mm": CANNULA_ID_MM,
        "cannula_work_J": CANNULA_WORK_J,
        "sizing_work_J": SIZING_WORK_J,
        "spring_energy_J": SPRING_ENERGY_J,
        "energy_margin": SPRING_ENERGY_J / FLOW_WORK_J,
        "energy_margin_on_real_cannula": SPRING_ENERGY_J / CANNULA_WORK_J,
        "ramp_normal_deg": RAMP_NORMAL_DEG,
        "ramp_cam_margin": RAMP_TAN / RAMP_MU,
        "carriage_lateral_play_mm": CARRIAGE_Y_PLAY,
        "plunger_stroke_mm": PLUNGER_STROKE,
        "plunger_force_N": PLUNGER_FORCE_N,
        "spring_peak_N": SPRING_PEAK_N,
        "spring_rate_N_mm": SPRING_RATE_N_MM,
        "hand_cock_force_N": SPRING_PEAK_N,
        "shots_per_fill": SHOTS_PER_FILL,
        "syringe_capacity_ml": SYRINGE_CAPACITY_ML,
        "fill_len_mm": FILL_LEN,
        "push_rod_od": PUSH_ROD_OD,
        "grip_tilt_deg": GRIP_TILT_DEG,
        # the EXACT root of D*cos(a) - t*sin(a) = d, not the atan stand-in that
        # used to be reported here and re-checked with itself
        "grip_bite_root_deg": GRIP_BITE_ROOT_DEG,
        "grip_bite_min_deg": GRIP_BITE_MIN_DEG,
        "grip_tilt_margin": GRIP_TILT_MARGIN,
        "grip_bite_aperture_mm": GRIP_BITE_APERTURE_MM,
        "grip_bite_interference_mm": GRIP_BITE_INTERFERENCE_ACTUAL_MM,
        "grip_square_clearance_mm": GRIP_SQUARE_CLEARANCE_MM,
        "piston_seal_drag_N": PISTON_SEAL_DRAG_N,
        "grip_return_spring_N": GRIP_RETURN_SPRING_N,
        "grip_release_margin": GRIP_RELEASE_MARGIN,
        "grip_clear_span_mm": GRIP_CLEAR_SPAN_MM,
        "grip_span_needed_mm": GRIP_SPAN_NEEDED_MM,
        "grip_span_deficit_mm": GRIP_SPAN_DEFICIT_MM,
        "rod_x0": ROD_X0,
        "rod_len": ROD_LEN,
        "frame_x0": FRAME_X0,
        "frame_len_mm": FRAME_LEN,
        "frame_growth_rearward_mm": -FRAME_X0,
        "carriage_x_cocked": CARRIAGE_X_COCKED,
        "carriage_x_fired": CARRIAGE_X_FIRED,
        "spring_seat_x": SPRING_SEAT_X,
        "carriage_top_z": _CARRIAGE_TOP,
        "sear_pivot_z": SEAR_PIVOT_Z,
        "recock_sweep_deg": RECOCK_SWEEP_DEG,
        "winch_pitch_r_max_mm": WINCH_R_MAX_EFF,
        "winch_pitch_r_min_mm": WINCH_R_MIN_EFF,
        "winch_phi0_rad": WINCH_PHI0_RAD,
        "recock_work_N_mm": RECOCK_WORK_N_MM,
        "recock_drag_N": RECOCK_DRAG_N,
        "winch_cable_torque_N_mm": WINCH_TORQUE_N_MM,
        "winch_servo_torque_N_mm": WINCH_SERVO_TORQUE_N_MM,
        "servo_usable_N_mm": SERVO_USABLE_N_MM,
        "mockup_body_count": len(mockups),
        "printed_part_count": len(PARTS),
        "plate_mm": [FRAME_LEN, PLATE_W, PLATE_T],
        "sear": sm,
    }


def export_params() -> None:
    """Publish the numbers downstream tools need, so the Blender viz reads data
    rather than importing this module (Blender's Python has no CadQuery)."""
    import json
    d = report()
    d.update(dict(
        PLUNGER_STROKE=PLUNGER_STROKE, SPRING_FREE_LEN=SPRING_FREE_LEN,
        SPRING_COCKED_LEN=SPRING_COCKED_LEN, OUTLET_X1=OUTLET_X1,
        MUZZLE_LEN=MUZZLE_LEN, FLUID_Y=FLUID_Y, SYRINGE_AXIS_Z=SYRINGE_AXIS_Z,
        PLATE_L=PLATE_L, PLATE_W=PLATE_W, SHOT_TIME_MS=SHOT_TIME_S * 1000.0,
    ))
    with open(os.path.join(OUT, "mk4_params.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    print("  wrote mk4_params.json")


def export_all() -> None:
    for name, fn in PARTS.items():
        s = fn()
        assert s.isValid(), f"{name}: invalid"
        assert len(s.Solids()) == 1, f"{name}: {len(s.Solids())} solids"
        b = s.BoundingBox()
        assert abs(b.zmin) < 0.01, f"{name}: zmin {b.zmin}"
        cq.exporters.export(cq.Workplane(obj=s), os.path.join(OUT, f"mk4_{name}.step"))
        cq.exporters.export(cq.Workplane(obj=s), os.path.join(OUT, f"mk4_{name}.stl"),
                            tolerance=0.05, angularTolerance=0.1)
        print(f"  {name:<16} vol={s.Volume():9.1f} mm3  {b.xlen:6.1f} x {b.ylen:6.1f} x {b.zlen:5.1f}")


if __name__ == "__main__":
    import json
    print("Web-Shooter Mk4")
    print(json.dumps(report(), indent=1))
    print("\nexporting:")
    export_all()
    export_params()
    sys.stdout.flush()
    os._exit(0)
