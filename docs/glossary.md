# Glossary

Use these terms consistently in procedures and issue reports.

| Term | Meaning |
| --- | --- |
| ACE | The connected Anycubic ACE Pro Gen 1. |
| Slot | One of the four ACE filament positions, numbered 1–4 on the enclosure. |
| Index | The software slot number, from 0 to 3. Slot 4 uses index 3. |
| Inlet | The ACE opening where the user inserts filament. |
| Gate state | The software interpretation of filament presence at an ACE inlet. |
| Head sensor | The U1 sensor that detects filament at a toolhead. |
| Load | The U1 workflow that transfers filament into the selected hotend. |
| Unload | The U1 workflow that releases filament from the hotend and retracts it into the PTFE path. |
| Forward take-up | A limited forward movement after retraction that pulls loose filament toward the U1. |
| Fast stage | The initial finite movement at the configured fast speed. |
| Slow stage | The approach movement that ends when the head sensor detects filament. |
| Origin | A temporary record that permits a calculated fast stage. |
| Advance | The conservative forward distance recorded after successful take-up. |
| Feed assist | ACE support for filament transport after the head takes control. |
| Fresh status | A recent ACE status reply from the current connection and command generation. |
| NFC | Near-field communication used to read a spool tag. |
| Material data | The brand, type, subtype, color, and presence fields associated with a slot. |
| External mode | The U1 detection setting that disables its internal reader path. |
| Root Access | The U1 setting that permits SSH system access. |
| Advanced Mode | The U1 setting that exposes extended controls. |
| Persistence marker | `/oem/.debug`, which enables persistence for system changes. |

The word **ready** describes a software status.
It does not prove filament position or mechanical tension.
