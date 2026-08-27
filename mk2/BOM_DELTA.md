# Mk2 buy-only BOM delta

Only items not stated as already owned are listed.

| Qty | Buy | Why / exact constraint |
|---:|---|---|
| 1 | Actuonix **L12-10-210-6-S** micro linear actuator | Real 10 mm-stroke, 210:1, 6 V limit-switch model; rated 80 N maximum load. The owned DS239MG is not adequate. |
| 1 | Pololu **U3V70F6** fixed 6 V step-up regulator | Supplies the actuator from the owned 1S LiPo. This is the explicitly required return of a boost rail; do not substitute an uncalibrated MT3608. |
| 1 | **DRV8833 dual H-bridge carrier**, >= 1 A/channel (Pololu #2130 or dimensionally equivalent) | Reverses the `-S` actuator for fire/reset from 3.3 V XIAO logic. |
| 1 | B. Braun/Air-Tite **NORM-JECT 10 mL two-part Luer Lock**, manufacturer NJ-4606728 / Restek 22775 | PP/PE, no rubber or silicone oil; 15.9 mm bore and 17.3 mm OD. Buy an individual unit if available rather than a 100-pack. |
| 2 | 14 ga blunt stainless dispensing needles, **>= 1.6 mm clear ID**, about 25 mm metal length | One live coherent-jet barrel and one capped symmetry dummy. Do not use the owned 0.4 mm brass nozzles. |
| 2 | 25 mm hook-and-loop cinch straps: about 300 mm forearm and 220 mm palm | The specified two removable straps; trim only after a fit test. |
| 1 | SS12D00-family SPDT slide power switch, body <= 13 x 8 x 7 mm, **verified >= 1 A at 6 VDC** | Required hard battery disconnect; the current rating must be genuine, not inferred from an AC-only listing. |

