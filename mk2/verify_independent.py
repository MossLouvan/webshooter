#!/usr/bin/env python3
"""
Independent verification harness for the Web-Shooter model.

Written deliberately by someone who did NOT author the geometry. The model ships
its own `verify_model()`; across three revisions that self-check reported
`failures: []` while independent audits found the parts unbuildable. The failure
mode was never bad arithmetic — it was checks that could not see the defect:

  * exclusions by name       (`servo_sear` removed from the stroke sweep)
  * pose sampling            (one static pose, so a jam at half-stroke was invisible)
  * missing pairings         (the moving plunger never compared to the static syringe)
  * thresholds above defects (a 350 mm2 overhang gate vs a 136 mm2 floating island)
  * coarse sampling          (9 sections per axis vs a 1.2 mm ligament gate)
  * tautologies              (fluid-path gap computed from constants, not geometry)
  * allowlists               (real solid overlaps excused by prose)

This harness therefore takes the opposite stance on every one of those:
NO exclusions by name, NO allowlist, sweeps instead of poses, fine sampling,
and physics derived from stored energy rather than read from a declared constant.

    python verify_independent.py            # full run
    python verify_independent.py --quick    # coarser sampling, faster
    python verify_independent.py --json OUT # machine-readable report
    python verify_independent.py --model webshooter_mk2   # audit the Mk3 model instead
                                            # (or set WS_MODEL=...)

Exit code 0 if every check passes, 1 otherwise. The process exits via os._exit
because CadQuery/OCCT can segfault at interpreter teardown.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cadquery as cq  # noqa: E402
import importlib  # noqa: E402
def _pick_model() -> str:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--model")
    ns, _ = pre.parse_known_args()
    return ns.model or os.environ.get("WS_MODEL", "webshooter_mk4")


_MODEL = _pick_model()
M = importlib.import_module(_MODEL)  # noqa: E402

# ----------------------------------------------------------------- thresholds
# Set from manufacturing reality, not from what the current model happens to do.
NOZZLE_D = 0.4                 # printer nozzle
MIN_WALL = 2 * NOZZLE_D        # 0.80 mm — below this a wall is a gap-fill line
MIN_LIGAMENT = 1.2             # 3 perimeters; below this a feature is decorative
MIN_SECTION_AREA = 2.0         # mm^2, smallest credible load-bearing cross-section
MIN_FIRST_LAYER = 150.0        # mm^2 of bed contact before adhesion is a gamble
MAX_UNSUPPORTED_ISLAND = 5.0   # mm^2 of material starting in mid-air
MIN_CLEARANCE = 0.15           # mm; anything tighter is a press fit or a collision
SECTION_STEP = 0.5             # mm between section planes
SWEEP_STEP = 0.25              # mm of travel between interference samples
LAYER_STEP = 0.4               # mm, island scan resolution

# Pairs permitted to TOUCH (gap ~0). Volume interpenetration is never permitted,
# for any pair - that distinction is the whole point. A sear must bear on the lug
# it holds; it must not occupy the same space as it.
TOUCH_OK = {
    frozenset({"printed/sear", "printed/carriage"}): "pawl bears on the carriage lug",
    frozenset({"printed/sear", "printed/baseplate"}): "pawl journals on its pivot pin",
    frozenset({"printed/carriage", "printed/baseplate"}): "carriage slides in its rails",
    frozenset({"printed/outlet_adapter", "printed/baseplate"}): "adapter seats in the thrust stop",
}

FAILURES: list[str] = []
WARNINGS: list[str] = []
REPORT: dict[str, Any] = {}


def fail(tag: str, msg: str) -> None:
    FAILURES.append(f"[{tag}] {msg}")


def warn(tag: str, msg: str) -> None:
    WARNINGS.append(f"[{tag}] {msg}")


# ------------------------------------------------------------------- helpers
def solid_of(shape) -> Any:
    """Normalize to a cadquery Shape. Explicit cases only — attribute sniffing
    is how the first draft of this ended up holding a bound method."""
    if isinstance(shape, cq.Workplane):
        return shape.val()
    if hasattr(shape, "shape") and hasattr(shape, "location"):
        return shape.shape.moved(shape.location)
    return shape


def placed(entry) -> Any:
    """Resolve the model's PlacedShape into world space."""
    if hasattr(entry, "shape") and hasattr(entry, "location"):
        return entry.shape.moved(entry.location)
    return solid_of(entry)


def vol(s) -> float:
    try:
        return s.Volume()
    except Exception:
        return 0.0


def bb(s):
    b = s.BoundingBox()
    return b


def intersect_volume(a, b) -> float:
    """Volume shared by two solids. Bounding boxes are checked first because a
    full boolean on non-overlapping solids is both slow and occasionally fragile."""
    ba, bbx = bb(a), bb(b)
    if (ba.xmax < bbx.xmin or bbx.xmax < ba.xmin or
            ba.ymax < bbx.ymin or bbx.ymax < ba.ymin or
            ba.zmax < bbx.zmin or bbx.zmax < ba.zmin):
        return 0.0
    try:
        return vol(a.intersect(b))
    except Exception:
        return float("nan")


def min_gap(a, b, samples: int = 2500) -> float:
    """Sampled minimum vertex distance. Coarse, but it is only used to catch
    tangency — a value at or near 0.0 is the signal, not the precise number."""
    va = [v.Center() for v in a.Vertices()]
    vb = [v.Center() for v in b.Vertices()]
    if not va or not vb:
        return float("inf")
    sa = max(1, len(va) // int(math.sqrt(samples)))
    sb = max(1, len(vb) // int(math.sqrt(samples)))
    best = float("inf")
    for p in va[::sa]:
        for q in vb[::sb]:
            d = (p - q).Length
            if d < best:
                best = d
    return best


def sections(s, axis: str, step: float):
    """Yield (coordinate, area, piece_count) slicing along an axis."""
    b = bb(s)
    lo, hi = {"x": (b.xmin, b.xmax), "y": (b.ymin, b.ymax), "z": (b.zmin, b.zmax)}[axis]
    n = max(2, int((hi - lo) / step))
    big = max(b.xlen, b.ylen, b.zlen) * 3 + 10
    for i in range(1, n):
        c = lo + (hi - lo) * i / n
        if axis == "x":
            box = cq.Workplane("YZ").workplane(offset=c).rect(big, big).extrude(step)
        elif axis == "y":
            box = cq.Workplane("XZ").workplane(offset=-c).rect(big, big).extrude(step)
        else:
            box = cq.Workplane("XY").workplane(offset=c).rect(big, big).extrude(step)
        try:
            sl = s.intersect(box.val())
        except Exception:
            continue
        v = vol(sl)
        if v <= 0:
            continue
        area = v / step
        pieces = len(sl.Solids())
        yield c, area, pieces


# ----------------------------------------------------------- 1. part integrity
def check_parts(parts: dict) -> None:
    print("\n=== 1. PART INTEGRITY ===")
    out = {}
    for name, s in parts.items():
        solids = len(s.Solids())
        shells = len(s.Shells())
        valid = s.isValid()
        b = bb(s)
        out[name] = dict(solids=solids, shells=shells, valid=valid, volume=vol(s),
                         zmin=b.zmin, dims=[b.xlen, b.ylen, b.zlen])
        flags = []
        if solids != 1:
            flags.append(f"{solids} SOLIDS")
            fail("integrity", f"{name}: {solids} disconnected solids")
        if not valid:
            flags.append("INVALID")
            fail("integrity", f"{name}: isValid() is False")
        if abs(b.zmin) > 0.01:
            flags.append(f"zmin={b.zmin:.3f}")
            fail("integrity", f"{name}: z_min {b.zmin:.3f} (must be ~0 for printing)")
        print(f"  {name:<22} solids={solids} shells={shells} valid={valid} "
              f"vol={vol(s):9.1f}  {'  '.join(flags)}")
    REPORT["parts"] = out


# --------------------------------------------------- 2. thin features (fine)
def check_thin_features(parts: dict, step: float) -> None:
    print(f"\n=== 2. THIN FEATURES (section step {step} mm) ===")
    out = {}
    for name, s in parts.items():
        worst = {}
        for axis in ("x", "y", "z"):
            min_area, min_at, max_pieces = float("inf"), None, 1
            for c, area, pieces in sections(s, axis, step):
                if area < min_area:
                    min_area, min_at = area, c
                max_pieces = max(max_pieces, pieces)
            worst[axis] = dict(min_area=min_area, at=min_at, max_pieces=max_pieces)
            if min_area < MIN_SECTION_AREA:
                fail("thin", f"{name}: {axis}-section {min_area:.2f} mm2 at {axis}={min_at:.1f} "
                             f"(< {MIN_SECTION_AREA})")
            if max_pieces > 1:
                warn("thin", f"{name}: up to {max_pieces} disjoint pieces in {axis}-sections "
                             f"(a thin ligament may be the only thing joining them)")
        out[name] = worst
        w = min(worst.values(), key=lambda d: d["min_area"])
        print(f"  {name:<22} min section {w['min_area']:8.2f} mm2   max pieces "
              f"{max(v['max_pieces'] for v in worst.values())}")
    REPORT["thin_features"] = out


# ------------------------------------------------- 3. printability / islands
def check_printability(parts: dict, step: float) -> None:
    print(f"\n=== 3. PRINTABILITY (layer step {step} mm) ===")
    out = {}
    for name, s in parts.items():
        b = bb(s)
        big = max(b.xlen, b.ylen) * 3 + 20
        # first layer
        sl = s.intersect(cq.Workplane("XY").workplane(offset=b.zmin - 0.01)
                         .rect(big, big).extrude(0.2).val())
        first_area = vol(sl) / 0.2 if vol(sl) > 0 else 0.0
        first_pieces = len(sl.Solids()) if vol(sl) > 0 else 0
        if first_area < MIN_FIRST_LAYER:
            fail("print", f"{name}: first layer {first_area:.1f} mm2 in {first_pieces} piece(s) "
                          f"(< {MIN_FIRST_LAYER})")

        # unsupported islands: material at layer z with nothing in the layer below
        islands = 0.0
        z = b.zmin + step
        prev = sl
        while z < b.zmax - step:
            cur = s.intersect(cq.Workplane("XY").workplane(offset=z)
                              .rect(big, big).extrude(step).val())
            if vol(cur) > 0:
                # A true ISLAND is a connected lump with nothing at all beneath it.
                # An OVERHANG is a lump partly over the layer below - a slicer
                # bridges that (the top of every round hole is one), so counting
                # overhang area as unsupported is a false positive. Split the
                # layer into components and only flag ones with zero support.
                try:
                    below = s.intersect(cq.Workplane("XY").workplane(offset=z - step)
                                        .rect(big, big).extrude(step).val())
                    lift = (below.moved(cq.Location(cq.Vector(0, 0, step)))
                            if vol(below) > 0 else None)
                    for lump in cur.Solids():
                        a = vol(lump) / step
                        if a <= MAX_UNSUPPORTED_ISLAND:
                            continue
                        supported = vol(lump.intersect(lift)) if lift is not None else 0.0
                        if supported <= 1e-6:
                            islands = max(islands, a)
                except Exception:
                    pass
            prev = cur
            z += step
        if islands > MAX_UNSUPPORTED_ISLAND:
            fail("print", f"{name}: {islands:.1f} mm2 of material begins unsupported "
                          f"(> {MAX_UNSUPPORTED_ISLAND})")
        out[name] = dict(first_layer_mm2=first_area, first_layer_pieces=first_pieces,
                         worst_unsupported_mm2=islands)
        print(f"  {name:<22} first layer {first_area:8.1f} mm2 ({first_pieces} pc)   "
              f"worst unsupported {islands:7.1f} mm2")
    REPORT["printability"] = out


# ------------------------------------------- 4. static clearance, NO allowlist
def check_clearances(bodies: dict) -> None:
    print("\n=== 4. STATIC CLEARANCE (no allowlist) ===")
    hits, tang = [], []
    names = sorted(bodies)
    for a, b in itertools.combinations(names, 2):
        v = intersect_volume(bodies[a], bodies[b])
        if v != v:  # NaN
            warn("clearance", f"{a} <> {b}: boolean failed")
            continue
        # (round 3) NO DEAD BAND. This used to be `if v > 0.5 ... elif v == 0.0`,
        # so any pair sharing 0 < v <= 0.5 mm3 was neither failed as an overlap
        # nor examined as a tangency - a hole exactly the size of the defects
        # this project keeps shipping. Solids may abut; they may never share
        # volume. Anything above numerical noise is a failure.
        if v > 1e-6:
            hits.append((v, a, b))
        else:
            g = min_gap(bodies[a], bodies[b])
            if g < MIN_CLEARANCE and frozenset({a, b}) not in TOUCH_OK:
                tang.append((g, a, b))
    # (Mk5 round 2) EVERY hit is failed; only the PRINTING is capped. This used
    # to slice [:25] before the fail() call, so overlap number 26 was computed,
    # discarded and never counted - a silent allowlist with a cardinality
    # instead of a name, in the one check whose whole purpose is to have neither.
    for i, (v, a, b) in enumerate(sorted(hits, reverse=True)):
        if i < 25:
            print(f"  OVERLAP  {v:9.2f} mm3   {a} <> {b}")
        fail("clearance", f"{a} <> {b} overlap {v:.2f} mm3")
    if len(hits) > 25:
        print(f"  ... and {len(hits)-25} further overlaps, all failed")
    for i, (g, a, b) in enumerate(sorted(tang)):
        if i < 25:
            print(f"  TANGENT  {g:9.3f} mm    {a} <> {b}")
        fail("clearance", f"{a} <> {b} gap {g:.3f} mm (< {MIN_CLEARANCE})")
    if len(tang) > 25:
        print(f"  ... and {len(tang)-25} further tangencies, all failed")
    if not hits and not tang:
        print("  clean")
    REPORT["clearance"] = dict(overlaps=[(v, a, b) for v, a, b in hits],
                               tangencies=[(g, a, b) for g, a, b in tang])


# ------------------------------- 5. motion sweeps — everything, no exclusions
def check_motion(bodies: dict, travel: float, step: float,
                 sear_release_deg=None) -> None:
    """The full nominal stroke, swept with THE SAME frame map the multi-shot
    check uses. There used to be two definitions of "what moves" in this file -
    a token match on the body name here, and an implicit one inside
    check_multishot - and they disagreed about the drive grip plate, which is
    why one of them called the stroke jammed and the other called it clean.
    `frame_of()` is now the only definition, and both read it."""
    print("")
    print(f"=== 5. MOTION SWEEP (0 to {travel:.3f} mm, step {step} mm, no exclusions) ===")
    # (round 4) THE BY-NAME EXCLUSION OF printed/sear IS GONE, and (Mk5 round 2)
    # so is the by-name definition of what moves. The sear is not part of the
    # frame during the firing stroke: it is ACTUATED, so it is swept POSED AT
    # THE RELEASE ANGLE 5b certified - present in the sweep, under its own name,
    # at the 1e-6 gate, never deleted from the dict.
    moving, statics = _drive_partition(bodies, sear_release_deg)
    if not moving:
        fail("motion", "the frame map puts no body in a moving frame: the "
                       "stroke cannot be swept")
        return
    if sear_release_deg is not None:
        print(f"  (pawl posed at its certified {sear_release_deg:g} deg "
              f"release angle and swept, not excluded)")
    print(f"  moving: {', '.join(f'{k} [{frame_of(k)}]' for k in sorted(moving))}")
    worst: dict[str, tuple[float, float]] = {}
    t = 0.0
    while t <= travel + 1e-9:
        for mname, mbody in moving.items():
            shifted = mbody.moved(cq.Location(cq.Vector(t, 0, 0)))
            for sname, sbody in statics.items():
                v = intersect_volume(shifted, sbody)
                # (round 4) THE 0.5 mm3 DEAD BAND IS GONE. Round 3 removed it
                # from the static check and left it here, so a moving part could
                # plough 0.5 mm3 through a static one at every sample and the
                # sweep would call the stroke clear. The round-3 rule - solids
                # may abut, they may never share volume - applies verbatim to a
                # sweep. The gate is numerical noise, not a jam threshold.
                if v > 1e-6:
                    key = f"{mname} -> {sname}"
                    if key not in worst or v > worst[key][0]:
                        worst[key] = (v, t)
        t += step
    if worst:
        for key, (v, at) in sorted(worst.items(), key=lambda kv: -kv[1][0]):
            print(f"  JAM  {v:9.2f} mm3 at travel {at:6.2f} mm   {key}")
            fail("motion", f"{key}: {v:.2f} mm3 interference at {at:.2f} mm of travel")
    else:
        print("  full stroke clear")
    REPORT["motion"] = {k: dict(volume=v, at_travel=t) for k, (v, t) in worst.items()}


# ---------------------------------------------- 6. physics derived, not read
def check_sear_release(bodies: dict, travel: float, step: float) -> None:
    """The sear is modelled ENGAGED. Firing requires it to rotate clear. Rather
    than excluding it from the sweep (which is exactly what hid Mk3's jam), find
    the smallest release angle at which the whole carriage stroke is clear, and
    fail if no angle under 90 deg works."""
    sear = bodies.get("printed/sear")
    carr = bodies.get("printed/carriage")
    if sear is None or carr is None:
        return
    print("")
    print("=== 5b. SEAR RELEASE (rotation required to clear the stroke) ===")
    px = getattr(M, "SEAR_PIVOT_X", 0.0)
    py = getattr(M, "SEAR_PIVOT_Y", 0.0)
    axis = cq.Vector(0, 1, 0)

    # --- STRENGTHENING (round 2) ---------------------------------------------
    # The pawl was only ever intersected with the carriage as it rotated. A pawl
    # that swings into its OWN pivot tower, into the adapter, or into any other
    # static body binds just as hard, and nothing here could see it. Same
    # rotation loop, every static body, every angle, worst interference per pair.
    # Volume interpenetration between solids is never permitted, so the gate is
    # zero (1e-6 mm3 of numerical noise), not the 0.5 mm3 jam threshold.
    SEAR_STATIC_EPS = 1e-6
    RELEASE_SWEEP_DEG = 90          # servo overtravels; a pawl clear only to the
                                    # release point is a pawl that binds.

    def _rot(deg):
        pz = getattr(M, "SEAR_PIVOT_Z", 0.0)
        r = sear.moved(cq.Location(cq.Vector(-px, -py, -pz)))
        r = r.rotate(cq.Vector(0, 0, 0), axis, deg)
        return r.moved(cq.Location(cq.Vector(px, py, pz)))

    statics = {k: v for k, v in bodies.items()
               if k != "printed/sear"
               and not any(t in k for t in ("carriage", "plunger", "moving"))}
    print(f"  -- sear vs {len(statics)} static bodies through {RELEASE_SWEEP_DEG} deg "
          f"(gate: any shared volume) --")
    per_pair: dict[str, tuple[float, int]] = {}
    swept = {}
    # (round 3) 1 deg steps, not 5: a pawl that fouls between samples fouls.
    for deg in range(0, RELEASE_SWEEP_DEG + 1, 1):
        rot = _rot(deg)
        row = []
        measured = {}
        for sname, sbody in sorted(statics.items()):
            v = intersect_volume(rot, sbody)
            if v != v:
                warn("sear", f"{sname}: boolean failed at {deg} deg")
                continue
            measured[sname] = round(v, 6)
            if v > SEAR_STATIC_EPS:
                row.append(f"{sname}={v:.4f}")
                if sname not in per_pair or v > per_pair[sname][0]:
                    per_pair[sname] = (v, deg)
        swept[deg] = measured
        if row or deg % 5 == 0:
            print(f"  {deg:3d} deg  " + ("  ".join(row) if row else "clear"))
    for sname, (v, deg) in sorted(per_pair.items(), key=lambda kv: -kv[1][0]):
        fail("sear", f"printed/sear <> {sname}: {v:.4f} mm3 interference "
                     f"at {deg} deg of release rotation")
    REPORT["sear_release_statics"] = swept
    # ------------------------------------------------------------------------

    # (round 3) TIGHTENED. The criterion here was `worst <= 0.5` mm3 sampled on a
    # 1.0 mm travel step. That declared 30 deg clear while the pawl was still
    # 0.06967 mm3 of solid inside the carriage at 30 deg; the true clear angle is
    # 31 deg when the stroke is sampled at 0.25 mm. A release angle is only clear
    # if the two solids share NO volume anywhere in the stroke, and the stroke is
    # sampled at the harness's own SWEEP_STEP, not at the --quick step.
    ok_angle = None
    CARR_EPS = 1e-6
    t2_step = 0.25
    for deg in range(0, 95, 1):
        rot = _rot(deg)
        worst = 0.0
        t2 = 0.0
        while t2 <= travel + 1e-9:
            v = intersect_volume(carr.moved(cq.Location(cq.Vector(t2, 0, 0))), rot)
            worst = max(worst, v if v == v else 0.0)
            t2 += t2_step
        if worst <= CARR_EPS:
            ok_angle = deg
            break
        if deg % 10 == 0:
            print(f"  {deg:3d} deg -> worst carriage interference {worst:8.2f} mm3")
    if ok_angle is None:
        fail("sear", "no release angle under 90 deg clears the carriage stroke")
        print("  NO ANGLE CLEARS - the pawl cannot get out of its own way")
    else:
        print(f"  clears at {ok_angle} deg of release rotation")
        REPORT["sear_release_deg"] = ok_angle
        if ok_angle > 45:
            warn("sear", f"needs {ok_angle} deg of release travel - check the servo throw")


def _sear_rotated(sear, deg: float):
    """Rotate a world-space sear about its own pivot axis (+Y). Positive is the
    release direction, matching check_sear_release; negative is forward, toward
    deeper engagement."""
    px = getattr(M, "SEAR_PIVOT_X", 0.0)
    py = getattr(M, "SEAR_PIVOT_Y", 0.0)
    pz = getattr(M, "SEAR_PIVOT_Z", 0.0)
    r = sear.moved(cq.Location(cq.Vector(-px, -py, -pz)))
    r = r.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), deg)
    return r.moved(cq.Location(cq.Vector(px, py, pz)))


def check_sear_rest_pose(bodies: dict) -> None:
    """WHERE DOES THE PAWL ACTUALLY SIT?

    Every other sear check in this file starts from the pose the model happens to
    draw and calls it 0 deg. Nothing has ever asked whether the pawl STAYS there.
    A pawl on a pin with no forward stop is free to droop until some face happens
    to touch, and the tooth/lug engagement is only worth what it is at THAT angle
    - not at the angle the CAD file was authored in.

    So: (a) do not assume 0. Rotate the pawl forward (negative) from 0 until it
    first shares volume with a static body, and bisect to 0.01 deg; the deepest
    still-clear angle is the equilibrium. (b) at that angle, advance the carriage
    forward from cocked until the tooth blocks it, bisect the first blocking
    offset to 0.001 mm, and measure the bearing patch by nudging past contact.
    (c) gate on both: the cocked carriage may not creep, and the patch that takes
    the spring load must be a real face, not a corner."""
    sear = bodies.get("printed/sear")
    carr = bodies.get("printed/carriage")
    if sear is None or carr is None:
        return
    print("")
    print("=== 5c. SEAR REST POSE (equilibrium measured, not assumed) ===")
    EPS = 1e-6
    MAX_FREE_ADVANCE = 0.02        # mm of creep before the tooth bites
    MIN_BEARING_AREA = 20.0        # mm2 carrying the full spring load
    NUDGE = 0.10                   # mm past contact, to turn a face into a volume
    statics = {k: v for k, v in bodies.items()
               if k != "printed/sear"
               and not any(t in k for t in ("carriage", "plunger", "moving"))}

    def blocked(deg: float):
        rot = _sear_rotated(sear, deg)
        worst, who = 0.0, None
        for sname, sbody in sorted(statics.items()):
            v = intersect_volume(rot, sbody)
            if v == v and v > worst:
                worst, who = v, sname
        return worst, who

    equilibrium = None
    v0, who0 = blocked(0.0)
    if v0 > EPS:
        print(f"  0 deg is NOT clear: {v0:.6f} mm3 shared with {who0}")
        fail("rest", f"sear shares {v0:.6f} mm3 with {who0} at 0 deg - the drawn "
                     f"pose is inside a static body, so there is no rest pose")
    else:
        hi, lo, found = 0.0, 0.0, False     # hi: deepest clear, lo: first blocked
        d = -0.05
        while d >= -20.0:
            v, _ = blocked(d)
            if v > EPS:
                lo, found = d, True
                break
            hi = d
            d = d * 2.0 if d > -1.0 else d - 1.0
        if not found:
            print("  UNDEFINED: the pawl rotates 20 deg forward without touching "
                  "anything - nothing defines where it rests")
            fail("rest", "no static body stops the sear within 20 deg of forward "
                         "rotation: the rest pose is an accident, not a feature")
        else:
            while (hi - lo) > 0.01:
                mid = 0.5 * (hi + lo)
                v, _ = blocked(mid)
                if v > EPS:
                    lo = mid
                else:
                    hi = mid
            equilibrium = hi
            _, stopper = blocked(lo)
            print(f"  equilibrium angle  {equilibrium:+.3f} deg  "
                  f"(forward rotation stopped by {stopper})")

    free, area = float("nan"), float("nan")
    if equilibrium is not None:
        rot = _sear_rotated(sear, equilibrium)
        base = bodies.get("printed/baseplate")

        # (round 4) THE PATCH IS GATED ON THE WORST OF THE LATERAL PLAY BAND.
        # The nominal pose is not the pose the part is in. The carriage is a
        # sliding block between two rails, and the clearance those rails were
        # drawn with is real travel the carriage can take. Measuring the bearing
        # patch only at dy = 0 is the same class of error as measuring one pose
        # instead of a sweep: at nominal the lug sat fully on the tooth for
        # 22 mm2, and 0.5 mm of the play the rails already permit walked the
        # lug off the tooth's inboard end and dropped the patch to 16 mm2 -
        # below this check's own MIN_BEARING_AREA - with nothing to report it.
        #
        # The play is MEASURED, not declared: slide the carriage sideways until
        # it shares volume with the baseplate and bisect that limit to 0.001 mm,
        # in each direction. Then the patch is measured at -y limit, nominal and
        # +y limit, and the gate takes the WORST of the three.
        def play_limit(sign):
            if base is None:
                return 0.0
            lo_p, hi_p, d = 0.0, None, 0.05
            while d <= 6.0 + 1e-9:
                v = intersect_volume(
                    carr.moved(cq.Location(cq.Vector(0, sign * d, 0))), base)
                if v == v and v > EPS:
                    hi_p = d
                    break
                lo_p = d
                d += 0.05
            if hi_p is None:
                return lo_p
            while (hi_p - lo_p) > 0.001:
                mid = 0.5 * (hi_p + lo_p)
                v = intersect_volume(
                    carr.moved(cq.Location(cq.Vector(0, sign * mid, 0))), base)
                if v == v and v > EPS:
                    hi_p = mid
                else:
                    lo_p = mid
            return lo_p

        play_m, play_p = play_limit(-1), play_limit(+1)
        print(f"  lateral play measured in the rails    -{play_m:.3f} .. "
              f"+{play_p:.3f} mm")
        REPORT["carriage_lateral_play_mm"] = [-play_m, play_p]

        def shared(t, dy=0.0):
            v = intersect_volume(
                carr.moved(cq.Location(cq.Vector(t, dy, 0))), rot)
            return 0.0 if v != v else v

        worst_free, worst_area, worst_at = float("-inf"), float("inf"), None
        for label, dy in (("-y limit", -play_m), ("nominal ", 0.0),
                          ("+y limit", play_p)):
            if shared(0.0, dy) > EPS:
                v0 = shared(0.0, dy)
                print(f"  {label}: tooth and lug already share {v0:.6f} mm3 at rest")
                fail("rest", f"at the rest angle, {label.strip()} of the lateral "
                             f"play band, the tooth is {v0:.6f} mm3 INSIDE the "
                             f"carriage lug - engagement by interpenetration")
                continue
            lo_t, hi_t, t = 0.0, None, 0.0
            while t <= 3.0 + 1e-9:
                if shared(t, dy) > EPS:
                    hi_t = t
                    break
                lo_t = t
                t += 0.05
            if hi_t is None:
                print(f"  {label}: the tooth NEVER blocks the carriage in 3 mm")
                fail("rest", f"at the rest angle, {label.strip()} of the lateral "
                             f"play band, the tooth does not block the carriage "
                             f"within 3 mm: nothing holds the cocked spring")
                if 0.0 < worst_area:
                    worst_area, worst_at = 0.0, label.strip()
                continue
            while (hi_t - lo_t) > 0.001:
                mid = 0.5 * (hi_t + lo_t)
                if shared(mid, dy) > EPS:
                    hi_t = mid
                else:
                    lo_t = mid
            f_i = lo_t
            a_i = shared(f_i + NUDGE, dy) / NUDGE
            print(f"  {label} (dy {dy:+.3f} mm)  free advance {f_i:.4f} mm   "
                  f"bearing patch {a_i:.2f} mm2")
            worst_free = max(worst_free, f_i)
            if a_i < worst_area:
                worst_area, worst_at = a_i, label.strip()
        free, area = worst_free, worst_area
        if free > float("-inf"):
            print(f"  WORST over the play band: free advance {free:.4f} mm, "
                  f"bearing patch {area:.2f} mm2 ({worst_at})")
            if free > MAX_FREE_ADVANCE:
                fail("rest", f"carriage creeps {free:.4f} mm at the rest angle "
                             f"before the tooth bites, worst over the measured "
                             f"lateral play band (> {MAX_FREE_ADVANCE})")
            if area < MIN_BEARING_AREA:
                fail("rest", f"tooth/lug bearing patch falls to {area:.2f} mm2 at "
                             f"the {worst_at} of the measured lateral play band "
                             f"(< {MIN_BEARING_AREA}); the gate is the worst of "
                             f"the band, not the nominal pose")
    REPORT["sear_rest_pose"] = dict(equilibrium_deg=equilibrium,
                                    free_advance_mm=free, bearing_area_mm2=area)


# ------------------------------------------- 5d. the return (cocking) stroke
# A shooter that fires once is a prop. Every check before this one looks at the
# mechanism going FORWARD; nothing has ever asked what happens when a hand pushes
# the carriage back to re-cock it. The pawl sits in the way, and whether the
# carriage can get past it is a property of the SHAPE of the two faces that meet,
# not of the fact that a pawl exists.
#
# Named constants, stated rather than buried:
PETG_FRICTION_MU = 0.35     # PETG on PETG, dry, printed faces. Literature for
                            # PETG-PETG sliding sits around 0.3-0.4; 0.35 is the
                            # middle of it and the number the ramp is derived from.
CAM_SAFETY = 1.5            # required tan(ramp) / mu before the ramp is called
                            # self-camming
MIN_RAMP_NORMAL_DEG = 25.0  # a contact normal this far off the travel axis is a
                            # ramp; 0 deg is a wall
COCK_SWEEP_DEG = 90.0       # how far the pawl is allowed to be lifted while
                            # looking for a clearing angle
CAM_PROBE_DEG = 0.25        # rotate back this far from the clearing angle to
                            # make the contacting faces into a thin sliver


def _inside(solid, p, r=0.02) -> bool:
    """Is a point inside a solid? Answered with a tiny box boolean, because that
    is the only test that is true for the OCCT solid rather than for a bounding
    approximation of it."""
    try:
        box = cq.Solid.makeBox(2 * r, 2 * r, 2 * r,
                               cq.Vector(p.x - r, p.y - r, p.z - r))
        return vol(solid.intersect(box)) > 0.25 * (2 * r) ** 3
    except Exception:
        return False


def _contact_normal_deg(a, b, axis=cq.Vector(1, 0, 0), travel=None):
    """THE CAM ANGLE OF THE FACES THAT ACTUALLY MEET.

    (round 5) `travel`, when given, is the unit direction the MOVING body `b`
    is travelling, and it removes faces that cannot carry a blocking force.
    Without it this function scored every face of the sliver, including faces
    on the moving body's TRAILING side - faces that are running away from
    whatever they are near and can never push on it.

    THE MEASUREMENT THAT FORCED THIS. On the cocking stroke (carriage running
    -X) the pawl's last contact before it drops in behind the lug is at
    (22.39, -20.00, 23.13): the tooth's rear face sliding down the LUG'S FRONT
    FACE, whose outward normal is +X. The carriage is moving -X, so that face is
    moving away from the tooth - it is the face the tooth has just cleared. The
    old scoring called its 0.00 deg normal "a wall, not a ramp" and failed the
    cocking stroke on a contact that separates. The three faces that actually
    carry the lift at that station are the lug's top (90.00 deg) and its top-front
    chamfer (60.20 deg); the tooth rides those.

    Blocking, stated once: a face on the STATIC body blocks when its outward
    normal opposes the travel direction (n . travel < 0); a face on the MOVING
    body blocks when it LEADS (n . travel > 0). Ownership is decided by probing
    just outside the sliver along the outward normal - a point that is still
    inside `b` puts the face on `a`, and vice versa. A coincident face, which is
    outside both, is kept, because a face that cannot be attributed is not a
    face that may be discarded.

    Given two solids overlapping by a thin sliver, every face of that sliver lies
    on a face of one of the two parents - those are the surfaces in contact. For
    each, take the outward normal (the side of the face that leaves the sliver)
    and measure its angle to the travel axis. A face whose normal is ALONG the
    travel axis is a wall: it can only stop the carriage. A face whose normal is
    off the axis is a ramp: the carriage's own motion has a component up it.

    Returns the MINIMUM such angle over the faces that carry real area, because
    the flattest face in the contact is the one that decides whether the carriage
    jams. Faces below 20% of the largest face's area are ignored as slivers of
    the sliver, not as contact.
    """
    try:
        inter = a.intersect(b)
    except Exception:
        return None, None
    faces = []
    for f in inter.Faces():
        try:
            ar = f.Area()
            c = f.Center()
            n = f.normalAt(c)
        except Exception:
            continue
        if ar <= 1e-9:
            continue
        faces.append((ar, n, c))
    if not faces:
        return None, None
    # ---- keep only the faces that can carry a blocking force ---------------
    keep = []
    for ar, n, c in faces:
        out = n
        try:
            if _inside(inter, c + n.multiply(0.02)):
                out = n.multiply(-1)
        except Exception:
            pass
        if travel is not None:
            p = c + out.multiply(0.02)
            try:
                in_b = _inside(b, p)
                in_a = _inside(a, p)
            except Exception:
                in_b = in_a = False
            dot = out.x * travel.x + out.y * travel.y + out.z * travel.z
            if in_b and not in_a:            # the face belongs to the STATIC a
                if dot >= -1e-9:             # it faces away from the oncoming b
                    continue
            elif in_a and not in_b:          # the face belongs to the MOVING b
                if dot <= 1e-9:              # it is a trailing face: it recedes
                    continue
            # neither, or both: unattributable, so it is kept
        keep.append((ar, out))
    if not keep:
        return None, None
    mx = max(k[0] for k in keep)
    best_ang, best_area = None, None
    for ar, out in keep:
        if ar < 0.20 * mx:
            continue
        d = abs(out.x * axis.x + out.y * axis.y + out.z * axis.z)
        ang = math.degrees(math.acos(max(0.0, min(1.0, d))))
        if best_ang is None or ang < best_ang:
            best_ang, best_area = ang, ar
    return best_ang, best_area


def check_cocking_stroke(bodies: dict, travel: float, step: float) -> None:
    """CAN IT BE RE-COCKED, BY ONE HAND, WITHOUT TOUCHING THE PAWL?

    Start at the fired offset and drive the carriage back toward 0 in `step`
    increments with the pawl at the equilibrium angle 5c MEASURED (not at an
    assumed 0). Where the carriage shares volume with the pawl, do not stop -
    find, by bisection to 0.01 deg, the smallest lift that clears that step, and
    measure the cam angle of the faces doing the blocking.

    Three gates, all of which the geometry must satisfy at EVERY step:
      (a) the lift the cocking stroke demands never exceeds the lift the firing
          release demands. A pawl that must travel further to cock than to fire
          cannot be cocked by the mechanism that fires it.
      (b) every blocking contact is a ramp, not a wall: the contact normal is at
          least MIN_RAMP_NORMAL_DEG off the travel axis.
      (c) the contact is SELF-CAMMING: tan(cam angle) > PETG_FRICTION_MU with
          CAM_SAFETY margin, so the hand pushing the carriage rearward lifts the
          pawl by itself and no second hand is needed on the tail.
    """
    sear = bodies.get("printed/sear")
    carr = bodies.get("printed/carriage")
    if sear is None or carr is None:
        return
    print("")
    print(f"=== 5d. COCKING STROKE ({travel:.3f} mm back to 0, step {step} mm) ===")
    EPS = 1e-6
    eq = (REPORT.get("sear_rest_pose") or {}).get("equilibrium_deg")
    if eq is None:
        fail("cock", "no measured rest pose: the cocking stroke cannot be driven "
                     "from an equilibrium that 5c could not find")
        return
    release = REPORT.get("sear_release_deg")
    if release is None:
        fail("cock", "no certified release angle: gate (a) has nothing to compare "
                     "the cocking lift against")
        return
    print(f"  pawl at the MEASURED equilibrium {eq:+.3f} deg; "
          f"release lift for comparison {release:g} deg")
    print(f"  mu = {PETG_FRICTION_MU} (PETG on PETG), camming margin required "
          f"{CAM_SAFETY}x  ->  ramp >= {math.degrees(math.atan(PETG_FRICTION_MU * CAM_SAFETY)):.2f} deg")

    def shared(t, deg):
        v = intersect_volume(carr.moved(cq.Location(cq.Vector(t, 0, 0))),
                             _sear_rotated(sear, deg))
        return 0.0 if v != v else v

    peak_lift, peak_at = 0.0, None
    min_ramp, min_ramp_at, min_ramp_lift = 180.0, None, None
    n_blocked, n_unliftable = 0, 0
    rows = []
    t = travel
    while t >= -1e-9:
        v0 = shared(t, eq)
        if v0 <= EPS:
            t -= step
            continue
        n_blocked += 1
        lo_a, hi_a, a = eq, None, eq
        while a <= eq + COCK_SWEEP_DEG:
            if shared(t, a) <= EPS:
                hi_a = a
                break
            lo_a = a
            a += 1.0
        if hi_a is None:
            n_unliftable += 1
            rows.append((t, float("inf"), None, v0))
            t -= step
            continue
        while (hi_a - lo_a) > 0.01:
            mid = 0.5 * (hi_a + lo_a)
            if shared(t, mid) <= EPS:
                hi_a = mid
            else:
                lo_a = mid
        lift = hi_a - eq
        probe = max(eq, hi_a - CAM_PROBE_DEG)
        # the carriage is running -X on the cocking stroke, and saying so is
        # what stops a face it has already passed from being scored as a wall.
        ang, _ = _contact_normal_deg(
            _sear_rotated(sear, probe),
            carr.moved(cq.Location(cq.Vector(t, 0, 0))),
            travel=cq.Vector(-1, 0, 0))
        rows.append((t, lift, ang, v0))
        if lift > peak_lift:
            peak_lift, peak_at = lift, t
        if ang is not None and ang < min_ramp:
            min_ramp, min_ramp_at, min_ramp_lift = ang, t, lift
        t -= step

    if n_blocked == 0:
        print("  the pawl never touches the carriage on the way back")
        fail("cock", "nothing blocks the carriage anywhere in the return stroke: "
                     "the pawl cannot be re-engaging, so the mechanism has no "
                     "second shot")
        REPORT["cocking"] = dict(blocked_steps=0)
        return

    shown = 0
    for t_i, lift_i, ang_i, v_i in rows:
        if shown < 8 or lift_i >= peak_lift - 1e-9 or (
                ang_i is not None and ang_i <= min_ramp + 1e-9):
            la = "NO LIFT CLEARS" if lift_i == float("inf") else f"{lift_i:6.2f} deg"
            aa = "  n/a" if ang_i is None else f"{ang_i:6.2f} deg"
            print(f"  offset {t_i:6.2f} mm  overlap {v_i:8.3f} mm3  "
                  f"lift {la}  cam {aa}")
            shown += 1
    if shown < len(rows):
        print(f"  ... {len(rows) - shown} further blocked steps not listed")

    cam_margin = (math.tan(math.radians(min_ramp)) / PETG_FRICTION_MU
                  if min_ramp < 89.999 else float("inf"))
    print(f"  PEAK required lift      {peak_lift:.2f} deg at offset "
          f"{peak_at if peak_at is None else round(peak_at, 2)} mm "
          f"(release lift is {release:g} deg)")
    print(f"  MINIMUM ramp angle      {min_ramp:.2f} deg at offset "
          f"{min_ramp_at if min_ramp_at is None else round(min_ramp_at, 2)} mm")
    print(f"  camming margin          {cam_margin:.3f}x "
          f"(tan {min_ramp:.2f} deg / mu {PETG_FRICTION_MU})")
    REPORT["cocking"] = dict(blocked_steps=n_blocked, peak_lift_deg=peak_lift,
                             peak_lift_at_mm=peak_at, min_ramp_deg=min_ramp,
                             min_ramp_at_mm=min_ramp_at,
                             cam_margin=cam_margin,
                             unliftable_steps=n_unliftable,
                             release_deg=release, mu=PETG_FRICTION_MU)

    # (a)
    if n_unliftable:
        fail("cock", f"{n_unliftable} step(s) of the return stroke cannot be "
                     f"cleared by any lift under {COCK_SWEEP_DEG:g} deg: the "
                     f"carriage cannot be pushed back past the pawl at all")
    if peak_lift > release + 1e-9:
        fail("cock", f"cocking needs {peak_lift:.2f} deg of pawl lift at offset "
                     f"{peak_at:.2f} mm but firing only needs {release:g} deg: "
                     f"the pawl must travel further to cock than to fire")
    # (b)
    if min_ramp < MIN_RAMP_NORMAL_DEG:
        fail("cock", f"blocking contact at offset {min_ramp_at:.2f} mm has its "
                     f"normal {min_ramp:.2f} deg off the travel axis "
                     f"(< {MIN_RAMP_NORMAL_DEG}): that face is a wall, not a "
                     f"ramp - the carriage stops dead against it")
    # (c)
    if cam_margin < CAM_SAFETY:
        need = math.degrees(math.atan(PETG_FRICTION_MU * CAM_SAFETY))
        fail("cock", f"camming margin {cam_margin:.3f}x < {CAM_SAFETY}x: with "
                     f"mu = {PETG_FRICTION_MU} a {min_ramp:.2f} deg ramp does not "
                     f"lift the pawl on its own (needs >= {need:.2f} deg), so "
                     f"re-cocking takes a second hand on the tail")


# ===================================================================== Mk5
# CHECKS FOR THE MULTI-SHOT MECHANISM.
#
# These checks were written and committed while the defects they look for were
# STILL PRESENT in the model, and were run against the unchanged Mk4 to confirm
# each one fires. That order is deliberate. Four revisions of this project
# shipped with a green harness and unbuildable parts, and the most recent cause
# was a check that could not see the defect. A check authored after the fix,
# against the fixed model, is a check that has never been observed to fail - it
# is a hypothesis, not an instrument.
#
# Measured on the UNCHANGED Mk4 at the moment of writing:
#   check_servo_torque      637 N.mm to release the sear vs 150 N.mm available
#   check_multishot         shot 2 delivers 0.79 mL, shot 3 delivers 0.00 mL
#   check_spring_buckling   slenderness 6.48 at 44% deflection, pilot 20%
#   check_wrist_profile     34.0 mm of stack against a 25 mm target
#   check_recock_budget     no recock mechanism declared at all
#   check_one_way_grip      no grip in the assembly at all
#
# Every one of them FAILS when the body it needs is absent, rather than
# skipping. That is the rule the `if hasattr(M, "mockups")` guard broke.

SERVO_DUTY_FRACTION = 1.0 / 3.0   # a third of stall is the honest continuous ceiling
SERVO_TORQUE_MARGIN = 1.5         # required available/needed before a linkage is credited
MAX_WRIST_PROFILE_MM = 25.0       # the brief's envelope, measured over EVERY body
RECOCK_MARGIN = 1.2               # required servo work / spring PE
# (round 4) RATCHET_EFFICIENCY is gone with the ratchet. The single-sweep
# winch's losses are the model's own WINCH_EFFICIENCY, read off the model in
# check_recock_budget, because they belong to the drum that is drawn.
MIN_SHOT_FRACTION = 0.90          # a shot delivering less than this is not a shot
MIN_ANCHOR_BEARING_MM = 3.0       # engaged Y a recock anchor must have to be a bearing
PILOT_COVERAGE = 0.90             # fraction of the compressed coil that must be piloted

# Shigley's spring buckling constants for steel (E = 203.4 GPa, G = 79.3 GPa).
_SPRING_E, _SPRING_G = 203.4e3, 79.3e3
_BUCK_C1 = _SPRING_E / (2.0 * (_SPRING_E - _SPRING_G))
_BUCK_C2 = 2.0 * math.pi ** 2 * (_SPRING_E - _SPRING_G) / (2.0 * _SPRING_G + _SPRING_E)


def _find(bodies: dict, *tokens: str):
    """First body whose key contains every token. Name-based LOOKUP is fine;
    name-based EXCLUSION from a sweep is what this harness forbids."""
    for k in sorted(bodies):
        low = k.lower()
        if all(t.lower() in low for t in tokens):
            return k, bodies[k]
    return None, None


def _find_all(bodies: dict, *tokens: str):
    return {k: v for k, v in sorted(bodies.items())
            if all(t.lower() in k.lower() for t in tokens)}


def _long_axis(s):
    b = bb(s)
    dims = {"x": b.xlen, "y": b.ylen, "z": b.zlen}
    return max(dims, key=dims.get)


def _axis_cyl(axis, length, r, x, y, z):
    d = {"x": cq.Vector(1, 0, 0), "y": cq.Vector(0, 1, 0), "z": cq.Vector(0, 0, 1)}[axis]
    return cq.Solid.makeCylinder(r, length, cq.Vector(x, y, z), d)


def _spring_state(bodies: dict):
    """MEASURE the spring, do not read it.

    Defect 6 of the brief - the spring force being 24% above every downstream
    number - existed because the model computed the force from the length it
    MEANT the spring to sit at, while the geometry seated it 2 mm further
    forward. So the length here comes from the spring body's own bounding box
    in assembly space, and the force from that length and the model's rate.
    """
    k, spring = _find(bodies, "spring")
    if spring is None:
        return None
    b = bb(spring)
    axis = _long_axis(spring)
    L_cocked = {"x": b.xlen, "y": b.ylen, "z": b.zlen}[axis]
    cross = sorted([b.xlen, b.ylen, b.zlen])[:2]
    od = sum(cross) / 2.0
    free = float(getattr(M, "SPRING_FREE_LEN", 0.0))
    rate = float(getattr(M, "SPRING_RATE_N_MM", 0.0))
    wire = float(getattr(M, "SPRING_WIRE", 0.0))
    return dict(key=k, body=spring, axis=axis, L_cocked=L_cocked, od=od,
                wire=wire, free=free, rate=rate,
                deflection=max(0.0, free - L_cocked),
                force_N=max(0.0, free - L_cocked) * rate)


# ------------------------------------------------------- 7. spring stability
def check_spring_buckling(bodies: dict) -> None:
    """A compression spring longer than about four coil diameters, deflected
    hard and guided by nothing, does not compress - it bows sideways and jams
    against whatever is beside it. Mk4's is 6.48 diameters at 44% deflection
    with an 8 mm stub for a pilot on a 25.6 mm compressed coil.

    Two gates. The slenderness gate is Shigley's absolute-stability criterion,
    evaluated at alpha = 1.0 (both ends squared and guided) - the most
    FAVOURABLE real end condition, so the verdict is not an artefact of a
    pessimistic assumption. The pilot gate is geometric: sample the spring's own
    inner bore along its axis and ask which fraction of it is occupied by some
    other body. A pilot that stops short is a pilot only where it reaches."""
    print("\n=== 7. SPRING BUCKLING (slenderness measured, pilot measured) ===")
    st = _spring_state(bodies)
    if st is None:
        fail("spring", "no spring body in the assembly: a spring-driven "
                       "mechanism with no spring in make_mockups() cannot be "
                       "checked for buckling, and absence is not a pass")
        return
    d_mean = st["od"] - st["wire"]
    if d_mean <= 0 or st["free"] <= 0:
        fail("spring", f"spring geometry incoherent: OD {st['od']:.2f}, wire "
                       f"{st['wire']:.2f}, free length {st['free']:.2f}")
        return
    lam = st["free"] / d_mean
    ratio = st["deflection"] / st["free"]
    if lam ** 2 <= _BUCK_C2:
        crit = 1.0
    else:
        crit = _BUCK_C1 * (1.0 - math.sqrt(1.0 - _BUCK_C2 / lam ** 2))
    print(f"  {st['key']}")
    print(f"  free {st['free']:.2f} mm  compressed {st['L_cocked']:.2f} mm  "
          f"mean coil dia {d_mean:.2f} mm  force {st['force_N']:.2f} N")
    print(f"  slenderness L0/D = {lam:.2f}   deflection {ratio*100:.1f}% of free "
          f"length   critical {crit*100:.1f}%")

    # --- the pilot, measured along the axis ---------------------------------
    b = bb(st["body"])
    ax = st["axis"]
    lo, hi = {"x": (b.xmin, b.xmax), "y": (b.ymin, b.ymax),
              "z": (b.zmin, b.zmax)}[ax]
    ctr = b.center
    r_bore = max(0.05, st["od"] / 2.0 - st["wire"])
    others = {k: v for k, v in bodies.items() if k != st["key"]}
    N = 40
    disc_t = (hi - lo) / N
    occupied = 0
    for i in range(N):
        c = lo + i * disc_t
        pos = {"x": (c, ctr.y, ctr.z),
               "y": (ctr.x, c, ctr.z),
               "z": (ctr.x, ctr.y, c)}[ax]
        disc = _axis_cyl(ax, disc_t, r_bore, *pos)
        for ob in others.values():
            v = intersect_volume(disc, ob)
            if v == v and v > 1e-6:
                occupied += 1
                break
    coverage = occupied / float(N)
    print(f"  pilot coverage inside the coil bore (r {r_bore:.2f} mm): "
          f"{coverage*100:.0f}% of the compressed length")
    REPORT["spring_buckling"] = dict(slenderness=lam, deflection_ratio=ratio,
                                     critical_ratio=crit, force_N=st["force_N"],
                                     pilot_coverage=coverage)
    unstable = ratio > crit
    if unstable and coverage < PILOT_COVERAGE:
        fail("spring", f"spring is unstable (deflected {ratio*100:.1f}% against a "
                       f"{crit*100:.1f}% critical ratio at slenderness {lam:.2f}) "
                       f"and only {coverage*100:.0f}% of its compressed length is "
                       f"piloted (needs {PILOT_COVERAGE*100:.0f}%): it will bow "
                       f"sideways instead of pushing")
    elif unstable:
        print("  unstable but fully piloted - the pilot is what makes it legal")


# ----------------------------------------------------------- 8. servo torque
def check_servo_torque(bodies: dict) -> None:
    """THE CHECK THAT DID NOT EXIST.

    There was not one load, stress or torque check in this harness's first
    1000 lines, which is why 'the servo cannot open the sear' survived four
    revisions. The release moment is computed here from the model's own pivot
    and contact coordinates and from the spring force MEASURED by
    _spring_state - not from any number the model declares about itself.

        M_hold = |r_z| * F          the spring's moment about the pivot
        M_fric = mu * F * |r_x|     sliding the tooth out from under the load
        M_pin  = mu * F * r_pin     journal drag at the pivot bore

    Mechanical advantage is credited ONLY where the model declares the linkage
    that provides it. An undrawn linkage has none.
    """
    print("\n=== 8. SERVO TORQUE (release moment derived from geometry) ===")
    st = _spring_state(bodies)
    if st is None:
        fail("servo", "no spring body: the release moment cannot be derived")
        return
    F = st["force_N"]
    print(f"  spring force MEASURED from its compressed length: {F:.2f} N")

    servos = _find_all(bodies, "servo")
    if not servos:
        fail("servo", "no servo body anywhere in the assembly. The mechanism is "
                      "described as servo-actuated and nothing in printed_parts "
                      "or make_mockups() is a servo, so no mount, horn, pushrod "
                      "or linkage can be checked for fit, reach or torque")
    else:
        print(f"  servo bodies present: {', '.join(sorted(servos))}")

    stall = float(getattr(M, "SERVO_STALL_N_MM", 0.0))
    if stall <= 0:
        fail("servo", "SERVO_STALL_N_MM is not declared: there is no torque "
                      "budget to check anything against")
        return
    usable = stall * SERVO_DUTY_FRACTION
    print(f"  stall {stall:.0f} N.mm, usable at {SERVO_DUTY_FRACTION:.2f} duty "
          f"{usable:.0f} N.mm")

    mu = float(getattr(M, "SEAR_FRICTION_MU", getattr(M, "RAMP_MU", 0.35)))
    r_pin = float(getattr(M, "SEAR_PIN_R", 1.75))
    try:
        r_x = M.SEAR_CONTACT_X - M.SEAR_PIVOT_X
        r_z = M.SEAR_CONTACT_Z - M.SEAR_PIVOT_Z
    except AttributeError:
        fail("servo", "sear pivot/contact coordinates are not declared: the "
                      "release moment cannot be derived from geometry")
        return
    m_hold = abs(r_z) * F
    m_fric = mu * F * abs(r_x)
    m_pin = mu * F * r_pin

    # --- (round 5) THE ENGAGEMENT SPRING IS PART OF THE RELEASE MOMENT -------
    # Architecture B buys its collapse of the holding moment by making the sear
    # NOT self-holding, and a sear that is not self-holding is held by a spring.
    # That spring resists release, so the servo pays for it, and it is charged
    # at the angle the release actually reaches - the angle check_sear_release
    # certified from the drawn geometry - not at first movement.
    #
    # This term can only make the check harder. It is derived from the model's
    # declared rate and preload, and if the model declares an architecture-B
    # geometry (|r_z| small) without declaring the spring that architecture
    # requires, that is a mechanism with nothing holding it closed and it fails
    # here rather than passing on the strength of the term it left out.
    B_RZ_LIMIT = 1.5        # mm; at or under this the sear is not self-holding
    rate = getattr(M, "SEAR_SPRING_RATE_N_MM_PER_DEG", None)
    preload = getattr(M, "SEAR_SPRING_PRELOAD_N_MM", None)
    spring_bodies = [k for k in bodies
                     if "sear" in k and "spring" in k or "torsion" in k]
    rel_deg = REPORT.get("sear_release_deg")
    if rel_deg is None:
        rel_deg = float(getattr(M, "SEAR_RELEASE_SWEEP_DEG", 45.0))
        print(f"  no certified release angle yet; charging the spring at the "
              f"model's own {rel_deg:.1f} deg")
    if rate is None or preload is None:
        m_spring = 0.0
        if abs(r_z) <= B_RZ_LIMIT:
            fail("servo", f"|r_z| = {abs(r_z):.2f} mm is architecture B - the "
                          f"load no longer holds the sear closed - but the model "
                          f"declares no SEAR_SPRING_PRELOAD_N_MM / "
                          f"SEAR_SPRING_RATE_N_MM_PER_DEG. A sear that is not "
                          f"self-holding and has no engagement spring is not "
                          f"closed by anything")
    else:
        m_spring = float(preload) + float(rate) * float(rel_deg)
        print(f"  engagement spring {preload:.1f} N.mm preload + {rate:.3f} "
              f"N.mm/deg x {rel_deg:.0f} deg = {m_spring:.1f} N.mm")
        if not spring_bodies:
            fail("servo", "SEAR_SPRING_PRELOAD_N_MM is declared but no sear "
                          "engagement-spring body exists in printed_parts or "
                          "make_mockups(): a spring that is only a number "
                          "cannot be checked for fit, and this is exactly the "
                          "starving that got Mk4 rejected")
        else:
            print(f"  spring bodies present: {', '.join(sorted(spring_bodies))}")
    m_req = m_hold + m_fric + m_pin + m_spring
    print(f"  r_x {r_x:+.2f} mm  r_z {r_z:+.2f} mm  mu {mu}")
    print(f"  holding {m_hold:.1f} + friction {m_fric:.1f} + pin drag "
          f"{m_pin:.1f} + spring {m_spring:.1f}  =  {m_req:.1f} N.mm at the "
          f"sear pivot")

    arm = float(getattr(M, "SEAR_ACTUATION_ARM_MM", getattr(M, "SEAR_TAIL_LEN", 0.0)))
    horn = float(getattr(M, "SERVO_HORN_R_MM", 0.0))
    if horn > 0 and arm > 0:
        adv = arm / horn
        note = f"horn {horn:.1f} mm driving a {arm:.1f} mm sear arm"
    else:
        adv = 1.0
        note = ("no SERVO_HORN_R_MM declared - no mechanical advantage credited, "
                "because an undrawn linkage has none")
    t_servo = m_req / adv
    margin = usable / t_servo if t_servo > 0 else float("inf")
    print(f"  linkage: {note}  ->  advantage {adv:.2f}")
    print(f"  torque demanded at the servo shaft {t_servo:.1f} N.mm vs "
          f"{usable:.0f} N.mm usable   margin {margin:.2f}x")
    REPORT["servo_torque"] = dict(spring_force_N=F, m_hold=m_hold, m_fric=m_fric,
                                  m_pin=m_pin, m_engagement_spring=m_spring,
                                  release_deg=rel_deg, m_required=m_req,
                                  advantage=adv, servo_torque=t_servo,
                                  usable=usable, margin=margin)
    if margin < SERVO_TORQUE_MARGIN:
        fail("servo", f"releasing the sear needs {t_servo:.0f} N.mm at the servo "
                      f"shaft but only {usable:.0f} N.mm is available "
                      f"({margin:.2f}x, needs {SERVO_TORQUE_MARGIN}x): the servo "
                      f"cannot open the sear")


# ---------------------------------------------------------- 9. one-way grip
def check_one_way_grip(bodies: dict) -> None:
    """Does anything hold the plunger forward while the drive slides back?

    A tilting-plate grip is a bore of diameter D on a rod of diameter d in a
    plate of thickness t. Tilted by alpha, the bore's projected aperture across
    the rod is D*cos(alpha) - t*sin(alpha) = R*cos(alpha + phi), and the plate
    bites when that falls to d. The root is

        alpha_root = acos(d/R) - phi ,  R = hypot(D,t) ,  phi = atan(t/D)

    which for this pair is 8.715 deg. Round 1 of Mk5 checked the declared tilt
    against `atan((D-d)/t)` - the SAME expression the model used to choose the
    tilt - so the gate read `x >= x` and had no failing state at all. It is a
    tautology of the kind this harness exists to remove, and it sat directly
    under the multi-shot claim. R and phi are re-derived here from the model's
    D, t and d; nothing about the angle is read from the model.

    NOTE ON WHAT THIS VERDICT NO LONGER DOES. It used to be published as a flag
    that check_multishot consulted to decide whether the carriage got a whole
    PLUNGER_STROKE. It does not any more, and it must never again: a bite angle
    is a statement about whether a plate can hold a rod, and it says nothing
    whatever about whether the frame has room for the rod to travel. Delivered
    volume comes from the stepper and from nowhere else."""
    print("\n=== 9. ONE-WAY GRIP (holds forward, releases on return) ===")
    plates = _find_all(bodies, "grip_plate")
    ok = False
    detail: dict = {}
    if not plates:
        fail("grip", "no one-way grip in the assembly. Without a grip that holds "
                     "the plunger while the drive slides back, the drive advances "
                     "the plunger by exactly one stroke per FILL, not per shot - "
                     "which is the single-shot defect")
    else:
        print(f"  grip plates present: {', '.join(sorted(plates))}")
        rod_d = float(getattr(M, "PUSH_ROD_OD", 0.0))
        bore_d = float(getattr(M, "GRIP_BORE_D", 0.0))
        t = float(getattr(M, "GRIP_PLATE_T", 0.0))
        if min(rod_d, bore_d, t) <= 0:
            fail("grip", "grip plates exist but PUSH_ROD_OD / GRIP_BORE_D / "
                         "GRIP_PLATE_T are not all declared, so the bite angle "
                         "cannot be derived from geometry")
        else:
            R = math.hypot(bore_d, t)
            phi = math.atan2(t, bore_d)
            root = math.degrees(math.acos(min(1.0, rod_d / R)) - phi)
            # A grip AT the root touches the rod on a line and carries nothing.
            # Holding 37 N needs the bore edges pressed INTO the rod, so the gate
            # is the interference angle, and the interference the model asks for
            # is a stated requirement of its own that has to be positive.
            inter = float(getattr(M, "GRIP_BITE_INTERFERENCE_MM", 0.0))
            if inter <= 0.0:
                fail("grip", "GRIP_BITE_INTERFERENCE_MM is not declared positive: "
                             "a tilting plate at exactly the bite root touches "
                             "the rod on a line and transmits no force")
            need = math.degrees(math.acos(min(1.0, (rod_d - inter) / R)) - phi)
            got = float(getattr(M, "GRIP_TILT_DEG", 0.0))
            aperture = R * math.cos(math.radians(got) + phi)
            atan_stand_in = math.degrees(math.atan((bore_d - rod_d) / t))
            print(f"  rod {rod_d:.2f}  bore {bore_d:.2f}  plate {t:.2f} mm")
            print(f"  exact bite root acos(d/R)-phi = {root:.3f} deg "
                  f"(the atan stand-in would say {atan_stand_in:.3f})")
            print(f"  + {inter:.2f} mm diametral interference -> needs "
                  f"{need:.3f} deg; declared tilt {got:.3f} deg "
                  f"(margin {got/max(root,1e-9):.2f}x over the root)")
            print(f"  aperture at the declared tilt {aperture:.3f} mm on a "
                  f"{rod_d:.2f} mm rod -> {rod_d-aperture:+.3f} mm interference")
            detail = dict(rod=rod_d, bore=bore_d, t=t, root_deg=root,
                          need_deg=need, tilt_deg=got, aperture_mm=aperture,
                          interference_mm=rod_d - aperture,
                          margin_over_root=got / max(root, 1e-9))
            if got + 1e-9 < need:
                fail("grip", f"grip plates tilted {got:.3f} deg but holding "
                             f"{inter:.2f} mm of interference on a {rod_d:.2f} mm "
                             f"rod through a {bore_d:.2f} bore needs "
                             f"{need:.3f} deg (bare bite root {root:.3f} deg): "
                             f"the rod slides through and the plunger is never "
                             f"advanced")
            else:
                ok = True
        rk, rod = _find(bodies, "push_rod")
        if rod is None:
            fail("grip", "grip plates exist but there is no push-rod body for "
                         "them to grip")
            ok = False
        else:
            # THE PLATES MUST STILL BE ON THE ROD ON THE LAST SHOT.
            # Bite angle alone certifies that a plate CAN grip a rod. It says
            # nothing about whether the rod is still under the plate by the time
            # the cartridge is empty. Without this, check_multishot credits a
            # re-grip that has nothing left to grip - a check that passes while
            # the device does not work, which is the exact failure mode that got
            # four revisions of this project rejected.
            #
            # The rod advances one stroke per shot, so sweep the whole fill and
            # require every plate to stay inside the rod's span, with
            # GRIP_ENGAGE_MM of rod still behind the plate to bite on.
            rb = bb(rod)
            stroke = float(M.PLUNGER_STROKE)
            shots = int(getattr(M, "SHOTS_PER_FILL", 1))
            engage = float(getattr(M, "GRIP_ENGAGE_MM", 0.0))
            worst = None
            for pk, pv in plates.items():
                pc = bb(pv).center.x
                for k in range(shots + 1):
                    behind = pc - (rb.xmin + k * stroke)
                    ahead = (rb.xmax + k * stroke) - pc
                    if worst is None or behind < worst[0]:
                        worst = (behind, pk, k, ahead)
                    if behind < engage or ahead < 0.0:
                        fail("grip", f"after {k} of {shots} shots the rod has "
                                     f"advanced past {pk}: {behind:.2f} mm of rod "
                                     f"remains behind the plate (needs "
                                     f"{engage:.2f}) and {ahead:.2f} mm ahead. "
                                     f"The grip has nothing left to bite, so the "
                                     f"last shots are not driven")
                        ok = False
            if worst is not None:
                print(f"  rod engagement over {shots} shots: worst is "
                      f"{worst[0]:.2f} mm behind {worst[1]} at shot {worst[2]} "
                      f"(needs {engage:.2f} mm)")

        # ---- THE AXIAL SPAN BETWEEN THE PLATES, MEASURED OFF THE BODIES ----
        # The stepper reports the stop as a travel; this reports the same stop
        # as a LENGTH THE FRAME IS SHORT BY, which is the form somebody can act
        # on. Both numbers come from geometry - the plates' own bounding boxes
        # in assembly space - not from the model's arithmetic about them.
        dk, dp = _find(bodies, "grip_plate_drive")
        ak, ap = _find(bodies, "grip_plate_antireturn")
        if dp is not None and ap is not None:
            span = bb(ap).xmin - bb(dp).xmax
            need_span = float(M.PLUNGER_STROKE) + MIN_CLEARANCE
            seat = float(getattr(M, "SPRING_SEAT_X", 0.0))
            print(f"  axial span drive-front {bb(dp).xmax:.2f} to "
                  f"antireturn-rear {bb(ap).xmin:.2f} = {span:.2f} mm; a full "
                  f"{M.PLUNGER_STROKE:.2f} mm stroke needs {need_span:.2f} mm")
            REPORT["grip_span"] = dict(span_mm=span, need_mm=need_span,
                                       deficit_mm=need_span - span)
            if span + 1e-9 < need_span:
                ok = False
                fail("grip", f"the two grip plates are {span:.2f} mm apart but a "
                             f"full stroke needs {need_span:.2f} mm: the frame is "
                             f"{need_span-span:.2f} mm SHORT along x. The plate "
                             f"cannot move forward (the syringe flange is 1.9 mm "
                             f"ahead of it) and the carriage cannot move back "
                             f"without the rear spring abutment at x = "
                             f"{seat:.2f} leaving a baseplate that starts at "
                             f"x = 0, so this is frame length owed, not a "
                             f"spacing error. Cutting SHOTS_PER_FILL does not "
                             f"pay it: shot count sets FILL_LEN, not "
                             f"PLUNGER_STROKE")
    REPORT["one_way_grip"] = dict(ok=ok, **detail)
    REPORT["one_way_grip_ok"] = ok
    if ok:
        print("  grip geometry bites")


# ================================================================== THE FRAMES
# ONE KINEMATIC MODEL. Round 2 of Mk5 found this harness holding two
# contradictory accounts of the same stroke: check_motion swept the carriage and
# reported it fouling grip_plate_antireturn at 7.25 mm of travel, while
# check_multishot printed five clean 2.00 mL shots. The second was not a
# simulation at all - it was an identity:
#
#     push := PLUNGER_STROKE                    (if a flag was set)
#     vol  := push * bore area
#     and PLUNGER_STROKE was itself defined as SHOT_VOLUME_ML / bore area
#
# so it re-derived the volume the model had already declared and could not, in
# principle, report anything else. The flag that gated it (`one_way_grip_ok`)
# was set by re-checking the same tilt formula the model used to CHOOSE the
# tilt. Nothing downstream of that was knowable, and this is the exact
# structural pattern - a check whose output is its input - behind four
# revisions that shipped with zero reported failures and unbuildable parts.
#
# It is replaced by a single stepper. Every body in the assembly, printed AND
# purchased, carries a frame tag. The carriage frame is stepped forward in
# <= 0.25 mm increments and every moving body is tested against every static
# body at every step. The stroke ends at the first contact. DELIVERED VOLUME IS
# AN OUTPUT OF THAT SWEEP - travel actually achieved times bore area - and there
# is no other path to a volume number in this file. A certified grip may close a
# gap; it may not manufacture travel.

FRAME_WORLD = "WORLD"        # the frame: baseplate, abutments, barrel, servos
FRAME_CARRIAGE = "CARRIAGE"  # driven forward by the spring
FRAME_ROD = "ROD"            # push-rod and piston: carried by the drive grip
FRAME_ROCKER = "ROCKER"      # the recock winch; at rest during the drive stroke

# Explicit, in one place, so that "what moves" has exactly one definition. A
# body not named here is WORLD - the safe default, because a static body is
# tested against everything that moves, and a moving body is not tested against
# other bodies in its own frame. Getting this wrong in the permissive direction
# DELETES pairs from the sweep, so the default must be the strict one.
_FRAME_EXACT = {
    "printed/carriage": FRAME_CARRIAGE,
    "mockup/grip_plate_drive": FRAME_CARRIAGE,
    # captive in the carriage pocket behind the drive plate, so it goes where the
    # carriage goes; leaving it in WORLD made the carriage collide with a spring
    # it is carrying, 1.00 mm into its own return stroke
    "mockup/grip_return_spring": FRAME_CARRIAGE,
    "mockup/push_rod": FRAME_ROD,
    "mockup/piston": FRAME_ROD,
    "mockup/rocker": FRAME_ROCKER,
    "mockup/hand_lever_hex_stub": FRAME_ROCKER,
    # (round 4) THE RECOCK ANCHOR TRAVELS WITH WHAT IT IS BOLTED TO. The pin is
    # a dowel through the carriage's own fork, so it is CARRIAGE; leaving it in
    # WORLD made the carriage collide with a pin it carries, 1.00 mm into its
    # own drive stroke. The cable is compliant and a rigid-body stepper cannot
    # represent slack, so it is swept in the CARRIAGE frame - the pose in which
    # it is TAUT and therefore in the way of most things - rather than excused
    # from the sweep. It is drawn at full cock, which is where it is taut.
    "mockup/recock_anchor_pin": FRAME_CARRIAGE,
    "mockup/recock_cable": FRAME_CARRIAGE,
    # named WORLD explicitly because their names contain a moving frame's token
    "mockup/rocker_pin": FRAME_WORLD,          # the pivot, not the swinging arm
    "mockup/winch_drum": FRAME_WORLD,          # on the servo shaft, not the carriage
    "mockup/grip_plate_antireturn": FRAME_WORLD,   # anchored to the abutment
}


def frame_of(name: str) -> str:
    return _FRAME_EXACT.get(name, FRAME_WORLD)


def frame_table(bodies: dict) -> dict:
    return {k: frame_of(k) for k in bodies}


def _drive_partition(bodies: dict, sear_release_deg):
    """Split the assembly for the DRIVE stroke.

    During the drive stroke the grip bites, so the rod and piston travel with
    the carriage 1:1 - one frame, kinematically. The rocker is at rest and is
    therefore an obstacle, not an excused body: it goes in the static set under
    its own name. The pawl is ACTUATED clear before the stroke starts, so it is
    swept POSED at the release angle 5b certified, never deleted.
    """
    moving, static = {}, {}
    for k, v in bodies.items():
        f = frame_of(k)
        if f in (FRAME_CARRIAGE, FRAME_ROD):
            moving[k] = v
        else:
            static[k] = v
    if "printed/sear" in static:
        if sear_release_deg is None:
            static.pop("printed/sear")
            fail("stroke", "no certified sear release angle: the drive stroke "
                           "could not be stepped against the pawl in its "
                           "released pose")
        else:
            s = static.pop("printed/sear")
            static[f"printed/sear @{sear_release_deg:g}deg released"] = \
                _sear_rotated(s, sear_release_deg)
    return moving, static


def step_drive_stroke(bodies: dict, max_travel: float, step: float,
                      sear_release_deg=None, rod_advance: float = 0.0,
                      carriage_advance: float = 0.0):
    """THE STEPPER. Advance the CARRIAGE frame and report how far it gets.

    `rod_advance` is how far the rod/piston have already been driven forward by
    previous shots; `carriage_advance` likewise for the carriage, which is 0 on
    every shot because the carriage re-cocks to the same place.

    Returns (travel, blockers, preexisting) where

      travel       mm the carriage moved before the first NEW contact, i.e. the
                   last sample at which nothing that was clear at rest overlaps
      blockers     [(pair, volume, at_travel)] - what stopped it
      preexisting  [(pair, volume)] - pairs already interfering at t = 0

    A pair already interfering at rest is a STATIC assembly defect, reported
    separately and failed, not folded into the travel number: it is not the
    stroke that put it there. Ignoring it silently would be starvation; charging
    it to the stroke would make every travel 0.00 mm and hide which feature
    is really the stop.
    """
    moving, static = _drive_partition(bodies, sear_release_deg)
    if not moving:
        return 0.0, [], []

    def placed_moving(t):
        out = {}
        for k, v in moving.items():
            d = (carriage_advance + t) if frame_of(k) == FRAME_CARRIAGE \
                else (rod_advance + t)
            out[k] = v.moved(cq.Location(cq.Vector(d, 0, 0)))
        return out

    # t = 0: which pairs are ALREADY interfering, before any travel at all
    pre = {}
    for mk, mb in placed_moving(0.0).items():
        for sk, sb in static.items():
            v = intersect_volume(mb, sb)
            if v == v and v > 1e-6:
                pre[(mk, sk)] = v

    # sample points include max_travel exactly, so a stroke clear to the very end
    # reports max_travel and not max_travel rounded down to a whole step
    n = max(1, int(math.ceil(max_travel / step)))
    samples = [min(max_travel, i * step) for i in range(n + 1)]
    if samples[-1] < max_travel - 1e-9:
        samples.append(max_travel)

    travel = 0.0
    blockers: list = []
    for t in samples:
        hits = []
        for mk, mb in placed_moving(t).items():
            for sk, sb in static.items():
                if (mk, sk) in pre:
                    continue          # a rest-state defect, charged elsewhere
                v = intersect_volume(mb, sb)
                if v == v and v > 1e-6:
                    hits.append((f"{mk} -> {sk}", v, t))
        if hits:
            blockers = sorted(hits, key=lambda h: -h[1])
            break
        travel = t
    return min(travel, max_travel), blockers, sorted(
        ((f"{a} <> {b}", v) for (a, b), v in pre.items()), key=lambda p: -p[1])


def step_recock_excursion(bodies: dict, stroke: float, step: float,
                          sear_release_deg=None, rod_advance: float = 0.0):
    """THE RETURN HALF, STEPPED, IN THE POSE IT ACTUALLY HAPPENS IN.

    (round 4) THE POSE BUG, AND WHY FIXING IT IS NOT A LOOSENING.
    check_grip_release used to take the CARRIAGE frame at the pose the model
    draws - which is FULL COCK, the carriage's rearmost position - and retract
    it a further PLUNGER_STROKE from there. That is 10.07 mm BEHIND the
    rearmost pose the mechanism has, into a compression spring the model draws
    at its COCKED length, so the very first sample drove the carriage into the
    coil and the check reported 0.00 of 10.07 mm every single run. The
    excursion the machine actually makes is fired -> cocked: it starts one full
    stroke FORWARD of the drawn pose and ends ON it. Both reviewers confirmed
    the physical excursion is clear, and check_multishot's own forward stepper
    walks the same corridor five times.

    So: advance the carriage frame by `stroke`, then walk it back to 0. The ROD
    stands still at `rod_advance` - that is the assertion under test, since the
    anti-return plate is what holds it - and the drive plate is squared to its
    released angle, because a plate rigid at its bite angle would drag the rod
    back with it.

    Returns (retracted_mm, stopper) where retracted_mm is how far of `stroke`
    the carriage got before the first NEW contact.
    """
    moving, statics = _drive_partition(bodies, sear_release_deg)
    moving = {k: v for k, v in moving.items() if frame_of(k) == FRAME_CARRIAGE}
    dk, _ = _find(bodies, "grip_plate_drive")
    tilt = float(getattr(M, "GRIP_TILT_DEG", 0.0))
    square = float(getattr(M, "GRIP_SQUARE_DEG", 0.0))
    if dk in moving:
        moving[dk] = _plate_at_tilt(moving[dk], tilt, square)
    rod_shift = cq.Location(cq.Vector(rod_advance, 0, 0))
    statics = {k: (v.moved(rod_shift) if frame_of(k) == FRAME_ROD else v)
               for k, v in statics.items()}
    # Pairs already interfering at the DRAWN pose are static assembly defects,
    # failed by name in check 4 and by the forward stepper; charging them to the
    # excursion would report 0.00 mm and hide which feature is really the stop.
    pre = set()
    for mk, mb in moving.items():
        for sk, sb in statics.items():
            v = intersect_volume(mb, sb)
            if v == v and v > 1e-6:
                pre.add((mk, sk))
    n = max(1, int(math.ceil(stroke / step)))
    back = 0.0
    stopper = None
    for i in range(n + 1):
        d = stroke - min(stroke, i * step)          # fired -> cocked
        hit = None
        for mk, mb in moving.items():
            shifted = mb.moved(cq.Location(cq.Vector(d, 0, 0)))
            for sk, sb in statics.items():
                if (mk, sk) in pre:
                    continue
                v = intersect_volume(shifted, sb)
                if v == v and v > 1e-6:
                    hit = (f"{mk} -> {sk}", v)
                    break
            if hit:
                break
        if hit:
            stopper = hit
            break
        back = stroke - d
    return min(back, stroke), stopper


# ------------------------------------------------ 9b. the release half-cycle
def _plate_at_tilt(plate, from_deg: float, to_deg: float):
    """Re-pose a tilted grip plate about its own centre. Same technique as
    _sear_rotated: the harness poses the body it was given rather than asking
    the model for a second body in a second pose, so there is exactly one plate
    in the assembly and no chance of double-counting it in the clearance check."""
    c = bb(plate).center
    return (plate.moved(cq.Location(-c))
                 .rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), to_deg - from_deg)
                 .moved(cq.Location(c)))


def check_grip_release(bodies: dict, step: float) -> None:
    """DOES THE DRIVE PLATE LET GO?

    Half the caulk-gun cycle had never been drawn or checked. Both plates were
    modelled RIGID at their bite angle, and a drive plate rigid at its bite
    angle does not release: it still holds the rod when the carriage retracts,
    so the return stroke pulls the piston back out of the barrel and the device
    nets zero displacement per cycle no matter how many times it fires. Every
    forward-going check in this file can pass with that defect present, because
    every one of them looks only at the forward half.

    A real tilting-plate grip works because the tilt is LOAD-INDUCED. At rest
    the plate is loose on the rod - the bore is larger than the rod - and the
    drive force is what cocks it. Take the force away, a light spring squares
    it, and it slides. So the plate has two poses and both are tested here:

      HOLD     posed at the model's tilt: the bore must INTERFERE with the rod
      RELEASE  posed square: the bore must CLEAR the rod, and the whole return
               stroke must be free with the rod standing still

    and the spring that squares it has to exist as a body."""
    print("\n=== 9b. GRIP RELEASE (the return half of the cycle) ===")
    dk, drive = _find(bodies, "grip_plate_drive")
    rk, rod = _find(bodies, "push_rod")
    if drive is None or rod is None:
        fail("release", "no drive grip plate or no push-rod: the return half of "
                        "the cycle cannot be simulated, and an unsimulated "
                        "return is not a working one")
        REPORT["grip_release_ok"] = False
        return
    tilt = float(getattr(M, "GRIP_TILT_DEG", 0.0))
    square = float(getattr(M, "GRIP_SQUARE_DEG", 0.0))
    ok = True

    # ---- 1. the HOLD pose must actually interfere with the rod -------------
    v_hold = intersect_volume(drive, rod)
    print(f"  hold pose  ({tilt:5.2f} deg): plate shares {v_hold:8.4f} mm3 with "
          f"the rod")
    if not (v_hold > 1e-6):
        ok = False
        fail("release", f"the drive plate at its {tilt:.2f} deg bite angle does "
                        f"not interfere with the rod at all: there is no bite, "
                        f"so nothing carries the {getattr(M,'SPRING_PEAK_N',0):.1f} "
                        f"N forward and the rod is never advanced")

    # ---- 2. the RELEASE pose must clear the rod ---------------------------
    sq = _plate_at_tilt(drive, tilt, square)
    v_free = intersect_volume(sq, rod)
    # NOT min_gap() here. That helper samples VERTICES, and a 130 mm cylinder has
    # vertices only on its two end circles, so it answers "how far is the plate
    # from the end of the rod" - it reported 40.959 mm for a plate sitting on the
    # rod. The meaningful clearance is radial and comes from the aperture.
    rod_d = float(getattr(M, "PUSH_ROD_OD", 0.0))
    bore_d = float(getattr(M, "GRIP_BORE_D", 0.0))
    R = math.hypot(bore_d, float(getattr(M, "GRIP_PLATE_T", 1.0)))
    phi = math.atan2(float(getattr(M, "GRIP_PLATE_T", 1.0)), bore_d)
    ap_sq = R * math.cos(math.radians(square) + phi)
    print(f"  square pose ({square:5.2f} deg): shares {v_free:8.4f} mm3, "
          f"aperture {ap_sq:.3f} mm on a {rod_d:.2f} rod "
          f"({ap_sq-rod_d:+.3f} mm diametral clearance)")
    if v_free > 1e-6:
        ok = False
        fail("release", f"squared to {square:.2f} deg the drive plate still "
                        f"shares {v_free:.4f} mm3 with the rod: it cannot slide "
                        f"back over it, so the carriage cannot re-cock and the "
                        f"mechanism fires once")

    # ---- 3. something has to square it ------------------------------------
    sk, spr = _find(bodies, "grip_return_spring")
    if spr is None:
        ok = False
        fail("release", "no return spring and no squaring pad anywhere in the "
                        "assembly: nothing takes the drive plate out of its bite "
                        "when the load goes away, so the plate stays tilted, "
                        "holds the rod on the return stroke and drags the piston "
                        "back out. The caulk-gun load path does not close")
    else:
        # A MOMENT BALANCE, not a force one, and not a fabricated stiffness.
        # An earlier draft of this check invented a bending stiffness for the
        # washer and got 264 N of "seating force" out of a part that is free to
        # rock on a rod - a number with no mechanism behind it. What actually
        # holds the plate tilted is AXIAL LOAD, through the same wedge that makes
        # it grip: the model's own statement of the bite is that axial
        # equilibrium puts f = F/2 of friction at each of two bore edges, so the
        # couple resisting a return to square is
        #       M_resist = F_residual * D/2
        # and the return spring, bearing at the plate's outer radius, supplies
        #       M_spring = F_spring * OD/2 .
        #
        # F_residual is what is STILL pushing on the plate after the shot. The
        # main spring is spent and back-pressure has decayed, so it is the
        # syringe plunger's own seal drag - a real force, declared by the model
        # as a bench measurement, not assumed to be zero. Assuming it zero would
        # make this check unfailable, which is the whole disease.
        f_spring = float(getattr(M, "GRIP_RETURN_SPRING_N", 0.0))
        f_res = float(getattr(M, "PISTON_SEAL_DRAG_N", 0.0))
        od = float(getattr(M, "GRIP_PLATE_OD", 14.0))
        if f_res <= 0.0:
            ok = False
            fail("release", "PISTON_SEAL_DRAG_N is not declared positive. A "
                            "syringe piston has seal drag; setting the residual "
                            "axial load to zero makes the release check "
                            "unfailable by construction")
        m_resist = f_res * bore_d / 2.0
        m_spring = f_spring * od / 2.0
        need_N = m_resist / (od / 2.0)
        print(f"  return spring {sk}: {f_spring:.2f} N at r {od/2:.1f} mm = "
              f"{m_spring:.2f} N.mm against {f_res:.2f} N of seal drag wedged at "
              f"r {bore_d/2:.2f} mm = {m_resist:.2f} N.mm "
              f"(margin {m_spring/max(m_resist,1e-9):.2f}x, needs "
              f"{need_N:.2f} N)")
        REPORT["grip_release_spring"] = dict(have_N=f_spring, need_N=need_N,
                                             m_spring=m_spring,
                                             m_resist=m_resist,
                                             residual_N=f_res)
        if m_spring < m_resist:
            ok = False
            fail("release", f"the drive plate's return spring makes "
                            f"{m_spring:.2f} N.mm but {m_resist:.2f} N.mm is "
                            f"needed to square it against {f_res:.2f} N of "
                            f"residual seal drag wedged through the bite: it "
                            f"stays bitten, holds the rod on the return stroke "
                            f"and drags the piston back out. The spring must be "
                            f"at least {need_N:.2f} N")

    # ---- 4. the RETURN STROKE ITSELF, stepped, with the rod standing still --
    # The anti-return plate is what holds the rod while the carriage retracts,
    # so the ROD frame does NOT move here - which is exactly the assertion under
    # test. Anything the retreating carriage touches ends the return.
    stroke = float(M.PLUNGER_STROKE)
    back, stopper = step_recock_excursion(bodies, stroke, step,
                                          REPORT.get("sear_release_deg"))
    print(f"  return stroke: carriage retracts {back:5.2f} of {stroke:5.2f} mm "
          f"with the rod held" + (f"; stopped by {stopper[0]}" if stopper else
                                  "; clear"))
    if back + 1e-9 < stroke:
        ok = False
        why = (f"{stopper[0]} ({stopper[1]:.2f} mm3)" if stopper
               else "the sweep, with no contact recorded")
        fail("release", f"the carriage retracts only {back:.2f} mm of the "
                        f"{stroke:.2f} mm it must to re-cock, stopped by "
                        f"{why}. It cannot get back "
                        f"far enough to bite fresh rod, so there is no second "
                        f"shot regardless of what the forward stroke does")
    # WRITTEN LAST, not in the middle. An earlier draft filled this dict before
    # the return-stroke verdict was in, so the JSON said ok=True while the run
    # failed on that very stroke - a stale flag of exactly the kind a downstream
    # check would have read and believed.
    REPORT["grip_release"] = dict(ok=ok, hold_mm3=v_hold, free_mm3=v_free,
                                  return_travel_mm=back, return_needed_mm=stroke,
                                  stopped_by=stopper[0] if stopper else None)
    REPORT["grip_release_ok"] = ok
    if ok:
        print("  the drive plate bites forward, squares up and lets go on return")


# ------------------------------------------------------------ 10. multi-shot
def check_multishot(bodies: dict, step: float, sear_release_deg=None) -> None:
    """SHOOT, RE-COCK, SHOOT AGAIN - and the volume is what the STEPPER says.

    Round 2 of Mk5 deleted this function's arithmetic. It used to compute

        push = PLUNGER_STROKE  (when a flag was set)
        ml   = push * bore area

    which, since PLUNGER_STROKE is DEFINED as SHOT_VOLUME_ML / bore area, could
    only ever print SHOT_VOLUME_ML back. It reported five clean 2.00 mL shots
    from an assembly the motion sweep, three checks earlier, said jams at
    7.25 mm. Both cannot be true; only one of them was measuring anything.

    Now: for each shot the carriage re-cocks to the same X, the rod stands where
    the previous shots left it, and the CARRIAGE frame is stepped forward until
    something touches. Delivered volume is (travel achieved) x bore area. If the
    mechanism cannot move, the volume is zero and it says so.

    There is no grip flag in this function. A one-way grip is what lets the rod
    KEEP the ground each shot has won - which is why the rod's start offset
    accumulates - but it cannot create room the frame does not have.
    """
    print("\n=== 10. MULTI-SHOT (delivered volume = measured travel x bore) ===")
    # (round 5) THE FLAG MAY NOT DISAGREE WITH THE FAILURE LIST.
    # `working = not bad` collected only the shots that came up short. Every
    # OTHER way this function fails - a pre-existing interference at rest, a
    # re-cock excursion that does not complete, a cartridge too small for the
    # shots demanded - called fail("multishot", ...) and then set the flag True
    # anyway, and full_r4.json says exactly that: one [multishot] failure and
    # multishot_working: true. The flag now starts from the failure list itself,
    # so no [multishot] failure can be emitted in a run that still claims the
    # mechanism works.
    _ms_mark = len(FAILURES)
    stroke = float(M.PLUNGER_STROKE)
    bore = float(getattr(M, "SYRINGE_BORE", 12.45))
    area = math.pi * (bore / 2.0) ** 2                  # mm2
    shot_ml = float(getattr(M, "SHOT_VOLUME_ML", 2.0))
    cap_ml = float(getattr(M, "SYRINGE_CAPACITY_ML", 0.0))
    want = int(getattr(M, "SHOTS_PER_FILL", 0)) or (
        int(cap_ml / shot_ml) if cap_ml else 2)
    need_ml = MIN_SHOT_FRACTION * shot_ml

    frames = frame_table(bodies)
    n_car = sum(1 for f in frames.values() if f == FRAME_CARRIAGE)
    n_rod = sum(1 for f in frames.values() if f == FRAME_ROD)
    print(f"  frames: {n_car} CARRIAGE, {n_rod} ROD, "
          f"{sum(1 for f in frames.values() if f == FRAME_ROCKER)} ROCKER, "
          f"{sum(1 for f in frames.values() if f == FRAME_WORLD)} WORLD")
    print(f"  bore {bore:.2f} mm -> {area:.2f} mm2; nominal stroke "
          f"{stroke:.2f} mm; target {want} shots of {shot_ml:.2f} mL")
    if n_car == 0 or n_rod == 0:
        fail("multishot", "the drive stroke has no CARRIAGE frame or no ROD "
                          "frame: there is nothing to step and no plunger for "
                          "it to push, so no shot can be measured")
        REPORT["multishot_working"] = False
        return

    rod_adv = 0.0
    rows, bad = [], []
    total_ml = 0.0
    bad_recock = []
    for k in range(1, want + 1):
        # (round 4) THE RETURN IS NO LONGER FREE. This loop used to hand itself
        # `carriage_advance = 0` on every shot with the comment "which is 0 on
        # every shot because the carriage re-cocks to the same place" - i.e. it
        # ASSUMED the thing the whole round is about. Between every pair of
        # shots the carriage now has to make the excursion for real, fired ->
        # cocked, stepped against everything static, with the rod standing where
        # the previous shots left it. A shot that cannot be re-cocked into does
        # not happen, and its volume is not counted.
        if k > 1:
            back, stop_r = step_recock_excursion(bodies, stroke, step,
                                                 sear_release_deg,
                                                 rod_advance=rod_adv)
            print(f"  recock {k-1}->{k}: carriage returns {back:6.2f} of "
                  f"{stroke:5.2f} mm with the rod held at {rod_adv:.2f} mm"
                  + (f"; stopped by {stop_r[0]}" if stop_r else "; clear"))
            if back + 1e-9 < stroke:
                why = (f"{stop_r[0]} ({stop_r[1]:.2f} mm3)" if stop_r
                       else "the sweep, with no contact recorded")
                bad_recock.append((k, back, why))
                rows.append(dict(n=k, travel_mm=0.0, ml=0.0,
                                 stopped_by=f"never re-cocked: {why}",
                                 rod_at_mm=rod_adv))
                bad.append((k, 0.0, 0.0, f"never re-cocked: {why}"))
                print(f"  shot {k}: NOT FIRED - the carriage could not get back "
                      f"to the sear")
                continue
        travel, blockers, pre = step_drive_stroke(
            bodies, stroke, step, sear_release_deg, rod_advance=rod_adv)
        ml = travel * area / 1000.0
        total_ml += ml
        rod_adv += travel
        stop = blockers[0][0] if blockers else "full stroke"
        rows.append(dict(n=k, travel_mm=travel, ml=ml, stopped_by=stop,
                         rod_at_mm=rod_adv))
        mark = "" if ml >= need_ml else "   <-- SHORT"
        print(f"  shot {k}: travelled {travel:6.2f} of {stroke:5.2f} mm  "
              f"-> {ml:5.2f} mL{mark}")
        print(f"          stopped by: {stop}")
        if k == 1 and pre:
            print(f"          {len(pre)} pair(s) already interfering at rest:")
            for nm, v in pre[:6]:
                print(f"            {v:9.2f} mm3  {nm}")
            fail("multishot", f"{len(pre)} pair(s) are already interfering "
                              f"before the stroke begins (worst {pre[0][1]:.2f} "
                              f"mm3, {pre[0][0]}). The drive stroke was measured "
                              f"from a pose that does not physically exist")
        if ml < need_ml:
            bad.append((k, ml, travel, stop))

    REPORT["multishot"] = dict(target_shots=want, bore_mm=bore, area_mm2=area,
                               nominal_stroke_mm=stroke, shots=rows,
                               total_ml=total_ml,
                               failed_recocks=[[k, round(b, 3), w]
                                               for k, b, w in bad_recock])
    if bad_recock:
        k, b, w = bad_recock[0]
        fail("multishot", f"{len(bad_recock)} of {want-1} re-cock excursions do "
                          f"not complete. Before shot {k} the carriage returns "
                          f"{b:.2f} of the {stroke:.2f} mm it must, stopped by "
                          f"{w}. The device fires until the first one that fails "
                          f"and then needs a hand on it")
    print(f"  total delivered {total_ml:.2f} mL over {want} attempted shots")

    if bad:
        k, ml, tr, stop = bad[0]
        fail("multishot", f"{len(bad)} of {want} shots deliver less than "
                          f"{MIN_SHOT_FRACTION*100:.0f}% of {shot_ml:.2f} mL. "
                          f"Shot {k} travels {tr:.2f} mm of the {stroke:.2f} mm "
                          f"it needs and delivers {ml:.2f} mL, stopped by "
                          f"{stop}. The travel is MEASURED, not assumed: this is "
                          f"how far the carriage frame actually gets")
    if cap_ml and want * shot_ml > cap_ml + 1e-9:
        fail("multishot", f"{want} shots x {shot_ml:.2f} mL = "
                          f"{want*shot_ml:.2f} mL demanded from a "
                          f"{cap_ml:.2f} mL cartridge")

    # THE FLAG, LAST, AND FROM THE FAILURE LIST - see the note at the top.
    emitted = [f for f in FAILURES[_ms_mark:] if f.startswith("[multishot]")]
    working = (not bad) and not emitted
    REPORT["multishot_working"] = working
    REPORT["multishot"]["failures_emitted"] = emitted
    if emitted and not bad:
        print(f"  multishot_working = False: {len(emitted)} [multishot] "
              f"failure(s) were emitted in this run")


# ------------------------------------------------------- 11. recock budget
_CLASSIFIERS: dict = {}


def _inside_fast(solid, x, y, z) -> bool:
    """_inside() with the topology classified once instead of a fresh boolean
    per point. Same question, same answer; _inside does ~2000 small booleans
    against a 240-segment scroll for every radius this check measures, and that
    is minutes rather than seconds. Nothing about the verdict changes."""
    try:
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier
        from OCP.gp import gp_Pnt
        from OCP.TopAbs import TopAbs_IN, TopAbs_ON
    except Exception:
        return _inside(solid, cq.Vector(x, y, z))
    key = id(solid)
    cls = _CLASSIFIERS.get(key)
    if cls is None:
        cls = BRepClass3d_SolidClassifier(solid.wrapped)
        _CLASSIFIERS[key] = cls
    cls.Perform(gp_Pnt(x, y, z), 1e-7)
    return cls.State() in (TopAbs_IN, TopAbs_ON)


def _ray_radius(solid, ax, az, y, ang_deg, r_hi=40.0, tol=1e-4) -> float:
    """Distance from (ax, az) to the far surface of `solid` along `ang_deg`, in
    the plane y = const. Bisection on _inside(); no model function is consulted.

    This is the whole point of the round: the drive radius is READ OFF the drawn
    drum at the angle the cable is standing on, not divided out of
    PLUNGER_STROKE and a sweep."""
    c, sn = math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg))

    def inside(t):
        return _inside_fast(solid, ax + t * c, y, az + t * sn)

    if not inside(1e-3):
        return float("nan")          # the axis is not inside the drum at all
    lo, hi = 1e-3, r_hi
    if inside(hi):
        return float("inf")
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if inside(mid):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _solid_gap(a, b) -> float:
    """Minimum distance between two solids, from the topology.

    min_gap() samples VERTICES, which on a cylinder means two end circles and
    tells you nothing about a body touching its side. Contact between a cable
    and the pin it is swaged around is exactly that case."""
    try:
        from OCP.BRepExtrema import BRepExtrema_DistShapeShape
        d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
        d.Perform()
        return d.Value() if d.IsDone() else float("nan")
    except Exception:
        return min_gap(a, b)


def _y_overlap(a, b) -> float:
    ba, bbx = bb(a), bb(b)
    return min(ba.ymax, bbx.ymax) - max(ba.ymin, bbx.ymin)


def check_recock_budget(bodies: dict) -> None:
    """CAN THE SERVO PUT THE SPRING BACK - measured off the drawn actuator.

    WHAT THIS CHECK USED TO BE, AND WHY IT WAS WORTHLESS.
    Rounds 1-3 read SERVO_STALL_N_MM, RECOCK_SWEEP_DEG and N_BITES, multiplied
    them, and derived the peak torque from

        r_winch = PLUNGER_STROKE / (sweep * N_BITES)          = 1.8035 mm

    which is not a measurement of anything. No part in the model had a feature
    at 1.8035 mm from any shaft; the number came out of the same three constants
    that went in, so the gate could be moved by editing a constant and could
    never be moved by drawing a part wrong. It reported 2.24x on a mechanism
    whose only contact with the carriage was an 0.850 mm sliver of bounding-box
    corner.

    WHAT IT IS NOW. Four assertions, none of which a constant can satisfy:

      1. THE RADIUS IS MEASURED. The drum solid is ray-cast from the servo shaft
         axis, in the plane the cable runs in, at every angle the sweep puts
         under the cable. The axis itself is checked against the drum's own hub
         bore before it is used.
      2. THE LOAD PATH CLOSES. Drum -> cable -> anchor pin -> carriage, each
         link in contact within tolerance, and the pin's engagement with the
         carriage measured in Y as a bearing width rather than a corner.
      3. PEAK TORQUE AT EVERY STEP - not the average an energy balance gives,
         the worst instant of the sweep, against the 1.5x gate.
      4. THE SWEEP DELIVERS THE STROKE, by integrating the measured radius over
         the sweep rather than assuming the mechanism that would.
    """
    print("\n=== 11. RECOCK ACTUATOR (radius measured off the drawn drum) ===")
    st = _spring_state(bodies)
    if st is None:
        fail("recock", "no spring body: the recock energy cannot be derived")
        return
    F_cocked = st["force_N"]
    stroke = float(M.PLUNGER_STROKE)
    k = F_cocked / stroke if stroke > 0 else 0.0
    drag = float(getattr(M, "RECOCK_DRAG_N", 0.0))
    pe = 0.5 * F_cocked * stroke + drag * stroke
    print(f"  spring MEASURED at {F_cocked:.2f} N cocked -> rate {k:.3f} N/mm; "
          f"work to restore {pe:.1f} N.mm ({pe/1000.0:.3f} J), including "
          f"{drag:.1f} N of constant drag")

    stall = float(getattr(M, "SERVO_STALL_N_MM", 0.0))
    sweep = float(getattr(M, "RECOCK_SWEEP_DEG", 0.0))
    if not stall or not sweep:
        fail("recock", "SERVO_STALL_N_MM or RECOCK_SWEEP_DEG undeclared: there "
                       "is no recock budget to check anything against")
        REPORT["recock"] = dict(pe_N_mm=pe, declared=False)
        return
    usable = stall * SERVO_DUTY_FRACTION

    dk, drum = _find(bodies, "winch_drum")
    ck, cable = _find(bodies, "recock_cable")
    pk, pin = _find(bodies, "recock_anchor_pin")
    sk, servo = _find(bodies, "servo_winch")
    _, carriage = _find(bodies, "printed/carriage")
    missing = [n for n, b in (("winch_drum", drum), ("recock_cable", cable),
                              ("recock_anchor_pin", pin),
                              ("servo_winch", servo)) if b is None]
    if missing or carriage is None:
        fail("recock", f"the recock actuator is not drawn: "
                       f"{', '.join(missing) or 'printed/carriage'} absent from "
                       f"the assembly. A drive radius cannot be measured off a "
                       f"body that does not exist, and an undrawn winch has no "
                       f"torque, no reach and no anchor")
        REPORT["recock"] = dict(pe_N_mm=pe, declared=False)
        return

    ax = float(getattr(M, "WINCH_AXIS_X", float("nan")))
    az = float(getattr(M, "WINCH_AXIS_Z", float("nan")))
    cy = float(getattr(M, "WINCH_CABLE_Y", float("nan")))
    dep = float(getattr(M, "WINCH_DEPARTURE_DEG", 90.0))
    if any(v != v for v in (ax, az, cy)):
        fail("recock", "WINCH_AXIS_X/Z or WINCH_CABLE_Y undeclared: the shaft "
                       "the drum turns on has no position, so nothing can be "
                       "measured from it")
        return

    # ---- 0. the declared axis has to BE the drawn drum's axis --------------
    # A declared axis with measured radii is only honest if it is the axis the
    # part was actually built around, so the hub bore is scanned in 24
    # directions and its radius has to come back constant.
    hub_y = 0.5 * (float(getattr(M, "WINCH_HUB_Y0", 0.0))
                   + float(getattr(M, "WINCH_HUB_Y1", 0.0)))
    bore = []
    for a in range(0, 360, 15):
        c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
        # WHERE DOES MATERIAL START going out from the declared axis? The
        # predicate is not monotone - past the hub's rim it is air again - so
        # this steps coarsely to the first material and only then bisects.
        # Bisecting straight off a 20 mm bracket reported "no bore anywhere",
        # because 20 mm out is indeed air.
        t, hit = 0.02, None
        while t < 20.0:
            if _inside_fast(drum, ax + t * c, hub_y, az + t * sn):
                hit = t
                break
            t += 0.1
        if hit is None:
            bore.append(20.0)
            continue
        lo, hi = max(0.0, hit - 0.1), hit
        while hi - lo > 0.005:
            mid = 0.5 * (lo + hi)
            if _inside_fast(drum, ax + mid * c, hub_y, az + mid * sn):
                hi = mid
            else:
                lo = mid
        bore.append(0.5 * (lo + hi))
    b_lo, b_hi = min(bore), max(bore)
    print(f"  hub bore around the declared axis: {b_lo:.2f}..{b_hi:.2f} mm "
          f"(runout {b_hi - b_lo:.3f} mm)")
    if b_hi >= 19.9:
        fail("recock", "the declared winch axis is not inside the drum's hub "
                       "bore at all: the axis the radii are measured from is "
                       "not the axis the drum was drawn around")
        return
    if b_hi - b_lo > 0.25:
        fail("recock", f"the drum's hub bore is not concentric with the declared "
                       f"winch axis: bore radius runs {b_lo:.2f}..{b_hi:.2f} mm "
                       f"over 360 deg ({b_hi - b_lo:.3f} mm of runout). The "
                       f"measured radii are being taken from the wrong centre")

    # ---- 1. the drive radius, at every angle the sweep touches -------------
    bcx = bb(cable)
    r_cable = min(bcx.ylen, bcx.zlen) / 2.0
    steps = 33
    rows = []
    travel = 0.0
    dphi = math.radians(sweep) / (steps - 1)
    prev_R = None
    bad_r = []
    for i in range(steps):
        u = i / (steps - 1.0)
        # the drum is DRAWN at full cock, so the profile angle standing at the
        # departure position after fraction u of the sweep is dep + (1-u)*sweep
        ang = dep + (1.0 - u) * sweep
        r_floor = _ray_radius(drum, ax, az, cy, ang)
        if r_floor != r_floor or r_floor == float("inf"):
            bad_r.append((u, ang))
            R = float("nan")
        else:
            R = r_floor + r_cable
        rows.append([u, ang, r_floor, R])
        if prev_R is not None and R == R and prev_R == prev_R:
            travel += 0.5 * (R + prev_R) * dphi
        prev_R = R
    if bad_r:
        fail("recock", f"the drum has no material under the cable at "
                       f"{len(bad_r)} of {steps} angles of the sweep (first at "
                       f"{bad_r[0][1]:.1f} deg): there is nothing for the cable "
                       f"to bear on, so the drive radius at those angles is not "
                       f"a radius of anything")
        REPORT["recock"] = dict(pe_N_mm=pe, declared=False)
        return

    # ---- 2. does the load path close? -------------------------------------
    # The perpendicular distance from the shaft axis to the drawn cable's own
    # centreline IS the moment arm, whatever direction the free span then runs.
    cab_z = 0.5 * (bcx.zmin + bcx.zmax)
    arm_drawn = abs(cab_z - az)
    R_end = rows[-1][3]
    print(f"  cable D{2 * r_cable:.2f} drawn at z {cab_z:.3f}, axis z {az:.3f} "
          f"-> moment arm {arm_drawn:.3f} mm against a measured groove-floor "
          f"radius + cable radius of {R_end:.3f} mm")
    closed = True
    if abs(arm_drawn - R_end) > 0.10:
        closed = False
        fail("recock", f"the drawn cable is not tangent to the drum it is drawn "
                       f"on: its centreline stands {arm_drawn:.3f} mm off the "
                       f"shaft axis but the groove floor measured at the "
                       f"departure angle plus the cable radius is {R_end:.3f} mm "
                       f"({arm_drawn - R_end:+.3f} mm). The drive radius and the "
                       f"cable disagree, so one of them is decoration")
    v_cd = intersect_volume(cable, drum)
    g_cd = _solid_gap(cable, drum)
    print(f"  cable <> drum: {g_cd:.3f} mm gap, {v_cd:.4f} mm3 shared "
          f"(a cable bears on its drum; it does not pass through it)")
    if v_cd > 1e-6:
        closed = False
        fail("recock", f"the cable shares {v_cd:.3f} mm3 with the drum: it is "
                       f"drawn through the flange, not wrapped on it")
    elif g_cd > 0.05:
        closed = False
        fail("recock", f"the cable stands {g_cd:.3f} mm clear of the drum: it is "
                       f"drawn beside the winch, not on it, so no torque reaches "
                       f"the carriage")
    bp = bb(pin)
    pin_r = min(bp.xlen, bp.zlen) / 2.0
    pin_axis_x = 0.5 * (bp.xmin + bp.xmax)
    pin_axis_z = 0.5 * (bp.zmin + bp.zmax)
    # THE CABLE MUST TOUCH THE PIN AND GO ROUND IT.
    # A first draft of this measured "distance from the pin axis to the cable's
    # furthest point", which a negative control walked straight through: cutting
    # the cable 3 mm short of the pin made that distance SMALLER, not larger,
    # because the furthest point of a wrap-around eye is on the far side. What
    # actually says the load path closes is a real solid-to-solid gap plus the
    # eye enclosing the pin axis in X.
    g_cp = _solid_gap(cable, pin)
    wraps = bcx.xmin < pin_axis_x < bcx.xmax
    print(f"  anchor pin D{2 * pin_r:.2f} at x {pin_axis_x:.2f}: cable-to-pin gap "
          f"{g_cp:.3f} mm, eye {'encloses' if wraps else 'does NOT enclose'} the "
          f"pin axis")
    if g_cp > 0.05 or not wraps:
        closed = False
        fail("recock", f"the cable does not close onto the anchor pin: gap "
                       f"{g_cp:.3f} mm and the eye "
                       f"{'encloses' if wraps else 'does not enclose'} the pin "
                       f"axis. Nothing connects the drum to the carriage, so the "
                       f"sweep pulls on air")
    # THE ENGAGED BEARING WIDTH, MEASURED AROUND THE PIN RATHER THAN OFF TWO
    # BOUNDING BOXES. A bounding-box y-overlap says only that the pin lies
    # within the carriage's width - a pin slid 4 mm outboard, entirely out of
    # its own fork, still scores the full overlap and a negative control proved
    # it. This walks the pin's axis and asks, at each station, whether there is
    # carriage material all the way round it at bore radius: that is what a
    # journal is.
    probe_r = pin_r + float(getattr(M, "CLEAR", 0.25)) + 0.30
    ys, eng = [], 0.0
    y = bp.ymin + 0.05
    dy = 0.10
    while y <= bp.ymax - 0.05:
        n = 0
        for a in range(0, 360, 45):
            c2, s2 = math.cos(math.radians(a)), math.sin(math.radians(a))
            if _inside_fast(carriage, pin_axis_x + probe_r * c2, y,
                            pin_axis_z + probe_r * s2):
                n += 1
        if n >= 5:
            eng += dy
        ys.append(n)
        y += dy
    v_pc = intersect_volume(pin, carriage)
    print(f"  pin <> carriage: {eng:.2f} mm of the pin is journalled in material "
          f"(bbox y-overlap would say {_y_overlap(pin, carriage):.2f}), "
          f"{v_pc:.3f} mm3 shared volume (the fork is bored, so 0 is right)")
    if eng < MIN_ANCHOR_BEARING_MM:
        closed = False
        fail("recock", f"only {eng:.2f} mm of the anchor pin is journalled in "
                       f"carriage material. That is not a bearing, it is a "
                       f"corner: the rocker this replaced reached the carriage "
                       f"with 0.850 mm of bounding-box overlap and carried "
                       f"nothing. At least {MIN_ANCHOR_BEARING_MM:.1f} mm of "
                       f"engaged width is needed to take {F_cocked:.0f} N")
    if v_pc > 1e-6:
        closed = False
        fail("recock", f"the anchor pin shares {v_pc:.2f} mm3 of volume with the "
                       f"carriage: the fork has no bore for it")
    bs, bd = bb(servo), bb(drum)
    on_axis = (bs.xmin - 0.5 <= ax <= bs.xmax + 0.5 and
               bs.zmin - 0.5 <= az <= bs.zmax + 0.5)
    _, shaft = _find(bodies, "winch_shaft")
    if shaft is None:
        closed = False
        fail("recock", "there is no winch output shaft in the assembly: the drum "
                       "is drawn beside the servo rather than on it, and a drum "
                       "that is not on a shaft is not driven by one")
        shaft_eng, sh_off = 0.0, float("nan")
    else:
        bsh = bb(shaft)
        # NOT `eng` - that name already holds the pin's journalled length four
        # lines up, and reusing it here overwrote a measured 3.40 mm with the
        # shaft's 2.00 mm in the JSON while the gate above kept the right value.
        shaft_eng = _y_overlap(shaft, drum)
        sh_off = math.hypot(0.5 * (bsh.xmin + bsh.xmax) - ax,
                            0.5 * (bsh.zmin + bsh.zmax) - az)
        gap_to_case = min(abs(bsh.ymin - bs.ymax), abs(bs.ymin - bsh.ymax))
        print(f"  output shaft: {shaft_eng:.2f} mm engaged in the drum hub, axis "
              f"{sh_off:.3f} mm off the declared winch axis, {gap_to_case:.2f} mm "
              f"from the servo case face")
        if sh_off > 0.10 or shaft_eng < 1.5 or gap_to_case > 0.10:
            closed = False
            fail("recock", f"the drum is not driven by the winch servo's shaft: "
                           f"{shaft_eng:.2f} mm of hub engagement, shaft axis "
                           f"{sh_off:.3f} mm off the declared winch axis and "
                           f"{gap_to_case:.2f} mm of shaft standing clear of the "
                           f"case. Torque cannot cross that")
    if not on_axis:
        closed = False
        fail("recock", "the declared winch axis is outside the winch servo's x/z "
                       "footprint: the shaft the drum turns on is not the "
                       "servo's")

    # ---- 3. peak torque at every step of the sweep ------------------------
    eff = float(getattr(M, "WINCH_EFFICIENCY", 1.0))
    s_draw = 0.0
    worst = (0.0, 0.0, 0.0)
    prev_R = None
    for row in rows:
        u, ang, r_floor, R = row
        if prev_R is not None:
            s_draw += 0.5 * (R + prev_R) * dphi
        prev_R = R
        F = k * s_draw + drag
        t_servo = F * R / eff
        row.extend([s_draw, F, t_servo])
        if t_servo > worst[0]:
            worst = (t_servo, u, R)
    t_peak, u_peak, R_peak = worst
    peak_margin = usable / t_peak if t_peak > 0 else float("inf")
    print(f"  {steps} steps through the {sweep:.0f} deg sweep, radius measured "
          f"at each:")
    for row in rows[::4]:
        print(f"    u {row[0]:4.2f}  profile {row[1]:6.1f} deg  R {row[3]:5.3f} "
              f"mm  drawn {row[4]:6.3f} mm  F {row[5]:6.2f} N  "
              f"T_servo {row[6]:6.1f} N.mm")
    print(f"  PEAK {t_peak:.1f} N.mm at u = {u_peak:.2f} (R {R_peak:.3f} mm) "
          f"against {usable:.0f} N.mm usable   margin {peak_margin:.2f}x")

    # ---- 3b. CAN THE DRUM TURN? -------------------------------------------
    # A rotating body is not checked by checking the pose it was drawn in. Every
    # static check in this file sees the drum at full cock and nothing else, so
    # the 200 deg of profile that is NOT under the cable at full cock has never
    # been tested against anything. Its swept envelope is a disc per y band -
    # the scroll band and the hub band have different radii and must not be
    # merged, or the hub's 5 mm band inherits the scroll's 7 mm reach and
    # invents collisions with the servo cradle.
    bands = []
    for nm, y0, y1 in (
            ("scroll", float(getattr(M, "WINCH_SCROLL_Y0", bd.ymin)),
             float(getattr(M, "WINCH_SCROLL_Y1", bd.ymax))),
            ("hub", float(getattr(M, "WINCH_HUB_Y0", bd.ymin)),
             float(getattr(M, "WINCH_HUB_Y1", bd.ymax)))):
        ymid = 0.5 * (y0 + y1)
        rmax = 0.0
        for a in range(0, 360, 5):
            # the OUTER radius, walking inward: _ray_radius answers from the
            # axis outward and returns nan wherever the axis is not in material,
            # which is exactly the case in the hub band - it has a bore - so
            # using it here silently skipped the hub's whole envelope.
            c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
            t = 20.0
            while t > 0.05 and not _inside_fast(drum, ax + t * c, ymid,
                                                az + t * sn):
                t -= 0.1
            if t > 0.05:
                rmax = max(rmax, t + 0.1)
        if rmax <= 0:
            continue
        env = cq.Solid.makeCylinder(rmax, y1 - y0, cq.Vector(ax, y0, az),
                                    cq.Vector(0, 1, 0))
        bands.append((nm, rmax, env))
    exempt = {dk, ck, pk, sk}
    if shaft is not None:
        exempt.add(_find(bodies, "winch_shaft")[0])
    # (round 5) THE BEARING IS NOT AN OBSTRUCTION. The drum no longer runs on the
    # shaft directly, it runs on a one-way clutch pressed into its own hub bore,
    # with a clock spring on its hub OD. Both are, geometrically, INSIDE the
    # swept envelope of the band they serve - exactly as the output shaft is,
    # which is why the shaft was already exempt. Anything a body ROTATES ON is
    # inside its own swept cylinder by construction; the envelope test is asking
    # what the drum would sweep through, and a body concentric with the drum's
    # own axis sweeps through nothing. The concentricity is the condition, and it
    # is MEASURED rather than assumed: a clutch or spring drawn off-axis stays in
    # the test and still fails it.
    for _tok in ("clutch", "rewind"):
        _bk, _bv = _find(bodies, _tok)
        if _bv is None:
            continue
        _b = bb(_bv)
        _off = math.hypot(0.5 * (_b.xmin + _b.xmax) - ax,
                          0.5 * (_b.zmin + _b.zmax) - az)
        if _off <= 0.10:
            print(f"  {_bk} is concentric with the winch axis "
                  f"({_off:.3f} mm off): it is what the drum turns ON, not "
                  f"something it turns INTO")
            exempt.add(_bk)
    hits = []
    for nm, rmax, env in bands:
        print(f"  swept envelope, {nm} band: r {rmax:.2f} mm about the shaft axis")
        for bk, bv in bodies.items():
            if bk in exempt:
                continue
            v = intersect_volume(env, bv)
            if v == v and v > 1e-6:
                hits.append((v, nm, bk))
    for v, nm, bk in sorted(hits, reverse=True):
        fail("recock", f"the drum cannot turn: its {nm} band sweeps {v:.2f} mm3 "
                       f"through {bk}. The drum was only ever checked in the one "
                       f"pose it is drawn in, which is full cock")
    if not hits:
        print(f"  the drum turns a full revolution clear of every other body")

    # ---- 4. does the sweep actually draw the stroke? ----------------------
    print(f"  cable drawn by integrating the MEASURED radius over the sweep: "
          f"{travel:.3f} mm against a {stroke:.3f} mm stroke")
    work = usable * math.radians(sweep) * eff
    margin = work / pe if pe > 0 else float("inf")
    REPORT["recock"] = dict(pe_N_mm=pe, declared=True, closed=closed,
                            usable=usable, sweep_deg=sweep,
                            r_measured_min=min(r[3] for r in rows),
                            r_measured_max=max(r[3] for r in rows),
                            cable_radius=r_cable, drawn_mm=travel,
                            stroke_mm=stroke, peak_torque=t_peak,
                            peak_margin=peak_margin, pin_journalled_mm=eng,
                            shaft_engagement_mm=shaft_eng,
                            work_N_mm=work, margin=margin,
                            steps=[[round(x, 4) for x in r] for r in rows])
    if travel + 1e-6 < stroke:
        fail("recock", f"one {sweep:.0f} deg sweep of the drawn drum draws only "
                       f"{travel:.3f} mm of cable but the carriage has to come "
                       f"back {stroke:.3f} mm. The drum is too small to re-cock "
                       f"in one sweep, so the device fires once")
    if peak_margin < SERVO_TORQUE_MARGIN:
        fail("recock", f"at u = {u_peak:.2f} of the sweep the drum demands "
                       f"{t_peak:.0f} N.mm at the servo shaft on a MEASURED "
                       f"radius of {R_peak:.3f} mm, against {usable:.0f} N.mm "
                       f"usable ({peak_margin:.2f}x, needs "
                       f"{SERVO_TORQUE_MARGIN}x): the servo stalls partway "
                       f"through every recock")
    if margin < RECOCK_MARGIN:
        fail("recock", f"recock needs {pe:.0f} N.mm of work but one {sweep:.0f} "
                       f"deg sweep at {usable:.0f} N.mm delivers {work:.0f} N.mm "
                       f"({margin:.2f}x, needs {RECOCK_MARGIN}x)")


# ------------------------- 11b. WHAT HOLDS THE CARRIAGE AT THE INSTANT OF RELEASE
# THE CHECK WHOSE ABSENCE LET A FIRING-STROKE TETHER BE DRAWN AND REPORTED AS
# multishot_working.
#
# Every other check in this file asks whether a body is in the way. None of them
# ever asked whether a body is HOLDING ON. The recock cable was inextensible,
# taut, wrapped on a drum splined to a position servo: 37.4 N reflected as
# 85 N.mm against a 451 N.mm stall, so the carriage could not move a micron -
# and the motion sweep saw no interference, because a cable that holds does not
# overlap anything. check_multishot then stepped the carriage frame forward
# through empty air and printed five clean 2.00 mL shots.
#
# So this check does not look for overlaps. It enumerates the things that resist
# the carriage over the firing stroke, states each one in newtons at the
# carriage and in N.mm about its own axis, and applies TWO gates:
#
#   GATE 1 - KINEMATIC. Anything that is an inextensible CONSTRAINT rather than
#   a drag holds the carriage outright, whatever its magnitude. A taut cable on
#   a held drum is the archetype. The only member permitted to constrain the
#   carriage at release is the SEAR, and only if its release has been certified
#   by check_servo_torque at full margin.
#
#   GATE 2 - MAGNITUDE. The sum of the drags must leave the spring a margin of
#   RELEASE_DRIVE_MARGIN. A shot that is 90% drag is not a shot.
#
# NEGATIVE CONTROL, run by hand and recorded here: setting WINCH_FREESPOOL =
# False in the model - i.e. re-drawing exactly the round-4 tether, a taut cable
# on a drum the servo holds, with no other change - must make this check fail on
# GATE 1. It does, and the measured numbers are recorded beside WINCH_FREESPOOL
# in the model.
RELEASE_DRIVE_MARGIN = 1.5


def check_release_resistance(bodies: dict) -> None:
    print("\n=== 11b. RELEASE RESISTANCE (what is holding the carriage?) ===")
    st = _spring_state(bodies)
    if st is None:
        fail("release", "no spring body: the driving force at release cannot be "
                        "measured, so nothing can be weighed against it")
        return
    F = st["force_N"]
    print(f"  driving force MEASURED off the compressed spring: {F:.2f} N")

    holders = []      # (name, why) - kinematic holds
    drags = []        # (name, N at the carriage, note)

    # ---- 1. the sear ------------------------------------------------------
    sv = REPORT.get("servo_torque") or {}
    margin = float(sv.get("margin", 0.0))
    if margin >= SERVO_TORQUE_MARGIN:
        print(f"  sear: certified release, {sv.get('m_required', 0.0):.1f} N.mm "
              f"at the pivot, {margin:.2f}x at the servo shaft - THE LEGAL HOLDER")
    else:
        holders.append(("printed/sear",
                        f"its release is not certified: {margin:.2f}x against "
                        f"the {SERVO_TORQUE_MARGIN}x this harness requires, so "
                        f"the trip servo cannot open it"))

    # ---- 2. the tether ----------------------------------------------------
    ck, cable = _find(bodies, "recock_cable")
    dk, drum = _find(bodies, "winch_drum")
    pk, pin = _find(bodies, "recock_anchor_pin")
    if cable is None or drum is None or pin is None:
        fail("release", "the recock tether is not drawn (cable, drum or anchor "
                        "pin missing), so whether it holds the carriage cannot "
                        "be measured off anything")
    else:
        ax = float(getattr(M, "WINCH_AXIS_X", float("nan")))
        az = float(getattr(M, "WINCH_AXIS_Z", float("nan")))
        bc = bb(cable)
        arm = abs(0.5 * (bc.zmin + bc.zmax) - az)
        bp = bb(pin)
        pin_x = 0.5 * (bp.xmin + bp.xmax)
        pin_z = 0.5 * (bp.zmin + bp.zmax)
        stroke = float(M.PLUNGER_STROKE)
        d0 = math.hypot(pin_x - ax, pin_z - az)
        d1 = math.hypot(pin_x + stroke - ax, pin_z - az)
        need = d1 - d0
        print(f"  tether: drawn moment arm about the winch axis {arm:.3f} mm; "
              f"the anchor pin stands {d0:.2f} mm from the axis cocked and "
              f"{d1:.2f} mm fired, so the firing stroke demands {need:+.2f} mm "
              f"of cable")
        free = bool(getattr(M, "WINCH_FREESPOOL", False))
        clutch = [k for k in bodies if "clutch" in k]
        rewind = [k for k in bodies if "rewind" in k]
        if need > 0.01 and not (free and clutch and rewind):
            missing = []
            if not free:
                missing.append("WINCH_FREESPOOL is not declared")
            if not clutch:
                missing.append("no one-way clutch body")
            if not rewind:
                missing.append("no rewind-spring body")
            reflected = F * arm
            stall = float(getattr(M, "SERVO_STALL_N_MM", 0.0))
            holders.append((ck,
                            f"the cable must lengthen {need:.2f} mm for the "
                            f"carriage to complete its stroke and there is no "
                            f"pay-out path drawn ({'; '.join(missing)}). An "
                            f"inextensible cable on a drum the servo holds "
                            f"reflects the full {F:.1f} N as {reflected:.0f} "
                            f"N.mm at the shaft against a {stall:.0f} N.mm "
                            f"stall: the servo wins and the carriage does not "
                            f"move"))
        elif need > 0.01:
            print(f"    pay-out path drawn: {', '.join(sorted(clutch + rewind))}")
            rew = float(getattr(M, "WINCH_REWIND_TORQUE_N_MM", 0.0))
            ovr = float(getattr(M, "WINCH_CLUTCH_OVERRUN_N_MM", 0.0))
            if rew <= 0.0 or ovr <= 0.0:
                fail("release", "WINCH_REWIND_TORQUE_N_MM or "
                                "WINCH_CLUTCH_OVERRUN_N_MM is not declared: a "
                                "free-spooling drum that costs nothing at all "
                                "is not a mechanism, it is an omission")
            if arm <= 1e-6:
                fail("release", "the drawn cable has no moment arm about the "
                                "winch axis, so the drum's drag cannot be "
                                "reflected onto the carriage")
            else:
                drags.append((ck, (rew + ovr) / arm,
                              f"rewind {rew:.1f} + clutch overrun {ovr:.1f} "
                              f"N.mm over a {arm:.3f} mm arm"))
        else:
            print("    the stroke does not lengthen the cable: nothing to pay out")

    # ---- 3. the sliding drags the model declares --------------------------
    for attr, note in (("RECOCK_DRAG_N", "rails, grip plates and cable lay"),
                       ("PISTON_SEAL_DRAG_N", "the piston's own seal in the bore")):
        v = getattr(M, attr, None)
        if v is None:
            fail("release", f"{attr} is not declared: the carriage is being "
                            f"given a frictionless stroke by omission")
        else:
            drags.append((attr, float(v), note))

    total = sum(d[1] for d in drags)
    ratio = (F / total) if total > 0 else float("inf")
    print("  resistances over the firing stroke:")
    for nm, n, note in drags:
        print(f"    {n:6.2f} N   {nm}  ({note})")
    print(f"    {total:6.2f} N   TOTAL DRAG   vs {F:.2f} N driving "
          f"-> {ratio:.2f}x")
    REPORT["release_resistance"] = dict(
        driving_N=F, total_drag_N=total, margin=ratio,
        drags=[[nm, round(n, 4), note] for nm, n, note in drags],
        kinematic_holders=[[nm, why] for nm, why in holders])

    for nm, why in holders:
        fail("release", f"{nm} is HOLDING the carriage at the instant of "
                        f"release: {why}. The only thing allowed to hold a "
                        f"cocked carriage is the sear, and only when its "
                        f"release is certified")
    if ratio < RELEASE_DRIVE_MARGIN:
        fail("release", f"the drags opposing the carriage total {total:.2f} N "
                        f"against {F:.2f} N of spring ({ratio:.2f}x, needs "
                        f"{RELEASE_DRIVE_MARGIN}x): the stroke is mostly "
                        f"friction, so the shot is not the spring's")


# ------------------------------------------------------- 12. wrist profile
def check_wrist_profile(bodies: dict) -> None:
    """How tall is the thing on the arm? Measured over EVERY body, printed and
    purchased, in assembly space - which is the first time a servo, a horn or a
    spring has been allowed to contribute to it."""
    print("\n=== 12. WRIST PROFILE (over every body in the assembly) ===")
    if not bodies:
        fail("profile", "no bodies to measure")
        return
    zmin = min(bb(v).zmin for v in bodies.values())
    tallest, ztop = None, -1e18
    for k, v in sorted(bodies.items()):
        z = bb(v).zmax
        if z > ztop:
            tallest, ztop = k, z
    height = ztop - zmin
    print(f"  underside z {zmin:.2f}, highest point {ztop:.2f} on {tallest}")
    print(f"  stack height {height:.2f} mm against a "
          f"{MAX_WRIST_PROFILE_MM:.0f} mm target")
    REPORT["wrist_profile"] = dict(height_mm=height, tallest=tallest,
                                   limit=MAX_WRIST_PROFILE_MM)
    if height > MAX_WRIST_PROFILE_MM:
        fail("profile", f"stack height {height:.2f} mm exceeds the "
                        f"{MAX_WRIST_PROFILE_MM:.0f} mm wrist target; the tallest "
                        f"body is {tallest} at z = {ztop:.2f}")


# --------------------------------------------- 13. piston inside the barrel
def check_piston_containment(bodies: dict) -> None:
    """A piston that merely fails to OVERLAP the barrel is not a piston in a
    barrel - it is a piston beside one.

    The barrel becomes a TUBE in Mk5, which removes two of Mk4's overlap
    failures at a stroke. That change must not be allowed to buy a quieter
    harness: this check lands with it and proves containment positively. The
    piston must be INSIDE the bore - its cross-section within the bore radius,
    its whole body between the barrel's ends - across the entire multi-shot
    travel, not merely at the pose the file was authored in."""
    print("\n=== 13. PISTON CONTAINMENT (inside the bore, not merely clear) ===")
    bk, barrel = _find(bodies, "syringe_barrel")
    pk, piston = _find(bodies, "piston")
    if barrel is None:
        fail("piston", "no syringe barrel body")
        return
    if piston is None:
        fail("piston", "no piston body. A barrel modelled as a tube with nothing "
                       "inside it produces no overlap and therefore no failure - "
                       "which is exactly the starved-harness pattern. The piston "
                       "must be present and proven contained")
        return
    bore = float(getattr(M, "SYRINGE_BORE", 0.0))
    if bore <= 0:
        fail("piston", "SYRINGE_BORE not declared")
        return
    bb_b, bb_p = bb(barrel), bb(piston)
    axis_y = getattr(M, "FLUID_Y", bb_b.center.y)
    axis_z = getattr(M, "SYRINGE_AXIS_Z", bb_b.center.z)
    stroke = float(M.PLUNGER_STROKE)
    shots = int(getattr(M, "SHOTS_PER_FILL", 1))
    total = stroke * shots
    print(f"  barrel {bk} x {bb_b.xmin:.2f}..{bb_b.xmax:.2f}, bore {bore:.2f} mm")
    print(f"  piston {pk} x {bb_p.xmin:.2f}..{bb_p.xmax:.2f}, "
          f"travel {total:.2f} mm over {shots} shots")
    # radial: the piston must fit within the bore cylinder about the fluid axis
    r_bore = bore / 2.0
    dy = max(abs(bb_p.ymax - axis_y), abs(axis_y - bb_p.ymin))
    dz = max(abs(bb_p.zmax - axis_z), abs(axis_z - bb_p.zmin))
    r_piston = max(dy, dz)
    print(f"  piston radial extent from the fluid axis {r_piston:.3f} mm "
          f"vs bore radius {r_bore:.3f} mm")
    if r_piston > r_bore + 1e-6:
        fail("piston", f"piston reaches {r_piston:.3f} mm from the fluid axis but "
                       f"the bore radius is {r_bore:.3f} mm: it is not inside the "
                       f"barrel, it is through the wall")
    # axial: at every shot the piston must still be between the barrel's ends
    for k in range(shots + 1):
        x0 = bb_p.xmin + k * stroke
        x1 = bb_p.xmax + k * stroke
        if x0 < bb_b.xmin - 1e-6 or x1 > bb_b.xmax + 1e-6:
            fail("piston", f"after {k} shot(s) the piston occupies x "
                           f"{x0:.2f}..{x1:.2f}, outside the barrel's "
                           f"{bb_b.xmin:.2f}..{bb_b.xmax:.2f}: it leaves the bore "
                           f"before the cartridge is empty")
            break
    else:
        print(f"  piston stays between the barrel ends for all {shots} shots")
    REPORT["piston_containment"] = dict(bore_r=r_bore, piston_r=r_piston,
                                        barrel_x=[bb_b.xmin, bb_b.xmax],
                                        piston_x=[bb_p.xmin, bb_p.xmax],
                                        total_travel=total)


def check_physics() -> None:
    print("\n=== 6. PHYSICS (derived from stored energy) ===")
    E = getattr(M, "SPRING_RELEASE_ENERGY_J", None) or getattr(M, "SPRING_ENERGY_J")
    V_m3 = getattr(M, 'SHOT_VOLUME_ML', 2.0) * 1e-6
    stroke_m = M.PLUNGER_STROKE / 1000.0
    A_p = math.pi * (getattr(M, "SYRINGE_BORE_DIAMETER", getattr(M, "SYRINGE_BORE", 12.45)) / 2000.0) ** 2

    # Real 8 ga cannula ID, not the model's "conservative effective" 3.0 mm.
    real_id_mm = 3.429
    for label, d_mm, L_mm in (("model 3.0 mm outlet", getattr(M, "ORIFICE_DIAMETER", getattr(M, "OUTLET_BORE", 3.0)), getattr(M, "NOZZLE_LENGTH", getattr(M, "OUTLET_LENGTH", 12.0))),
                              ("real 8 ga ID 3.429", real_id_mm, getattr(M, "NOZZLE_LENGTH", getattr(M, "OUTLET_LENGTH", 12.0))),
                              ("outlet as designed", getattr(M, "OUTLET_BORE", 3.0), getattr(M, "OUTLET_LENGTH", 12.0))):
        r = d_mm / 2000.0
        A_o = math.pi * r * r
        # velocity implied by the DECLARED shot time
        v_declared = (V_m3 / M.SHOT_TIME_S) / A_o
        rng = v_declared ** 2 / 9.81
        # energy actually required to push that flow through this restriction
        Q = V_m3 / M.SHOT_TIME_S
        mu = 0.5  # Pa.s, 1:1 thinned Fabri-Tac, the model's own figure
        dP = 8 * mu * (L_mm / 1000.0) * Q / (math.pi * r ** 4)
        work = dP * V_m3
        print(f"  {label:<22} A_o={A_o*1e6:6.2f} mm2  v={v_declared:5.2f} m/s  "
              f"range={rng:5.2f} m  dP={dP/1000:7.1f} kPa  work={work:6.4f} J")
        REPORT.setdefault("physics", {})[label] = dict(
            area_mm2=A_o * 1e6, v_m_s=v_declared, range_m=rng,
            dP_kPa=dP / 1000, work_J=work)
        if label != "model 3.0 mm outlet" and work > E:
            fail("physics", f"{label}: needs {work:.4f} J but the spring stores {E:.4f} J")
        if label == "real 8 ga ID 3.429" and rng < 1.5:
            fail("physics", f"real orifice gives {rng:.2f} m range (target >= 1.5 m)")
    print(f"  spring stores {E:.4f} J   cocked {getattr(M, "SPRING_COCKED_FORCE_N", getattr(M, "SPRING_PEAK_N", 0.0)):.2f} N   "
          f"stroke {M.PLUNGER_STROKE:.3f} mm")
    derived = hasattr(M, "FLOW_RATE_M3_S") and hasattr(M, "FLOW_WORK_J")
    if derived:
        print(f"  shot time {M.SHOT_TIME_S*1000:.1f} ms is DERIVED from flow rate; "
              f"work {M.FLOW_WORK_J:.4f} J vs stored {E:.4f} J "
              f"(margin {E/M.FLOW_WORK_J:.2f}x)")
    else:
        print(f"  NOTE: SHOT_TIME_S = {M.SHOT_TIME_S} is a declared constant.")
        warn("physics", "SHOT_TIME_S is declared, not derived from the energy balance")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--model", default=_MODEL, help="model module to audit (default: webshooter_mk4)")
    a = ap.parse_args()
    sec_step = 2.0 if a.quick else SECTION_STEP
    lay_step = 1.0 if a.quick else LAYER_STEP
    swp_step = 1.0 if a.quick else SWEEP_STEP

    print("Independent verification —", os.path.basename(M.__file__))
    print("thresholds: wall>=%.2f ligament>=%.2f section>=%.1f first_layer>=%.0f "
          "island<=%.1f clearance>=%.2f"
          % (MIN_WALL, MIN_LIGAMENT, MIN_SECTION_AREA, MIN_FIRST_LAYER,
             MAX_UNSUPPORTED_ISLAND, MIN_CLEARANCE))

    # Printed parts are checked for printability in their OWN frame (that is how
    # they reach the bed) but for clearance in ASSEMBLY space. Conflating the two
    # was this harness's own first bug: every part overlapped every other part
    # because they all sit at the origin until placed.
    parts = {}      # local frame, for print checks
    assembled = {}  # world frame, for clearance and motion
    try:
        for name, entry in M.printed_parts.items():
            parts[name] = solid_of(entry.shape)
            assembled[f"printed/{name}"] = entry.shape.moved(entry.location)
    except Exception as e:
        fail("build", f"printed parts: {e}")

    if hasattr(M, "mockups"):
        try:
            for name, entry in M.mockups.items():
                assembled[f"mockup/{name}"] = placed(entry)
        except Exception as e:
            fail("build", f"mockups: {e}")

    bodies = assembled

    check_parts(parts)
    check_thin_features(parts, sec_step)
    check_printability(parts, lay_step)
    check_clearances(bodies)

    # ONE frame map, read by every kinematic check (see frame_of()). The old
    # token match here - "carriage" or "plunger" or "moving" in the name - was
    # the second, contradictory definition of what moves: it made the drive grip
    # plate a static obstacle in the sweep while check_multishot treated it as
    # part of the carriage. Both checks now partition the assembly the same way.
    moving = {k: v for k, v in bodies.items()
              if frame_of(k) in (FRAME_CARRIAGE, FRAME_ROD)}
    if moving:
        # ORDER MATTERS NOW. check_motion no longer deletes the pawl from the
        # sweep by name; it poses it at the release angle instead, so that angle
        # has to be certified first. 5d then drives the return stroke from the
        # rest pose 5c measures.
        check_sear_release(bodies, M.PLUNGER_STROKE, max(swp_step, 1.0))
        check_sear_rest_pose(bodies)
        check_cocking_stroke(bodies, M.PLUNGER_STROKE, swp_step)
        check_motion(bodies, M.PLUNGER_STROKE, swp_step,
                     REPORT.get("sear_release_deg"))
    else:
        fail("motion", "the frame map puts no body in a moving frame, so the "
                       "firing stroke was never swept. An unswept stroke is not "
                       "a clear one")
    check_physics()
    # Mk5 mechanism checks. These run unconditionally and FAIL when the
    # body they need is absent - never skip, never soften.
    check_spring_buckling(bodies)
    check_servo_torque(bodies)
    check_one_way_grip(bodies)
    check_grip_release(bodies, swp_step)
    check_multishot(bodies, swp_step, REPORT.get("sear_release_deg"))
    check_recock_budget(bodies)
    check_release_resistance(bodies)
    check_wrist_profile(bodies)
    check_piston_containment(bodies)

    print("\n" + "=" * 72)
    if WARNINGS:
        print(f"WARNINGS ({len(WARNINGS)})")
        for w in WARNINGS:
            print("  " + w)
    print(f"\nFAILURES ({len(FAILURES)})")
    for f in FAILURES:
        print("  " + f)
    if not FAILURES:
        print("  none — every independent check passed")
    REPORT["failures"] = FAILURES
    REPORT["warnings"] = WARNINGS
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(REPORT, fh, indent=1, default=str)
        print(f"\nwrote {a.json}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)
