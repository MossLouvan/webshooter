# Mk3 buy-only BOM delta

**No additional purchase is required beyond the inventory and updated cart stated in `MK3_REBUILD_BRIEF.md`.**

## Deleted from the Mk2 purchase list

| Qty removed | Item | Reason |
|---:|---|---|
| 1 | Actuonix L12-10-210-6-S | A 210:1 gearbox cannot deliver the required plunger speed. Even its no-load kinematic ceiling dribbles. Replaced by a hand-cocked spring and sear. |
| 1 | Pololu U3V70F6 fixed 6 V boost | It existed only for the deleted linear actuator. |
| 1 | DRV8833 carrier | It existed only to reverse the deleted linear actuator. |
| 1 | Separate NORM-JECT syringe purchase | The updated cart already contains 10 mL Luer-lock syringes. Verify the actual bore/OD/flanges against the sourced envelope before printing. |
| 2 | Separate 14 ga needle purchase | The updated cart already contains an 8/10/12/14 ga blunt-needle assortment. Mk3 uses one live 8 ga nozzle and one capped 8 ga dummy. |
| 2 | Separate 25 mm straps | The updated cart already contains 1 inch hook-and-loop strapping. |
| 1 | Separate slide-switch purchase | The builder already owns tactile switches; the required hard battery disconnect remains an owned-item wiring gate. If the owned stock lacks a DC-rated disconnect, add one only after measuring it and update the CAD envelope. |

## Inventory consumed by Mk3

| Qty | Owned / already buying | Use |
|---:|---|---|
| 1 | Corona DS239MG servo | Trips the unloaded sear; does not drive the syringe or hold spring force. |
| 1 | Compression spring selected from assortment | OD <=10 mm, free length about 39.7 mm, measured rate 1.94 N/mm, <=28 N cocked, <=0.20 J measured release energy. |
| 1 | 10 mL Luer-lock syringe | 15.9 mm modeled bore; complete barrel, finger flange, plunger rod and thumb flange are included in the assembly mockup. |
| 2 | 8 ga blunt needles | One live 3.0 mm-effective outlet and one capped visual dummy. |
| 1 each | XIAO ESP32C3, TP4056/DW01, 1S LiPo | Logic, protected charging, and power. No motor driver or actuator boost. |
| 3+ | M3 screws; 2 M3 heat-set inserts | Bridge joint, carriage/cocking pin, sear pivot and servo mounting as shown. Final screw lengths must match the actual owned hardware. |
| As needed | EPDM O-rings/bands | Syringe and board retention in modeled grooves/anchors. |
| As needed | 1 inch hook-and-loop strap | Two forearm loops and one palm/switch-pod loop. |
| Small batch | Fabri-Tac and acetone | 1:1 starting mixture only, with ventilation and ignition control. |
| 6 parts | PETG | Base, bridge, carriage, cocking lever, sear and switch pod. |

Do not substitute a stiffer spring to chase range. The generator rejects more than 0.25 J modeled release energy, and the build notes impose a lower 0.20 J measured spring-selection gate.
