"""Web-Shooter Mk5 — the presentation scene.

    blender -b --python build_mk5_viz.py     # render + save
    blender    --python build_mk5_viz.py     # open it

Design intent, per the brief: sleek but not sterile. The mechanism stays visible
because it is worth seeing — this should read as a considered instrument someone
built, not a consumer product and not parts bolted to a board. So: a restrained
palette, a translucent baseplate that reveals rather than hides, brass on the one
precise part, and labels only where they teach something.
"""
import bpy, os, math, glob, json

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "mk5_assembly_stl")
with open(os.path.join(HERE, "mk4_params.json"), encoding="utf-8") as f:
    P = json.load(f)

# ---------------------------------------------------------------- palette
# Cool graphite structure, warm brass for the working parts, one red accent on
# the trigger. Restraint is the point: three families, not fifteen.
STEEL   = (0.44, 0.50, 0.57, 1)
STEEL_T = (0.50, 0.58, 0.66, 1)
BRASS   = (0.78, 0.58, 0.24, 1)
BRASS_D = (0.52, 0.38, 0.16, 1)
GLASS   = (0.80, 0.86, 0.90, 1)
ACCENT  = (0.80, 0.22, 0.18, 1)
BOARD   = (0.13, 0.35, 0.30, 1)
SKIN    = (0.50, 0.40, 0.35, 1)

INFO = {
 "print_baseplate":       ("Baseplate",        "PRINTED PETG  ·  frame, rails, wrist curve", STEEL_T, .30, "1 Printed"),
 "print_carriage":        ("Carriage",         "PRINTED  ·  the spring drives this", STEEL, 1, "1 Printed"),
 "print_sear":            ("Lifting pawl",     "PRINTED  ·  holds 30 N, servo lifts it", STEEL, 1, "1 Printed"),
 "print_outlet_adapter":  ("Outlet adapter",   "PRINTED  ·  4 mm bore, replaces the Luer", STEEL, 1, "1 Printed"),
 "print_switch_pod":      ("Palm pod",         "PRINTED  ·  two-finger trigger", STEEL, 1, "1 Printed"),
 "mock_syringe_5ml_barrel":  ("5 mL cartridge", "reservoir · pump · seal, in one part", GLASS, .34, "2 Purchased"),
 "mock_syringe_plunger":     ("Plunger",        "travels 16.4 mm", BRASS, 1, "2 Purchased"),
 "mock_plunger_thumb_flange":("Thumb flange",   "what the carriage pushes", BRASS, 1, "2 Purchased"),
 "mock_compression_spring":  ("Spring",         "stores 0.247 J", BRASS_D, 1, "2 Purchased"),
 "mock_brass_muzzle":        ("Brass muzzle",   "the spinneret", BRASS, 1, "2 Purchased"),
 "mock_lipo_2000mah":        ("LiPo",           "2000 mAh", BRASS_D, 1, "2 Purchased"),
 "mock_xiao_esp32c3":        ("XIAO ESP32-C3",  "watches the palm switch", BOARD, 1, "2 Purchased"),
 "mock_tp4056_usbc":         ("TP4056",         "USB-C charging", BOARD, 1, "2 Purchased"),
 "mock_ds239mg_servo":       ("Servo",          "lifts the pawl · carries no load", (.12,.13,.15,1), 1, "2 Purchased"),
 "mock_palm_switch_12mm":    ("Palm switch",    "double-tap to fire", ACCENT, 1, "2 Purchased"),
 "mock_forearm_reference":   ("Forearm",        "", SKIN, .12, "3 Reference"),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'
sc.unit_settings.scale_length = 0.001
sc.unit_settings.length_unit = 'MILLIMETERS'

COLL = {}
for c in ("1 Printed", "2 Purchased", "3 Reference", "4 Labels", "5 Fluid"):
    col = bpy.data.collections.new(c)
    sc.collection.children.link(col)
    COLL[c] = col


def link(o, c):
    for x in list(o.users_collection):
        x.objects.unlink(o)
    COLL[c].objects.link(o)


def mat(name, rgba, alpha=1.0, metal=0.0, rough=0.42, emit=0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        try:
            b.inputs["Emission Color"].default_value = rgba
            b.inputs["Emission Strength"].default_value = emit
        except KeyError:
            pass
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
    label, role, rgba, alpha, coll = INFO.get(key, (key, "", STEEL, 1, "1 Printed"))
    before = set(bpy.data.objects)
    try:
        bpy.ops.wm.stl_import(filepath=fp)
    except AttributeError:
        bpy.ops.import_mesh.stl(filepath=fp)
    for o in [x for x in bpy.data.objects if x not in before]:
        o.name = label
        o.data.materials.clear()
        metal = 0.85 if rgba in (BRASS, BRASS_D) else 0.0
        rough = 0.28 if metal else 0.45
        o.data.materials.append(mat("M_" + key, rgba, alpha, metal, rough))
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
        o.data.update()
        link(o, coll)
        objs[key] = o

xs, ys, zs = [], [], []
for k, o in objs.items():
    if k == "mock_forearm_reference":   # reference geometry must not drag the framing
        continue
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        xs.append(w.x); ys.append(w.y); zs.append(w.z)
cx, cy, cz = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2
print("bounds X %.1f..%.1f Y %.1f..%.1f Z %.1f..%.1f" % (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)))

# ------------------------------------------------------------------ cameras
def camera(name, loc, lens, aim=(cx, cy, cz)):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object
    c.name = name
    c.data.lens = lens
    t = bpy.data.objects.new(name + " aim", None)
    sc.collection.objects.link(t)
    t.location = aim
    k = c.constraints.new('TRACK_TO')
    k.target = t; k.track_axis = 'TRACK_NEGATIVE_Z'; k.up_axis = 'UP_Y'
    return c


hero = camera("Camera - hero", (cx + 175, cy - 215, cz + 140), 46)
detail = camera("Camera - mechanism", (cx - 20, cy - 165, cz + 95), 62,
                aim=(P["PLATE_L"] * 0.28, P["FLUID_Y"], cz + 4))
plan = camera("Camera - plan", (cx, cy - 0.01, cz + 300), 42)
sc.camera = hero

# ------------------------------------------------------------------- labels
LBL = mat("M_Label", (0.90, 0.93, 0.96, 1), 1, 0, 0.6)
LBL_B = mat("M_LabelBrass", (0.92, 0.76, 0.42, 1), 1, 0, 0.6)
ORDER = ["print_baseplate", "mock_compression_spring", "print_carriage", "print_sear",
         "mock_ds239mg_servo", "mock_syringe_5ml_barrel", "print_outlet_adapter",
         "mock_brass_muzzle", "mock_palm_switch_12mm", "mock_lipo_2000mah",
         "mock_xiao_esp32c3", "mock_tp4056_usbc"]
for i, key in enumerate(ORDER):
    o = objs.get(key)
    if not o:
        continue
    label, role, *_ = INFO[key]
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    top = max(v.z for v in vs)
    mx = sum(v.x for v in vs)/len(vs); my = sum(v.y for v in vs)/len(vs)
    # Alternate sides and step along X in the order the mechanism acts, so the
    # callouts read left-to-right and never pile onto one another.
    side = -1 if (i % 2 == 0) else 1
    span = (max(xs) - min(xs))
    lx = min(xs) + span * (i / max(1, len(ORDER) - 1))
    ly = cy + side * 86.0
    lz = top + 20 + (i % 2) * 16
    bpy.ops.object.text_add(location=(lx, ly, lz))
    tx = bpy.context.object
    tx.name = "LBL " + label
    tx.data.body = label + ("\n" + role if role else "")
    tx.data.size = 4.2
    tx.data.align_x = 'CENTER'
    tx.data.materials.append(LBL_B if key.startswith("mock") else LBL)
    k = tx.constraints.new('TRACK_TO'); k.target = hero
    k.track_axis = 'TRACK_Z'; k.up_axis = 'UP_Y'
    link(tx, "4 Labels")
    cu = bpy.data.curves.new("LEAD", 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(1)
    sp.points[0].co = (lx, ly, lz - 2.0, 1)
    sp.points[1].co = (mx, my, top + 1.0, 1)
    cu.bevel_depth = 0.30
    lo = bpy.data.objects.new("LEAD " + label, cu)
    sc.collection.objects.link(lo)
    lo.data.materials.append(LBL_B if key.startswith("mock") else LBL)
    link(lo, "4 Labels")

# ---------------------------------------------------------------- animation
STROKE = P["plunger_stroke_mm"]
F_REST, F_COCK0, F_COCKED, F_HOLD, F_TRIP, F_FIRED, F_END = 1, 14, 48, 60, 64, 67, 92
sc.frame_start, sc.frame_end = 1, F_END
sc.render.fps = 60

movers = [objs.get(k) for k in ("print_carriage", "mock_syringe_plunger",
                                "mock_plunger_thumb_flange")]
movers = [m for m in movers if m]
for m in movers:
    x0 = m.location.x
    for f, dx in ((F_REST, STROKE), (F_COCK0, STROKE), (F_COCKED, 0.0),
                  (F_HOLD, 0.0), (F_TRIP, 0.0), (F_FIRED, STROKE), (F_END, STROKE)):
        m.location.x = x0 + dx
        m.keyframe_insert("location", frame=f)
    m.location.x = x0

spring = objs.get("mock_compression_spring")
if spring:
    free, cocked = 1.0, P["SPRING_COCKED_LEN"] / P["SPRING_FREE_LEN"]
    for f, s in ((F_REST, free), (F_COCK0, free), (F_COCKED, cocked),
                 (F_HOLD, cocked), (F_TRIP, cocked), (F_FIRED, free), (F_END, free)):
        spring.scale.x = s
        spring.keyframe_insert("scale", frame=f)

# the pawl lifts to release — the measured release angle, not a guess
sear = objs.get("print_sear")
if sear:
    lift = math.radians(25.0)
    for f, r in ((F_REST, 0.0), (F_COCKED, 0.0), (F_HOLD, 0.0), (F_TRIP, 0.0),
                 (F_TRIP + 3, lift), (F_FIRED + 4, lift), (F_END, 0.0)):
        sear.rotation_euler.y = r
        sear.keyframe_insert("rotation_euler", frame=f)
    sear.rotation_euler.y = 0.0

fl = mat("M_Fluid", (0.60, 0.86, 1.0, 1), 0.9, 0.0, 0.15, emit=1.2)
mz = P["OUTLET_X1"] + P["MUZZLE_LEN"]
for i in range(9):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.7 - i * 0.13,
                                         location=(mz, P["FLUID_Y"], P["SYRINGE_AXIS_Z"]))
    b = bpy.context.object
    b.name = "Fluid %d" % (i + 1)
    b.data.materials.append(fl)
    link(b, "5 Fluid")
    s0 = F_FIRED + i
    b.scale = (0, 0, 0); b.keyframe_insert("scale", frame=s0 - 1)
    b.scale = (1, 1, 1); b.keyframe_insert("scale", frame=s0)
    b.location = (mz, P["FLUID_Y"], P["SYRINGE_AXIS_Z"])
    b.keyframe_insert("location", frame=s0)
    b.location = (mz + 300, P["FLUID_Y"], P["SYRINGE_AXIS_Z"] - 34)
    b.keyframe_insert("location", frame=s0 + 18)
    b.scale = (1, 1, 1); b.keyframe_insert("scale", frame=s0 + 17)
    b.scale = (0, 0, 0); b.keyframe_insert("scale", frame=s0 + 18)

for f, n in ((F_REST, "REST"), (F_COCK0, "COCK BY HAND"), (F_COCKED, "PAWL CATCHES"),
             (F_HOLD, "COCKED  30 N HELD"), (F_TRIP, "SERVO LIFTS PAWL"),
             (F_FIRED, "2 mL  ·  41.5 ms  ·  3.8 m/s"), (F_END, "RESET")):
    sc.timeline_markers.new(n, frame=f)
sc.frame_set(F_HOLD)

# ------------------------------------------------------------- world + light
world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.035, 0.040, 0.048, 1)


def area(loc, e, size, rot):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object
    l.data.energy = e; l.data.size = size; l.rotation_euler = rot


area((270, -300, 340), 1.5e6, 340, (math.radians(40), 0, math.radians(40)))
area((-280, -230, 150), 4.2e5, 420, (math.radians(72), 0, math.radians(-52)))
area((70, 330, 250), 5.0e5, 320, (math.radians(-52), 0, 0))

for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue
sc.render.resolution_x, sc.render.resolution_y = 2000, 1300
try:
    sc.view_settings.view_transform = 'Standard'
except TypeError:
    pass
for attr, val in (("use_bloom", True), ("use_ssr", True), ("use_gtao", True)):
    try:
        setattr(sc.eevee, attr, val)
    except Exception:
        pass

# Viewport shading must be set on bpy.data.screens, NOT through
# window_manager.windows: in background mode there are no windows, so that loop
# is a silent no-op and the saved file opens in flat Solid shading with no
# materials or lighting. This is why it looked "low res".
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for space in area.spaces:
            if space.type != 'VIEW_3D':
                continue
            space.shading.type = 'MATERIAL'
            space.shading.use_scene_lights = True
            space.shading.use_scene_world = True
            space.clip_end = 20000
            space.overlay.show_relationship_lines = False
            space.overlay.show_extras = False        # hides camera/light gizmos
            space.overlay.show_floor = False
            space.overlay.show_axis_x = False
            space.overlay.show_axis_y = False

blend = os.path.join(HERE, "webshooter_mk5.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
print("saved", blend)

if bpy.app.background:
    labels = COLL["4 Labels"]
    for nm, cam, fr, show_labels in (("mk5_01_hero", hero, F_HOLD, True),
                                     ("mk5_02_mechanism", detail, F_HOLD, False),
                                     ("mk5_03_plan", plan, F_HOLD, False),
                                     ("mk5_04_firing", hero, F_FIRED + 6, False)):
        labels.hide_render = not show_labels
        sc.camera = cam
        sc.frame_set(fr)
        sc.render.filepath = os.path.join(HERE, nm + ".png")
        bpy.ops.render.render(write_still=True)
        print("rendered", nm)
    labels.hide_render = False
    sc.camera = hero
    sc.frame_set(F_HOLD)
print("done")
