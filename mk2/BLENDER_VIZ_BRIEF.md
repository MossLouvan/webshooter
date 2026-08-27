# Web-Shooter Mk3 — Blender Visualization Brief

**To:** Codex (full access)
**Goal:** a Blender scene the builder can open, spin, and understand — showing the finished
Mk3 device assembled, with every part named and every purchased component in place.

Blender **5.2.1** is installed at:
`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`
Run headless as `blender -b --python <script>.py`, or with a GUI as `blender --python <script>.py`.

---

## 1. What you are visualizing

The Mk3 web-shooter you just built in `webshooter_mk2.py`. Source geometry is the STL set in
`assembly_stl/` — **printed parts and purchased-part mockups, each already transformed into its
assembly position.** If any mockup is missing from that folder, export it first; the whole point of
this deliverable is showing the bought parts in place, not just the printed ones.

**Who it is for.** A university student who is going to build this thing. He has said, repeatedly
and fairly, that he wants to *see* how it works and what each piece does. He is not a CAD person.
Assume he will open the .blend, orbit it, click things, and expect that to teach him the machine.

---

## 2. Hard requirements

1. **A `.blend` file** in this directory that opens ready to look at — framed, lit, material
   preview shading on, nothing selected, no console errors.
2. **Every object named in plain language**, not `mockup_ds239mg_servo`. "Servo (fires the sear)"
   beats a part number.
3. **Printed vs purchased must be visually obvious at a glance.** Pick a scheme and be consistent.
4. **Text labels in 3D with leader lines to their parts**, positioned so they do not overlap each
   other or bury the model. This is harder than it sounds — a naive "label above each part" pile
   collapses into unreadable soup. Fan them, stagger them, or place them in a ring; whatever
   actually reads. Check your own renders and iterate until it is legible.
5. **Collections** so groups can be toggled: printed parts, purchased parts, labels, reference
   (arm/hand). Named so the outliner is self-explanatory.
6. **The chassis/baseplate should not hide the mechanism.** Transparency, a cutaway, or a section —
   your call, but the internals must be visible.
7. **At least three rendered PNGs** saved beside the .blend: an isometric hero, a plan view, and one
   more of your choosing that best explains the mechanism.

## 3. What would make it genuinely good

These are not required. Take them if they serve.

- **Show the mechanism moving.** The whole device is one motion: cock the spring, trip the sear,
  plunger drives forward, fluid leaves the barrel. A short timeline animation — even 60 frames of
  the plunger stroke and the sear release — would teach more than any static render. Keyframe it so
  he can scrub.
- **An exploded view** on a second frame range, or as a separate scene, so he can see the stack-up.
- **A callout for the fluid path** — the route from syringe to barrel is the thing most likely to
  confuse, and it is worth making legible on its own.
- **A scale reference.** A hand, a forearm, a ruler — something that makes 118 mm feel like a real
  size rather than an abstract number.

## 4. Latitude

**The above is the goal, not a recipe.** You know Blender's Python API and you can see the actual
geometry; I cannot. If a different presentation explains this machine better, build that instead
and say why in your notes. Specifically, you may freely choose: camera framing and lens, lighting
rig, materials and colour scheme, label typography and placement strategy, whether to animate,
whether to explode, and how to handle transparency.

Two things I would not change without a reason: **plain-language names**, and **purchased parts
visible in place**. Everything else is yours.

## 5. Deliver

- The `.blend`, the render PNGs, and the generator script (so it can be re-run after CAD changes —
  this model will keep changing, and a viewer that must be hand-rebuilt each time is dead weight).
- A short note in `DESIGN_NOTES.md` or a separate `VIZ_NOTES.md`: what you built, what you chose and
  why, and how to regenerate it.

Verify before you finish: open the .blend headlessly, confirm the expected object count, confirm no
part is missing, and look at your own renders. If a render is unreadable, fix it and render again —
do not ship the first one.

Work autonomously. Do not stop to ask questions.
