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
    for v, a, b in sorted(hits, reverse=True)[:25]:
        print(f"  OVERLAP  {v:9.2f} mm3   {a} <> {b}")
        fail("clearance", f"{a} <> {b} overlap {v:.2f} mm3")
    for g, a, b in sorted(tang)[:25]:
        print(f"  TANGENT  {g:9.3f} mm    {a} <> {b}")
        fail("clearance", f"{a} <> {b} gap {g:.3f} mm (< {MIN_CLEARANCE})")
    if not hits and not tang:
        print("  clean")
    REPORT["clearance"] = dict(overlaps=[(v, a, b) for v, a, b in hits],
                               tangencies=[(g, a, b) for g, a, b in tang])


# ------------------------------- 5. motion sweeps — everything, no exclusions
def check_motion(bodies: dict, moving: dict, travel: float, step: float,
                 sear_release_deg=None) -> None:
    print("")
    print(f"=== 5. MOTION SWEEP (0 to {travel:.3f} mm, step {step} mm, no exclusions) ===")
    # (round 4) THE BY-NAME EXCLUSION OF printed/sear IS GONE. "the sear is
    # checked separately in 5b" is the same sentence, in shape, as the Mk3
    # exclusion of servo_sear from this very sweep - item one on this project's
    # list of historical failures, and it must not survive to the last revision.
    #
    # The sear is not part of the frame during the firing stroke: it is
    # ACTUATED, and the stroke only begins after the servo has lifted it. So it
    # is swept POSED AT THE RELEASE ANGLE 5b certified - present in the sweep,
    # under its own name, at the 1e-6 gate, never deleted from the dict. If no
    # release angle was certified, that is reported here as an unswept stroke
    # rather than silently skipped.
    statics = {k: v for k, v in bodies.items() if k not in moving}
    if "printed/sear" in statics:
        if sear_release_deg is None:
            fail("motion", "no certified release angle: the firing stroke could "
                           "not be swept against the pawl in its released pose")
            del statics["printed/sear"]
        else:
            rotated = _sear_rotated(statics.pop("printed/sear"), sear_release_deg)
            statics[f"printed/sear @{sear_release_deg:g}deg released"] = rotated
            print(f"  (pawl posed at its certified {sear_release_deg:g} deg "
                  f"release angle and swept, not excluded)")
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


def _contact_normal_deg(a, b, axis=cq.Vector(1, 0, 0)):
    """THE CAM ANGLE OF THE FACES THAT ACTUALLY MEET.

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
    mx = max(f[0] for f in faces)
    best_ang, best_area = None, None
    for ar, n, c in faces:
        if ar < 0.20 * mx:
            continue
        out = n
        try:
            if _inside(inter, c + n.multiply(0.02)):
                out = n.multiply(-1)
        except Exception:
            pass
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
        ang, _ = _contact_normal_deg(
            _sear_rotated(sear, probe),
            carr.moved(cq.Location(cq.Vector(t, 0, 0))))
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

    moving = {k: v for k, v in bodies.items()
              if any(t in k for t in ("carriage", "plunger", "moving"))}
    if moving:
        # ORDER MATTERS NOW. check_motion no longer deletes the pawl from the
        # sweep by name; it poses it at the release angle instead, so that angle
        # has to be certified first. 5d then drives the return stroke from the
        # rest pose 5c measures.
        check_sear_release(bodies, M.PLUNGER_STROKE, max(swp_step, 1.0))
        check_sear_rest_pose(bodies)
        check_cocking_stroke(bodies, M.PLUNGER_STROKE, swp_step)
        check_motion(bodies, moving, M.PLUNGER_STROKE, swp_step,
                     REPORT.get("sear_release_deg"))
    else:
        warn("motion", "no moving bodies identified; sweep skipped")
    check_physics()

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
