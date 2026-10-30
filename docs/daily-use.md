# Daily loading and unloading

[简体中文](daily-use.zh-CN.md) · [Tube calibration](configuration.md) · [NFC](nfc.md)

## Insert and identify

1. Insert filament into an empty ACE inlet.
2. Keep your hands away from the rollers.
3. Wait for the short intake and NFC search to finish.
4. Check material details on U1. Enter them manually if the spool has no readable tag.

The filament waits near ACE. Insertion alone does not start full loading to the head.
ACE controls its recognition movement; this project does not promise a fixed intake distance for every tag.

## Load to the head

1. Select the matching tool on the U1 screen.
2. Start its normal **Load** operation.
3. Follow the screen prompts. Wait for completion before sending another command.

ACE first feeds the configured fast segment when its starting position is known.
It then uses the slower approach until the head sensor detects filament.
U1 completes its native hotend loading process.
After a restart or uncertain position, transport can remain at the slower speed.

## Unload and reduce loose loops

1. Start normal **Unload** for the matching tool.
2. Wait for U1 to finish releasing filament from the hotend.
3. Wait for ACE to complete its configured retraction.
4. If forward take-up is enabled, wait for that movement to finish.
5. Confirm that the tip remains in ACE and its rear tube.

Material information stays available while the ACE inlet remains occupied.
To load again, select normal Load without removing the filament.

> [!IMPORTANT]
> **Forward take-up starts disabled on new installations. Calibrate it before use.**
> It feeds filament toward U1 to remove loose loops. It has no tension sensor and does not drive the roller independently.

The tested example uses 1250 mm retraction at 80 mm/s, then 300 mm forward at 50 mm/s.
These are not universal distances. See [the calibration procedure](configuration.md).

## Remote operation

The easiest remote control is the optional U1 screen mirror.
Enable **Firmware Config → Web → Remote Screen Access**, then open `/screen/` on that printer.
Use the same Load or Unload control as on the physical screen.
This installer does not enable the screen mirror automatically.
See the [v24 remote-screen instructions](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/remote_screen.md).

The web console also exposes the full native workflow.
For slot 1, send **one** of these commands and follow the printer prompts:

Load:

```gcode
AUTO_FEEDING EXTRUDER=0 LOAD=1
```

Unload:

```gcode
AUTO_FEEDING EXTRUDER=0 UNLOAD=1
```

| ACE slot | `EXTRUDER` value |
| --- | --- |
| 1 | 0 |
| 2 | 1 |
| 3 | 2 |
| 4 | 3 |

Do not send Load and Unload together. Do not use `ACE_FEED` or `ACE_RETRACT` as substitutes for the hotend workflow.
Those commands only perform lower-level transport.
The optional [AFC panel](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/afc-lite.md) requires its own AFC Stub setting; it is not a default panel supplied by this installation.
