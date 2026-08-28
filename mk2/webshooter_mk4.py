#!/usr/bin/env python3
"""
Web-Shooter Mk4 — parametric CadQuery model.

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
TARGET_RANGE_M = 1.5
G = 9.81

EXIT_VELOCITY_M_S = math.sqrt(TARGET_RANGE_M * G)        # 3.836 m/s
OUTLET_BORE = 4.0                                        # mm — the Luer is cut off
OUTLET_LENGTH = 12.0                                     # mm of wetted bore

_r = OUTLET_BORE / 2000.0
_V = SHOT_VOLUME_ML * 1e-6
OUTLET_DP_PA = 8 * FLUID_VISCOSITY_PA_S * (OUTLET_LENGTH / 1000.0) * EXIT_VELOCITY_M_S / (_r * _r)
FLOW_WORK_J = OUTLET_DP_PA * _V
SHOT_TIME_S = _V / (EXIT_VELOCITY_M_S * math.pi * _r * _r)   # derived
BALLISTIC_RANGE_M = EXIT_VELOCITY_M_S ** 2 / G

# ------------------------------------------------------------------ cartridge
# 5 mL NORM-JECT (Restek 22775 table). Bore does not affect exit velocity.
SYRINGE_BORE = 12.45
SYRINGE_OD = 13.70
SYRINGE_BARREL_LEN = 73.8
SYRINGE_FLANGE_OD = 22.0
SYRINGE_FLANGE_T = 2.5

_A_p = math.pi * (SYRINGE_BORE / 2000.0) ** 2
PLUNGER_STROKE = _V / _A_p * 1000.0                      # 16.43 mm
PLUNGER_FORCE_N = OUTLET_DP_PA * _A_p                    # 5.60 N
PLUNGER_ROD_OD = 6.0
PLUNGER_THUMB_OD = 18.0
PLUNGER_THUMB_T = 2.5

# ----------------------------------------------------- the sizing restriction
# THE SPRING IS SIZED FROM THE TIGHTEST BORE THE FLUID ACTUALLY SEES, NOT FROM
# THE ONE THE ADAPTER IS DRAWN WITH.
# The adapter's own bore is 4.00 mm, but a real 8 ga blunt-tip dispensing
# cannula - the thing that will be on the front of this, and the case the
# independent harness sizes against - has an ID of 3.429 mm. Poiseuille goes as
# r^-4, so that 14% smaller radius costs 85% more work: 0.1705 J against the
# 0.0921 J the 4 mm bore needs. Sizing the spring from the design bore and then
# fitting the real cannula is how the drive ends up energy-starved, which is one
# of the four failures Mk4 was created to remove. So the sizing case is
# max(design bore, real cannula), and the margin is applied to that.
CANNULA_ID_MM = 3.429                                    # real 8 ga blunt tip
_rc = CANNULA_ID_MM / 2000.0
FLOW_RATE_M3_S = EXIT_VELOCITY_M_S * math.pi * _r * _r   # set by the design bore
CANNULA_DP_PA = (8 * FLUID_VISCOSITY_PA_S * (OUTLET_LENGTH / 1000.0)
                 * FLOW_RATE_M3_S / (math.pi * _rc ** 4))
CANNULA_WORK_J = CANNULA_DP_PA * _V
SIZING_WORK_J = max(FLOW_WORK_J, CANNULA_WORK_J)

# --------------------------------------------------------------------- spring
# Sized from the derived sizing work with margin, not chosen then justified.
SPRING_MARGIN = 1.45
SPRING_ENERGY_J = SIZING_WORK_J * SPRING_MARGIN
SPRING_PEAK_N = 2.0 * SPRING_ENERGY_J / (PLUNGER_STROKE / 1000.0)
SPRING_RATE_N_MM = SPRING_PEAK_N / PLUNGER_STROKE
SPRING_OD = 8.0
SPRING_WIRE = 0.9
SPRING_FREE_LEN = 46.0
SPRING_COCKED_LEN = SPRING_FREE_LEN - PLUNGER_STROKE

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

# stations along X
BATT_X0, BATT_X1 = 6.0, 60.0            # LiPo 54 x 34 x 10, beside the spring
SPRING_X0 = 8.0
CARRIAGE_X_FIRED = SPRING_X0 + SPRING_FREE_LEN - 6.0
CARRIAGE_LEN = 16.0
SYRINGE_X0 = CARRIAGE_X_FIRED + CARRIAGE_LEN + 2.0
SYRINGE_X1 = SYRINGE_X0 + SYRINGE_BARREL_LEN
OUTLET_X0 = SYRINGE_X1
OUTLET_X1 = OUTLET_X0 + OUTLET_LENGTH
MUZZLE_LEN = 14.0
PLATE_L = OUTLET_X1 + MUZZLE_LEN + 6.0

SYRINGE_AXIS_Z = PLATE_T + SYRINGE_OD / 2.0 + 0.6
CARRIAGE_Z0 = PLATE_T

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
CARRIAGE_BODY_H = RAIL_H - 1.0                    # body sits below the rail tops
CARRIAGE_PAD_H = SYRINGE_AXIS_Z - PLATE_T + 3.0   # push pad, over the plunger axis
CARRIAGE_TAB_H = 5.0                              # thumb tab, above the body top

# tallest carriage feature that is NOT the sear lug, in world Z
_CARRIAGE_TOP = CARRIAGE_Z0 + CARRIAGE_LIFT + max(
    CARRIAGE_PAD_H, CARRIAGE_BODY_H + CARRIAGE_TAB_H)

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
SEAR_PIVOT_Y = -31.0                              # outboard, clear of the lane
SEAR_PIVOT_Z = _LUG_TOP + 9.0                     # above everything it must clear
SEAR_W = 5.0                                      # slab thickness, measured in Y
SEAR_TAIL_LEN = 24.0
SEAR_POST_R = 3.0
SEAR_BACK = SEAR_PIVOT_X - SEAR_CONTACT_X         # tooth is this far behind
SEAR_DROP = SEAR_PIVOT_Z - SEAR_CONTACT_Z         # and this far below

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
    plate = _box(PLATE_L, PLATE_W, PLATE_T)

    # Shallow cylindrical relief in the underside, inboard of a flat rim.
    # The cylinder sits BELOW the plate so its top surface is highest on the
    # centreline - that is what cups the arm. (Centring it above hollows the
    # edges instead, which is the opposite of a wrist curve.)
    relief_w = PLATE_W - 2 * RELIEF_RIM
    cyl_z = RELIEF_DEPTH - WRIST_RADIUS
    cutter = (cq.Workplane("YZ").circle(WRIST_RADIUS).extrude(PLATE_L + 20.0)
              .val().moved(cq.Location(cq.Vector(-10.0, 0.0, cyl_z))))
    keep = _box(PLATE_L + 20.0, relief_w, PLATE_T + 6.0, -10.0, 0.0, -3.0)
    plate = plate.cut(cutter.intersect(keep))

    # carriage ways: two rails either side of the fluid lane
    inner = SYRINGE_OD / 2.0 + 3.0
    rail_x0 = SPRING_X0 - 2.0
    rail_len = (SYRINGE_X0 - 1.0) - rail_x0
    for sgn in (-1, 1):
        y = FLUID_Y + sgn * inner
        plate = _fuse(plate, _box(rail_len, RAIL_T, RAIL_H, rail_x0, y, PLATE_T))

    # spring rear abutment — reacts the full spring force into the plate
    plate = _fuse(plate, _box(WALL, 2 * inner + 2 * RAIL_T, RAIL_H + 4.0,
                              SPRING_X0 - 2.0 - WALL, FLUID_Y, PLATE_T))

    # syringe cradle: a trough plus two ribs that capture the barrel
    cradle_r = SYRINGE_OD / 2.0 + BORE_CLEAR
    for cx in (SYRINGE_X0 + 6.0, SYRINGE_X1 - 12.0):
        rib = _box(6.0, SYRINGE_OD + 2 * 4.0, SYRINGE_AXIS_Z + 2.0, cx, FLUID_Y, PLATE_T)
        rib = rib.cut(_cyl_x(8.0, cradle_r, cx - 1.0, FLUID_Y, SYRINGE_AXIS_Z))
        # open the top so the cartridge drops in
        rib = rib.cut(_box(8.0, 2 * cradle_r * 0.72, 20.0,
                           cx - 1.0, FLUID_Y, SYRINGE_AXIS_Z))
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
                              SEAR_PIVOT_Y - 0.5, 0.0))
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
    # CHEEK_RELIEF_R - 1.7 = 2.05 mm collar all the way round.
    quad = _box(SEAR_POST_R + 1.0, TOWER_W + 2.0,
                (TOWER_TOP_Z - SEAR_PIVOT_Z) + 1.0,
                SEAR_PIVOT_X - SEAR_POST_R - 1.0, SEAR_PIVOT_Y, SEAR_PIVOT_Z)
    plate = plate.cut(quad.cut(_cyl_y(
        TOWER_W + 8.0, CHEEK_RELIEF_R, SEAR_PIVOT_X,
        SEAR_PIVOT_Y - TOWER_W / 2.0 - 4.0, SEAR_PIVOT_Z)))

    # pivot pin bore, on the Y axis, through BOTH cheeks
    plate = plate.cut(_cyl_y(TOWER_W + 12.0, 1.7, SEAR_PIVOT_X,
                             SEAR_PIVOT_Y - TOWER_W / 2.0 - 6.0, SEAR_PIVOT_Z))

    # electronics shelf ribs (open, so nothing prints in mid-air)
    for cx in (BATT_X1 + 6.0, BATT_X1 + 40.0):
        plate = _fuse(plate, _box(4.0, 26.0, 6.0, cx, ELEC_Y, PLATE_T))

    # strap slots — 25 mm webbing, two stations
    for sx in (16.0, PLATE_L - 26.0):
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
    """Slides in the rails, pushes the plunger thumb flange, and presents a REAR
    face for the sear. Firing carries it away from the sear, so no stroke jam."""
    inner = SYRINGE_OD / 2.0 + 3.0
    body_w = 2 * inner - 2 * RAIL_T - 2 * CLEAR   # clear span, not centres
    body = _box(CARRIAGE_LEN, body_w, CARRIAGE_BODY_H, 0.0, 0.0, 0.0)

    # push pad against the plunger thumb flange. Height is CARRIAGE_PAD_H, which
    # SEAR_CONTACT_Z is derived from - the pad may not grow past the tooth.
    pad = _box(3.0, body_w, CARRIAGE_PAD_H, CARRIAGE_LEN - 3.0, 0.0, 0.0)
    body = _fuse(body, pad)

    # spring pilot: a stub the coil sits over, so it cannot buckle sideways
    body = _fuse(body, _cyl_x(8.0, SPRING_OD / 2.0 - SPRING_WIRE - 0.4,
                              -8.0, 0.0, CARRIAGE_BODY_H / 2.0))

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

    # thumb tab for hand cocking
    body = _fuse(body, _box(4.0, body_w, CARRIAGE_TAB_H, 2.0, 0.0, CARRIAGE_BODY_H))
    return _ground(body)


# ==================================================================== part 3/5
def _sear_raw() -> cq.Shape:
    """Lifting pawl, in ASSEMBLY orientation with the pivot at the origin.

    Shape: a hub at the pivot, a cross-arm reaching inboard over the lane, a leg
    dropping to the tooth (below and behind the pivot), and a tail the servo
    lifts. Load pushes the tooth +X, which rotates it DOWN into the lug.
    """
    back = SEAR_PIVOT_X - SEAR_CONTACT_X          # tooth is this far behind
    drop = SEAR_PIVOT_Z - SEAR_CONTACT_Z          # and this far below
    lat = SEAR_CONTACT_Y - SEAR_PIVOT_Y           # positive: tooth is inboard

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

    # The leg drops outboard of the carriage lane; only the tooth cantilevers
    # inboard to the lug. A leg at the lug's own Y would fall through the
    # carriage body on every stroke.
    leg_y = 5.0                                   # leg centre, outboard of the body
    # jog: carries the slab out to the leg. It overlaps the cross-arm in Y (so
    # the fuse is a volume, not a shared face). Its front face - and the leg's -
    # sit at SEAR_INBOARD_X. That face does two jobs: it is the surface that
    # sweeps past the relieved cheek corner (CHEEK_RELIEF_R, above), and at
    # 0 deg it is the surface that bottoms flat on the baseplate's rotation stop
    # pad, which is why the two are built from the same number.
    jog = _box((back + 5.0) - SEAR_INBOARD_X, leg_y + 2.5, arm_h,
               -(back + 5.0), (leg_y + 2.5) / 2.0, arm_z0)
    leg = _box(back - SEAR_INBOARD_X, 5.0, drop, -back, leg_y, -drop)
    # The tooth's REAR face abuts the lug's FRONT face and nothing else: it is
    # SEAR_TOOTH_H tall, seated SEAR_TOOTH_GAP above the carriage's tallest
    # non-lug feature and finishing below the lug top, so the only coincident
    # surface in the pair is that one vertical face.
    #
    # ITS WIDTH IS DERIVED FROM THE LUG'S SWEPT Y BAND, not from the lug's
    # nominal position. It starts flush with the leg's outboard face and runs
    # inboard far enough to still overlap the whole lug when the carriage is
    # at either limit of the lateral play the rails permit, plus margin.
    tooth_y0 = leg_y - 5.0 / 2.0
    tooth_y1 = ((_LUG_Y_INBOARD + CARRIAGE_Y_PLAY + TOOTH_CAPTURE_MARGIN)
                - SEAR_PIVOT_Y)
    assert (SEAR_PIVOT_Y + tooth_y0
            <= _LUG_Y_OUTBOARD - CARRIAGE_Y_PLAY - TOOTH_CAPTURE_MARGIN), \
        "tooth does not reach outboard past the lug's play band"
    lat = tooth_y1 - tooth_y0
    tooth = _box(SEAR_TOOTH_L, lat, SEAR_TOOTH_H, -back,
                 tooth_y0 + lat / 2.0, -drop)
    tail = _box(SEAR_TAIL_LEN + 6.0, SEAR_W, 4.0, -3.0, 0.0, -2.0)
    body = _fuse(hub, cross, jog, leg, tooth, tail)

    # THE COCKING RAMP on the sear's FRONT, cut across the FULL width of the
    # part. Cutting it on the tooth alone would leave the LEG's square front
    # standing 1 mm further forward, and at the outboard limit of the
    # carriage's lateral play the lug reaches the leg - so the lug would find
    # a 0 deg wall exactly where the tooth had a ramp. One cut across all Y
    # makes the ramp a property of the part rather than of one feature.
    # The cut spans from the tooth's underside up past the lug top, so there is
    # no square face left at any height the lug can reach.
    far = -back + SEAR_TOOTH_L + 20.0
    ramp = (cq.Workplane("XZ")
            .polyline([(-back + SEAR_TOOTH_L - SEAR_RAMP_RUN, -drop),
                       (far, -drop),
                       (far, -drop + SEAR_RAMP_BAND),
                       (-back + SEAR_TOOTH_L, -drop + SEAR_RAMP_BAND)])
            .close().extrude(lat + 40.0).val()
            .moved(cq.Location(cq.Vector(0.0, tooth_y1 + 20.0, 0.0))))
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


def sear_moment_check() -> dict:
    """Does the spring load hold the sear closed, or open it?

    Mk3 failed here and asserted the opposite in prose. Compute it.
    Contact force on the tooth is +X (the carriage pushing forward).
    Moment about the pivot, in the XZ plane, about +Y:
        M_y = r_z * F_x - r_x * F_z ,  with F_z = 0  ->  M_y = r_z * F_x
    r_z = tooth_z - pivot_z is negative (tooth below pivot), so M_y is negative:
    a rotation that drives the tooth further into the notch. Engagement is stable.
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
        "printed_part_count": len(PARTS),
        "plate_mm": [PLATE_L, PLATE_W, PLATE_T],
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
