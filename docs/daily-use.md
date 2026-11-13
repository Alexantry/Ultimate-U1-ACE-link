# Daily loading and unloading

[简体中文](daily-use.zh-CN.md) · [Tube calibration](configuration.md) · [NFC](nfc.md)

## What to do and what happens

| You do this | This happens |
| --- | --- |
| Insert filament into an empty ACE inlet, hands away from the rollers | The ACE grips the filament, reads the NFC tag, and waits. It does not load to the head. |
| Check the material details on the U1 | Enter them manually if the spool has no readable tag. |
| Select the tool on the U1 and start normal **Load** | The ACE feeds fast, then slowly until the head sensor detects filament. The U1 completes the hotend load. |
| Start normal **Unload** for the tool | The U1 releases the filament from the hotend. The ACE retracts it and keeps the tip in the ACE and its rear tube. |
| Select Load again without removing the filament | The load starts directly. Material data stays while the ACE inlet remains occupied. |

- Wait for each operation to finish before sending another command.
- After a restart or with an uncertain position, the whole feed can run at the slower speed.

> [!IMPORTANT]
> **Forward take-up starts disabled on new installations. Calibrate it before use.**
> It feeds filament toward U1 to remove loose loops. It has no tension sensor and does not drive the roller independently.

The tested example uses 1250 mm retraction at 80 mm/s, then 300 mm forward at 50 mm/s.
These are not universal distances. See [the calibration procedure](configuration.md).

## Remote operation

**Screen mirror.** Enable **Firmware Config → Web → Remote Screen Access**, then open `/screen/` on that printer and use Load or Unload as on the physical screen.
The installer does not enable it. See the [v24 remote-screen instructions](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/remote_screen.md).

**Web console.** For slot 1, send **one** of these commands and follow the printer prompts. For slots 2, 3, and 4, use `EXTRUDER=1`, `2`, and `3`.

Load:

```gcode
AUTO_FEEDING EXTRUDER=0 LOAD=1
```

Unload:

```gcode
AUTO_FEEDING EXTRUDER=0 UNLOAD=1
```

- Do not send Load and Unload together.
- Do not use `ACE_FEED` or `ACE_RETRACT` instead. They only move filament and skip the hotend workflow.
- The optional [AFC panel](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/afc-lite.md) needs its own AFC Stub setting. This installation does not provide it by default.
