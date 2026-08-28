"""Build the Mk4 Blender scene from mk4_assembly_stl/.

    blender -b --python build_mk4_viz.py      # renders + saves the .blend
    blender    --python build_mk4_viz.py      # opens it

Cyan = printed. Amber = purchased. Labels carry leader lines and say what a part
DOES, not just what it is called.
"""
import bpy, os, math, glob

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "mk4_assembly_stl")

# key -> (label, role, rgba, alpha, collection)
INFO = {
    "print_baseplate":        ("Baseplate", "PRINTED — frame, rails, cradle", (.35,.62,.75,1), .28, "1 Printed"),
    "print_carriage":         ("Carriage", "PRINTED — spring pushes this", (.30,.70,.85,1), 1, "1 Printed"),
    "print_sear":             ("Sear", "PRINTED — holds the cocked spring", (.30,.70,.85,1), 1, "1 Printed"),
    "print_outlet_adapter":   ("Outlet adapter", "PRINTED — replaces the cut Luer, 4 mm bore", (.30,.70,.85,1), 1, "1 Printed"),
    "print_switch_pod":       ("Palm switch pod", "PRINTED — trigger, two middle fingers", (.30,.70,.85,1), 1, "1 Printed"),
    "mock_syringe_5ml_barrel":  ("5 mL cartridge", "BUY — reservoir, pump and seal in one", (.85,.88,.92,1), .38, "2 Purchased"),
    "mock_syringe_plunger":     ("Plunger", "BUY — driven 16.43 mm", (.90,.66,.28,1), 1, "2 Purchased"),
    "mock_plunger_thumb_flange":("Thumb flange", "BUY — what the carriage pushes", (.90,.66,.28,1), 1, "2 Purchased"),
    "mock_compression_spring":  ("Compression spring", "BUY — stores 0.133 J", (.86,.55,.20,1), 1, "2 Purchased"),
    "mock_muzzle_tube":         ("Muzzle", "BUY — brass, the spinneret", (.85,.68,.28,1), 1, "2 Purchased"),
    "mock_lipo_2000mah":        ("LiPo 2000 mAh", "BUY — power", (.70,.52,.16,1), 1, "2 Purchased"),
    "mock_xiao_esp32c3":        ("XIAO ESP32-C3", "BUY — reads the palm switch", (.90,.60,.24,1), 1, "2 Purchased"),
    "mock_tp4056_usbc":         ("TP4056", "BUY — USB-C charging", (.90,.60,.24,1), 1, "2 Purchased"),
    "mock_ds239mg_servo":       ("DS239MG servo", "BUY — trips the sear only", (.55,.40,.14,1), 1, "2 Purchased"),
    "mock_palm_switch_12mm":    ("Tactile switch", "BUY — double-tap to fire", (.86,.26,.20,1), 1, "2 Purchased"),
    "mock_forearm_reference":   ("Your forearm", "reference", (.52,.42,.36,1), .13, "3 Reference"),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'
sc.unit_settings.scale_length = 0.001
sc.unit_settings.length_unit = 'MILLIMETERS'

COLL = {}
for c in ("1 Printed", "2 Purchased", "3 Reference", "4 Labels"):
    col = bpy.data.collections.new(c)
    sc.collection.children.link(col)
    COLL[c] = col


def link(o, c):
    for x in list(o.users_collection):
        x.objects.unlink(o)
    COLL[c].objects.link(o)


def mat(name, rgba, alpha):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = .42
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.blend_method = 'BLEND'
        except Exception:
            pass
    return m


objs = {}
for fp in sorted(glob.glob(os.path.join(SRC, "*.stl"))):
    key = os.path.splitext(os.path.basename(fp))[0]
    label, role, rgba, alpha, coll = INFO.get(key, (key, "", (.6,.6,.6,1), 1, "1 Printed"))
    before = set(bpy.data.objects)
    try:
        bpy.ops.wm.stl_import(filepath=fp)
    except AttributeError:
        bpy.ops.import_mesh.stl(filepath=fp)
    for o in [x for x in bpy.data.objects if x not in before]:
        o.name = label
        o.data.materials.clear()
        o.data.materials.append(mat("M_" + key, rgba, alpha))
        link(o, coll)
        objs[key] = o

xs, ys, zs = [], [], []
for o in objs.values():
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        xs.append(w.x); ys.append(w.y); zs.append(w.z)
cx, cy, cz = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2
print("bounds X %.1f..%.1f  Y %.1f..%.1f  Z %.1f..%.1f" % (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)))

bpy.ops.object.camera_add(location=(cx+330, cy-430, cz+300))
cam = bpy.context.object
cam.name = "Camera — hero"
cam.data.lens = 32
sc.camera = cam
aim = bpy.data.objects.new("Aim", None)
sc.collection.objects.link(aim)
aim.location = (cx, cy, cz)
t = cam.constraints.new('TRACK_TO'); t.target = aim
t.track_axis = 'TRACK_NEGATIVE_Z'; t.up_axis = 'UP_Y'

LBL_P = mat("M_LabelPrinted", (.72,.92,1.0,1), 1)
LBL_B = mat("M_LabelBought", (1.0,.80,.42,1), 1)

for i, (key, o) in enumerate(sorted(objs.items())):
    label, role, *_ = INFO.get(key, (key, "", None, 1, ""))
    if key == "mock_forearm_reference":
        continue
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    top = max(v.z for v in vs)
    mx = sum(v.x for v in vs)/len(vs); my = sum(v.y for v in vs)/len(vs)
    ang = (i / max(1, len(objs))) * 2 * math.pi
    lx = cx + math.cos(ang) * 185.0
    ly = cy + math.sin(ang) * 150.0
    lz = top + 30 + (i % 5) * 17
    bpy.ops.object.text_add(location=(lx, ly, lz))
    tx = bpy.context.object
    tx.name = "LBL " + label
    tx.data.body = label + ("\n" + role if role else "")
    tx.data.size = 5.4
    tx.data.align_x = 'CENTER'
    tx.data.materials.append(LBL_B if key.startswith("mock") else LBL_P)
    c = tx.constraints.new('TRACK_TO'); c.target = cam
    c.track_axis = 'TRACK_Z'; c.up_axis = 'UP_Y'
    link(tx, "4 Labels")
    cu = bpy.data.curves.new("LEAD", 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(1)
    sp.points[0].co = (lx, ly, lz - 2, 1)
    sp.points[1].co = (mx, my, top + 1, 1)
    cu.bevel_depth = 0.32
    lo = bpy.data.objects.new("LEAD " + label, cu)
    sc.collection.objects.link(lo)
    lo.data.materials.append(LBL_B if key.startswith("mock") else LBL_P)
    link(lo, "4 Labels")

world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (.045,.05,.06,1)


def area(loc, e, s, rot):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object; l.data.energy = e; l.data.size = s; l.rotation_euler = rot


area((260,-300,340), 1.1e6, 380, (math.radians(40),0,math.radians(40)))
area((-270,-220,160), 3.2e5, 420, (math.radians(70),0,math.radians(-50)))
area((60,320,260), 3.6e5, 340, (math.radians(-52),0,0))

for eng in ('BLENDER_EEVEE_NEXT','BLENDER_EEVEE','BLENDER_WORKBENCH'):
    try:
        sc.render.engine = eng; break
    except TypeError:
        continue
sc.render.resolution_x, sc.render.resolution_y = 1900, 1250
try:
    sc.view_settings.view_transform = 'Standard'
except TypeError:
    pass

for w in bpy.context.window_manager.windows:
    for a in w.screen.areas:
        if a.type == 'VIEW_3D':
            for s2 in a.spaces:
                if s2.type == 'VIEW_3D':
                    s2.shading.type = 'MATERIAL'
                    s2.clip_end = 20000


# ----------------------------------------------------------------- animation
# One cycle: rest -> hand-cock -> sear latches -> servo trips -> fire.
# The fire itself is 41.5 ms, which at 60 fps is 2.5 frames - so it is genuinely
# almost instant, and the cocking is the slow part. That asymmetry is the point.
import json as _json
with open(os.path.join(HERE, "mk4_params.json"), encoding="utf-8") as _f:
    _P = _json.load(_f)

class _MK:
    pass
MK = _MK()
for _k, _v in _P.items():
    setattr(MK, _k, _v)

STROKE = MK.PLUNGER_STROKE
F_REST_END   = 12
F_COCKED     = 42
F_HOLD_END   = 52
F_TRIP       = 56
F_FIRED      = 59
F_END        = 78

sc.frame_start, sc.frame_end = 1, F_END
sc.render.fps = 60

def key_x(obj, frame, dx):
    obj.location.x = obj.get("_x0", obj.location.x) + dx
    obj.keyframe_insert("location", frame=frame)

# remember each mover's authored X (the scene is built in the COCKED pose)
movers = [objs.get(k) for k in ("print_carriage", "mock_syringe_plunger",
                                "mock_plunger_thumb_flange")]
movers = [m for m in movers if m]
for m in movers:
    m["_x0"] = m.location.x

for m in movers:
    key_x(m, 1, STROKE)              # rest = fired = fully forward
    key_x(m, F_REST_END, STROKE)
    key_x(m, F_COCKED, 0.0)          # hand pulls it back
    key_x(m, F_HOLD_END, 0.0)
    key_x(m, F_TRIP, 0.0)
    key_x(m, F_FIRED, STROKE)        # spring release
    key_x(m, F_END, STROKE)

# spring: compressed when cocked, extended when fired
spring = objs.get("mock_compression_spring")
if spring:
    sx_free = 1.0
    sx_cocked = MK.SPRING_COCKED_LEN / MK.SPRING_FREE_LEN
    for f, sx in ((1, sx_free), (F_REST_END, sx_free), (F_COCKED, sx_cocked),
                  (F_HOLD_END, sx_cocked), (F_TRIP, sx_cocked),
                  (F_FIRED, sx_free), (F_END, sx_free)):
        spring.scale.x = sx
        spring.keyframe_insert("scale", frame=f)

# sear: rocks over to release, then returns
sear = objs.get("print_sear")
if sear:
    r0 = sear.rotation_euler.y
    for f, r in ((1, r0), (F_COCKED, r0), (F_HOLD_END, r0),
                 (F_TRIP, r0), (F_TRIP + 2, r0 - math.radians(18)),
                 (F_FIRED + 4, r0 - math.radians(18)), (F_END, r0)):
        sear.rotation_euler.y = r
        sear.keyframe_insert("rotation_euler", frame=f)
    sear.rotation_euler.y = r0

# fluid: a short train of beads leaving the muzzle after release
pulse = bpy.data.collections.new("5 Fluid pulse")
sc.collection.children.link(pulse)
fl_mat = mat("M_Fluid", (.62, .88, 1.0, 1), .85)
muzzle_x = MK.OUTLET_X1 + MK.MUZZLE_LEN
for i in range(7):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.5 - i * 0.12,
                                         location=(muzzle_x, MK.FLUID_Y, MK.SYRINGE_AXIS_Z))
    bead = bpy.context.object
    bead.name = f"Fluid bead {i+1}"
    bead.data.materials.append(fl_mat)
    for c in list(bead.users_collection):
        c.objects.unlink(bead)
    pulse.objects.link(bead)
    start = F_FIRED + i
    bead.location = (muzzle_x, MK.FLUID_Y, MK.SYRINGE_AXIS_Z)
    bead.keyframe_insert("location", frame=start)
    bead.scale = (0, 0, 0); bead.keyframe_insert("scale", frame=start - 1)
    bead.scale = (1, 1, 1); bead.keyframe_insert("scale", frame=start)
    bead.location = (muzzle_x + 240, MK.FLUID_Y, MK.SYRINGE_AXIS_Z - 26)
    bead.keyframe_insert("location", frame=start + 16)
    bead.scale = (1, 1, 1); bead.keyframe_insert("scale", frame=start + 15)
    bead.scale = (0, 0, 0); bead.keyframe_insert("scale", frame=start + 16)

for f, name in ((1, "REST / FIRED"), (F_REST_END, "PULL TO COCK"),
                (F_COCKED, "SEAR LATCHES"), (F_HOLD_END, "COCKED + READY"),
                (F_TRIP, "SERVO TRIPS SEAR"), (F_FIRED, "2 mL OUT IN 41.5 ms"),
                (F_END, "RESET")):
    sc.timeline_markers.new(name, frame=f)

sc.frame_set(F_HOLD_END)

blend = os.path.join(HERE, "webshooter_mk4.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
print("saved", blend)

if bpy.app.background:
    for nm, loc in {"mk4_01_hero": (cx+330, cy-430, cz+300),
                    "mk4_02_plan": (cx, cy-0.01, cz+560),
                    "mk4_03_mech": (cx-30, cy-260, cz+95)}.items():
        cam.location = loc
        sc.render.filepath = os.path.join(HERE, nm + ".png")
        bpy.ops.render.render(write_still=True)
        print("rendered", nm)
print("done")
