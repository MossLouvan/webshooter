# Web-Shooter Mk5 visualization

`webshooter_mk5.blend` is a Cycles product-presentation scene generated from
the transformed STLs in `mk5_assembly_stl/`. It opens at the cocked/ready frame
with the labeled hero camera active.

## Presentation design

- Satin/brushed steel distinguishes printed working structure; warm polished
  brass identifies the spring, plunger interfaces, and muzzle.
- The cartridge uses transmissive borosilicate glass. Frosted translucent PETG
  keeps the chassis readable without hiding the mechanism.
- Electronics use graphite polymer, LiPo foil, and green FR4/solder-mask
  materials. The palm switch is matte red rubber.
- Every imported STL has a 0.4 mm, three-segment highlight bevel.
- A four-light studio rig, low-strength environment, and smooth charcoal
  cyclorama provide soft contact shadows and controlled metal/glass reflections.
- The label-free beauty camera uses restrained depth of field. The technical
  camera is fully sharp and retains short, staggered, part-following leaders;
  the baseplate label remains below the device.
- The mechanism camera views the sear/pawl from the open side so the dark servo
  does not wall off the working interface.

## Outputs

- `mk5_00_beauty.png` — label-free portfolio hero.
- `mk5_01_hero.png` — labeled technical hero.
- `mk5_02_mechanism.png` — sear/pawl and spring-drive close-up.
- `mk5_03_plan.png` — top-down assembly layout.
- `mk5_04_firing.png` — fired state and fluid pulse.

All final stills are 2560 × 1600, rendered in Cycles at 256 samples with
denoising and AgX medium-high contrast.

## Regenerate

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b --python '.\build_mk5_viz.py'
```

The generator requests OptiX first, CUDA second, and reports a CPU fallback if
neither GPU backend initializes. For quick beauty look-development, set
`MK5_LOOKDEV=1`. To render only one named output, set `MK5_VIEW` to its filename
stem, for example `mk5_02_mechanism`.
