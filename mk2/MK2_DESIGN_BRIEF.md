# Web-Shooter Mk2 — DESIGN BRIEF

**From:** Claude Code (Fable 5), 2026-08-27
**To:** Codex (full access)
**Status:** clean-sheet redesign. Mk1 is archived at `../archive_mk1/` and is **not** to be reused.

---

## 0. Why Mk1 was scrapped

Mk1 was an **enclosure containing a pump**. It grew to a 118 × 64 × 38 mm box because rigid parts
were stacked orthogonally and walls were wrapped around whatever the total came to. It also fired
only **0.1 mL per shot** (a fragrance pump's dose), which is roughly two orders of magnitude short
of what makes a visible strand. Three independent reviews found it over-engineered, badly packed,
and functionally doubtful.

**Mk2 is a different object: an open frame carrying a projector.**

The builder showed a reference build he wants to match — a flat plate strapped to the forearm,
components mounted exposed on top, and barrels extending forward over the back of the hand. No
shell. That silhouette is the design target, and it is not negotiable.

---

## 1. Design targets, in priority order

1. **Sleek.** Profile at the wrist **≤ 25 mm** above the skin. Nothing may look like a box.
2. **Functional.** It must deliver enough fluid to read as a strand, not a mist. Target
   **≥ 1.5 mL per shot** — at least 15× Mk1.
3. **Simple.** Target **≤ 6 printed parts**. Mk1 had 13.
4. **Buildable** by a student with a Bambu printer, hand tools, and the existing cart.

Where 1 and 2 conflict, say so explicitly and propose the trade rather than silently picking.

---

## 2. Architecture

**Open baseplate, no enclosure.** A curved plate that follows the dorsal forearm, ~3–4 mm thick,
with components bolted to its top face and left exposed. Cable runs and mechanism are visible —
that is the aesthetic, not a compromise.

**Three zones along the arm:**

| Zone | Location | Contents |
|---|---|---|
| Rear | forearm, x ≈ 0–90 | reservoir + drive mechanism |
| Mid | wrist, x ≈ 90–120 | electronics, kept thinnest — this crosses the flex point |
| Front | back of hand, x ≈ 120–190 | barrel bridge + barrels |

The **barrel bridge** is the signature feature. A narrow arm carrying the barrels forward over the
knuckles, so the barrels sit high and point where the hand points. The back of the hand is flat and
unused — exploit it. Keep the bridge narrow so it does not obstruct finger movement, and set the
barrel line so it clears the knuckles when the wrist is neutral.

**Two barrels.** Both are visible; at minimum one is live. Decide whether the second is live
(split flow, two strands) or a dummy for symmetry, and justify it. Symmetry is a legitimate reason
— this is a worn object.

**Straps, not a cuff.** Two strap slots in the baseplate for 25 mm webbing: one across the forearm,
one across the palm/hand. Delete the entire Mk1 elliptical-cuff apparatus. The baseplate's underside
should be a simple concave curve (dorsal forearm crown radius ≈ 50 mm) with a thin foam pad
assumed, not a fitted anthropometric shell.

---

## 3. Fluid system — the part that must actually work

**Use a syringe as reservoir, pump, and seal in one part.**

This is the key simplification. A syringe already is: a sealed reservoir, a positive-displacement
pump, a plunger seal, and a standard Luer outlet. Adopting it deletes the atomizer, both EPDM
glands, the M6 nut, the nozzle block's seal stack, the PTFE thread tape and the moving actuator —
i.e. every leak path in Mk1.

- **Reservoir:** a 10–20 mL plastic syringe, laid along the forearm. Must be **PP/PE with no rubber
  plunger tip** — acetone swells rubber. Parameterize barrel OD and length.
- **Outlet:** Luer taper → short PTFE or PP line → barrel. A blunt dispensing needle in the
  **1.0–1.5 mm** range is the physics-recommended orifice for a coherent jet; the 0.4 mm brass
  nozzle from Mk1 is explicitly **not** the plan (that orifice forces heavy dilution, and dilution
  is what destroys stringing).
- **Fluid:** Beacon Fabri-Tac, **undiluted or thinned no more than 1:0.5**. The concentration is
  what makes it string.

**Drive:** the servo pushes the plunger. The plunger needs tens of millimetres of travel, which a
short horn cannot give, so you need mechanical advantage — a long lever, a rack, a lead screw, or
a cam. **This is the single most important engineering decision in Mk2 and it is yours to make.**

Constraints and known data:
- Corona DS239MG: **4.6 kg·cm at 6 V**, and servodatabase lists its rotation as limited — verify
  and design conservatively. The builder owns **two**.
- Required plunger force is **unknown** and depends on syringe bore, fluid viscosity and orifice.
  Estimate it, show the arithmetic, and state the margin.
- **If the DS239MG cannot do it, say so and specify what to buy instead** (a higher-torque servo, a
  geared DC motor with a lead screw, or a linear actuator). A correct recommendation to buy a
  different actuator is a better outcome than a design that stalls.
- A one-shot-per-fill design is acceptable if it buys sleekness; a multi-shot ratchet is better.
  Choose and justify.

**Refill** must not require disassembly — the syringe should lift out or be reloaded in place.

---

## 4. Electronics

Carry over from Mk1, unchanged and already owned: **XIAO ESP32-C3**, **TP4056 USB-C with DW01
protection**, **EEMB 103454 LiPo**, **12 × 12 mm tactile switch**, 26 AWG silicone wire, JST-PH.
**No MT3608** — the boost was deleted and stays deleted unless your actuator choice forces it back,
in which case flag it loudly.

- Trigger: palm switch, **double-tap within 400 ms**.
- **Do not use GPIO8 or GPIO9** for the switch — GPIO9 is the boot strapping pin.
- A **power switch is required** and does not exist yet. Specify one and give it a mount.
- Boards have **no mounting holes** — design clips or captive pockets.
- USB-C on the TP4056 must be reachable for charging; the XIAO's USB-C must be reachable for
  flashing. On an open frame this is easy — do not squander it.

---

## 5. Deliverables

Work in `mk2/`. Do not touch `../archive_mk1/`.

1. **`webshooter_mk2.py`** — parameterized CadQuery model. Named constants at the top with a
   confidence comment on anything unverified. Exports one STEP and STL per printed part.
2. **A real assembly** — `cadquery.Assembly` with explicit transforms, plus **mockup solids** for
   every purchased item (syringe, servo with horn/lever, LiPo, XIAO, TP4056, switch, barrels,
   straps, and a forearm + hand reference) so the assembly shows how it works. Mockups in a
   separate dict, never exported as printable.
3. **`assembly_stl/`** — every part at its assembly transform, for rendering.
4. **`DESIGN_NOTES.md`** — the actuator decision with its force arithmetic, the profile height
   achieved, part count, what is proxy/estimate/unverified, and a measure-before-printing list.
5. **`BOM_DELTA.md`** — exactly what must be **bought that the builder does not already own**, with
   quantities and why each is needed. Be specific and minimal. He already owns everything in §4
   plus Fabri-Tac, acetone, PTFE tube, EPDM assortment, M3 screws, M3 heat-set inserts (5.0 × 4.0),
   4 × 2 mm magnets, brass 0.4 mm nozzles, glass atomizers, dropper bottles, butyl gloves,
   respirator, goggles.

## 6. Hard requirements — these will be checked

- Every printed part: **exactly one solid**, `isValid()`, and no geometry below its own z = 0.
- **No unintended interference.** Run a pairwise intersection check across all parts *and* mockups
  and report the volumes. Intended contacts must be listed explicitly with a reason. Assume a
  reviewer will run this check without your allow-list — Mk1's did, and found 18 pairs.
- Every mating feature must exist on **both** sides, driven by **shared named constants**. No
  duplicated coordinate literals.
- No declared-but-unused parameters.
- Wrist profile height stated and ≤ 25 mm.
- Shot volume stated and ≥ 1.5 mL.

## 7. Latitude

The zones, the syringe, and the barrel bridge are the concept. **Everything else is yours.** If a
different drive mechanism, a different reservoir, or a different part split serves the three targets
better, take it and explain why. If you conclude a target is unachievable, say which one and what it
would cost to reach — do not quietly miss it.

Three independent reviewers will audit this build and will keep auditing until they have no
substantive findings. Design for that.

Work autonomously. Do not stop to ask questions.
