# Mk5 — MULTI-SHOT BRIEF

**Status:** Mk4 was rejected NOT READY by two independent acceptance reviews. The builder has
independently identified the same top defect: **it fires once and does not return.** He wants a
mechanism that shoots, re-cocks itself, and shoots again.

This brief is the fix list plus the new requirement. Read it whole before editing anything.

---

## 1. THE NEW REQUIREMENT — multi-shot with self-recock

**Mk4 fires exactly one useful shot per fill, and nobody noticed until two reviewers and the
builder found it separately.** The carriage cocks to a fixed x=31.57 and fires to a fixed x=48.00.
After shot 1 the syringe plunger has advanced 16.43 mm and sits at x=60.00 — beyond anywhere the
carriage can reach. Shot 2 pushes air.

**Mk5 must fire, re-cock, and fire again, repeatedly, until the cartridge is empty.**

### This is a caulk gun

The problem is exactly the one a caulk gun solves: a **fixed-stroke actuator advancing a plunger
incrementally through a one-way grip.** The plunger never retracts — it does not need to. Each
cycle the carriage grips the rod further back, drives it forward one stroke, then releases and
slides back along the now-stationary rod to grip again.

Adopt that. A tilting grip plate, a ratchet and rack, or a one-way roller clutch are all valid;
pick one and justify it. The grip must hold 37 N forward and release cleanly on the return.

### Shot count is a cartridge-size decision

| Cartridge | shots at 2.0 mL |
|---|---|
| 5 mL (Mk4) | 2.5 |
| **10 mL** | **5** |
| 20 mL | 10 |

Mk4 went 10 mL -> 5 mL to cut force and height. With a ratchet the force argument weakens, because
the servo can do the work. **Re-open that choice.** If you go back to 10 mL, say what it costs in
wrist profile and re-check the target (<= 25 mm).

If you reduce shot volume to gain shots, the outlet bore must shrink to hold exit velocity —
`A_o = V / (t · v_exit)`. 1.5 mL -> 3.46 mm bore; 1.0 mL -> 2.83 mm. Do not silently lose range.

### Auto-recock is affordable — I checked before asking

```
recock work            = ½ · 37.42 N · 16.43 mm = 307 N·mm = 0.307 J
DS239MG stall           = 451 N·mm   (4.6 kg·cm at 6 V)
honest continuous (⅓)   = 150 N·mm

torque needed vs servo sweep:
    90°  -> 196 N·mm   too much
   120°  -> 147 N·mm   marginal
   160°  -> 110 N·mm   1.4× margin
   180°  ->  98 N·mm   1.5× margin
```

**A generous sweep (160–180°) through a cam or lever makes recock feasible with the servo he already
owns.** Verify the DS239MG's actual usable rotation — servodatabase lists it as limited, and if it
cannot sweep 160° this whole approach changes.

---

## 2. THE SEAR PROBLEM, AND THE ARCHITECTURE CHOICE

Both reviewers computed the sear release torque, which nothing had ever computed:

```
holding moment  |r_z| · F = 13.4 × 37.42      = 501 N·mm
face friction   µ · F · |r_x| = .35 × 37.42 × 9 = 118 N·mm
pin drag                                       ≈  18 N·mm
                                       total  ≈ 520–620 N·mm
```

against ~150–300 N·mm from the servo. **The over-centre sear is too self-holding to open.** Being
strongly self-holding and being openable are the same axis, and Mk4 maximised the wrong end.

Three architectures. Choose one, justify it, and say what you gave up:

**A — Cam cock-and-release, no sear at all.** The servo sweeps once: the cam draws the carriage
back, and at the drop-off point releases it. Simplest, deletes a printed part and the entire
release-torque problem. **Cost:** a ~1 s wind-up between trigger and shot — you lose the instant
thwip, which is most of the appeal.

**B — Near-pivot sear (recommended starting point).** Move the contact onto the pivot line so
`r_z ≈ 0`. Holding moment collapses toward zero and release becomes **friction-only**, tens of
N·mm. It is then no longer self-holding, so it needs a light return spring to keep it engaged —
which is what every real firearm sear has. Keeps the instant shot; costs one spring.

**C — Hand-cocked ratchet.** The builder cocks between shots; the servo only trips. Simplest and
most reliable, but it is not what he asked for.

**B is the recommendation.** A reviewer proposed it independently: *"a simpler transverse sear
bearing near the pivot line — so the release torque is friction only."*

---

## 3. BLOCKING DEFECTS TO FIX (all measured, not inferred)

| # | Defect | Evidence |
|---|---|---|
| 1 | **Single-shot** | above — the headline |
| 2 | **Servo cannot open the sear** | 520–620 N·mm needed vs ~150–300 available |
| 3 | **No servo interface exists anywhere** | `grep servo` finds only comments. No mount, horn, pushrod or linkage. `BOM_DELTA.md` says "servo mounting as shown"; nothing is shown |
| 4 | **Plunger thumb flange does not fit** | Ø18.0 vs 14.90 mm rail clear span. 385 mm³ into the carriage, 31.85 mm³ into the baseplate |
| 5 | **Finger flange buried in the plate** | 115.60 mm³ |
| 6 | **Spring force 24% above every downstream number** | it seats on the abutment FRONT face at x=6.0, not x=8.0. True cocked force **37.42 N**, not 30.09. The docstring still claims an 11.2 N "thumb pull" |
| 7 | **Cartridge cannot be installed** | the drop-in opening is `2 × cradle_r × 0.72 = 10.30 mm` against a **13.70 mm** barrel |
| 8 | **Thrust path never lands on a face** | the stop is bored r=9.35; the adapter is r=9.05 and passes through it. ~10–30 N per shot goes into a glue joint and an insert-boss corner |
| 9 | **Carriage has no vertical retention** | 3.25 mm of free lift on a wrist-worn device |
| 10 | **Bore clogs permanently** | 151 mm³ of adhesive in an open 4 mm bore; clearing a cured plug needs ~151 N against 30 N available. The adapter is *bonded*, so there is no disassembly path. **Design a purge or a serviceable joint** |
| 11 | **Spring buckling** | L/D = 6.48 at 0.357 deflection, pinned-pinned. Needs a pilot or a guide tube |
| 12 | **Half-cock is not held** | abort a cock and the spring cams the pawl open and throws the carriage. It can catch a finger between the pad and the plunger flange |
| 13 | No fillets or chamfers anywhere | one `fillet` token in the whole file, in a comment. Every edge on a 172 mm plate worn against an arm is a printed square corner |

---

## 4. THE HARNESS — how this was missed, and the rule

`verify_independent.py` guards its mockup load with `if hasattr(M, "mockups")`. Mk4 defined none,
so the guard silently skipped and `bodies` held only the five printed parts. Every defect above
lives at a printed-to-purchased interface. A reviewer's phrasing: **"the harness was not gamed by
editing — it was starved by the model."**

`make_mockups()` now exists and the harness sees 7 real overlaps where it saw 0.

**RULES, absolute:**
- **Never** delete or narrow `make_mockups()` to make a failure disappear. Every body the machine
  touches belongs in it — and that now includes the servo, its horn and any linkage you add.
- **Never** loosen a threshold or grow `TOUCH_OK` to pass. If a check is a genuine false positive,
  prove it with measured geometry and fix the check.
- **Add checks for what you build.** A ratchet needs a check that it holds forward and releases on
  return. A servo linkage needs a **torque** check — there is not one load, stress or torque check
  in 1000+ lines, which is why defect 2 survived four revisions.

---

## 5. WHAT MUST NOT REGRESS

- exit velocity 3.84 m/s, ballistic range >= 1.5 m, shot volume >= 1.5 mL, all **derived**
- energy margin > 1.0 against the **real 8 ga cannula** (0.170 J), not just the 4 mm bore
- every printed part: exactly one solid, valid, `z_min ≈ 0`
- wrist profile <= 25 mm
- the sear kinematics that finally work — both reviewers confirmed the holding sign, the 24 mm²
  bearing patch and the self-camming re-cock ramp are correct. **Keep what works.**

## 6. DESIGN INTENT

Sleek but not sterile. The mechanism stays visible because it is worth seeing. This should read as
a considered instrument someone built — not a consumer product, and not parts bolted to a board.
Keep the part count honest: adding a ratchet is justified because it buys multi-shot; adding
anything that merely solves a problem another choice created is not.
