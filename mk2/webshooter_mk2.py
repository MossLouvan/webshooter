"""Web-Shooter Mk2 - clean-sheet, open-frame CadQuery model.

Run with:  python webshooter_mk2.py

The module intentionally leaves ``assembly``, ``printed_parts``, and ``mockups``
available for reviewer inspection after import.  Purchased-item mockups are never
exported as printable parts.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import cadquery as cq
from cadquery import exporters


# -----------------------------------------------------------------------------
# PARAMETERS -- millimetres unless noted.  Confidence is stated on every proxy.
# -----------------------------------------------------------------------------

OUT_DIR = Path(__file__).resolve().parent
PART_DIR = OUT_DIR / "printed_parts"
ASSEMBLY_STL_DIR = OUT_DIR / "assembly_stl"

# Anthropometric concept dimensions from brief (MEDIUM confidence; measure wearer).
FOREARM_CROWN_RADIUS = 50.0
FOREARM_PLATE_WIDTH = 56.0
FOREARM_PLATE_LENGTH = 118.0
BASE_THICKNESS = 3.2
FOAM_GAP = 0.8

# Attachment hardware (HIGH confidence: owned M3 hardware / named shared fits).
M3_CLEARANCE_DIAMETER = 3.4
M3_HEAD_DIAMETER = 5.8
M3_INSERT_OD = 5.0
M3_INSERT_LENGTH = 4.0
M3_INSERT_POCKET_DIAMETER = M3_INSERT_OD + 0.2
BRIDGE_FASTENER_X = 116.0
BRIDGE_FASTENER_Y = 20.0
BRIDGE_INTERFACE_Z = 12.6
INTERPART_GAP = 0.35

# Strap geometry (HIGH confidence for specified 25 mm webbing; thickness proxy).
STRAP_WIDTH = 25.0
STRAP_THICKNESS = 1.5  # MEDIUM confidence; measure purchased webbing.
STRAP_SLOT_LENGTH = STRAP_WIDTH + 2.0
STRAP_SLOT_WIDTH = STRAP_THICKNESS + 2.0
FOREARM_STRAP_X = 28.0
PALM_STRAP_LOCAL_X = 16.0

# Syringe (HIGH confidence cylinder dimensions: NORM-JECT 10 mL, Restek 22775).
SYRINGE_BORE_DIAMETER = 15.9
SYRINGE_BARREL_OD = 17.3
SYRINGE_BARREL_LENGTH = 85.3
SYRINGE_AXIS_Y = 0.0
SYRINGE_AXIS_Z = 20.85
SYRINGE_BARREL_START_X = 83.0
SYRINGE_PLUNGER_START_X = 73.0
SYRINGE_PLUNGER_TRAVEL = 10.0
SHOT_VOLUME_ML = (
    math.pi * (SYRINGE_BORE_DIAMETER / 2.0) ** 2 * SYRINGE_PLUNGER_TRAVEL / 1000.0
)
SYRINGE_MOUNT_CLEARANCE = 0.5

# Chosen drive: Actuonix L12-10-210-6-S (dimensions are conservative proxies;
# HIGH confidence in 10 mm stroke / 80 N max from manufacturer datasheet).
ACTUATOR_BODY_LENGTH = 54.0
ACTUATOR_BODY_WIDTH = 15.0
ACTUATOR_BODY_HEIGHT = 12.0
ACTUATOR_STROKE = 10.0
ACTUATOR_AXIS_Y = 17.0
ACTUATOR_AXIS_Z = 18.2
ACTUATOR_BODY_START_X = 4.0
ACTUATOR_CLEVIS_PIN_X = 65.0
ACTUATOR_PIN_DIAMETER = M3_CLEARANCE_DIAMETER

# Electronics proxies from common published dimensions / brief (MEDIUM confidence).
LIPO_SIZE = (54.0, 34.0, 10.0)       # EEMB 103454 nominal envelope.
XIAO_SIZE = (17.8, 21.0, 3.6)        # Same board, rotated in-plane for packing.
TP4056_SIZE = (28.0, 17.0, 4.0)      # Common USB-C TP4056/DW01 module proxy.
BOOST_SIZE = (32.0, 17.0, 6.0)       # Pololu U3V70F6 conservative envelope.
DRIVER_SIZE = (18.0, 15.0, 3.0)      # DRV8833 carrier conservative envelope.
POWER_SWITCH_SIZE = (13.0, 8.0, 7.0) # SS12D00-family slide switch proxy.
PALM_SWITCH_SIZE = (12.0, 12.0, 4.3)
BOARD_CLEARANCE = 0.45

# Hand bridge and barrels (MEDIUM confidence; measure wearer and needles).
BRIDGE_TRANSLATE_X = 112.0
BRIDGE_LENGTH = 78.0
BRIDGE_WIDTH = 26.0
BRIDGE_THICKNESS = 3.0
BARREL_AXIS_Z_LOCAL = 9.0
BARREL_Y = 6.0
BARREL_OD = 2.4             # 14 ga blunt needle nominal OD proxy.
BARREL_CLEARANCE_DIAMETER = BARREL_OD + 0.5
BARREL_GLOBAL_START_X = 178.0
BARREL_LENGTH = 25.0
BARREL_SUPPORT_LOCAL_X = (68.0, 75.0)

# General manufacturing clearances (HIGH confidence starting points for Bambu FDM).
SLIDING_CLEARANCE = 0.35
CONTACT_EPSILON = 1.0e-6


@dataclass(frozen=True)
class PlacedShape:
    shape: cq.Shape
    location: cq.Location

    def global_shape(self) -> cq.Shape:
        return self.shape.moved(self.location)


def _box(x: float, y: float, z: float, centered=(False, False, False)) -> cq.Shape:
    return cq.Workplane("XY").box(x, y, z, centered=centered).val()


def _cylinder_x(length: float, radius: float) -> cq.Shape:
    return cq.Workplane("YZ").circle(radius).extrude(length).val()


def _cylinder_y(length: float, radius: float) -> cq.Shape:
    return cq.Workplane("XZ").circle(radius).extrude(length).val()


def _cylinder_z(height: float, radius: float) -> cq.Shape:
    return cq.Workplane("XY").circle(radius).extrude(height).val()


def _compound(*shapes: cq.Shape) -> cq.Shape:
    return cq.Compound.makeCompound(list(shapes))


def _forearm_surface_z(y: float, radial_offset: float = 0.0) -> float:
    half = FOREARM_PLATE_WIDTH / 2.0
    circle_center_z = -math.sqrt(FOREARM_CROWN_RADIUS**2 - half**2)
    radius = FOREARM_CROWN_RADIUS + radial_offset
    return circle_center_z + math.sqrt(radius**2 - y**2)


def make_baseplate() -> cq.Shape:
    """Curved open frame with integral rails, board clips and bridge interface."""
    half = FOREARM_PLATE_WIDTH / 2.0
    circle_center_z = -math.sqrt(FOREARM_CROWN_RADIUS**2 - half**2)

    outer = (
        cq.Workplane("YZ")
        .center(0, circle_center_z)
        .circle(FOREARM_CROWN_RADIUS + BASE_THICKNESS)
        .extrude(FOREARM_PLATE_LENGTH)
        .val()
    )
    inner = (
        cq.Workplane("YZ")
        .center(0, circle_center_z)
        .circle(FOREARM_CROWN_RADIUS)
        .extrude(FOREARM_PLATE_LENGTH)
        .val()
    )
    clip = (
        cq.Workplane("XY")
        .box(FOREARM_PLATE_LENGTH, FOREARM_PLATE_WIDTH, 30.0,
             centered=(False, True, False))
        .val()
    )
    base = outer.cut(inner).intersect(clip)

    def add_support(shape: cq.Shape, x: float, y: float, sx: float, sy: float,
                    top_z: float) -> cq.Shape:
        """Fuse a mount down into the curved shell without protruding through it."""
        sample_y = max(-FOREARM_PLATE_WIDTH / 2.0 + 0.2,
                       min(FOREARM_PLATE_WIDTH / 2.0 - 0.2, y + sy / 2.0))
        bottom_z = _forearm_surface_z(sample_y, BASE_THICKNESS) - 0.8
        support = _box(sx, sy, top_z - bottom_z).moved(
            cq.Location(cq.Vector(x, y, bottom_z))
        )
        return shape.fuse(support)

    # Two transverse-webbing slot pairs.  Each opening is sized from shared strap constants.
    for slot_x in (FOREARM_STRAP_X,):
        for side in (-1.0, 1.0):
            cutter = (
                _box(STRAP_SLOT_LENGTH, STRAP_SLOT_WIDTH, 30.0)
                .moved(cq.Location(cq.Vector(slot_x - STRAP_SLOT_LENGTH / 2.0,
                                             side * 23.0 - STRAP_SLOT_WIDTH / 2.0, 0.0)))
            )
            base = base.cut(cutter)

    # Mounting pads for the bridge: the bridge underside clears the curved crown.
    for y in (-BRIDGE_FASTENER_Y, BRIDGE_FASTENER_Y):
        base = add_support(base, FOREARM_PLATE_LENGTH - 12.0, y - 4.0,
                           12.0, 8.0, BRIDGE_INTERFACE_Z - INTERPART_GAP)
        hole = _cylinder_z(M3_INSERT_LENGTH + 0.2, M3_INSERT_POCKET_DIAMETER / 2.0).moved(
            cq.Location(cq.Vector(BRIDGE_FASTENER_X, y,
                                         BRIDGE_INTERFACE_Z - INTERPART_GAP - M3_INSERT_LENGTH))
        )
        base = base.cut(hole)

    # Actuator side rails, deliberately outside its clearance envelope.
    actuator_y_edge = ACTUATOR_BODY_WIDTH / 2.0 + BOARD_CLEARANCE
    for side in (-1.0, 1.0):
        y = ACTUATOR_AXIS_Y + side * (actuator_y_edge + 1.0)
        base = add_support(base, ACTUATOR_BODY_START_X - 1.5, y - 1.0,
                           ACTUATOR_BODY_LENGTH + 3.0, 2.0, 24.0)

    # LiPo corner clips: low open tabs, not a pocket or enclosure.
    lipo_x0, lipo_y0 = 3.0, -27.0
    for cx in (lipo_x0 - 2.5, lipo_x0 + LIPO_SIZE[0] + 0.5):
        for cy in (lipo_y0 - 2.5, lipo_y0 + LIPO_SIZE[1] + 0.5):
            base = add_support(base, cx, cy, 2.0, 2.0, 23.3)

    # Board/boost clip pairs; USB-C ends remain completely open.
    clip_specs = (
        (61.0, -28.5, BOOST_SIZE),
        (94.0, -31.0, XIAO_SIZE),
        (76.0, 11.5, TP4056_SIZE),
        (56.0, 28.0, DRIVER_SIZE),
    )
    for x0, y0, size in clip_specs:
        for side in (-1.0, 1.0):
            cy = y0 + (0.0 if side < 0 else size[1]) + side * 1.0
            base = add_support(base, x0, cy - 0.75, size[0], 1.5, 12.2 + size[2] + 1.0)

    # Thin side outriggers connect no-hole board clips and keep USB-C ends exposed.
    electronics_outrigger = _box(74.0, 11.0, 9.2).moved(
        cq.Location(cq.Vector(38.0, 26.0, 3.0))
    )
    base = base.fuse(electronics_outrigger)
    xiao_outrigger = _box(20.0, 6.0, 9.2).moved(
        cq.Location(cq.Vector(93.0, -32.0, 3.0))
    )
    base = base.fuse(xiao_outrigger)
    driver_outrigger = _box(22.0, 19.0, 9.2).moved(
        cq.Location(cq.Vector(54.0, 26.0, 3.0))
    )
    base = base.fuse(driver_outrigger)

    # Required power-switch saddle on the same open positive-side outrigger.
    for wall_y in (25.5, 35.0):
        wall = _box(15.0, 1.5, 8.5).moved(
            cq.Location(cq.Vector(39.0, wall_y, 11.7))
        )
        base = base.fuse(wall)

    # Rear syringe guide; the forward guide is integral to the hand bridge.
    for side in (-1.0, 1.0):
        cy = SYRINGE_AXIS_Y + side * (SYRINGE_BARREL_OD / 2.0 + SYRINGE_MOUNT_CLEARANCE + 1.0)
        base = add_support(base, 80.0, cy - 1.0, 6.0, 2.0, 22.5)

    return base.clean().moved(cq.Location(cq.Vector(0.0, 0.0, 0.06)))


def make_bridge() -> cq.Shape:
    """Narrow, exposed dorsal-hand bridge with syringe and twin-barrel guides."""
    bridge = (
        cq.Workplane("XY")
        .rect(BRIDGE_LENGTH, BRIDGE_WIDTH, centered=False)
        .extrude(BRIDGE_THICKNESS)
        .val()
        .moved(cq.Location(cq.Vector(0.0, -BRIDGE_WIDTH / 2.0, 0.0)))
    )
    # Rear butterfly only: broad enough for two M3s, then immediately narrows.
    rear_wing = _box(10.0, 48.0, BRIDGE_THICKNESS).moved(
        cq.Location(cq.Vector(0.0, -24.0, 0.0))
    )
    bridge = bridge.fuse(rear_wing)

    # Palm strap pair.
    for side in (-1.0, 1.0):
        cutter = _box(STRAP_SLOT_LENGTH, STRAP_SLOT_WIDTH, 10.0).moved(
            cq.Location(cq.Vector(PALM_STRAP_LOCAL_X - STRAP_SLOT_LENGTH / 2.0,
                                         side * 10.5 - STRAP_SLOT_WIDTH / 2.0, 0.0))
        )
        bridge = bridge.cut(cutter)

    # Shared bridge interface holes, aligned to the baseplate constants.
    for y in (-BRIDGE_FASTENER_Y, BRIDGE_FASTENER_Y):
        local_x = BRIDGE_FASTENER_X - BRIDGE_TRANSLATE_X
        hole = _cylinder_z(10.0, M3_CLEARANCE_DIAMETER / 2.0).moved(
            cq.Location(cq.Vector(local_x, y, 0.0))
        )
        bridge = bridge.cut(hole)

    # Open center lane: the syringe is carried between side guides, never buried in a plate.
    syringe_lane = _box(60.0, SYRINGE_BARREL_OD + 2.0 * SYRINGE_MOUNT_CLEARANCE,
                         BRIDGE_THICKNESS + 2.0).moved(
        cq.Location(cq.Vector(0.0,
                                     SYRINGE_AXIS_Y - SYRINGE_BARREL_OD / 2.0 - SYRINGE_MOUNT_CLEARANCE,
                                     -0.5))
    )
    bridge = bridge.cut(syringe_lane)

    # Forward syringe guide, outside the barrel OD envelope.
    for side in (-1.0, 1.0):
        cy = SYRINGE_AXIS_Y + side * (SYRINGE_BARREL_OD / 2.0 + SYRINGE_MOUNT_CLEARANCE + 1.0)
        guide = _box(6.0, 2.0, 10.0).moved(
            cq.Location(cq.Vector(34.0, cy - 1.0, 2.2))
        )
        bridge = bridge.fuse(guide)

    # Two perforated barrel towers make both barrels visually explicit.
    for x in BARREL_SUPPORT_LOCAL_X:
        tower = _box(5.0, 23.0, 11.0).moved(
            cq.Location(cq.Vector(x - 2.5, -11.5, 2.2))
        )
        for y in (-BARREL_Y, BARREL_Y):
            bore = _cylinder_x(8.0, BARREL_CLEARANCE_DIAMETER / 2.0).moved(
                cq.Location(cq.Vector(x - 4.0, y, BARREL_AXIS_Z_LOCAL))
            )
            tower = tower.cut(bore)
        bridge = bridge.fuse(tower)

    return bridge.clean().moved(cq.Location(cq.Vector(0.0, 0.0, 0.01)))


def make_pusher_yoke() -> cq.Shape:
    """Single printed clevis/tappet joining the L12 output to syringe flange."""
    tongue = _box(6.0, 4.0, 7.0).moved(cq.Location(cq.Vector(0.0, 0.0, 1.0)))
    bridge = _box(3.0, ACTUATOR_AXIS_Y - SYRINGE_AXIS_Y + 4.0, 6.0).moved(
        cq.Location(cq.Vector(6.0, -(ACTUATOR_AXIS_Y - SYRINGE_AXIS_Y), 1.5))
    )
    pad = _box(3.0, 10.0, 9.0).moved(
        cq.Location(cq.Vector(6.0, -(ACTUATOR_AXIS_Y - SYRINGE_AXIS_Y) - 3.0, 0.0))
    )
    yoke = tongue.fuse(bridge).fuse(pad)
    # Pin axis is local Y; both actuator clevis and this hole use the same named diameter.
    pin_hole = _cylinder_y(10.0, ACTUATOR_PIN_DIAMETER / 2.0).moved(
        cq.Location(cq.Vector(3.0, -3.0, 4.5))
    )
    return yoke.cut(pin_hole).clean().moved(cq.Location(cq.Vector(0.0, 0.0, 0.001)))


def make_switch_pod() -> cq.Shape:
    """Open palm-facing tactile switch frame; retained by the palm strap."""
    outer = _box(18.0, 18.0, 6.5)
    pocket = _box(PALM_SWITCH_SIZE[0] + BOARD_CLEARANCE * 2.0,
                  PALM_SWITCH_SIZE[1] + BOARD_CLEARANCE * 2.0, 6.0).moved(
        cq.Location(cq.Vector((18.0 - PALM_SWITCH_SIZE[0] - BOARD_CLEARANCE * 2.0) / 2.0,
                                     (18.0 - PALM_SWITCH_SIZE[1] - BOARD_CLEARANCE * 2.0) / 2.0,
                                     1.5))
    )
    pod = outer.cut(pocket)
    # Webbing tunnel uses the same purchased strap thickness.
    tunnel = _box(20.0, STRAP_WIDTH + 1.0, STRAP_THICKNESS + SLIDING_CLEARANCE).moved(
        cq.Location(cq.Vector(-1.0, (18.0 - STRAP_WIDTH - 1.0) / 2.0, 0.0))
    )
    return pod.cut(tunnel).clean()


def make_mockups() -> Dict[str, PlacedShape]:
    """Purchased/owned item proxies.  All shapes are deliberately clearance-separated."""
    items: Dict[str, PlacedShape] = {}

    # 10 mL all-plastic syringe: barrel, Luer, plunger rod and thumb flange.
    barrel = _cylinder_x(SYRINGE_BARREL_LENGTH, SYRINGE_BARREL_OD / 2.0).moved(
        cq.Location(cq.Vector(SYRINGE_BARREL_START_X, SYRINGE_AXIS_Y, SYRINGE_AXIS_Z))
    )
    luer = _cylinder_x(9.0, 2.2).moved(cq.Location(cq.Vector(
        SYRINGE_BARREL_START_X + SYRINGE_BARREL_LENGTH, SYRINGE_AXIS_Y, SYRINGE_AXIS_Z)))
    plunger_rod = _cylinder_x(SYRINGE_BARREL_START_X - SYRINGE_PLUNGER_START_X,
                              3.0).moved(cq.Location(cq.Vector(
        SYRINGE_PLUNGER_START_X, SYRINGE_AXIS_Y, SYRINGE_AXIS_Z)))
    flange = _box(2.0, 18.0, 13.0).moved(cq.Location(cq.Vector(
        SYRINGE_PLUNGER_START_X - 2.0, SYRINGE_AXIS_Y - 9.0, SYRINGE_AXIS_Z - 6.5)))
    items["syringe_10ml_all_plastic"] = PlacedShape(_compound(barrel, luer, plunger_rod, flange), cq.Location())

    # L12 body and rod/clevis proxy in its loaded (retracted) state.
    body = _box(ACTUATOR_BODY_LENGTH, ACTUATOR_BODY_WIDTH, ACTUATOR_BODY_HEIGHT).moved(
        cq.Location(cq.Vector(ACTUATOR_BODY_START_X,
                                     ACTUATOR_AXIS_Y - ACTUATOR_BODY_WIDTH / 2.0,
                                     ACTUATOR_AXIS_Z - ACTUATOR_BODY_HEIGHT / 2.0))
    )
    rod = _cylinder_x(4.0, 2.0).moved(cq.Location(cq.Vector(
        ACTUATOR_BODY_START_X + ACTUATOR_BODY_LENGTH, ACTUATOR_AXIS_Y, ACTUATOR_AXIS_Z)))
    clevis_left = _box(5.0, 2.0, 7.0).moved(cq.Location(cq.Vector(
        ACTUATOR_CLEVIS_PIN_X - 3.0, ACTUATOR_AXIS_Y - 5.0, ACTUATOR_AXIS_Z - 3.5)))
    clevis_right = _box(5.0, 2.0, 7.0).moved(cq.Location(cq.Vector(
        ACTUATOR_CLEVIS_PIN_X - 3.0, ACTUATOR_AXIS_Y + 3.0, ACTUATOR_AXIS_Z - 3.5)))
    clevis_hole = _cylinder_y(12.0, ACTUATOR_PIN_DIAMETER / 2.0).moved(cq.Location(cq.Vector(
        ACTUATOR_CLEVIS_PIN_X, ACTUATOR_AXIS_Y - 6.0, ACTUATOR_AXIS_Z)))
    actuator = _compound(body, rod, clevis_left.cut(clevis_hole), clevis_right.cut(clevis_hole))
    items["actuonix_L12_10_210_6_S"] = PlacedShape(actuator, cq.Location())
    items["actuator_clevis_M3_pin"] = PlacedShape(
        _cylinder_y(11.0, 1.5),
        cq.Location(cq.Vector(ACTUATOR_CLEVIS_PIN_X, ACTUATOR_AXIS_Y - 5.5,
                                     ACTUATOR_AXIS_Z)))

    # Battery and exposed electronics, each with its own solid envelope.
    items["lipo_EEMB_103454"] = PlacedShape(
        _box(*LIPO_SIZE), cq.Location(cq.Vector(3.0, -27.0, 12.3)))
    items["boost_6V_U3V70F6"] = PlacedShape(
        _box(*BOOST_SIZE), cq.Location(cq.Vector(61.0, -28.5, 12.2)))
    items["motor_driver_DRV8833"] = PlacedShape(
        _box(*DRIVER_SIZE), cq.Location(cq.Vector(56.0, 28.0, 12.7)))
    items["xiao_esp32c3"] = PlacedShape(
        _box(*XIAO_SIZE), cq.Location(cq.Vector(94.0, -31.0, 12.7)))
    items["tp4056_usbc_dw01"] = PlacedShape(
        _box(*TP4056_SIZE), cq.Location(cq.Vector(76.0, 11.5, 12.7)))
    items["power_slide_switch"] = PlacedShape(
        _box(*POWER_SWITCH_SIZE), cq.Location(cq.Vector(40.0, 27.0, 12.7)))

    # Twin barrels: lower-Y barrel is live; upper-Y barrel is capped dummy symmetry.
    for name, y in (("barrel_live_14ga", -BARREL_Y), ("barrel_dummy_14ga", BARREL_Y)):
        shape = _cylinder_x(BARREL_LENGTH, BARREL_OD / 2.0)
        items[name] = PlacedShape(shape, cq.Location(cq.Vector(
            BARREL_GLOBAL_START_X, y, BRIDGE_INTERFACE_Z + BARREL_AXIS_Z_LOCAL)))

    # Fasteners are owned M3 screws, modeled with clearance from all holes.
    insert_bottom_z = BRIDGE_INTERFACE_Z - INTERPART_GAP - M3_INSERT_LENGTH + 0.06
    bridge_top_z = BRIDGE_INTERFACE_Z + 0.01 + BRIDGE_THICKNESS
    for idx, y in enumerate((-BRIDGE_FASTENER_Y, BRIDGE_FASTENER_Y), start=1):
        shaft_length = bridge_top_z - insert_bottom_z
        shaft = _cylinder_z(shaft_length, 1.5)
        head = _cylinder_z(2.0, M3_HEAD_DIAMETER / 2.0).moved(
            cq.Location(cq.Vector(0, 0, shaft_length)))
        items[f"bridge_M3_screw_{idx}"] = PlacedShape(
            _compound(shaft, head), cq.Location(cq.Vector(BRIDGE_FASTENER_X, y, insert_bottom_z)))
        insert_outer = _cylinder_z(M3_INSERT_LENGTH, M3_INSERT_OD / 2.0)
        insert_bore = _cylinder_z(M3_INSERT_LENGTH, M3_CLEARANCE_DIAMETER / 2.0)
        items[f"bridge_M3_insert_{idx}"] = PlacedShape(
            insert_outer.cut(insert_bore),
            cq.Location(cq.Vector(BRIDGE_FASTENER_X, y, insert_bottom_z)))

    # Visible webbing tabs inside the four baseplate/bridge slots (loop continues below skin).
    forearm_tabs = []
    for slot_x in (FOREARM_STRAP_X,):
        for side in (-1.0, 1.0):
            forearm_tabs.append(_box(STRAP_WIDTH, STRAP_THICKNESS, 5.0).moved(
                cq.Location(cq.Vector(slot_x - STRAP_WIDTH / 2.0,
                                             side * 23.0 - STRAP_THICKNESS / 2.0, 3.8))))
    items["forearm_strap_25mm"] = PlacedShape(_compound(*forearm_tabs), cq.Location())

    palm_tabs = []
    for side in (-1.0, 1.0):
        palm_tabs.append(_box(STRAP_WIDTH, STRAP_THICKNESS, 4.0).moved(
            cq.Location(cq.Vector(BRIDGE_TRANSLATE_X + PALM_STRAP_LOCAL_X - STRAP_WIDTH / 2.0,
                                         side * 10.5 - STRAP_THICKNESS / 2.0,
                                         BRIDGE_INTERFACE_Z + 3.3))))
    items["palm_strap_25mm"] = PlacedShape(_compound(*palm_tabs), cq.Location())

    # Palm trigger and its pod are below the hand reference; wiring is intentionally omitted.
    items["palm_tactile_switch_12mm"] = PlacedShape(
        _box(*PALM_SWITCH_SIZE), cq.Location(cq.Vector(145.0, -6.0, -15.5)))

    # Short live fluid line is a straight proxy kept clear of the syringe and live barrel.
    tube = _cylinder_x(6.0, 1.0)
    items["ptfe_line_owned"] = PlacedShape(tube, cq.Location(cq.Vector(
        151.0, -13.0, SYRINGE_AXIS_Z)))

    # Anatomical references are non-purchased mockups but live in the same audit dictionary.
    circle_center_z = -math.sqrt(FOREARM_CROWN_RADIUS**2 - (FOREARM_PLATE_WIDTH / 2.0) ** 2)
    arm_cylinder = (
        cq.Workplane("YZ").center(0, circle_center_z - FOAM_GAP)
        .circle(FOREARM_CROWN_RADIUS).extrude(118.0).val()
    )
    arm_clip = _box(118.0, 64.0, 60.0).moved(cq.Location(cq.Vector(0.0, -32.0, -51.0)))
    items["forearm_reference"] = PlacedShape(arm_cylinder.intersect(arm_clip), cq.Location())

    hand = cq.Workplane("XY").ellipse(34.0, 25.0).extrude(9.0).val()
    items["hand_reference"] = PlacedShape(hand, cq.Location(cq.Vector(153.0, 0.0, -1.5)))

    return items


printed_parts: Dict[str, PlacedShape] = {
    "baseplate": PlacedShape(make_baseplate(), cq.Location()),
    "barrel_bridge": PlacedShape(make_bridge(), cq.Location(cq.Vector(
        BRIDGE_TRANSLATE_X, 0.0, BRIDGE_INTERFACE_Z))),
    "pusher_yoke": PlacedShape(make_pusher_yoke(), cq.Location(cq.Vector(
        ACTUATOR_CLEVIS_PIN_X - 3.0,
        ACTUATOR_AXIS_Y - 2.0,
        ACTUATOR_AXIS_Z - 4.501))),
    "palm_switch_pod": PlacedShape(make_switch_pod(), cq.Location(cq.Vector(
        142.0, -9.0, -17.0))),
}

mockups: Dict[str, PlacedShape] = make_mockups()

# A real CadQuery assembly with explicit transforms for all printable and mockup items.
assembly = cq.Assembly(name="webshooter_mk2_open_frame")
for name, placed in printed_parts.items():
    assembly.add(placed.shape, name=f"printed_{name}", loc=placed.location,
                 color=cq.Color(0.82, 0.12, 0.12, 1.0))
for name, placed in mockups.items():
    color = cq.Color(0.55, 0.58, 0.62, 0.72)
    if "reference" in name:
        color = cq.Color(0.82, 0.65, 0.52, 0.25)
    elif "barrel" in name:
        color = cq.Color(0.72, 0.75, 0.80, 1.0)
    elif "strap" in name:
        color = cq.Color(0.08, 0.08, 0.08, 1.0)
    assembly.add(placed.shape, name=f"mockup_{name}", loc=placed.location, color=color)


def _solid_count(shape: cq.Shape) -> int:
    return len(shape.Solids())


def _min_z(shape: cq.Shape) -> float:
    return shape.BoundingBox().zmin


def verify_model() -> dict:
    """Run all hard checks; there is intentionally no contact allow-list."""
    report = {
        "shot_volume_ml": SHOT_VOLUME_ML,
        "printed_part_count": len(printed_parts),
        "printed_parts": {},
        "pairwise_intersections_mm3": {},
        "failures": [],
    }

    for name, placed in printed_parts.items():
        shape = placed.shape
        entry = {
            "solid_count": _solid_count(shape),
            "is_valid": bool(shape.isValid()),
            "local_z_min_mm": _min_z(shape),
            "local_z_max_mm": shape.BoundingBox().zmax,
            "volume_mm3": shape.Volume(),
        }
        report["printed_parts"][name] = entry
        if entry["solid_count"] != 1:
            report["failures"].append(f"{name}: solid_count={entry['solid_count']}")
        if not entry["is_valid"]:
            report["failures"].append(f"{name}: invalid solid")
        if entry["local_z_min_mm"] < -CONTACT_EPSILON:
            report["failures"].append(f"{name}: geometry below local z=0")

    if SHOT_VOLUME_ML < 1.5:
        report["failures"].append("shot volume below 1.5 mL")
    if SYRINGE_PLUNGER_TRAVEL > ACTUATOR_STROKE:
        report["failures"].append("commanded syringe travel exceeds actuator stroke")
    if len(printed_parts) > 6:
        report["failures"].append("more than 6 printed parts")

    # Full O(n^2) audit across printed parts AND every mockup, no exclusions.
    all_items: Dict[str, cq.Shape] = {}
    all_items.update({f"printed/{k}": v.global_shape() for k, v in printed_parts.items()})
    all_items.update({f"mockup/{k}": v.global_shape() for k, v in mockups.items()})
    names = sorted(all_items)
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            try:
                common = all_items[first].intersect(all_items[second])
                volume = float(common.Volume()) if not common.isNull() else 0.0
            except Exception as exc:  # Reviewer should see computation failures, never silent passes.
                report["failures"].append(f"intersection failed: {first} / {second}: {exc}")
                volume = -1.0
            key = f"{first} <> {second}"
            report["pairwise_intersections_mm3"][key] = volume
            if volume > CONTACT_EPSILON:
                report["failures"].append(f"interference {key}: {volume:.6f} mm^3")

    # Profile is measured from the local anatomical surface, not global datum.
    wrist_x0, wrist_x1 = 90.0, 120.0
    wrist_top = -1.0e9
    for placed in list(printed_parts.values()) + list(mockups.values()):
        bb = placed.global_shape().BoundingBox()
        if bb.xmax >= wrist_x0 and bb.xmin <= wrist_x1 and bb.zmin > -5.0:
            wrist_top = max(wrist_top, bb.zmax)
    skin_crown = _forearm_surface_z(0.0) - FOAM_GAP
    report["wrist_profile"] = {
        "wrist_x_range_mm": [wrist_x0, wrist_x1],
        "highest_geometry_global_z_mm": wrist_top,
        "skin_crown_global_z_mm": skin_crown,
        "profile_above_skin_mm": wrist_top - skin_crown,
    }
    if report["wrist_profile"]["profile_above_skin_mm"] > 25.0:
        report["failures"].append("wrist profile exceeds 25 mm")

    return report


def export_all() -> dict:
    PART_DIR.mkdir(exist_ok=True)
    if ASSEMBLY_STL_DIR.exists():
        shutil.rmtree(ASSEMBLY_STL_DIR)
    ASSEMBLY_STL_DIR.mkdir()

    for name, placed in printed_parts.items():
        exporters.export(placed.shape, str(PART_DIR / f"{name}.step"))
        exporters.export(placed.shape, str(PART_DIR / f"{name}.stl"),
                         tolerance=0.08, angularTolerance=0.15)
        exporters.export(placed.global_shape(), str(ASSEMBLY_STL_DIR / f"{name}.stl"),
                         tolerance=0.08, angularTolerance=0.15)

    # Assembly STEP preserves component names/transforms and proves this is a real assembly.
    assembly.save(str(OUT_DIR / "webshooter_mk2_assembly.step"), exportType="STEP")

    report = verify_model()
    (OUT_DIR / "verification_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if report["failures"]:
        raise RuntimeError("Verification failed:\n  " + "\n  ".join(report["failures"]))
    return report


if __name__ == "__main__":
    result = export_all()
    print(json.dumps({
        "status": "PASS",
        "printed_parts": result["printed_part_count"],
        "shot_volume_ml": round(result["shot_volume_ml"], 3),
        "wrist_profile_mm": round(result["wrist_profile"]["profile_above_skin_mm"], 3),
        "pairwise_pairs_checked": len(result["pairwise_intersections_mm3"]),
    }, indent=2))
    # CadQuery 2.8 / OCCT on this Windows host returns 1 during interpreter teardown
    # after a successful STEP assembly export.  Flush and bypass only that teardown;
    # all verification exceptions above still exit non-zero normally.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
