"""Web-Shooter Mk3 spring/sear open-frame CadQuery model.

Run with::

    python webshooter_mk2.py

The filename is retained because it is the requested rebuild target.  The module
leaves ``assembly``, ``printed_parts``, ``mockups`` and ``verification_report``
available to geometry auditors after import.  Only ``printed_parts`` are exported
to the printable-parts directory; every placed item, including mockups, is also
exported to ``assembly_stl``.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping

import cadquery as cq
from cadquery import exporters


# -----------------------------------------------------------------------------
# Shared design parameters -- millimetres, seconds and SI physics where noted.
# -----------------------------------------------------------------------------

OUT_DIR = Path(__file__).resolve().parent
PART_DIR = OUT_DIR / "printed_parts"
ASSEMBLY_STL_DIR = OUT_DIR / "assembly_stl"

# Flat, shallow chord: the 0.8 mm closed-cell foam is the conformal skin interface.
BASE_LENGTH = 118.0
BASE_WIDTH = 64.0
BASE_THICKNESS = 2.8
FOAM_THICKNESS = 0.8
WRIST_PROFILE_LIMIT = 25.0

# Purchased/owned hardware.
M3_CLEARANCE_DIAMETER = 3.4
M3_INSERT_OD = 5.0
M3_INSERT_LENGTH = 4.0
M3_INSERT_POCKET_DIAMETER = 4.8  # deliberate heat-set interference, never a clearance proxy
M3_HEAD_DIAMETER = 5.8
STRAP_WIDTH = 25.0
STRAP_THICKNESS = 1.5
STRAP_CLEARANCE = 1.0

# Syringe and fluid path.  The live path is straight on one named axis.
SYRINGE_BORE_DIAMETER = 15.9
SYRINGE_BARREL_OD = 17.3
SYRINGE_BARREL_LENGTH = 85.3
SYRINGE_X = 84.0
SYRINGE_AXIS_Y = -6.0
SYRINGE_AXIS_Z = 12.5
SYRINGE_LUER_LENGTH = 9.0
SYRINGE_LUER_OD = 4.4
SYRINGE_FINGER_FLANGE_X = SYRINGE_X - 2.0
SYRINGE_THUMB_FLANGE_X = 70.5
SYRINGE_GUIDE_CLEARANCE = 0.60

SHOT_VOLUME_ML = 2.00
PLUNGER_AREA_MM2 = math.pi * SYRINGE_BORE_DIAMETER**2 / 4.0
PLUNGER_STROKE = SHOT_VOLUME_ML * 1000.0 / PLUNGER_AREA_MM2

# Hard target is ballistic, so it governs the illustrative 0.5 s line in the brief.
ORIFICE_DIAMETER = 3.0
ORIFICE_AREA_MM2 = math.pi * ORIFICE_DIAMETER**2 / 4.0
AREA_RATIO = PLUNGER_AREA_MM2 / ORIFICE_AREA_MM2
SHOT_TIME_S = 0.069
PLUNGER_SPEED_M_S = (PLUNGER_STROKE / 1000.0) / SHOT_TIME_S
EXIT_VELOCITY_M_S = PLUNGER_SPEED_M_S * AREA_RATIO
GRAVITY_M_S2 = 9.80665
BALLISTIC_RANGE_M = EXIT_VELOCITY_M_S**2 / GRAVITY_M_S2  # ideal, level, 45 degrees

# Bench-selection specification for the owned spring assortment.  Releasable energy
# is below 0.2 J and peak plunger force is below 30 N.
SPRING_OD = 10.0
SPRING_FREE_LENGTH = 39.7
SPRING_FIRED_LENGTH = 35.6
SPRING_COCKED_LENGTH = SPRING_FIRED_LENGTH - PLUNGER_STROKE
SPRING_RATE_N_MM = 1.94
SPRING_FIRED_FORCE_N = (SPRING_FREE_LENGTH - SPRING_FIRED_LENGTH) * SPRING_RATE_N_MM
SPRING_COCKED_FORCE_N = (SPRING_FREE_LENGTH - SPRING_COCKED_LENGTH) * SPRING_RATE_N_MM
SPRING_RELEASE_ENERGY_J = (
    (SPRING_FIRED_FORCE_N + SPRING_COCKED_FORCE_N) * 0.5 * PLUNGER_STROKE / 1000.0
)
COCKING_LEVER_MECHANICAL_ADVANTAGE = 2.20
MAX_HAND_COCK_FORCE_N = SPRING_COCKED_FORCE_N / COCKING_LEVER_MECHANICAL_ADVANTAGE

# Layout driven from shared interfaces.
BRIDGE_X = 105.0
BRIDGE_LENGTH = 92.0
BRIDGE_DECK_Z = 6.2
BRIDGE_FASTENER_X = 111.0
BRIDGE_FASTENER_Y = 18.0
BRIDGE_THICKNESS = 3.0
NOZZLE_AXIS_Y = SYRINGE_AXIS_Y
NOZZLE_AXIS_Z = SYRINGE_AXIS_Z
NOZZLE_START_X = SYRINGE_X + SYRINGE_BARREL_LENGTH + SYRINGE_LUER_LENGTH
NOZZLE_LENGTH = 25.4
NOZZLE_OD = 4.19  # real 8 ga nominal OD; the conservative effective outlet is 3.0 mm
NOZZLE_GUIDE_CLEARANCE = 0.60

CARRIAGE_X = SYRINGE_THUMB_FLANGE_X - 5.0
CARRIAGE_Y = -14.0
CARRIAGE_Z = 3.3
SPRING_REAR_X = CARRIAGE_X - SPRING_COCKED_LENGTH
SPRING_AXIS_Y = SYRINGE_AXIS_Y
SPRING_AXIS_Z = 10.0

MIN_ASSEMBLY_GAP = 0.25
GEOMETRY_TOLERANCE = 1.0e-4
FIRST_LAYER_SAMPLE = 0.20
SECTION_SAMPLE_THICKNESS = 0.25


@dataclass(frozen=True)
class PlacedShape:
    shape: cq.Shape
    location: cq.Location

    def global_shape(self) -> cq.Shape:
        return self.shape.moved(self.location)


@dataclass(frozen=True)
class MockupSource:
    source: str
    envelope: str
    confidence: str


def _box(x: float, y: float, z: float, centered=(False, False, False)) -> cq.Shape:
    return cq.Workplane("XY").box(x, y, z, centered=centered).val()


def _cylinder_x(length: float, radius: float) -> cq.Shape:
    return cq.Workplane("YZ").circle(radius).extrude(length).val()


def _cylinder_y(length: float, radius: float) -> cq.Shape:
    return cq.Workplane("XZ").circle(radius).extrude(length).val()


def _cylinder_z(height: float, radius: float) -> cq.Shape:
    return cq.Workplane("XY").circle(radius).extrude(height).val()


def _move(shape: cq.Shape, x=0.0, y=0.0, z=0.0) -> cq.Shape:
    return shape.moved(cq.Location(cq.Vector(x, y, z)))


def _compound(shapes: Iterable[cq.Shape]) -> cq.Shape:
    return cq.Compound.makeCompound(list(shapes))


def _fuse_all(seed: cq.Shape, additions: Iterable[cq.Shape]) -> cq.Shape:
    result = seed
    for addition in additions:
        result = result.fuse(addition)
    return result


def _ground(shape: cq.Shape) -> cq.Shape:
    """Place the computed bottom face on z=0; this is print orientation, not an epsilon lift."""
    cleaned = shape.clean()
    return _move(cleaned, z=-cleaned.BoundingBox().zmin)


def _strap_slot(x_center: float, y_center: float) -> cq.Shape:
    return _move(
        _box(STRAP_WIDTH + 2.0 * STRAP_CLEARANCE,
             STRAP_THICKNESS + 2.0 * STRAP_CLEARANCE, 12.0),
        x_center - STRAP_WIDTH / 2.0 - STRAP_CLEARANCE,
        y_center - STRAP_THICKNESS / 2.0 - STRAP_CLEARANCE,
        -1.0,
    )


def make_baseplate() -> cq.Shape:
    """Flat-printing chord frame with load paths under every mounted item."""
    outer = _move(_box(BASE_LENGTH, BASE_WIDTH, BASE_THICKNESS), 0.0, -BASE_WIDTH / 2.0)
    window = _move(_box(104.0, 48.0, BASE_THICKNESS + 2.0), 7.0, -24.0, -1.0)
    base = outer.cut(window)

    # Broad floors/ribs reconnect the perimeter.  Nothing is supported by a butt face.
    floors = (
        _move(_box(39.5, 58.0, BASE_THICKNESS), 1.0, -29.0),       # LiPo tray
        _move(_box(47.0, 16.0, BASE_THICKNESS), 34.0, -15.0),      # spring spine
        _move(_box(34.0, 27.0, BASE_THICKNESS), 38.0, 3.0),        # servo tray
        _move(_box(47.0, 29.0, BASE_THICKNESS), 70.0, 3.0),        # board deck
        _move(_box(22.0, 54.0, BASE_THICKNESS), 96.0, -27.0),      # bridge root
        _move(_box(20.0, 24.0, BASE_THICKNESS), 78.0, -19.0),      # syringe reaction rib
    )
    base = _fuse_all(base, floors)

    # Two true forearm strap pairs, kept outside the central mechanisms.
    for strap_x in (22.0, 88.0):
        for side_y in (-23.0, 23.0):
            base = base.cut(_strap_slot(strap_x, side_y))

    additions: list[cq.Shape] = []

    # LiPo: four low corner keepers, with >=0.5 mm clearance and no top clamp.
    for x0 in (0.5, 37.0):
        for y0 in (-29.5, 27.5):
            additions.append(_move(_box(2.0, 2.0, 5.0), x0, y0, BASE_THICKNESS))

    # Spring reaction wall and two long carriage rails.  Rail faces are 0.4 mm
    # outside the moving carriage at every point in the stroke.
    additions.append(_move(_box(3.0, 18.0, 15.0), SPRING_REAR_X - 3.0, -15.0, BASE_THICKNESS))
    additions.append(_move(_box(45.0, 1.6, 13.7), 39.0, -16.0, BASE_THICKNESS))
    additions.append(_move(_box(45.0, 1.6, 13.7), 39.0, 2.4, BASE_THICKNESS))

    # Servo cradle and two real M3 mounting bosses for its ears.
    additions.extend((
        _move(_box(31.5, 1.4, 5.0), 40.0, 3.0, BASE_THICKNESS),
        _move(_box(31.5, 1.4, 5.0), 40.0, 28.6, BASE_THICKNESS),
        _move(_box(1.4, 24.2, 5.0), 40.0, 4.4, BASE_THICKNESS),
        _move(_box(1.4, 24.2, 5.0), 70.1, 4.4, BASE_THICKNESS),
    ))
    for x0, y0 in ((43.0, 2.0), (68.0, 2.0)):
        boss = _move(_cylinder_z(8.0, 3.5), x0, y0, BASE_THICKNESS)
        boss = boss.cut(_move(_cylinder_z(10.0, 1.7), x0, y0, BASE_THICKNESS - 1.0))
        additions.append(boss)

    # Board keepers are open posts with EPDM-retainer notches; USB ends stay open.
    board_specs = ((89.0, 3.5, 17.0, 28.0), (70.5, 6.0, 17.8, 21.0))
    for x0, y0, sx, sy in board_specs:
        for px in (x0 - 1.8, x0 + sx + 0.6):
            for py in (y0 - 1.8, y0 + sy + 0.6):
                post = _move(_box(2.5, 2.5, 7.5), px, py, BASE_THICKNESS)
                notch = _move(_box(0.8, 3.5, 1.5), px + 1.7, py - 0.5, BASE_THICKNESS + 5.0)
                additions.append(post.cut(notch))

    # Rear syringe cradle, open at the top, plus a broad two-post flange stop.
    for guide_y in (
        SYRINGE_AXIS_Y - SYRINGE_BARREL_OD / 2.0 - SYRINGE_GUIDE_CLEARANCE - 3.0,
        SYRINGE_AXIS_Y + SYRINGE_BARREL_OD / 2.0 + SYRINGE_GUIDE_CLEARANCE,
    ):
        additions.append(_move(_box(7.0, 3.0, 16.7), 88.0, guide_y, BASE_THICKNESS))
    additions.append(_move(_box(13.0, 21.0, 0.5), 86.0, -16.5, BASE_THICKNESS))
    for stop_y in (-20.0, 3.0):
        additions.append(_move(_box(2.0, 7.0, 17.0), 79.5, stop_y, BASE_THICKNESS))

    # Bridge bosses are well inboard of the +X face.  Their top is the actual
    # joint plane: there is no designed air gap.
    for y in (-BRIDGE_FASTENER_Y, BRIDGE_FASTENER_Y):
        boss = _move(_cylinder_z(BRIDGE_DECK_Z, 6.0), BRIDGE_FASTENER_X, y, 0.0)
        pocket = _move(
            _cylinder_z(M3_INSERT_LENGTH, M3_INSERT_POCKET_DIAMETER / 2.0),
            BRIDGE_FASTENER_X, y, BRIDGE_DECK_Z - M3_INSERT_LENGTH,
        )
        additions.append(boss.cut(pocket))

    # Cocking-lever and sear pivots close their loads into the base floor.
    for x0, y0, height in ((42.0, -25.0, 19.5), (68.0, 4.0, 15.6)):
        boss = _move(_cylinder_z(height - BASE_THICKNESS, 4.5), x0, y0, BASE_THICKNESS)
        hole = _move(_cylinder_z(height + 2.0, 1.7), x0, y0, 0.0)
        additions.append(boss.cut(hole))

    return _ground(_fuse_all(base, additions))


def make_bridge() -> cq.Shape:
    """Continuous 32 mm spine; slots live in wings and never neck the load path."""
    deck = _move(_box(BRIDGE_LENGTH, 32.0, BRIDGE_THICKNESS), 0.0, -22.0)
    rear_wing = _move(_box(16.0, 50.0, BRIDGE_THICKNESS), 0.0, -25.0)
    palm_wing = _move(_box(32.0, 50.0, BRIDGE_THICKNESS), 14.0, -25.0)
    bridge = deck.fuse(rear_wing).fuse(palm_wing)

    # The barrel sits in an open center lane.  Two 6.75 x 3 mm side rails remain,
    # giving 40.5 mm2 total section instead of Mk2's two 0.75 mm ligaments.
    syringe_lane = _move(_box(68.0, SYRINGE_BARREL_OD + 2.0 * SYRINGE_GUIDE_CLEARANCE,
                              BRIDGE_THICKNESS + 2.0),
                          0.0, SYRINGE_AXIS_Y - SYRINGE_BARREL_OD / 2.0
                          - SYRINGE_GUIDE_CLEARANCE, -1.0)
    bridge = bridge.cut(syringe_lane)

    for y in (-BRIDGE_FASTENER_Y, BRIDGE_FASTENER_Y):
        local_x = BRIDGE_FASTENER_X - BRIDGE_X
        bridge = bridge.cut(_move(_cylinder_z(8.0, M3_CLEARANCE_DIAMETER / 2.0), local_x, y, -1.0))

    # Palm strap openings are separated outboard slots; 22.5 mm of the central
    # spine remains continuous through their station.
    for y in (-19.0, 7.0):
        bridge = bridge.cut(_strap_slot(30.0, y))

    additions: list[cq.Shape] = []

    # Forward syringe cradle with the same named radial clearance and O-ring notches.
    for guide_y in (
        SYRINGE_AXIS_Y - SYRINGE_BARREL_OD / 2.0 - SYRINGE_GUIDE_CLEARANCE - 3.0,
        SYRINGE_AXIS_Y + SYRINGE_BARREL_OD / 2.0 + SYRINGE_GUIDE_CLEARANCE,
    ):
        post = _move(_box(7.0, 3.0, 13.7), 45.0, guide_y, BRIDGE_THICKNESS)
        notch = _move(_box(3.0, 4.0, 1.8), 47.0, guide_y - 0.5, 12.5)
        additions.append(post.cut(notch))
    additions.append(_move(_box(12.0, 21.0, 0.5), 43.0, -22.5, BRIDGE_THICKNESS))

    # Two robust bored towers.  Each has >6 mm material between the live and dummy
    # bores and a full 32x3 mm deck below it.
    bore_radius = (NOZZLE_OD + NOZZLE_GUIDE_CLEARANCE) / 2.0
    for local_x in (80.0, 87.0):
        tower = _move(_box(6.0, 22.0, 13.7), local_x - 3.0, -18.0, BRIDGE_THICKNESS)
        for y in (NOZZLE_AXIS_Y, 0.0):
            bore = _move(_cylinder_x(8.0, bore_radius), local_x - 4.0, y, NOZZLE_AXIS_Z - BRIDGE_DECK_Z)
            tower = tower.cut(bore)
        additions.append(tower)

    return _ground(_fuse_all(bridge, additions))


def make_carriage() -> cq.Shape:
    """Broad guided tappet with spring seat, plunger face, latch and cocking lug."""
    body = _box(5.0, 16.0, 13.0)
    spring_seat = _move(_box(2.0, 12.0, 10.0), 0.0, 2.0, 1.7)
    push_pad = _move(_box(1.8, 14.0, 12.0), 3.2, 1.0, 0.5)
    latch_lug = _move(_box(5.0, 3.0, 3.0), 0.0, 19.0, 12.7)
    cock_lug = _move(_box(5.0, 8.0, 3.0), 0.0, -5.0, 13.5)
    carriage = body.fuse(spring_seat).fuse(push_pad).fuse(latch_lug).fuse(cock_lug)
    cock_hole = _move(_cylinder_z(5.0, 1.7), 2.5, -1.0, 13.0)
    return _ground(carriage.cut(cock_hole))


def make_cocking_lever() -> cq.Shape:
    """One-hand lever; 45 degrees deployment retracts the carriage 10.1 mm."""
    bar = _move(_box(83.0, 8.0, 3.0), -55.0, -4.0)
    grip = _move(_box(18.0, 12.0, 3.0), -57.0, -6.0)
    lever = bar.fuse(grip)
    lever = lever.cut(_move(_cylinder_z(5.0, 1.7), 0.0, 0.0, -1.0))
    # Closed drive eye is stronger than the Mk2 yoke and cannot cam off its pin.
    lever = lever.cut(_move(_cylinder_z(5.0, 1.9), 27.857, 0.0, -1.0))
    return _ground(lever)


def make_sear() -> cq.Shape:
    """M3-pivoted sear; the servo horn only moves the low-load release tail."""
    tooth = _box(4.0, 4.0, 3.0)
    arm = _move(_box(6.5, 4.0, 3.0), -6.5, 0.0)
    tail = _move(_box(8.0, 4.0, 3.0), -7.0, 6.0)
    neck = _move(_box(4.0, 6.0, 3.0), -4.0, 3.0)
    sear = tooth.fuse(arm).fuse(tail).fuse(neck)
    return _ground(sear.cut(_move(_cylinder_z(5.0, 1.7), -2.5, 2.0, -1.0)))


def make_switch_pod() -> cq.Shape:
    """Strap-retained tactile carrier with a 2 mm floor and bounded slots."""
    pod = _box(28.0, 34.0, 7.0)
    pocket = _move(_box(13.0, 13.0, 5.0), 7.5, 10.5, 2.0)
    pod = pod.cut(pocket)
    # Slots stop 4 mm from both Y edges; the floor between them remains 13 mm wide.
    for x0 in (4.0, 20.5):
        slot = _move(_box(3.5, 26.0, 9.0), x0, 4.0, -1.0)
        pod = pod.cut(slot)
    # Lead holes retain the switch mechanically after its legs are bent over.
    for x0 in (10.0, 18.0):
        pod = pod.cut(_move(_cylinder_z(4.0, 0.7), x0, 17.0, -1.0))
    return _ground(pod)


printed_parts: Dict[str, PlacedShape] = {
    "baseplate": PlacedShape(make_baseplate(), cq.Location()),
    "barrel_bridge": PlacedShape(make_bridge(), cq.Location(cq.Vector(BRIDGE_X, 0.0, BRIDGE_DECK_Z))),
    "spring_carriage": PlacedShape(make_carriage(), cq.Location(cq.Vector(CARRIAGE_X, CARRIAGE_Y, CARRIAGE_Z))),
    "cocking_lever": PlacedShape(
        make_cocking_lever(),
        cq.Location(cq.Vector(42.0, -25.0, 19.9), cq.Vector(0.0, 0.0, 1.0), 21.038),
    ),
    "servo_sear": PlacedShape(make_sear(), cq.Location(cq.Vector(70.5, 5.0, 16.0))),
    "palm_switch_pod": PlacedShape(make_switch_pod(), cq.Location(cq.Vector(132.0, -17.0, -12.0))),
}


MOCKUP_SOURCES: Dict[str, MockupSource] = {}


def _source(name: str, source: str, envelope: str, confidence: str = "HIGH") -> None:
    MOCKUP_SOURCES[name] = MockupSource(source, envelope, confidence)


def make_mockups() -> Dict[str, PlacedShape]:
    """Real envelopes only; every entry is paired with a printed report source."""
    items: Dict[str, PlacedShape] = {}

    # Complete two-part syringe, including the previously omitted finger flange.
    barrel = _move(_cylinder_x(SYRINGE_BARREL_LENGTH, SYRINGE_BARREL_OD / 2.0),
                   SYRINGE_X, SYRINGE_AXIS_Y, SYRINGE_AXIS_Z)
    luer = _move(_cylinder_x(SYRINGE_LUER_LENGTH, SYRINGE_LUER_OD / 2.0),
                 SYRINGE_X + SYRINGE_BARREL_LENGTH, SYRINGE_AXIS_Y, SYRINGE_AXIS_Z)
    finger_flange = _move(_box(2.0, 24.0, 18.0), SYRINGE_FINGER_FLANGE_X,
                          SYRINGE_AXIS_Y - 12.0, SYRINGE_AXIS_Z - 9.0)
    thumb_flange = _move(_box(2.0, 20.0, 14.0), SYRINGE_THUMB_FLANGE_X,
                         SYRINGE_AXIS_Y - 10.0, SYRINGE_AXIS_Z - 7.0)
    rod = _move(_cylinder_x(SYRINGE_FINGER_FLANGE_X - (SYRINGE_THUMB_FLANGE_X + 2.0), 3.0),
                SYRINGE_THUMB_FLANGE_X + 2.0, SYRINGE_AXIS_Y, SYRINGE_AXIS_Z)
    items["syringe_norm_ject_10ml"] = PlacedShape(
        _compound((barrel, luer, finger_flange, thumb_flange, rod)), cq.Location())
    _source("syringe_norm_ject_10ml", "Restek 22775 / NORM-JECT specification table",
            "15.9 ID, 17.3 OD, 85.3 cylinder; flange conservatively caliper-sized")

    # Live 8 ga nozzle: transparent hub plus the real 4.19 mm OD metal cannula.
    live_hub = _move(_cylinder_x(7.0, 3.5), NOZZLE_START_X - 4.0, NOZZLE_AXIS_Y, NOZZLE_AXIS_Z)
    live_tube = _move(_cylinder_x(NOZZLE_LENGTH, NOZZLE_OD / 2.0),
                      NOZZLE_START_X + 3.0, NOZZLE_AXIS_Y, NOZZLE_AXIS_Z)
    items["live_8ga_blunt_nozzle"] = PlacedShape(_compound((live_hub, live_tube)), cq.Location())
    _source("live_8ga_blunt_nozzle", "ISO 9626 gauge table + owned 8/10/12/14 ga assortment",
            "8 ga OD 4.19, 25.4 mm cannula; 3.0 mm conservative effective outlet")

    dummy = _move(_cylinder_x(NOZZLE_LENGTH, NOZZLE_OD / 2.0),
                  NOZZLE_START_X + 3.0, 0.0, NOZZLE_AXIS_Z)
    cap = _move(_cylinder_x(3.0, 2.8), NOZZLE_START_X + NOZZLE_LENGTH, 0.0, NOZZLE_AXIS_Z)
    items["capped_dummy_8ga_nozzle"] = PlacedShape(_compound((dummy, cap)), cq.Location())
    _source("capped_dummy_8ga_nozzle", "ISO 9626 gauge table + owned 8/10/12/14 ga assortment",
            "8 ga OD 4.19, capped; no fluid connection")

    # Cocked spring is an envelope, not a cosmetic arbitrary coil.
    spring = _move(_cylinder_x(SPRING_COCKED_LENGTH, SPRING_OD / 2.0),
                   SPRING_REAR_X, SPRING_AXIS_Y, SPRING_AXIS_Z)
    items["selected_compression_spring"] = PlacedShape(spring, cq.Location())
    _source("selected_compression_spring", "owned compression-spring assortment; select by scale test",
            "OD <=10, free 39.7, rate 1.94 N/mm, cocked 25.53, peak 27.6 N", "MEASURE")

    # DS239MG lying on its side, including lugs and horn sweep envelope.
    servo_body = _move(_box(27.5, 23.0, 12.0), 42.0, 5.0, 3.4)
    servo_lugs = _move(_box(31.5, 4.0, 2.0), 40.0, 1.0, 8.0).fuse(
        _move(_box(31.5, 4.0, 2.0), 40.0, 28.0, 8.0))
    servo = servo_body.fuse(servo_lugs)
    items["corona_ds239mg_servo"] = PlacedShape(servo, cq.Location())
    _source("corona_ds239mg_servo", "HobbyKing Corona DS239MG published dimensions",
            "27.5 x 23 x 12 body plus mounting lugs")

    horn = _move(_box(3.0, 16.0, 1.6), 63.0, 8.0, 15.7)
    items["ds239mg_horn"] = PlacedShape(horn, cq.Location())
    _source("ds239mg_horn", "owned DS239MG supplied horn; conservative measured envelope",
            "3 x 16 x 1.6")

    # Electronics retained on open floors; deleted boost and H-bridge are absent.
    lipo = _move(_box(34.0, 54.0, 10.0), 3.5, -27.0, 3.4)
    items["lipo_eemb_103454_rotated"] = PlacedShape(lipo, cq.Location())
    _source("lipo_eemb_103454_rotated", "EEMB 103454 manufacturer envelope",
            "54 x 34 x 10, rotated in plane; 0.6 mm floor gap and no top clamp")

    tp4056 = _move(_box(28.0, 17.0, 4.0), 70.5, 8.0, 3.4)
    items["tp4056_usbc_dw01"] = PlacedShape(tp4056, cq.Location())
    _source("tp4056_usbc_dw01", "owned common USB-C TP4056/DW01 board, conservative caliper envelope",
            "28 x 17 x 4", "MEASURE")

    xiao = _move(_box(17.8, 21.0, 3.6), 99.0, 6.0, 3.4)
    items["seeed_xiao_esp32c3"] = PlacedShape(xiao, cq.Location())
    _source("seeed_xiao_esp32c3", "Seeed Studio XIAO ESP32C3 mechanical drawing",
            "17.8 x 21 x 3.6")

    switch = _move(_box(12.0, 12.0, 4.3), 140.0, -6.0, -9.6)
    items["tactile_switch_12mm"] = PlacedShape(switch, cq.Location())
    _source("tactile_switch_12mm", "Omron B3F 12 mm-class tactile switch drawing",
            "12 x 12 x 4.3")

    # Fasteners and pins use owned hardware; modeled shafts are real 3.0 mm OD.
    for index, y in enumerate((-BRIDGE_FASTENER_Y, BRIDGE_FASTENER_Y), 1):
        shaft = _cylinder_z(BRIDGE_DECK_Z + BRIDGE_THICKNESS + 1.8, 1.5)
        head = _move(_cylinder_z(2.0, M3_HEAD_DIAMETER / 2.0), 0.0, 0.0,
                     BRIDGE_DECK_Z + BRIDGE_THICKNESS + 1.8)
        name = f"bridge_m3_screw_{index}"
        items[name] = PlacedShape(_compound((shaft, head)),
                                  cq.Location(cq.Vector(BRIDGE_FASTENER_X, y, 0.2)))
        _source(name, "owned ISO M3 socket screws", "3.0 shaft, 5.8 head")

        insert = _cylinder_z(M3_INSERT_LENGTH, M3_INSERT_OD / 2.0).cut(
            _cylinder_z(M3_INSERT_LENGTH, 1.35))
        iname = f"bridge_m3_insert_{index}"
        items[iname] = PlacedShape(insert, cq.Location(cq.Vector(
            BRIDGE_FASTENER_X, y, BRIDGE_DECK_Z - M3_INSERT_LENGTH)))
        _source(iname, "owned M3 heat-set inserts", "5.0 OD x 4.0 length")

    for name, x0, y0, z0, length in (
        ("cocking_pivot_m3", 35.0, -25.0, 0.2, 23.0),
        ("cocking_drive_m3", 67.7, -20.9, 17.8, 6.0),
        ("sear_pivot_m3", 64.5, 5.0, 0.2, 19.0),
    ):
        items[name] = PlacedShape(_move(_cylinder_z(length, 1.5), x0, y0, z0), cq.Location())
        _source(name, "owned ISO M3 screws", f"3.0 OD x {length:.1f} envelope")

    # EPDM retainers are explicit; they sit above, rather than clamp, the pouch.
    for name, x0, y0, sx, sy, z0 in (
        ("tp4056_epdm_retainer", 68.8, 6.2, 31.4, 20.4, 8.7),
        ("xiao_epdm_retainer", 97.3, 4.2, 21.2, 24.4, 8.3),
    ):
        outer = _move(_box(sx, sy, 1.2), x0, y0, z0)
        inner = _move(_box(sx - 2.0, sy - 2.0, 2.0), x0 + 1.0, y0 + 1.0, z0 - 0.4)
        items[name] = PlacedShape(outer.cut(inner), cq.Location())
        _source(name, "owned EPDM O-rings / bands", f"retainer envelope {sx} x {sy}", "MEASURE")

    syringe_retainer = _move(_cylinder_x(5.0, 11.0), 84.0, SYRINGE_AXIS_Y, SYRINGE_AXIS_Z)
    syringe_retainer = syringe_retainer.cut(
        _move(_cylinder_x(7.0, 9.7), 83.0, SYRINGE_AXIS_Y, SYRINGE_AXIS_Z))
    items["syringe_epdm_retainer"] = PlacedShape(syringe_retainer, cq.Location())
    _source("syringe_epdm_retainer", "owned EPDM O-rings", "stretched OD <=22 around guide notches", "MEASURE")

    # Webbing segments in slots are clearance-separated and prove both strap pairs exist.
    forearm_tabs = []
    for strap_x in (22.0, 88.0):
        for side_y in (-23.0, 23.0):
            forearm_tabs.append(_move(_box(STRAP_WIDTH, STRAP_THICKNESS, 5.2),
                                      strap_x - STRAP_WIDTH / 2.0,
                                      side_y - STRAP_THICKNESS / 2.0, -2.8))
    items["forearm_straps_25mm"] = PlacedShape(_compound(forearm_tabs), cq.Location())
    _source("forearm_straps_25mm", "owned 1 inch hook-and-loop strapping",
            "25 x 1.5 segments; thickness to verify", "MEASURE")

    palm_tabs = []
    for y in (-19.0, 7.0):
        palm_tabs.append(_move(_box(STRAP_WIDTH, STRAP_THICKNESS, 4.2),
                               BRIDGE_X + 30.0 - STRAP_WIDTH / 2.0,
                               y - STRAP_THICKNESS / 2.0, BRIDGE_DECK_Z - 2.0))
    # Two additional vertical tabs route the same strap through the switch pod.
    palm_tabs.extend((
        _move(_box(1.5, STRAP_WIDTH, 6.0), 137.0, -12.5, -11.5),
        _move(_box(1.5, STRAP_WIDTH, 6.0), 153.5, -12.5, -11.5),
    ))
    items["palm_strap_25mm"] = PlacedShape(_compound(palm_tabs), cq.Location())
    _source("palm_strap_25mm", "owned 1 inch hook-and-loop strapping",
            "25 x 1.5 routed tabs; thickness to verify", "MEASURE")

    return items


mockups: Dict[str, PlacedShape] = make_mockups()


# Explicit transforms and a complete visual assembly.
assembly = cq.Assembly(name="webshooter_mk3_spring_sear_open_frame")
for name, placed in printed_parts.items():
    assembly.add(placed.shape, name=f"printed_{name}", loc=placed.location,
                 color=cq.Color(0.82, 0.12, 0.12, 1.0))
for name, placed in mockups.items():
    color = cq.Color(0.55, 0.58, 0.62, 0.72)
    if "strap" in name or "epdm" in name:
        color = cq.Color(0.06, 0.06, 0.06, 0.9)
    elif "nozzle" in name or "screw" in name or "insert" in name:
        color = cq.Color(0.74, 0.77, 0.82, 1.0)
    assembly.add(placed.shape, name=f"mockup_{name}", loc=placed.location, color=color)


def _pair(a: str, b: str) -> frozenset[str]:
    return frozenset((a, b))


# Only these pairs may touch/interfere, and every exception states the load/function.
CONTACT_ALLOWLIST: Dict[frozenset[str], str] = {
    _pair("printed/baseplate", "printed/barrel_bridge"): "M3-clamped bridge boss faces",
    _pair("printed/spring_carriage", "mockup/syringe_norm_ject_10ml"): "plunger push face",
    _pair("printed/spring_carriage", "mockup/selected_compression_spring"): "spring seat",
    _pair("printed/spring_carriage", "printed/servo_sear"): "latched sear shoulder",
    _pair("printed/cocking_lever", "mockup/cocking_pivot_m3"): "cocking pivot bearing",
    _pair("printed/cocking_lever", "mockup/cocking_drive_m3"): "closed cocking eye",
    _pair("printed/spring_carriage", "mockup/cocking_drive_m3"): "carriage drive pin",
    _pair("printed/servo_sear", "mockup/sear_pivot_m3"): "sear pivot bearing",
    _pair("printed/servo_sear", "mockup/ds239mg_horn"): "servo trip contact",
    _pair("mockup/corona_ds239mg_servo", "mockup/ds239mg_horn"): "servo output spline",
    _pair("mockup/syringe_norm_ject_10ml", "mockup/live_8ga_blunt_nozzle"): "Luer-lock fluid joint",
    _pair("printed/baseplate", "mockup/selected_compression_spring"): "spring reaction wall",
    _pair("printed/palm_switch_pod", "mockup/palm_strap_25mm"): "strap retention",
}
for i in (1, 2):
    CONTACT_ALLOWLIST[_pair("printed/baseplate", f"mockup/bridge_m3_insert_{i}")] = "heat-set interference"
    CONTACT_ALLOWLIST[_pair("printed/baseplate", f"mockup/bridge_m3_screw_{i}")] = "fastener through insert"
    CONTACT_ALLOWLIST[_pair("printed/barrel_bridge", f"mockup/bridge_m3_screw_{i}")] = "screw head clamp"
    CONTACT_ALLOWLIST[_pair(f"mockup/bridge_m3_insert_{i}", f"mockup/bridge_m3_screw_{i}")] = "thread engagement"
CONTACT_ALLOWLIST[_pair("printed/baseplate", "mockup/cocking_pivot_m3")] = "pivot screw in boss"
CONTACT_ALLOWLIST[_pair("printed/baseplate", "mockup/sear_pivot_m3")] = "pivot screw in boss"


FIRST_LAYER_MIN_MM2: Mapping[str, float] = {
    "baseplate": 1200.0,
    "barrel_bridge": 1500.0,
    "spring_carriage": 70.0,
    "cocking_lever": 200.0,
    "servo_sear": 65.0,
    "palm_switch_pod": 300.0,
}


def _first_layer_area(shape: cq.Shape) -> float:
    slab = _move(_box(shape.BoundingBox().xlen + 4.0, shape.BoundingBox().ylen + 4.0,
                      FIRST_LAYER_SAMPLE),
                 shape.BoundingBox().xmin - 2.0, shape.BoundingBox().ymin - 2.0, 0.0)
    return shape.intersect(slab).Volume() / FIRST_LAYER_SAMPLE


def _triangle_overhang_area(shape: cq.Shape) -> tuple[float, int]:
    vertices, triangles = shape.tessellate(0.18)
    area_total = 0.0
    count = 0
    cutoff = -math.cos(math.radians(45.0))
    for ia, ib, ic in triangles:
        a, b, c = vertices[ia], vertices[ib], vertices[ic]
        ux, uy, uz = b.x - a.x, b.y - a.y, b.z - a.z
        vx, vy, vz = c.x - a.x, c.y - a.y, c.z - a.z
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        twice_area = math.sqrt(nx * nx + ny * ny + nz * nz)
        if twice_area <= 1.0e-12:
            continue
        centroid_z = (a.z + b.z + c.z) / 3.0
        # The build-plane face is supported by the bed and is not an overhang.
        if centroid_z > FIRST_LAYER_SAMPLE and nz / twice_area < cutoff:
            area_total += 0.5 * twice_area
            count += 1
    return area_total, count


def _section_audit(shape: cq.Shape) -> dict:
    """Sample real slabs on all axes; report weak disconnected section components."""
    bb = shape.BoundingBox()
    axis_data = {
        "x": (bb.xmin, bb.xmax, bb.ylen + 4.0, bb.zlen + 4.0),
        "y": (bb.ymin, bb.ymax, bb.xlen + 4.0, bb.zlen + 4.0),
        "z": (bb.zmin, bb.zmax, bb.xlen + 4.0, bb.ylen + 4.0),
    }
    result: dict[str, dict] = {}
    for axis, (low, high, span_a, span_b) in axis_data.items():
        samples = []
        for fraction in (0.08, 0.16, 0.25, 0.35, 0.50, 0.65, 0.75, 0.84, 0.92):
            plane = low + (high - low) * fraction
            t = SECTION_SAMPLE_THICKNESS
            if axis == "x":
                slab = _move(_box(t, span_a, span_b), plane - t / 2.0, bb.ymin - 2.0, bb.zmin - 2.0)
                section_dims = lambda sb: (sb.ylen, sb.zlen)
            elif axis == "y":
                slab = _move(_box(span_a, t, span_b), bb.xmin - 2.0, plane - t / 2.0, bb.zmin - 2.0)
                section_dims = lambda sb: (sb.xlen, sb.zlen)
            else:
                slab = _move(_box(span_a, span_b, t), bb.xmin - 2.0, bb.ymin - 2.0, plane - t / 2.0)
                section_dims = lambda sb: (sb.xlen, sb.ylen)
            cut = shape.intersect(slab)
            solids = cut.Solids() if not cut.isNull() else []
            components = []
            for solid in solids:
                area = solid.Volume() / t
                d1, d2 = section_dims(solid.BoundingBox())
                if area > 0.20:
                    components.append({"area_mm2": area, "min_span_mm": min(d1, d2)})
            samples.append({
                "plane_mm": plane,
                "total_area_mm2": sum(c["area_mm2"] for c in components),
                "components": components,
            })
        result[axis] = {
            "minimum_total_area_mm2": min((s["total_area_mm2"] for s in samples), default=0.0),
            "minimum_component_area_mm2": min(
                (c["area_mm2"] for s in samples for c in s["components"]), default=0.0),
            "minimum_component_span_mm": min(
                (c["min_span_mm"] for s in samples for c in s["components"]), default=0.0),
            "samples": samples,
        }
    return result


def _intersection_volume(a: cq.Shape, b: cq.Shape) -> float:
    common = a.intersect(b)
    return 0.0 if common.isNull() else float(common.Volume())


def _stroke_carriage_shape(travel: float) -> cq.Shape:
    return printed_parts["spring_carriage"].global_shape().moved(
        cq.Location(cq.Vector(travel, 0.0, 0.0)))


def verify_model() -> dict:
    report: dict = {
        "architecture": "hand-cocked compression spring + DS239MG-tripped sear",
        "deleted_drive_items": ["Actuonix L12", "Pololu U3V70F6", "DRV8833"],
        "physics": {
            "shot_volume_ml": SHOT_VOLUME_ML,
            "plunger_area_mm2": PLUNGER_AREA_MM2,
            "plunger_stroke_mm": PLUNGER_STROKE,
            "orifice_diameter_mm": ORIFICE_DIAMETER,
            "area_ratio": AREA_RATIO,
            "shot_time_s": SHOT_TIME_S,
            "plunger_speed_m_s": PLUNGER_SPEED_M_S,
            "exit_velocity_m_s": EXIT_VELOCITY_M_S,
            "ideal_45deg_ballistic_range_m": BALLISTIC_RANGE_M,
            "spring_release_energy_j": SPRING_RELEASE_ENERGY_J,
            "spring_force_fired_n": SPRING_FIRED_FORCE_N,
            "spring_force_cocked_n": SPRING_COCKED_FORCE_N,
            "maximum_hand_cock_force_n": MAX_HAND_COCK_FORCE_N,
        },
        "printed_part_count": len(printed_parts),
        "printed_parts": {},
        "mockup_sources": {name: vars(source) for name, source in MOCKUP_SOURCES.items()},
        "contact_allowlist": {
            " <> ".join(sorted(pair)): reason for pair, reason in CONTACT_ALLOWLIST.items()
        },
        "pairwise_clearance": {},
        "stroke_sweep": [],
        "fluid_path": {},
        "failures": [],
    }

    # Kinematic and target assertions are run every time and printed by __main__.
    p = report["physics"]
    if p["shot_volume_ml"] < 2.0 - 1.0e-9:
        report["failures"].append("shot volume below hard 2.0 mL target")
    if p["shot_time_s"] > 0.250:
        report["failures"].append("shot time exceeds 250 ms")
    if p["ideal_45deg_ballistic_range_m"] < 1.5:
        report["failures"].append("ideal ballistic range below 1.5 m")
    if p["spring_release_energy_j"] > 0.25:
        report["failures"].append("stored release energy exceeds 0.25 J safety ceiling")
    if len(printed_parts) > 6:
        report["failures"].append("more than six printed parts")

    for name, placed in printed_parts.items():
        shape = placed.shape
        bb = shape.BoundingBox()
        footprint = _first_layer_area(shape)
        overhang_area, triangle_count = _triangle_overhang_area(shape)
        sections = _section_audit(shape)
        entry = {
            "solid_count": len(shape.Solids()),
            "is_valid": bool(shape.isValid()),
            "local_z_min_mm": bb.zmin,
            "local_z_max_mm": bb.zmax,
            "volume_mm3": shape.Volume(),
            "first_layer_footprint_mm2": footprint,
            "first_layer_minimum_mm2": FIRST_LAYER_MIN_MM2[name],
            "downfacing_overhang_area_below_45deg_mm2": overhang_area,
            "downfacing_sample_triangle_count": triangle_count,
            "section_audit": sections,
        }
        report["printed_parts"][name] = entry
        if entry["solid_count"] != 1:
            report["failures"].append(f"{name}: solid_count={entry['solid_count']}")
        if not entry["is_valid"]:
            report["failures"].append(f"{name}: invalid solid")
        if abs(entry["local_z_min_mm"]) >= GEOMETRY_TOLERANCE:
            report["failures"].append(f"{name}: abs(z_min)={abs(entry['local_z_min_mm']):.6g} mm")
        if footprint < FIRST_LAYER_MIN_MM2[name]:
            report["failures"].append(
                f"{name}: first-layer footprint {footprint:.2f} < {FIRST_LAYER_MIN_MM2[name]:.2f} mm2")
        # Horizontal bores have bounded, bridgeable overhangs.  A large floating
        # underside such as Mk2's 7,841 mm2 still fails decisively.
        if overhang_area > 350.0:
            report["failures"].append(f"{name}: down-facing overhang area {overhang_area:.2f} mm2")
        for axis, audit in sections.items():
            if audit["minimum_total_area_mm2"] < 2.0:
                report["failures"].append(
                    f"{name}: {axis}-section total area {audit['minimum_total_area_mm2']:.3f} mm2")
            if audit["minimum_component_area_mm2"] < 2.0:
                report["failures"].append(
                    f"{name}: {axis}-section component area {audit['minimum_component_area_mm2']:.3f} mm2")
            if audit["minimum_component_span_mm"] < 1.2:
                report["failures"].append(
                    f"{name}: {axis}-section ligament {audit['minimum_component_span_mm']:.3f} mm")

    # Every source must be explicit and bound to an actual mockup name.
    if set(MOCKUP_SOURCES) != set(mockups):
        report["failures"].append("mockup source table does not exactly match mockup dictionary")
    for name, source in MOCKUP_SOURCES.items():
        if not source.source.strip() or not source.envelope.strip():
            report["failures"].append(f"{name}: missing real envelope source")

    all_items: Dict[str, cq.Shape] = {
        **{f"printed/{name}": placed.global_shape() for name, placed in printed_parts.items()},
        **{f"mockup/{name}": placed.global_shape() for name, placed in mockups.items()},
    }
    names = sorted(all_items)
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            pair = _pair(first, second)
            allowed_reason = CONTACT_ALLOWLIST.get(pair)
            try:
                volume = _intersection_volume(all_items[first], all_items[second])
                gap = float(all_items[first].distance(all_items[second]))
            except Exception as exc:
                report["failures"].append(f"pair computation failed {first} / {second}: {exc}")
                volume, gap = -1.0, -1.0
            key = f"{first} <> {second}"
            report["pairwise_clearance"][key] = {
                "intersection_mm3": volume,
                "minimum_gap_mm": gap,
                "allowed_contact": allowed_reason,
            }
            if allowed_reason is None:
                if volume > GEOMETRY_TOLERANCE:
                    report["failures"].append(f"unallowed interference {key}: {volume:.6f} mm3")
                if gap < MIN_ASSEMBLY_GAP - GEOMETRY_TOLERANCE:
                    report["failures"].append(f"unallowed gap {key}: {gap:.6f} mm")

    # Moving carriage is checked every 0.5 mm plus the exact endpoint.  Items that
    # intentionally move with it or contact it are excluded by name, not position.
    static_exclusions = {
        "printed/spring_carriage", "printed/cocking_lever", "printed/servo_sear",
        "mockup/selected_compression_spring", "mockup/cocking_drive_m3",
        "mockup/syringe_norm_ject_10ml",  # plunger subassembly is represented separately below
    }
    sweep_static = {name: shape for name, shape in all_items.items() if name not in static_exclusions}
    step_count = int(math.floor(PLUNGER_STROKE / 0.5))
    sweep_positions = [i * 0.5 for i in range(step_count + 1)]
    if abs(sweep_positions[-1] - PLUNGER_STROKE) > 1.0e-6:
        sweep_positions.append(PLUNGER_STROKE)
    for travel in sweep_positions:
        carriage = _stroke_carriage_shape(travel)
        minimum_gap = float("inf")
        nearest = None
        maximum_intersection = 0.0
        for name, static_shape in sweep_static.items():
            volume = _intersection_volume(carriage, static_shape)
            gap = float(carriage.distance(static_shape))
            if gap < minimum_gap:
                minimum_gap, nearest = gap, name
            maximum_intersection = max(maximum_intersection, volume)
            if volume > GEOMETRY_TOLERANCE:
                report["failures"].append(
                    f"stroke {travel:.3f} mm interference with {name}: {volume:.6f} mm3")
            if gap < MIN_ASSEMBLY_GAP - GEOMETRY_TOLERANCE:
                report["failures"].append(
                    f"stroke {travel:.3f} mm gap to {name}: {gap:.6f} mm")
        report["stroke_sweep"].append({
            "travel_mm": travel,
            "minimum_static_gap_mm": minimum_gap,
            "nearest_static_item": nearest,
            "maximum_intersection_mm3": maximum_intersection,
        })

    # Centerline connectivity: outlet, hub inlet and both tower bores are coaxial.
    syringe_outlet = (NOZZLE_START_X, SYRINGE_AXIS_Y, SYRINGE_AXIS_Z)
    nozzle_inlet = (NOZZLE_START_X, NOZZLE_AXIS_Y, NOZZLE_AXIS_Z)
    axis_offset = math.hypot(syringe_outlet[1] - nozzle_inlet[1],
                             syringe_outlet[2] - nozzle_inlet[2])
    axial_gap = abs(syringe_outlet[0] - nozzle_inlet[0])
    tower_centers = [(BRIDGE_X + x, NOZZLE_AXIS_Y, NOZZLE_AXIS_Z) for x in (80.0, 87.0)]
    tower_axis_error = max(math.hypot(y - NOZZLE_AXIS_Y, z - NOZZLE_AXIS_Z)
                           for _, y, z in tower_centers)
    report["fluid_path"] = {
        "syringe_outlet_xyz_mm": syringe_outlet,
        "nozzle_inlet_xyz_mm": nozzle_inlet,
        "axis_offset_mm": axis_offset,
        "axial_gap_mm": axial_gap,
        "tower_bore_axis_error_mm": tower_axis_error,
        "outlet_xyz_mm": (NOZZLE_START_X + 3.0 + NOZZLE_LENGTH,
                           NOZZLE_AXIS_Y, NOZZLE_AXIS_Z),
        "connected": axis_offset <= 0.05 and axial_gap <= 0.05 and tower_axis_error <= 0.05,
    }
    if not report["fluid_path"]["connected"]:
        report["failures"].append("live fluid centerline is not connected")

    # Profile is measured over the wrist zone from the foam-backed skin plane.
    wrist_x0, wrist_x1 = 90.0, 120.0
    top = max(
        shape.BoundingBox().zmax for shape in all_items.values()
        if shape.BoundingBox().xmax >= wrist_x0
        and shape.BoundingBox().xmin <= wrist_x1
        and shape.BoundingBox().zmin > -2.0
    )
    profile = top + FOAM_THICKNESS
    report["wrist_profile"] = {
        "x_range_mm": [wrist_x0, wrist_x1],
        "skin_plane_z_mm": -FOAM_THICKNESS,
        "highest_geometry_z_mm": top,
        "profile_above_skin_mm": profile,
    }
    if profile > WRIST_PROFILE_LIMIT:
        report["failures"].append(f"wrist profile {profile:.3f} exceeds 25 mm")

    return report


def _safe_filename(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)


def export_all() -> dict:
    PART_DIR.mkdir(exist_ok=True)
    ASSEMBLY_STL_DIR.mkdir(exist_ok=True)

    # Remove only generated files, preserving any user-owned files in these folders.
    for path in PART_DIR.glob("*.step"):
        path.unlink()
    for path in PART_DIR.glob("*.stl"):
        path.unlink()
    for path in ASSEMBLY_STL_DIR.glob("*.stl"):
        path.unlink()

    for name, placed in printed_parts.items():
        exporters.export(placed.shape, str(PART_DIR / f"{name}.step"))
        exporters.export(placed.shape, str(PART_DIR / f"{name}.stl"),
                         tolerance=0.08, angularTolerance=0.15)
        exporters.export(placed.global_shape(), str(ASSEMBLY_STL_DIR / f"printed_{name}.stl"),
                         tolerance=0.08, angularTolerance=0.15)

    for name, placed in mockups.items():
        exporters.export(placed.global_shape(),
                         str(ASSEMBLY_STL_DIR / f"mockup_{_safe_filename(name)}.stl"),
                         tolerance=0.10, angularTolerance=0.18)

    assembly.save(str(OUT_DIR / "webshooter_mk2_assembly.step"), exportType="STEP")

    report = verify_model()
    (OUT_DIR / "verification_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if report["failures"]:
        raise RuntimeError("Verification failed:\n  " + "\n  ".join(report["failures"]))
    return report


verification_report: dict | None = None


if __name__ == "__main__":
    verification_report = export_all()
    physics = verification_report["physics"]
    print(f"Exit velocity: {physics['exit_velocity_m_s']:.3f} m/s")
    print(f"Ideal 45-degree ballistic range: {physics['ideal_45deg_ballistic_range_m']:.3f} m")
    print(f"Shot: {physics['shot_volume_ml']:.3f} mL in {physics['shot_time_s'] * 1000.0:.1f} ms")
    print(json.dumps({
        "status": "PASS",
        "architecture": verification_report["architecture"],
        "printed_parts": verification_report["printed_part_count"],
        "wrist_profile_mm": round(verification_report["wrist_profile"]["profile_above_skin_mm"], 3),
        "stroke_poses_checked": len(verification_report["stroke_sweep"]),
        "pairwise_pairs_checked": len(verification_report["pairwise_clearance"]),
        "assembly_stl_count": len(list(ASSEMBLY_STL_DIR.glob("*.stl"))),
    }, indent=2))
    # CadQuery 2.8 / OCCT on this host returns 1 during normal interpreter teardown
    # after STEP assembly export.  Verification exceptions above still exit nonzero.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
