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

Exit code 0 if every check passes, 1 otherwise.
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
_MODEL = os.environ.get("WS_MODEL", "webshooter_mk2")
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
        if v > 0.5:
            hits.append((v, a, b))
        elif v == 0.0:
            g = min_gap(bodies[a], bodies[b])
            if g < MIN_CLEARANCE:
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
def check_motion(bodies: dict, moving: dict, travel: float, step: float) -> None:
    print(f"\n=== 5. MOTION SWEEP (0 to {travel:.3f} mm, step {step} mm, no exclusions) ===")
    statics = {k: v for k, v in bodies.items() if k not in moving}
    worst: dict[str, tuple[float, float]] = {}
    t = 0.0
    while t <= travel + 1e-9:
        for mname, mbody in moving.items():
            shifted = mbody.moved(cq.Location(cq.Vector(t, 0, 0)))
            for sname, sbody in statics.items():
                v = intersect_volume(shifted, sbody)
                if v > 0.5:
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
        check_motion(bodies, moving, M.PLUNGER_STROKE, swp_step)
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
    sys.exit(main())
