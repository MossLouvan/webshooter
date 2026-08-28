"""Read-only integrity check for webshooter_mk3_visualization.blend."""

from pathlib import Path
import bpy


root = Path(__file__).resolve().parent
expected_files = sorted(path.name for path in (root / "assembly_stl").glob("*.stl"))
source_files = sorted({obj.get("source_stl") for obj in bpy.data.objects if obj.get("source_stl")})
missing = sorted(set(expected_files) - set(source_files))
extra = sorted(set(source_files) - set(expected_files))
printed = [obj for obj in bpy.data.objects if obj.get("part_type") == "PRINTED"]
purchased = [obj for obj in bpy.data.objects if obj.get("part_type") == "PURCHASED"]
labels = [obj for obj in bpy.data.objects if obj.type == "FONT" and obj.name.startswith("3D label")]
leaders = [obj for obj in bpy.data.objects if obj.name.startswith("Leader line")]
animated = [obj for obj in bpy.data.objects if obj.animation_data and obj.animation_data.action]

assert len(expected_files) == 28, len(expected_files)
assert source_files == expected_files, (missing, extra)
assert len(printed) == 6, len(printed)
assert len(purchased) == 23, len(purchased)  # syringe STL is fixed + moving objects
assert len(labels) >= 30, len(labels)
assert len(leaders) >= 35, len(leaders)
assert len(animated) >= 10, len(animated)
assert bpy.context.scene.frame_current == 46, bpy.context.scene.frame_current
assert bpy.context.scene.camera and "HERO" in bpy.context.scene.camera.name
assert not bpy.context.selected_objects

required_collections = (
    "01 — PRINTED PARTS (blue; toggle me)",
    "02 — PURCHASED PARTS (orange; toggle me)",
    "03 — LABELS + LEADER LINES (toggle me)",
    "04 — REFERENCE ARM + 100 mm SCALE (toggle me)",
)
for name in required_collections:
    assert bpy.data.collections.get(name), name

pngs = sorted(root.glob("mk3_viz_*.png"))
assert len(pngs) >= 4, len(pngs)
dimensions = {}
for path in pngs:
    image = bpy.data.images.load(str(path), check_existing=False)
    dimensions[path.name] = tuple(image.size)
    assert image.size[0] >= 1800 and image.size[1] >= 1200, (path.name, image.size[:])
    bpy.data.images.remove(image)

print(
    "VIZ_VERIFY_OK "
    f"total_objects={len(bpy.data.objects)} unique_source_stls={len(source_files)} "
    f"printed_objects={len(printed)} purchased_objects={len(purchased)} "
    f"labels={len(labels)} leaders={len(leaders)} animated_objects={len(animated)} "
    f"frame={bpy.context.scene.frame_current} camera={bpy.context.scene.camera.name!r} "
    f"png_dimensions={dimensions}"
)
