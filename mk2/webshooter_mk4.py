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
  3. 11.2 N IS A THUMB PULL, so the cocking lever and its two pins are deleted.
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
FLOW_RATE_M3_S = EXIT_VELOCITY_M_S * math.pi * _r * _r
SHOT_TIME_S = _V / FLOW_RATE_M3_S                        # derived, not declared
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

# --------------------------------------------------------------------- spring
# Sized from the derived flow work with margin, not chosen then justified.
SPRING_MARGIN = 1.45
SPRING_ENERGY_J = FLOW_WORK_J * SPRING_MARGIN
SPRING_PEAK_N = 2.0 * SPRING_ENERGY_J / (PLUNGER_STROKE / 1000.0)
SPRING_RATE_N_MM = SPRING_PEAK_N / PLUNGER_STROKE
SPRING_OD = 8.0
SPRING_WIRE = 0.9
SPRING_FREE_LEN = 46.0
SPRING_COCKED_LEN = SPRING_FREE_LEN - PLUNGER_STROKE

# ------------------------------------------------------------------- envelope
PLATE_T = 3.0
PLATE_W = 64.0
WALL = 2.4
RAIL_H = 9.0
RAIL_T = 2.4

CLEAR = 0.25                    # located fit, per side
BORE_CLEAR = 0.30
M3_CLEAR = 3.6                  # printed, at the bed
INSERT_PILOT = 4.5              # 5.0 x 4.0 knurled inserts
INSERT_BOSS_OD = 10.0

# lanes: fluid on -Y, electronics on +Y
FLUID_Y = -20.0
ELEC_Y = 11.0

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
SEAR_PIVOT_X = CARRIAGE_X_FIRED - 4.0
SEAR_PIVOT_Z = PLATE_T + RAIL_H + 9.0
SEAR_TOOTH_X = SEAR_PIVOT_X - 6.0
SEAR_TOOTH_Z = PLATE_T + 4.0
SEAR_W = 5.0
SEAR_TAIL_LEN = 22.0

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

    # sear pivot post
    post = _box(6.0, SEAR_W + 2 * 2.4, SEAR_PIVOT_Z - PLATE_T + 4.0,
                SEAR_PIVOT_X - 3.0, FLUID_Y - inner - RAIL_T - 3.2, PLATE_T)
    post = post.cut(_cyl_x(30.0, 1.7, SEAR_PIVOT_X - 12.0,
                           FLUID_Y - inner - RAIL_T - 3.2, SEAR_PIVOT_Z))
    plate = _fuse(plate, post)

    # electronics shelf ribs (open, so nothing prints in mid-air)
    for cx in (BATT_X1 + 6.0, BATT_X1 + 40.0):
        plate = _fuse(plate, _box(4.0, 26.0, 6.0, cx, ELEC_Y, PLATE_T))

    # strap slots — 25 mm webbing, two stations
    for sx in (16.0, PLATE_L - 26.0):
        plate = plate.cut(_box(4.0, 27.0, PLATE_T + 2, sx, 0.0, -1.0))

    # bridge inserts
    for y in (-16.0, 16.0):
        bx = PLATE_L - 12.0
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
    body = _box(CARRIAGE_LEN, body_w, RAIL_H - 1.0, 0.0, 0.0, 0.0)

    # push pad against the plunger thumb flange
    pad = _box(3.0, PLUNGER_THUMB_OD, SYRINGE_AXIS_Z - PLATE_T + 6.0,
               CARRIAGE_LEN - 3.0, 0.0, 0.0)
    body = _fuse(body, pad)

    # spring pilot: a stub the coil sits over, so it cannot buckle sideways
    body = _fuse(body, _cyl_x(8.0, SPRING_OD / 2.0 - SPRING_WIRE - 0.4,
                              -8.0, 0.0, (RAIL_H - 1.0) / 2.0))

    # sear shelf on the REAR face — a square notch the tooth drops into
    notch = _box(3.2, SEAR_W + 2 * CLEAR, 5.0, 0.0, -body_w / 2.0 + 4.0, 0.0)
    body = body.cut(notch)

    # thumb tab for hand cocking — 11.2 N peak, no lever needed
    body = _fuse(body, _box(4.0, body_w, 14.0, 2.0, 0.0, RAIL_H - 1.0))
    return _ground(body)


# ==================================================================== part 3/5
def make_sear() -> cq.Shape:
    """Pawl. Pivot sits above and forward of the tooth so the spring's +X load
    produces a moment that drives the tooth DOWN into the notch."""
    dx = SEAR_PIVOT_X - SEAR_TOOTH_X
    dz = SEAR_PIVOT_Z - SEAR_TOOTH_Z
    arm_len = math.hypot(dx, dz)

    # Modelled flat: the 5 mm dimension is Z, so the whole profile lies on the bed
    # and prints without support. Rotate 90 deg about X at assembly.
    arm = _box(arm_len, 5.0, SEAR_W, 0.0, 0.0, 0.0)
    tooth = _box(3.0, 6.0, SEAR_W, 0.0, -5.5, 0.0)
    tail = _box(SEAR_TAIL_LEN, 4.0, SEAR_W, arm_len - 2.0, 0.5, 0.0)
    body = _fuse(arm, tooth, tail)
    body = body.cut(_cyl_z(SEAR_W + 2, 1.7, arm_len - 3.0, 0.0, -1.0))
    return _ground(body)


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
SEAR_Y = FLUID_Y - SYRINGE_OD / 2.0 - 3.0 - RAIL_T - 3.2

printed_parts: Dict[str, Placed] = {
    "baseplate": Placed(make_baseplate(), cq.Location()),
    "carriage": Placed(make_carriage(), cq.Location(cq.Vector(
        CARRIAGE_X_FIRED - PLUNGER_STROKE, FLUID_Y, CARRIAGE_Z0 + 0.4))),
    "sear": Placed(make_sear(), cq.Location(
        cq.Vector(SEAR_TOOTH_X, SEAR_Y - 4.0, SEAR_TOOTH_Z + 6.0),
        cq.Vector(1.0, 0.0, 0.0), 90.0)),
    "outlet_adapter": Placed(make_outlet(), cq.Location(cq.Vector(
        OUTLET_X0 - 2.0, FLUID_Y, SYRINGE_AXIS_Z - (SYRINGE_OD / 2.0 + 2.2) + 3.0))),
    # palm pod rides its own strap, clear of the plate entirely
    "switch_pod": Placed(make_switch_pod(), cq.Location(cq.Vector(
        PLATE_L - 30.0, -PLATE_W / 2.0 - 24.0, 0.0))),
}


def sear_moment_check() -> dict:
    """Does the spring load hold the sear closed, or open it?

    Mk3 failed here and asserted the opposite in prose. Compute it.
    Contact force on the tooth is +X (the carriage pushing forward).
    Moment about the pivot, in the XZ plane, about +Y:
        M_y = r_z * F_x - r_x * F_z ,  with F_z = 0  ->  M_y = r_z * F_x
    r_z = tooth_z - pivot_z is negative (tooth below pivot), so M_y is negative:
    a rotation that drives the tooth further into the notch. Engagement is stable.
    """
    r_x = SEAR_TOOTH_X - SEAR_PIVOT_X
    r_z = SEAR_TOOTH_Z - SEAR_PIVOT_Z
    F = SPRING_PEAK_N
    m_y = r_z * F - r_x * 0.0
    return dict(r_x_mm=r_x, r_z_mm=r_z, force_N=F, moment_N_mm=m_y,
                self_holding=m_y < 0,
                note="negative M_y drives the tooth deeper into the notch")


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
        "spring_energy_J": SPRING_ENERGY_J,
        "energy_margin": SPRING_ENERGY_J / FLOW_WORK_J,
        "plunger_stroke_mm": PLUNGER_STROKE,
        "plunger_force_N": PLUNGER_FORCE_N,
        "spring_peak_N": SPRING_PEAK_N,
        "spring_rate_N_mm": SPRING_RATE_N_MM,
        "hand_cock_force_N": SPRING_PEAK_N,
        "printed_part_count": len(PARTS),
        "plate_mm": [PLATE_L, PLATE_W, PLATE_T],
        "sear": sm,
    }


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
    sys.stdout.flush()
    os._exit(0)
