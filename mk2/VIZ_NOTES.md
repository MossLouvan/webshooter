# Mk3 Blender visualization

## What is included

- `webshooter_mk3_visualization.blend` opens at frame 46 in the cocked-and-ready hero view. Nothing is selected, the hero camera is active, and material preview is enabled for interactive orbiting.
- All 28 transformed source STLs in `assembly_stl/` are present: 6 printed parts and 22 purchased-part mockups. The syringe STL is split inside Blender into a fixed barrel and a moving plunger so the mechanism can animate correctly; it still retains its source-STL metadata.
- Every imported part has a plain-language Outliner name. Printed parts are cyan/blue; purchased parts are orange/amber. The translucent cyan baseplate is a deliberate cutaway so the spring, carriage, sear, electronics, and syringe interfaces remain visible.
- Numbered top-level collections toggle printed parts, purchased parts, labels, reference geometry, the animated fluid pulse, and studio cameras/lights. The label collection has separate Hero, Plan, Mechanism, and Fluid Path callout sets.
- 3D callout plaques and leader lines are placed in camera-facing rings/rows rather than piled above the model. The plan view groups small hardware into builder-friendly subsystems to keep the leader layout readable.
- A simplified translucent forearm and a real 100 mm scale bar provide size context.

## Animation

Scrub frames 1–72 at 60 fps. Timeline markers explain each phase:

- Frames 1–8: fired/rest state.
- Frames 8–36: the hand lever retracts the carriage and compresses the spring.
- Frames 36–46: the positive sear holds the cocked load while the lever returns.
- Frames 46–52: the servo horn trips the unloaded sear tail.
- Frames 53–57: the carriage and syringe plunger move 10.073 mm over four frames (about 67 ms, matching the 69 ms design target).
- Frames 56–67: a cyan pulse leaves the live lower nozzle. The upper nozzle remains capped and inactive.

The file opens on frame 46 so it is useful as a static model immediately; animation is available by scrubbing without changing scenes.

## Rendered views

- `mk3_viz_01_hero.png` — assembled isometric overview.
- `mk3_viz_02_plan.png` — plan-view component map with grouped subsystem callouts.
- `mk3_viz_03_mechanism.png` — sear-release close-up at frame 52.
- `mk3_viz_04_fluid_path.png` — syringe, straight fluid route, live nozzle, capped dummy nozzle, and animated discharge at frame 60.

## Regenerate and verify

From this directory in PowerShell:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b --python '.\build_blender_viz.py'
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b '.\webshooter_mk3_visualization.blend' --python '.\verify_blender_viz.py'
```

The generator clears and rebuilds only its Blender scene and rewrites the `.blend` and four PNGs; it does not change the STL sources. The verifier is read-only.

Final verification on Blender 5.2.1: 220 scene objects, 28 unique source STLs, 6 printed objects, 23 purchased scene objects after the syringe split, 37 3D labels, 42 leader lines, and 13 animated objects. All four PNGs are at least 1800 × 1200; the plan view is 2000 × 1300.
