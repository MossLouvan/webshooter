#!/usr/bin/env python3
"""
bl — a command-line driver for the Web-Shooter Blender scene.

Every subcommand runs Blender headlessly against a .blend and prints plain text,
so the whole scene is inspectable and controllable without opening the GUI.

    python bl.py <command> [options]

INSPECT
    ls                       list objects: name, collection, dims, location
    tree                     collections and their contents
    info <name>              everything about one object
    stats                    scene summary: counts, bounds, materials, frame range
    measure <a> <b>          min gap and centre distance between two objects
    bounds [--of NAME...]    bounding box of the scene or named objects
    materials                materials and what uses them
    anim                     frame range, markers, and which objects are keyframed

CONTROL
    show <name>...           make objects visible (accepts collections)
    hide <name>...           hide objects (accepts collections)
    isolate <name>...        show only these, hide everything else
    reset                    unhide everything

RENDER
    render [--out F] [--cam NAME] [--frame N] [--res WxH] [--samples N]
    turntable [--frames N] [--out DIR]     orbit render sequence
    views [--out DIR]        render from every camera in the scene
    shot --az A --el E [--dist D]          render from an arbitrary angle

EXPORT
    export --fmt {stl,obj,glb,ply} [--out F] [--only NAME...]
    screenshot-viewport      solid-shaded quick look, no lighting setup

Global: --blend FILE (default: webshooter_mk3_visualization.blend)
        --blender PATH (default: the Windows 5.2 install)
        --dry  print the generated Blender script instead of running it
"""
from __future__ import annotations
import argparse
import os
import shlex
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BLEND = os.path.join(HERE, "webshooter_mk3_visualization.blend")
DEFAULT_BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# ---------------------------------------------------------------- preamble
# Injected at the top of every generated script. Gives each snippet a small
# vocabulary for finding objects and reporting geometry.
PREAMBLE = r'''
import bpy, sys, json, math
from mathutils import Vector

ARGV = json.loads(sys.argv[sys.argv.index("--blargs") + 1])

def objs():
    return [o for o in bpy.data.objects]

def mesh_objs():
    return [o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices)]

def norm(s):
    """Fold to lowercase alphanumerics so em-dashes, spacing and punctuation
    never stand between a user's pattern and a match."""
    return "".join(ch for ch in s.lower() if ch.isalnum())

def find(pattern, meshes_only=False):
    """Match objects by exact name, normalized substring, or collection."""
    pool = mesh_objs() if meshes_only else objs()
    p = pattern.lower()
    pn = norm(pattern)
    exact = [o for o in pool if o.name.lower() == p]
    if exact:
        return exact
    # collection: exact, then normalized substring
    coll = bpy.data.collections.get(pattern)
    if coll is None:
        cands = [c for c in bpy.data.collections if norm(c.name) == pn]
        if not cands:
            cands = [c for c in bpy.data.collections if pn and pn in norm(c.name)]
        if len(cands) == 1:
            coll = cands[0]
        elif len(cands) > 1:
            names = set()
            for c in cands:
                names |= {o.name for o in c.all_objects}
            return [o for o in pool if o.name in names]
    if coll is not None:
        names = {o.name for o in coll.all_objects}
        return [o for o in pool if o.name in names]
    return [o for o in pool if pn and pn in norm(o.name)]

def find_many(patterns, meshes_only=False):
    out, seen = [], set()
    for pat in patterns:
        for o in find(pat, meshes_only):
            if o.name not in seen:
                seen.add(o.name)
                out.append(o)
    return out

def world_verts(o):
    m = o.matrix_world
    return [m @ v.co for v in o.data.vertices]

def bbox(o):
    vs = world_verts(o)
    xs = [v.x for v in vs]; ys = [v.y for v in vs]; zs = [v.z for v in vs]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

def dims(o):
    x0, x1, y0, y1, z0, z1 = bbox(o)
    return (x1 - x0, y1 - y0, z1 - z0)

def colls_of(o):
    return ", ".join(c.name for c in o.users_collection) or "-"

def scene_bounds(items=None):
    if items is None:
        items = mesh_objs()
    xs, ys, zs = [], [], []
    for o in items:
        x0, x1, y0, y1, z0, z1 = bbox(o)
        xs += [x0, x1]; ys += [y0, y1]; zs += [z0, z1]
    if not xs:
        return None
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

def set_visible(o, vis):
    o.hide_viewport = not vis
    o.hide_render = not vis
'''

# ---------------------------------------------------------------- snippets
SNIPPETS: dict[str, str] = {}

SNIPPETS["ls"] = r'''
rows = []
for o in sorted(objs(), key=lambda x: x.name):
    if o.type == "MESH" and len(o.data.vertices):
        d = dims(o)
        dtxt = "%7.1f x %6.1f x %6.1f" % d
        loc = "%7.1f %7.1f %7.1f" % tuple(o.location)
    else:
        dtxt = "%25s" % o.type
        loc = "%7.1f %7.1f %7.1f" % tuple(o.location)
    vis = " " if not o.hide_viewport else "h"
    rows.append("%s %-42s %-22s %s  %s" % (vis, o.name[:42], colls_of(o)[:22], dtxt, loc))
print("%-1s %-42s %-22s %25s  %s" % ("", "NAME", "COLLECTION", "DIMS (mm)", "LOCATION"))
print("-" * 118)
print("\n".join(rows))
print("-" * 118)
print("%d objects (%d mesh)   'h' = hidden" % (len(objs()), len(mesh_objs())))
'''

SNIPPETS["tree"] = r'''
def walk(c, depth=0):
    own = [o for o in c.objects]
    print("%s%s  (%d direct, %d total)" % ("  " * depth, c.name, len(own), len(c.all_objects)))
    for o in sorted(own, key=lambda x: x.name):
        mark = " " if not o.hide_viewport else "h"
        print("%s  %s %s" % ("  " * depth, mark, o.name))
    for ch in c.children:
        walk(ch, depth + 1)
for c in bpy.context.scene.collection.children:
    walk(c)
loose = [o for o in bpy.context.scene.collection.objects]
if loose:
    print("(scene root)")
    for o in loose:
        print("    %s" % o.name)
'''

SNIPPETS["info"] = r'''
for o in find_many(ARGV["names"]):
    print("=" * 70)
    print("name        %s" % o.name)
    print("type        %s" % o.type)
    print("collections %s" % colls_of(o))
    print("visible     viewport=%s render=%s" % (not o.hide_viewport, not o.hide_render))
    print("location    %.3f %.3f %.3f" % tuple(o.location))
    print("rotation    %.2f %.2f %.2f deg" % tuple(math.degrees(a) for a in o.rotation_euler))
    print("scale       %.3f %.3f %.3f" % tuple(o.scale))
    if o.type == "MESH" and len(o.data.vertices):
        x0, x1, y0, y1, z0, z1 = bbox(o)
        print("dims        %.2f x %.2f x %.2f mm" % dims(o))
        print("bbox X      %.2f .. %.2f" % (x0, x1))
        print("bbox Y      %.2f .. %.2f" % (y0, y1))
        print("bbox Z      %.2f .. %.2f" % (z0, z1))
        print("mesh        %d verts, %d faces" % (len(o.data.vertices), len(o.data.polygons)))
        print("materials   %s" % (", ".join(m.name for m in o.data.materials if m) or "-"))
    if o.animation_data and o.animation_data.action:
        fcs = o.animation_data.action.fcurves
        kf = sorted({int(k.co[0]) for fc in fcs for k in fc.keyframe_points})
        print("keyframes   %s" % (kf if len(kf) < 20 else "%d keys %d..%d" % (len(kf), kf[0], kf[-1])))
    for c in o.constraints:
        print("constraint  %s -> %s" % (c.type, getattr(c, "target", None)))
'''

SNIPPETS["stats"] = r'''
sc = bpy.context.scene
print("blend        %s" % bpy.data.filepath)
print("objects      %d total, %d mesh, %d cameras, %d lights"
      % (len(objs()),
         len(mesh_objs()),
         len([o for o in objs() if o.type == "CAMERA"]),
         len([o for o in objs() if o.type == "LIGHT"])))
print("collections  %s" % ", ".join(c.name for c in bpy.data.collections))
print("materials    %d" % len(bpy.data.materials))
print("frames       %d .. %d (current %d)  fps=%s" % (sc.frame_start, sc.frame_end, sc.frame_current, sc.render.fps))
mk = sorted(sc.timeline_markers, key=lambda m: m.frame)
if mk:
    print("markers      %s" % "; ".join("%d:%s" % (m.frame, m.name) for m in mk))
print("engine       %s   resolution %dx%d" % (sc.render.engine, sc.render.resolution_x, sc.render.resolution_y))
print("cameras      %s" % ", ".join(o.name for o in objs() if o.type == "CAMERA"))
b = scene_bounds()
if b:
    print("bounds       X %.1f..%.1f   Y %.1f..%.1f   Z %.1f..%.1f" % b)
    print("size         %.1f x %.1f x %.1f mm" % (b[1]-b[0], b[3]-b[2], b[5]-b[4]))
anim = [o.name for o in objs() if o.animation_data and o.animation_data.action]
print("animated     %s" % (", ".join(anim) if anim else "none"))
'''

SNIPPETS["measure"] = r'''
import mathutils
a_objs = find(ARGV["a"], True)
b_objs = find(ARGV["b"], True)
if not a_objs or not b_objs:
    print("no match: %s -> %d, %s -> %d" % (ARGV["a"], len(a_objs), ARGV["b"], len(b_objs)))
else:
    for A in a_objs:
        for B in b_objs:
            if A.name == B.name:
                continue
            va = world_verts(A); vb = world_verts(B)
            # coarse bbox gap first
            ba, bb_ = bbox(A), bbox(B)
            gap_axis = []
            for i in range(3):
                lo_a, hi_a = ba[i*2], ba[i*2+1]
                lo_b, hi_b = bb_[i*2], bb_[i*2+1]
                gap_axis.append(max(0.0, max(lo_a - hi_b, lo_b - hi_a)))
            bbox_gap = math.sqrt(sum(g*g for g in gap_axis))
            # true min vertex distance (sampled if large)
            step_a = max(1, len(va) // 3000)
            step_b = max(1, len(vb) // 3000)
            best = 1e18
            for p in va[::step_a]:
                for q in vb[::step_b]:
                    d = (p - q).length
                    if d < best:
                        best = d
            ca = sum(va, Vector()) / len(va)
            cb = sum(vb, Vector()) / len(vb)
            print("%-34s <> %-34s  bbox_gap=%8.3f  min_vert=%8.3f  centres=%8.3f"
                  % (A.name[:34], B.name[:34], bbox_gap, best, (ca - cb).length))
'''

SNIPPETS["bounds"] = r'''
names = ARGV.get("of") or []
items = find_many(names, True) if names else mesh_objs()
if names and not items:
    print("no objects matched: %s" % ", ".join(names))
    items = []
b = scene_bounds(items)
if not b:
    print("nothing to measure")
else:
    print("objects  %d" % len(items))
    print("X  %9.2f .. %9.2f   (%8.2f)" % (b[0], b[1], b[1]-b[0]))
    print("Y  %9.2f .. %9.2f   (%8.2f)" % (b[2], b[3], b[3]-b[2]))
    print("Z  %9.2f .. %9.2f   (%8.2f)" % (b[4], b[5], b[5]-b[4]))
'''

SNIPPETS["materials"] = r'''
for m in sorted(bpy.data.materials, key=lambda x: x.name):
    users = [o.name for o in mesh_objs() if m.name in [x.name for x in o.data.materials if x]]
    base = alpha = None
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                base = tuple(round(c, 3) for c in n.inputs["Base Color"].default_value[:3])
                alpha = round(n.inputs["Alpha"].default_value, 3)
                break
    print("%-28s rgb=%-24s alpha=%-6s  %d users" % (m.name[:28], base, alpha, len(users)))
    for u in users[:6]:
        print("      %s" % u)
    if len(users) > 6:
        print("      ... and %d more" % (len(users) - 6))
'''

SNIPPETS["anim"] = r'''
sc = bpy.context.scene
print("frames %d..%d at %s fps  (current %d)" % (sc.frame_start, sc.frame_end, sc.render.fps, sc.frame_current))
mk = sorted(sc.timeline_markers, key=lambda m: m.frame)
if mk:
    print("\nmarkers:")
    for m in mk:
        print("  %4d  %s" % (m.frame, m.name))
print("\nanimated objects:")
any_anim = False
for o in sorted(objs(), key=lambda x: x.name):
    if o.animation_data and o.animation_data.action:
        any_anim = True
        fcs = o.animation_data.action.fcurves
        keys = sorted({int(k.co[0]) for fc in fcs for k in fc.keyframe_points})
        paths = sorted({fc.data_path for fc in fcs})
        print("  %-40s %-28s keys %d..%d (%d)"
              % (o.name[:40], ",".join(paths)[:28], keys[0], keys[-1], len(keys)))
if not any_anim:
    print("  none")
'''

SNIPPETS["visibility"] = r'''
mode = ARGV["mode"]
targets = find_many(ARGV["names"]) if ARGV.get("names") else []
if mode == "reset":
    for o in objs():
        set_visible(o, True)
    for c in bpy.data.collections:
        c.hide_viewport = False
        c.hide_render = False
    print("all objects and collections visible")
elif mode == "isolate":
    keep = {o.name for o in targets}
    for o in mesh_objs():
        set_visible(o, o.name in keep)
    print("isolated %d object(s):" % len(keep))
    for n in sorted(keep):
        print("   %s" % n)
else:
    vis = (mode == "show")
    for o in targets:
        set_visible(o, vis)
    print("%s %d object(s)" % ("showed" if vis else "hid", len(targets)))
    for o in targets:
        print("   %s" % o.name)
bpy.ops.wm.save_mainfile()
'''

SNIPPETS["render"] = r'''
sc = bpy.context.scene
if ARGV.get("cam"):
    cams = [o for o in objs() if o.type == "CAMERA" and ARGV["cam"].lower() in o.name.lower()]
    if cams:
        sc.camera = cams[0]
        print("camera: %s" % cams[0].name)
    else:
        print("no camera matching %r; using %s" % (ARGV["cam"], sc.camera.name if sc.camera else None))
if ARGV.get("frame") is not None:
    sc.frame_set(int(ARGV["frame"]))
if ARGV.get("res"):
    w, h = ARGV["res"].lower().split("x")
    sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
if ARGV.get("samples"):
    try:
        sc.eevee.taa_render_samples = int(ARGV["samples"])
    except Exception:
        pass
sc.render.filepath = ARGV["out"]
print("rendering frame %d at %dx%d -> %s"
      % (sc.frame_current, sc.render.resolution_x, sc.render.resolution_y, ARGV["out"]))
bpy.ops.render.render(write_still=True)
print("done")
'''

SNIPPETS["shot"] = r'''
sc = bpy.context.scene
b = scene_bounds()
cx, cy, cz = (b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2
span = max(b[1]-b[0], b[3]-b[2], b[5]-b[4])
dist = float(ARGV.get("dist") or span * 2.0)
az = math.radians(float(ARGV["az"]))
el = math.radians(float(ARGV["el"]))
x = cx + dist * math.cos(el) * math.cos(az)
y = cy + dist * math.cos(el) * math.sin(az)
z = cz + dist * math.sin(el)
cam_data = bpy.data.cameras.new("bl_shot")
cam_data.lens = float(ARGV.get("lens") or 50)
cam = bpy.data.objects.new("bl_shot", cam_data)
sc.collection.objects.link(cam)
cam.location = (x, y, z)
tgt = bpy.data.objects.new("bl_shot_aim", None)
sc.collection.objects.link(tgt)
tgt.location = (cx, cy, cz)
c = cam.constraints.new("TRACK_TO")
c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
sc.camera = cam
if ARGV.get("frame") is not None:
    sc.frame_set(int(ARGV["frame"]))
if ARGV.get("res"):
    w, h = ARGV["res"].lower().split("x")
    sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
sc.render.filepath = ARGV["out"]
print("az=%s el=%s dist=%.1f -> %s" % (ARGV["az"], ARGV["el"], dist, ARGV["out"]))
bpy.ops.render.render(write_still=True)
print("done")
'''

SNIPPETS["turntable"] = r'''
import os
sc = bpy.context.scene
b = scene_bounds()
cx, cy, cz = (b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2
span = max(b[1]-b[0], b[3]-b[2], b[5]-b[4])
dist = float(ARGV.get("dist") or span * 2.0)
el = math.radians(float(ARGV.get("el") or 25))
n = int(ARGV.get("frames") or 24)
outdir = ARGV["out"]
os.makedirs(outdir, exist_ok=True)
cam_data = bpy.data.cameras.new("bl_tt")
cam_data.lens = float(ARGV.get("lens") or 50)
cam = bpy.data.objects.new("bl_tt", cam_data)
sc.collection.objects.link(cam)
tgt = bpy.data.objects.new("bl_tt_aim", None)
sc.collection.objects.link(tgt)
tgt.location = (cx, cy, cz)
c = cam.constraints.new("TRACK_TO")
c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
sc.camera = cam
if ARGV.get("frame") is not None:
    sc.frame_set(int(ARGV["frame"]))
for i in range(n):
    az = 2 * math.pi * i / n
    cam.location = (cx + dist*math.cos(el)*math.cos(az),
                    cy + dist*math.cos(el)*math.sin(az),
                    cz + dist*math.sin(el))
    sc.render.filepath = os.path.join(outdir, "tt_%03d.png" % i)
    bpy.ops.render.render(write_still=True)
    print("  %d/%d  az=%.0f" % (i+1, n, math.degrees(az)))
print("wrote %d frames to %s" % (n, outdir))
'''

SNIPPETS["views"] = r'''
import os
sc = bpy.context.scene
outdir = ARGV["out"]
os.makedirs(outdir, exist_ok=True)
cams = [o for o in objs() if o.type == "CAMERA"]
if not cams:
    print("no cameras in scene")
for cam in cams:
    sc.camera = cam
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in cam.name)
    sc.render.filepath = os.path.join(outdir, "view_%s.png" % safe)
    bpy.ops.render.render(write_still=True)
    print("  %s -> %s" % (cam.name, sc.render.filepath))
print("done")
'''

SNIPPETS["export"] = r'''
sel = find_many(ARGV["only"], True) if ARGV.get("only") else mesh_objs()
bpy.ops.object.select_all(action="DESELECT")
for o in sel:
    o.select_set(True)
bpy.context.view_layer.objects.active = sel[0] if sel else None
fmt = ARGV["fmt"]; out = ARGV["out"]
print("exporting %d object(s) as %s -> %s" % (len(sel), fmt, out))
if fmt == "stl":
    try:
        bpy.ops.wm.stl_export(filepath=out, export_selected_objects=True)
    except AttributeError:
        bpy.ops.export_mesh.stl(filepath=out, use_selection=True)
elif fmt == "obj":
    try:
        bpy.ops.wm.obj_export(filepath=out, export_selected_objects=True)
    except AttributeError:
        bpy.ops.export_scene.obj(filepath=out, use_selection=True)
elif fmt == "glb":
    bpy.ops.export_scene.gltf(filepath=out, use_selection=True, export_format="GLB")
elif fmt == "ply":
    try:
        bpy.ops.wm.ply_export(filepath=out, export_selected_objects=True)
    except AttributeError:
        bpy.ops.export_mesh.ply(filepath=out, use_selection=True)
print("done")
'''


def build_script(kind: str, argv: dict) -> str:
    return PREAMBLE + "\n" + SNIPPETS[kind]


def run(blender: str, blend: str, kind: str, argv: dict, dry: bool) -> int:
    script = build_script(kind, argv)
    if dry:
        print(script)
        return 0
    if not os.path.exists(blend):
        print("blend file not found: %s" % blend, file=sys.stderr)
        return 2
    fd, path = tempfile.mkstemp(suffix=".py", prefix="bl_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(script)
    try:
        import json as _json
        cmd = [blender, "-b", blend, "--python", path, "--", "--blargs", _json.dumps(argv)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        out = proc.stdout
        # Blender is chatty; keep everything after our marker-free preamble noise
        lines = [ln for ln in out.splitlines()
                 if not ln.startswith(("Blender ", "Read blend:", "Info: ", "Fra:"))
                 and "Warning: " not in ln
                 and ln.strip() != ""]
        print("\n".join(lines))
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr[-4000:])
        return proc.returncode
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def main() -> int:
    p = argparse.ArgumentParser(
        prog="bl", description="Command-line driver for the Web-Shooter Blender scene.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--blend", default=DEFAULT_BLEND)
    p.add_argument("--blender", default=DEFAULT_BLENDER)
    p.add_argument("--dry", action="store_true", help="print the generated script, do not run")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ls")
    sub.add_parser("tree")
    sub.add_parser("stats")
    sub.add_parser("materials")
    sub.add_parser("anim")
    sub.add_parser("reset")

    q = sub.add_parser("info");    q.add_argument("names", nargs="+")
    q = sub.add_parser("show");    q.add_argument("names", nargs="+")
    q = sub.add_parser("hide");    q.add_argument("names", nargs="+")
    q = sub.add_parser("isolate"); q.add_argument("names", nargs="+")

    q = sub.add_parser("measure"); q.add_argument("a"); q.add_argument("b")
    q = sub.add_parser("bounds");  q.add_argument("--of", nargs="*", default=[])

    q = sub.add_parser("render")
    q.add_argument("--out", default=os.path.join(HERE, "bl_render.png"))
    q.add_argument("--cam"); q.add_argument("--frame", type=int)
    q.add_argument("--res"); q.add_argument("--samples", type=int)

    q = sub.add_parser("shot")
    q.add_argument("--az", required=True); q.add_argument("--el", required=True)
    q.add_argument("--dist"); q.add_argument("--lens"); q.add_argument("--frame", type=int)
    q.add_argument("--res"); q.add_argument("--out", default=os.path.join(HERE, "bl_shot.png"))

    q = sub.add_parser("turntable")
    q.add_argument("--frames", type=int, default=24); q.add_argument("--el", default="25")
    q.add_argument("--dist"); q.add_argument("--lens"); q.add_argument("--frame", type=int)
    q.add_argument("--out", default=os.path.join(HERE, "turntable"))

    q = sub.add_parser("views")
    q.add_argument("--out", default=os.path.join(HERE, "views"))

    q = sub.add_parser("export")
    q.add_argument("--fmt", choices=["stl", "obj", "glb", "ply"], required=True)
    q.add_argument("--out"); q.add_argument("--only", nargs="*", default=[])

    a = p.parse_args()
    argv = {k: v for k, v in vars(a).items()
            if k not in ("cmd", "blend", "blender", "dry")}

    kind = a.cmd
    if kind in ("show", "hide", "isolate", "reset"):
        argv["mode"] = kind
        argv.setdefault("names", [])
        kind = "visibility"
    if a.cmd == "export" and not argv.get("out"):
        argv["out"] = os.path.join(HERE, "bl_export." + a.fmt)

    return run(a.blender, a.blend, kind, argv, a.dry)


if __name__ == "__main__":
    sys.exit(main())
