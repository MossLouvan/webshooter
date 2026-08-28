"""Build the annotated, animated Blender visualization for the Web-Shooter Mk3.

Run with Blender 5.2.1 from this directory:

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python build_blender_viz.py

The script treats every STL in ``assembly_stl`` as source geometry.  It adds
presentation materials, plain-language names, camera-specific 3D callouts,
reference geometry, a scrubbable mechanism timeline, and four PNG renders.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
STL_DIR = ROOT / "assembly_stl"
BLEND_PATH = ROOT / "webshooter_mk3_visualization.blend"

EXPECTED_STLS = 28
STROKE_MM = 10.073
FPS = 60


PART_INFO = {
    "printed_baseplate": ("Baseplate / chassis (printed)", "printed"),
    "printed_barrel_bridge": ("Barrel bridge (printed)", "printed"),
    "printed_spring_carriage": ("Spring carriage / plunger pusher (printed)", "printed"),
    "printed_cocking_lever": ("One-hand cocking lever (printed)", "printed"),
    "printed_servo_sear": ("Positive sear (printed)", "printed"),
    "printed_palm_switch_pod": ("Palm switch pod (printed)", "printed"),
    "mockup_xiao_epdm_retainer": ("EPDM band over controller (purchased)", "elastomer"),
    "mockup_tp4056_usbc_dw01": ("USB-C charger + battery protection (purchased)", "electronics"),
    "mockup_tp4056_epdm_retainer": ("EPDM band over charger (purchased)", "elastomer"),
    "mockup_tactile_switch_12mm": ("Palm firing switch (purchased)", "electronics"),
    "mockup_syringe_norm_ject_10ml": ("10 mL syringe assembly (purchased)", "syringe"),
    "mockup_syringe_epdm_retainer": ("EPDM syringe retainer (purchased)", "elastomer"),
    "mockup_selected_compression_spring": ("Measured compression spring (purchased)", "metal"),
    "mockup_seeed_xiao_esp32c3": ("XIAO ESP32-C3 controller (purchased)", "electronics"),
    "mockup_sear_pivot_m3": ("M3 sear pivot screw (purchased)", "metal"),
    "mockup_palm_strap_25mm": ("25 mm palm strap (purchased)", "strap"),
    "mockup_live_8ga_blunt_nozzle": ("Live 8 ga nozzle — fluid exits here (purchased)", "metal"),
    "mockup_lipo_eemb_103454_rotated": ("1-cell LiPo battery (purchased)", "electronics"),
    "mockup_forearm_straps_25mm": ("25 mm forearm straps (purchased)", "strap"),
    "mockup_ds239mg_horn": ("Servo horn — trips sear (purchased)", "metal"),
    "mockup_corona_ds239mg_servo": ("Servo — releases the sear only (purchased)", "electronics"),
    "mockup_cocking_pivot_m3": ("M3 cocking-lever pivot (purchased)", "metal"),
    "mockup_cocking_drive_m3": ("M3 carriage drive pin (purchased)", "metal"),
    "mockup_capped_dummy_8ga_nozzle": ("Capped dummy nozzle — no fluid (purchased)", "metal"),
    "mockup_bridge_m3_screw_2": ("Bridge clamp screw, upper side (purchased)", "metal"),
    "mockup_bridge_m3_screw_1": ("Bridge clamp screw, lower side (purchased)", "metal"),
    "mockup_bridge_m3_insert_2": ("Heat-set insert, upper side (purchased)", "metal"),
    "mockup_bridge_m3_insert_1": ("Heat-set insert, lower side (purchased)", "metal"),
}


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.curves, bpy.data.meshes, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        # Objects are gone; remove only orphaned datablocks from the prior file.
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    for child in list(bpy.context.scene.collection.children):
        bpy.context.scene.collection.children.unlink(child)


def new_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    coll = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def move_to_collection(obj: bpy.types.Object, coll: bpy.types.Collection) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    coll.objects.link(obj)


def make_material(name: str, color, metallic=0.0, roughness=0.42,
                  alpha=1.0, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Alpha"].default_value = alpha
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        try:
            mat.surface_render_method = "DITHERED"
        except Exception:
            pass
        mat.use_transparency_overlap = False
    return mat


def assign_material(obj, mat) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def import_stls(printed_coll, purchased_coll, mats):
    paths = sorted(STL_DIR.glob("*.stl"))
    if len(paths) != EXPECTED_STLS:
        raise RuntimeError(f"Expected {EXPECTED_STLS} STL files, found {len(paths)}")
    imported = {}
    for path in paths:
        stem = path.stem
        if stem not in PART_INFO:
            raise RuntimeError(f"No plain-language mapping for {path.name}")
        before = set(bpy.context.scene.objects)
        bpy.ops.wm.stl_import(filepath=str(path))
        created = list(set(bpy.context.scene.objects) - before)
        if len(created) != 1:
            raise RuntimeError(f"Import of {path.name} created {len(created)} objects")
        obj = created[0]
        plain, category = PART_INFO[stem]
        obj.name = plain
        obj.data.name = f"Mesh — {plain}"
        obj["source_stl"] = path.name
        obj["part_type"] = "PRINTED" if category == "printed" else "PURCHASED"
        obj["plain_language_name"] = plain
        move_to_collection(obj, printed_coll if category == "printed" else purchased_coll)
        if stem == "printed_baseplate":
            assign_material(obj, mats["baseplate"])
        else:
            assign_material(obj, mats[category])
        imported[stem] = obj
    return imported


def split_syringe(source_obj, purchased_coll, syringe_mat):
    """Split the source STL shells so the real plunger can move independently."""
    bpy.ops.object.select_all(action="DESELECT")
    source_obj.select_set(True)
    bpy.context.view_layer.objects.active = source_obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    pieces = list(bpy.context.selected_objects)
    if len(pieces) < 4:
        raise RuntimeError(f"Syringe STL did not split into expected shells ({len(pieces)} found)")

    moving = []
    static = []
    for obj in pieces:
        world_center_x = sum((obj.matrix_world @ Vector(corner)).x for corner in obj.bound_box) / 8.0
        (moving if world_center_x < 82.0 else static).append(obj)

    def join_group(group, name):
        bpy.ops.object.select_all(action="DESELECT")
        for item in group:
            item.select_set(True)
            move_to_collection(item, purchased_coll)
        bpy.context.view_layer.objects.active = group[0]
        bpy.ops.object.join()
        result = group[0]
        result.name = name
        result.data.name = f"Mesh — {name}"
        result["source_stl"] = "mockup_syringe_norm_ject_10ml.stl"
        result["part_type"] = "PURCHASED"
        assign_material(result, syringe_mat)
        return result

    static_obj = join_group(static, "Syringe barrel + finger flange (purchased)")
    moving_obj = join_group(moving, "Syringe plunger — moves 10.073 mm (purchased)")
    return static_obj, moving_obj


def set_origin_world(obj, point):
    cursor = bpy.context.scene.cursor
    old = cursor.location.copy()
    cursor.location = point
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
    cursor.location = old


def look_at(camera, target):
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_camera(name, location, target, ortho_scale, coll):
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO"
    data.ortho_scale = ortho_scale
    data.lens = 50
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    obj["purpose"] = name
    return obj


def add_area_light(name, location, energy, size, color, coll, target=(100, 0, 0)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def add_cube(name, location, scale, mat, coll, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0] / 2.0, scale[1] / 2.0, scale[2] / 2.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        assign_material(obj, mat)
    if bevel:
        mod = obj.modifiers.new("Softened presentation edges", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    move_to_collection(obj, coll)
    return obj


def add_uv_sphere(name, location, radius, mat, coll):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, mat)
    move_to_collection(obj, coll)
    return obj


def add_curve(name, points, mat, coll, thickness=0.34):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = thickness
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1.0)
    obj = bpy.data.objects.new(name, curve)
    coll.objects.link(obj)
    assign_material(obj, mat)
    return obj


def add_arrow(name, start, end, mat, coll, shaft=0.55, head=2.2):
    start, end = Vector(start), Vector(end)
    vec = end - start
    length = vec.length
    if length <= head:
        raise ValueError("Arrow too short")
    direction = vec.normalized()
    shaft_end = end - direction * head
    add_curve(f"{name} — shaft", [start, shaft_end], mat, coll, shaft)
    bpy.ops.mesh.primitive_cone_add(vertices=28, radius1=head * 0.7, radius2=0.0,
                                    depth=head, location=end - direction * head * 0.5)
    cone = bpy.context.object
    cone.name = f"{name} — arrowhead"
    cone.rotation_mode = "QUATERNION"
    cone.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction)
    assign_material(cone, mat)
    move_to_collection(cone, coll)


def label_basis(camera):
    q = camera.matrix_world.to_quaternion()
    return q @ Vector((1, 0, 0)), q @ Vector((0, 1, 0)), q @ Vector((0, 0, 1)), q


def add_label(name, body, anchor, uv, camera, target, category, coll, mats,
              size=4.0, width=None, extra_anchors=()):
    right, up, toward, rotation = label_basis(camera)
    # Keep plaques in front of every possible model depth while retaining real
    # 3D leader lines back to the assembly.  Orthographic framing is unchanged.
    pos = Vector(target) + right * uv[0] + up * uv[1] + toward * 75.0
    lines = body.split("\n")
    estimated_width = width or max(len(line) for line in lines) * size * 0.57 + 5.0
    height = len(lines) * size * 1.25 + 3.0

    panel = add_cube(f"Callout plaque — {name}", pos - toward * 0.18,
                     (estimated_width, height, 0.55), mats[f"label_{category}"], coll, bevel=0.7)
    panel.rotation_euler = rotation.to_euler()

    curve = bpy.data.curves.new(f"Text data — {name}", "FONT")
    curve.body = body
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size
    curve.extrude = 0.045
    curve.bevel_depth = 0.012
    curve.space_line = 0.9
    text_obj = bpy.data.objects.new(f"3D label — {name}", curve)
    coll.objects.link(text_obj)
    text_obj.location = pos + toward * 0.2
    text_obj.rotation_euler = rotation.to_euler()
    assign_material(text_obj, mats["label_text"])

    for idx, endpoint in enumerate((anchor, *extra_anchors)):
        if endpoint is None:
            continue
        add_curve(f"Leader line — {name} {idx + 1}", [pos - toward * 0.4, Vector(endpoint)],
                  mats[f"leader_{category}"], coll, thickness=0.3)
        add_uv_sphere(f"Leader endpoint — {name} {idx + 1}", endpoint, 0.75,
                      mats[f"leader_{category}"], coll)
    return text_obj


def add_title(body, uv, camera, target, coll, mats, size=6.0, width=100):
    add_label(body.replace("\n", " "), body, None, uv, camera, target, "guide", coll,
              mats, size=size, width=width)


def add_reference(reference_coll, mats):
    # A deliberately simplified forearm: enough to communicate scale, not anatomy.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=24, location=(58, 0, -13))
    arm = bpy.context.object
    arm.name = "Simplified forearm scale reference — not a fitted part"
    arm.scale = (67, 31, 13)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(arm, mats["reference"])
    move_to_collection(arm, reference_coll)

    ruler = add_cube("100 mm scale bar", (66, -48, -7), (100, 2.2, 1.4), mats["ruler"], reference_coll, 0.3)
    ruler["scale_length_mm"] = 100.0
    for index in range(11):
        x = 16 + index * 10
        height = 5.0 if index in (0, 5, 10) else 3.0
        tick = add_cube(f"Scale tick — {index * 10} mm", (x, -48, -4.5),
                        (0.65, 1.4, height), mats["ruler"], reference_coll)
        tick["millimetres"] = index * 10


def configure_animation(parts, syringe_plunger, animation_coll, mats):
    scene = bpy.context.scene
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = 72

    carriage = parts["printed_spring_carriage"]
    spring = parts["mockup_selected_compression_spring"]
    lever = parts["printed_cocking_lever"]
    sear = parts["printed_servo_sear"]
    horn = parts["mockup_ds239mg_horn"]

    set_origin_world(carriage, (65.5, -6.0, 10.0))
    set_origin_world(syringe_plunger, (70.5, -6.0, 12.5))
    set_origin_world(spring, (39.967, -6.0, 10.0))
    set_origin_world(lever, (42.0, -25.0, 19.9))
    set_origin_world(sear, (68.0, 13.7, 17.5))
    set_origin_world(horn, (64.5, 18.3, 16.5))

    def key_loc_x(obj, frame, x):
        obj.location.x = x
        obj.keyframe_insert("location", frame=frame, index=0)

    # Fired/rest state, then hand-cock, latch, servo trip, and a four-frame shot.
    for obj in (carriage, syringe_plunger):
        key_loc_x(obj, 1, STROKE_MM)
        key_loc_x(obj, 8, STROKE_MM)
        key_loc_x(obj, 36, 0.0)
        key_loc_x(obj, 53, 0.0)
        key_loc_x(obj, 57, STROKE_MM)
        key_loc_x(obj, 72, STROKE_MM)

    spring.scale.x = 35.6 / (35.6 - STROKE_MM)
    spring.location.x = 0.0
    spring.keyframe_insert("scale", frame=1, index=0)
    spring.keyframe_insert("location", frame=1, index=0)
    spring.keyframe_insert("scale", frame=8, index=0)
    spring.keyframe_insert("location", frame=8, index=0)
    spring.scale.x = 1.0
    spring.location.x = 0.0
    spring.keyframe_insert("scale", frame=36, index=0)
    spring.keyframe_insert("location", frame=36, index=0)
    spring.keyframe_insert("scale", frame=53, index=0)
    spring.keyframe_insert("location", frame=53, index=0)
    spring.scale.x = 35.6 / (35.6 - STROKE_MM)
    spring.location.x = 0.0
    spring.keyframe_insert("scale", frame=57, index=0)
    spring.keyframe_insert("location", frame=57, index=0)
    spring.keyframe_insert("scale", frame=72, index=0)
    spring.keyframe_insert("location", frame=72, index=0)

    lever.rotation_euler.z = 0.0
    lever.keyframe_insert("rotation_euler", frame=1, index=2)
    lever.keyframe_insert("rotation_euler", frame=8, index=2)
    lever.rotation_euler.z = math.radians(-45)
    lever.keyframe_insert("rotation_euler", frame=36, index=2)
    lever.rotation_euler.z = 0.0
    lever.keyframe_insert("rotation_euler", frame=45, index=2)
    lever.keyframe_insert("rotation_euler", frame=72, index=2)

    for obj, angle in ((sear, math.radians(17)), (horn, math.radians(-24))):
        obj.rotation_euler.z = 0.0
        obj.keyframe_insert("rotation_euler", frame=46, index=2)
        obj.rotation_euler.z = angle
        obj.keyframe_insert("rotation_euler", frame=51, index=2)
        obj.keyframe_insert("rotation_euler", frame=60, index=2)
        obj.rotation_euler.z = 0.0
        obj.keyframe_insert("rotation_euler", frame=68, index=2)

    # Scrubbable visual pulse beyond the nozzle.  Each bead appears, advances, disappears.
    for index in range(7):
        bead = add_uv_sphere(f"Animated fluid pulse bead {index + 1}", (206, -6, 12.5),
                            1.25, mats["fluid"], animation_coll)
        start = 56 + index * 0.6
        bead.scale = (0.001, 0.001, 0.001)
        bead.location.x = 205.0
        bead.keyframe_insert("scale", frame=start)
        bead.keyframe_insert("location", frame=start)
        bead.scale = (1.0, 1.0, 1.0)
        bead.location.x = 214.0 + index * 2.5
        bead.keyframe_insert("scale", frame=start + 2)
        bead.keyframe_insert("location", frame=start + 2)
        bead.location.x = 252.0 + index * 4.0
        bead.keyframe_insert("location", frame=start + 8)
        bead.scale = (0.001, 0.001, 0.001)
        bead.keyframe_insert("scale", frame=start + 10)

    markers = [(1, "FIRED / REST"), (8, "PULL LEVER TO COCK"), (36, "SEAR LATCHES"),
               (46, "COCKED + READY"), (50, "SERVO TRIPS SEAR"),
               (53, "SPRING RELEASE"), (57, "2 mL SHOT COMPLETE (~67 ms)"),
               (68, "RESET")]
    for frame, name in markers:
        scene.timeline_markers.new(name, frame=frame)


def build_callouts(cameras, colls, mats):
    hero, plan, mech, fluid = cameras["hero"], cameras["plan"], cameras["mechanism"], cameras["fluid"]
    hero_target = (105, 0, 6)
    plan_target = (105, 0, 4)
    mech_target = (65, -2, 11)
    fluid_target = (148, -5, 12)

    add_title("WEB-SHOOTER Mk3\nCOCKED + READY", (0, 105), hero, hero_target,
              colls["hero"], mats, size=6.2, width=82)
    hero_labels = [
        ("base", "PRINTED: translucent baseplate", (55, -10, 1.5), (-30, -54), "printed"),
        ("lever", "One-hand cocking lever", (25, -30, 20), (-86, -42), "printed"),
        ("spring", "Compression spring\n27.5 N cocked", (52, -6, 10), (-86, -13), "bought"),
        ("electronics", "Controller + charger + LiPo", (82, 22, 8), (-82, 17), "bought"),
        ("sear", "Servo trips positive sear", (67, 14, 17), (-72, 54), "bought"),
        ("syringe", "10 mL syringe reservoir", (130, -6, 15), (78, 54), "bought"),
        ("bridge", "PRINTED: barrel bridge", (160, 11, 9), (86, 29), "printed"),
        ("live", "LIVE 8 ga nozzle\nfluid exits here", (205, -6, 12.5), (89, 0), "bought"),
        ("switch", "Palm firing switch", (146, 0, -7), (80, -31), "bought"),
        ("straps", "Palm + forearm straps", (90, -23, -1), (35, -56), "bought"),
    ]
    for name, body, anchor, uv, cat in hero_labels:
        add_label(name, body, anchor, uv, hero, hero_target, cat, colls["hero"], mats, size=3.6)
    add_title("PLAN VIEW — COMPONENT MAP", (0, 94), plan, plan_target,
              colls["plan"], mats, size=5.0, width=105)
    plan_labels = [
        ("power group", "POWER\nLiPo battery", (18, 0, 9), (-91, 72), "bought", ()),
        ("electronic group", "CONTROL\nXIAO + charger + EPDM bands", (81, 19, 7), (-31, 72), "bought", ((99, 20, 7),)),
        ("fluid package group", "FLUID PACKAGE\nsyringe + EPDM retainer", (128, -6, 15), (31, 72), "bought", ((90, -6, 22),)),
        ("bridge hardware group", "BRIDGE HARDWARE\n2 screws + 2 inserts", (112, -24, 11), (91, 72), "bought", ((112, 24, 11), (112, -24, 4), (112, 24, 4))),
        ("cock hardware group", "COCKING HARDWARE\nlever pivot + drive pin", (42, -25, 18), (-91, -72), "bought", ((68, -19, 20),)),
        ("forearm group", "ARM MOUNT\n2× 25 mm forearm straps", (22, -23, -1), (-31, -72), "bought", ((88, 23, -1),)),
        ("palm controls group", "PALM CONTROL\nstrap + printed pod + switch", (146, 0, -7), (31, -72), "bought", ((140, -19, 6), (150, 0, -8))),
        ("nozzle group", "TWIN NOZZLES\nlower LIVE / upper CAPPED", (203, -6, 12.5), (91, -72), "bought", ((203, 0, 12.5),)),
    ]
    for name, body, anchor, uv, cat, extras in plan_labels:
        add_label(name, body, anchor, uv, plan, plan_target, cat, colls["plan"], mats,
                  size=2.85, extra_anchors=extras)

    add_title("MECHANISM — FRAME 52: SEAR RELEASE", (0, 59), mech, mech_target,
              colls["mechanism"], mats, size=4.2, width=104)
    mechanism_labels = [
        ("spring mech", "Spring stores 0.179 J", (52, -6, 10), (-57, 39), "bought"),
        ("carriage mech", "Carriage drives plunger\n10.073 mm →", (68, -6, 13), (-57, 15), "printed"),
        ("drive pin", "M3 drive pin", (68, -19, 20), (-56, -10), "bought"),
        ("lever mech", "Hand lever cocks spring", (34, -28, 20), (-51, -37), "printed"),
        ("servo mech", "Servo only trips;\nit does not hold load", (55, 28, 10), (57, 39), "bought"),
        ("horn mech", "Horn nudges sear tail", (64.5, 21, 17), (58, 15), "bought"),
        ("sear mech", "Positive sear releases", (68, 13.7, 18), (57, -10), "printed"),
        ("sear pivot", "M3 sear pivot", (68, 13.7, 15), (51, -37), "bought"),
    ]
    for name, body, anchor, uv, cat in mechanism_labels:
        add_label(name, body, anchor, uv, mech, mech_target, cat, colls["mechanism"], mats, size=2.75)
    add_arrow("Plunger stroke direction", (68, -8, 24), (84, -8, 24), mats["motion"], colls["mechanism"])

    add_title("FLUID PATH — FRAME 60", (0, 69), fluid, fluid_target,
              colls["fluid"], mats, size=4.8, width=82)
    fluid_labels = [
        ("barrel fluid", "Fixed syringe barrel\nholds fluid", (128, -6, 17), (-60, 42), "bought"),
        ("plunger fluid", "Plunger moves →\n2.00 mL per shot", (78, -6, 13), (-61, 12), "bought"),
        ("retainer fluid", "EPDM band keeps\nsyringe seated", (90, -6, 22), (-58, -20), "bought"),
        ("bridge fluid", "Bridge holds the\nstraight fluid axis", (168, -6, 9), (61, 42), "printed"),
        ("live fluid", "LIVE nozzle\n3.0 mm effective outlet", (205, -6, 12.5), (64, 11), "bought"),
        ("dummy fluid", "Dummy is capped\nand carries no fluid", (205, 0, 12.5), (60, -21), "bought"),
    ]
    for name, body, anchor, uv, cat in fluid_labels:
        add_label(name, body, anchor, uv, fluid, fluid_target, cat, colls["fluid"], mats, size=3.15)
    add_arrow("Fluid path through syringe and live nozzle", (92, -6, 25), (208, -6, 25),
              mats["fluid"], colls["fluid"], shaft=0.72, head=3.2)
    add_label("fluid legend", "CYAN ARROW = fluid route\nOnly the lower barrel is live",
              None, (0, -66), fluid, fluid_target, "guide", colls["fluid"], mats,
              size=3.3, width=74)


def set_label_visibility(label_colls, active):
    for key, coll in label_colls.items():
        visible = key == active
        coll.hide_render = not visible
        coll.hide_viewport = not visible


def render_view(scene, camera, label_colls, label_key, frame, filename, resolution):
    set_label_visibility(label_colls, label_key)
    scene.camera = camera
    scene.frame_set(frame)
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.filepath = str(ROOT / filename)
    bpy.ops.render.render(write_still=True)


def configure_scene(scene):
    scene.name = "Mk3 — annotated animated assembly"
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 1200
    scene.render.pixel_aspect_x = 1
    scene.render.pixel_aspect_y = 1
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 20
    try:
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.use_high_quality_normals = True
    except Exception:
        pass
    scene.world.color = (0.035, 0.045, 0.065)
    world = scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.028, 0.038, 0.055, 1)
    bg.inputs["Strength"].default_value = 0.65
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001


def validate_scene(imported):
    source_files = sorted({obj.get("source_stl") for obj in bpy.data.objects if obj.get("source_stl")})
    disk_files = sorted(path.name for path in STL_DIR.glob("*.stl"))
    missing = sorted(set(disk_files) - set(source_files))
    if missing:
        raise RuntimeError(f"Source STL(s) absent from scene metadata: {missing}")
    if len(source_files) != EXPECTED_STLS:
        raise RuntimeError(f"Expected {EXPECTED_STLS} unique source STLs in scene, found {len(source_files)}")
    printed = [obj for obj in bpy.data.objects if obj.get("part_type") == "PRINTED"]
    purchased = [obj for obj in bpy.data.objects if obj.get("part_type") == "PURCHASED"]
    if len(printed) != 6:
        raise RuntimeError(f"Expected 6 printed objects, found {len(printed)}")
    # The syringe STL is intentionally split into fixed and moving subassemblies.
    if len(purchased) != 23:
        raise RuntimeError(f"Expected 23 purchased scene objects after syringe split, found {len(purchased)}")
    print(f"VIZ_VALIDATE source_stls={len(source_files)} printed_objects={len(printed)} "
          f"purchased_objects={len(purchased)} total_scene_objects={len(bpy.data.objects)}")


def main():
    reset_scene()
    scene = bpy.context.scene
    configure_scene(scene)

    printed_coll = new_collection("01 — PRINTED PARTS (blue; toggle me)")
    purchased_coll = new_collection("02 — PURCHASED PARTS (orange; toggle me)")
    labels_parent = new_collection("03 — LABELS + LEADER LINES (toggle me)")
    label_colls = {
        "hero": new_collection("Labels — Hero overview", labels_parent),
        "plan": new_collection("Labels — Plan component map", labels_parent),
        "mechanism": new_collection("Labels — Mechanism release", labels_parent),
        "fluid": new_collection("Labels — Fluid path", labels_parent),
    }
    reference_coll = new_collection("04 — REFERENCE ARM + 100 mm SCALE (toggle me)")
    animation_coll = new_collection("05 — ANIMATED FLUID PULSE (frames 56–67)")
    studio_coll = new_collection("06 — CAMERAS + LIGHTING")

    mats = {
        "printed": make_material("PRINTED — saturated cyan PETG", (0.025, 0.46, 0.62), 0.08, 0.29,
                                 emission=(0.015, 0.24, 0.38), emission_strength=0.32),
        "baseplate": make_material("PRINTED — translucent cutaway baseplate", (0.02, 0.42, 0.58), 0.02, 0.26, 0.29,
                                   emission=(0.01, 0.20, 0.32), emission_strength=0.24),
        "electronics": make_material("PURCHASED — warm orange electronics", (0.95, 0.27, 0.055), 0.08, 0.32,
                                     emission=(0.55, 0.09, 0.01), emission_strength=0.30),
        "metal": make_material("PURCHASED — warm brass metal", (0.9, 0.49, 0.09), 0.72, 0.23,
                               emission=(0.40, 0.12, 0.01), emission_strength=0.22),
        "elastomer": make_material("PURCHASED — dark orange elastomer", (0.58, 0.095, 0.02), 0.0, 0.72,
                                   emission=(0.30, 0.035, 0.005), emission_strength=0.22),
        "strap": make_material("PURCHASED — orange webbing", (0.78, 0.16, 0.03), 0.0, 0.82,
                               emission=(0.35, 0.04, 0.005), emission_strength=0.22),
        "syringe": make_material("PURCHASED — translucent amber syringe", (0.94, 0.45, 0.08), 0.05, 0.18, 0.50,
                                 emission=(0.42, 0.11, 0.01), emission_strength=0.22),
        "reference": make_material("REFERENCE — translucent neutral forearm", (0.19, 0.23, 0.31), 0.0, 0.65, 0.24),
        "ruler": make_material("REFERENCE — 100 mm scale", (0.78, 0.83, 0.9), 0.2, 0.3),
        "label_text": make_material("LABEL — white lettering", (1.0, 1.0, 1.0), 0.0, 0.28,
                                    emission=(1.0, 1.0, 1.0), emission_strength=3.5),
        "label_printed": make_material("LABEL PLAQUE — printed blue", (0.012, 0.13, 0.19), 0.0, 0.38,
                                       emission=(0.005, 0.04, 0.07), emission_strength=0.25),
        "label_bought": make_material("LABEL PLAQUE — purchased orange", (0.30, 0.045, 0.007), 0.0, 0.42,
                                      emission=(0.10, 0.01, 0.001), emission_strength=0.22),
        "label_guide": make_material("LABEL PLAQUE — explanatory navy", (0.025, 0.05, 0.11), 0.0, 0.38,
                                     emission=(0.01, 0.025, 0.07), emission_strength=0.3),
        "leader_printed": make_material("LEADER — printed cyan", (0.06, 0.88, 1.0), 0.15, 0.25,
                                        emission=(0.02, 0.42, 0.65), emission_strength=0.7),
        "leader_bought": make_material("LEADER — purchased amber", (1.0, 0.45, 0.06), 0.15, 0.25,
                                       emission=(0.7, 0.18, 0.01), emission_strength=0.6),
        "leader_guide": make_material("LEADER — guide", (0.5, 0.68, 0.95), 0.05, 0.3),
        "motion": make_material("MOTION — lime arrow", (0.48, 1.0, 0.1), 0.0, 0.25,
                                emission=(0.25, 0.8, 0.03), emission_strength=1.6),
        "fluid": make_material("FLUID — emissive cyan", (0.02, 0.66, 1.0), 0.0, 0.16,
                               emission=(0.01, 0.55, 1.0), emission_strength=2.5),
        "floor": make_material("STUDIO — dark floor", (0.018, 0.025, 0.038), 0.0, 0.72),
    }

    imported = import_stls(printed_coll, purchased_coll, mats)
    syringe_static, syringe_plunger = split_syringe(imported["mockup_syringe_norm_ject_10ml"],
                                                     purchased_coll, mats["syringe"])
    imported["mockup_syringe_norm_ject_10ml"] = syringe_static
    imported["syringe_plunger"] = syringe_plunger

    add_reference(reference_coll, mats)
    floor = add_cube("Studio shadow floor", (105, 0, -30), (390, 260, 3), mats["floor"], studio_coll, 2)
    floor.visible_diffuse = True

    cameras = {
        "hero": add_camera("Camera — HERO isometric", (285, -280, 215), (105, 0, 6), 280, studio_coll),
        "plan": add_camera("Camera — PLAN component map", (105, 0, 330), (105, 0, 4), 260, studio_coll),
        "mechanism": add_camera("Camera — MECHANISM close-up", (75, -175, 100), (65, -2, 11), 150, studio_coll),
        "fluid": add_camera("Camera — FLUID PATH close-up", (165, -175, 92), (148, -5, 12), 170, studio_coll),
    }
    add_area_light("Key light — large softbox", (55, -90, 205), 720000, 115, (0.78, 0.9, 1.0), studio_coll)
    add_area_light("Fill light — warm", (220, -10, 125), 480000, 100, (1.0, 0.55, 0.28), studio_coll)
    add_area_light("Rim light — cyan", (90, 130, 150), 620000, 85, (0.3, 0.72, 1.0), studio_coll)
    add_area_light("Front label fill", (100, -180, 85), 320000, 120, (1.0, 0.82, 0.64), studio_coll)

    configure_animation(imported, syringe_plunger, animation_coll, mats)
    build_callouts(cameras, label_colls, mats)
    validate_scene(imported)

    # Render four complementary, camera-specific annotated views.
    render_view(scene, cameras["hero"], label_colls, "hero", 46,
                "mk3_viz_01_hero.png", (1800, 1200))
    render_view(scene, cameras["plan"], label_colls, "plan", 46,
                "mk3_viz_02_plan.png", (2000, 1300))
    render_view(scene, cameras["mechanism"], label_colls, "mechanism", 52,
                "mk3_viz_03_mechanism.png", (1800, 1200))
    render_view(scene, cameras["fluid"], label_colls, "fluid", 60,
                "mk3_viz_04_fluid_path.png", (1800, 1200))

    # Save a clean, ready-to-orbit state: hero labels, cocked pose, nothing selected.
    set_label_visibility(label_colls, "hero")
    scene.camera = cameras["hero"]
    scene.frame_set(46)
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 1200
    scene.render.filepath = str(ROOT / "mk3_viz_01_hero.png")
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = None
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.shading.type = "MATERIAL"
                area.spaces.active.region_3d.view_distance = 190
    scene["README"] = (
        "Open at frame 46 (cocked). Scrub frames 1–72: cock, latch, servo trip, "
        "10.073 mm / ~67 ms shot, fluid pulse. Toggle numbered collections in the Outliner."
    )
    scene["source_stl_count"] = EXPECTED_STLS
    scene["printed_source_count"] = 6
    scene["purchased_source_count"] = 22
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"VIZ_DONE blend={BLEND_PATH}")


if __name__ == "__main__":
    main()
