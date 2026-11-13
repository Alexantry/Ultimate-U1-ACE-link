# ACE Gen1 firmware: advanced manual procedure

**[Use the bilingual ACE firmware wizard](ace-wizard.md) · [中文向导说明](ace-wizard.zh-CN.md)**

Most users do not need this page. The wizard, or the [manual installation ACE firmware step](installation.md#ace-firmware) ([中文手动安装](installation.zh-CN.md#ace-firmware)), updates the ACE without profile editing.
This page is an **advanced alternative** with private profiles and low-level commands.

- Do not run it during a wizard or controlled-backend transaction. Do not mix the two transaction methods.
- **Skip flashing when the intended OpenCubic Gen1 build already runs and NFC works.** A reported version alone does not identify every community build.
- Only **ACE Pro Gen1 with the USB JSON protocol** is covered. ACE 2 Pro uses a different protocol.

The target is unmodified **OpenCubic Gen1 CFW 1.1.1**, distributed in release `v1.0.2`. The only physically tested upgrade route is:

| Source application | Source bootloader | Target |
| --- | --- | --- |
| `V1.3.856` | `V1.0.1` | Exact OpenCubic Gen1 CFW 1.1.1 image reporting `CV1.3.863` |

Other source or boot combinations are not validated by this project. Do not change probe values or invent a compatibility review.

## Images

| Purpose | Upstream file | SHA-256 |
| --- | --- | --- |
| Multi-brand NFC | [OpenCubic v1.0.2 release](https://github.com/Jupsi/OpenCubic/releases/tag/v1.0.2), `ACE_V1.3.863_20260716.bin`, 113720 bytes, reports `CV1.3.863` | `95e0b6ddb1e77d624d127ac91d9b3e21caf58adc5e1598faf2be3feacf9b4048` |
| Stock rollback reference | [Community-hosted original](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/originalFirmware/ACE_V1.3.863_20250518.bin), 105652 bytes, reports `V1.3.863` | `3f3676ba357749b3d0367922cb7f6b0dedc9b3d104c1c29e719ac3e563f5eb63` |

No image is included or covered by this repository's GPL license; see [THIRD_PARTY.md](../THIRD_PARTY.md).
The stock reference is not your device backup. Its hash is not a vendor signature or a recovery guarantee. **A physical rollback has not been tested.**

## Connect to the supported U1

First complete the upload steps in [Installation](installation.md#4-transfer-the-project). Keep that PowerShell session open.

1. Open an interactive SSH shell in the uploaded directory.
```powershell
ssh -t $PrinterTarget "cd '$RemoteDir' && exec sh"
```
2. Confirm root privileges. The result must be `0`.
```sh
id -u
```
3. Confirm the project directory. Continue only when `PACKAGE_OK` appears.
```sh
pwd
test -f tools/ace_usb/ace_iap.py && echo PACKAGE_OK
```
4. Verify Python (3.9 or newer) and pyserial. Both versions must print without an exception.
```sh
python3 -c 'import sys, serial; assert sys.version_info >= (3, 9); print(sys.version); print(serial.__version__)'
```

If this check fails, stop and repair the prerequisite environment. Do not continue with an untested Python executable.
All remaining commands run on the U1 inside this SSH session, from the repository root.

## Offline preparation

1. Download the pinned community image, then the pinned stock reference.
```sh
python3 tools/ace_usb/fetch_firmware.py opencubic-gen1
```
```sh
python3 tools/ace_usb/fetch_firmware.py stock-gen1-863
```
2. Inspect the community image, then the stock reference. This establishes file identity and format, not device compatibility.
```sh
python3 tools/ace_usb/ace_iap.py inspect --image-id opencubic-gen1
```
```sh
python3 tools/ace_usb/ace_iap.py inspect --image-id stock-gen1-863
```
3. Check the locked plan. The shipped profile reports `write_enabled: false`.
```sh
python3 tools/ace_usb/ace_iap.py plan --image-id opencubic-gen1
```

## Before any live probe

The tools do not move filament, scan NFC, or stop drying. Check these conditions yourself.

1. Printing has finished, and the U1 and ACE are idle. ACE drying is stopped.
2. Every heater target is zero, and every current heater temperature is below 50 degrees Celsius.
3. ACE power and its USB connection are stable.
4. List stable serial-device names.
```sh
ls -l /dev/serial/by-id/
```
5. Assign the intended ACE path. Replace the final component with your own listed ACE device name.
```sh
ACE_DEVICE='/dev/serial/by-id/REPLACE_WITH_YOUR_ACE_DEVICE_NAME'
```

Do not select the U1 MCU or another serial device. Do not identify a device only by its numbered `ttyACM` name. Do not reuse another person's device identity.

6. Confirm that the selected path exists.
```sh
ls -l "$ACE_DEVICE"
```
7. Stop Klipper.
```sh
/etc/init.d/S60klipper stop
```
8. Check exclusive serial ownership. `PORT_FREE` means no other process owns the device.
```sh
python3 -c 'import sys; sys.path.insert(0, "tools/ace_usb"); from ace_iap import require_unused_device; require_unused_device(sys.argv[1]); print("PORT_FREE")' "$ACE_DEVICE"
```

An occupied-port error lists the owning process IDs. Stop the identified ACE diagnostic program, then repeat this check. Do not kill an unidentified process.
`ACE_DISABLE_FEED_ASSIST` is not a pure stop command. The inherited helper can also retract 5 mm at speed 10.

## Read-only device probe

Probe records contain device identity and state. Keep them private and outside the repository.

1. Restrict permissions for new files, then create a private evidence directory.
```sh
umask 077
```
```sh
ACE_EVIDENCE=$(mktemp -d /tmp/ace-review.XXXXXX)
```
2. Run one read-only probe. It does not enter IAP.
```sh
python3 tools/ace_usb/ace_iap.py probe \
  --device "$ACE_DEVICE" \
  --output "$ACE_EVIDENCE/probe.json" \
  --log "$ACE_EVIDENCE/probe.jsonl"
```
3. Display the private probe record.
```sh
python3 -m json.tool "$ACE_EVIDENCE/probe.json"
```
4. Review the exact model, slot count, ready state, stopped dryer, and physical USB identity. Match the application and boot versions against the tested route above.

Stop if the source or boot combination is unreviewed. ACE responses cannot establish the U1 heater conditions.

## Exit after probing only

Use this branch when your source version is unsupported or you choose not to flash. For the supported upgrade, skip to the next section.
Use it only if you ran `probe` and **never ran `flash` or another IAP command**. An uncertain update must follow [Uncertain results and recovery](#uncertain-results-and-recovery) instead.

1. Capture a fresh read-only status.
```sh
python3 tools/ace_usb/ace_iap.py probe \
  --device "$ACE_DEVICE" \
  --output "$ACE_EVIDENCE/resume-probe.json" \
  --log "$ACE_EVIDENCE/resume-probe.jsonl"
```
2. Verify the idle result. Continue only when `READ_ONLY_READY` appears. An exception means you must inspect the state before restoring control.
```sh
python3 -c 'import json, sys; sys.path.insert(0, "tools/ace_usb"); from ace_iap import ready_state; data=json.load(open(sys.argv[1])); status=data["snapshot"]["status"]; assert ready_state(status); assert all(slot.get("status") in ("ready", "empty") for slot in status["slots"]); print("READ_ONLY_READY")' "$ACE_EVIDENCE/resume-probe.json"
```
3. Start Klipper. Confirm that it becomes ready in the printer interface.
```sh
/etc/init.d/S60klipper start
```

Stop this firmware workflow here. Do not continue into profile generation after restarting Klipper.

## Per-device write profile

The draft generator accepts only the tested upgrade route above. It leaves every authorization field disabled.

1. Create a locked draft from the probe. Success reports `write_enabled: false` and `all_checks_false: true`.
```sh
python3 tools/ace_usb/prepare_profile.py \
  --probe "$ACE_EVIDENCE/probe.json" \
  --output "$ACE_EVIDENCE/profile.draft.json"
```
2. Copy the draft for manual review.
```sh
cp "$ACE_EVIDENCE/profile.draft.json" "$ACE_EVIDENCE/reviewed-profile.json"
```
3. Calculate the probe digest, then compare it with `probe_sha256` in the draft.
```sh
sha256sum "$ACE_EVIDENCE/probe.json"
```
```sh
python3 -m json.tool "$ACE_EVIDENCE/profile.draft.json"
```
4. Generate a UTC review timestamp.
```sh
date -u '+%Y-%m-%dT%H:%M:%S+00:00'
```
5. Open the review copy in the editor. Press `i` to enter editing mode.
```sh
vi "$ACE_EVIDENCE/reviewed-profile.json"
```
6. In `"reviewed_at_utc": null`, replace only `null` with the generated timestamp as a JSON string. Keep the comma when another field follows.
7. Set each completed check in the table below to `true` (lowercase, without quotes).
8. Set `write_enabled` to `true` only after every check is complete.
9. Keep the automatically copied identity fields unchanged. Do not replace them with example values.
10. Press Escape, type `:wq`, and press Enter to save.

| Check | Meaning before setting true |
| --- | --- |
| `idle_state_verified` | U1 and ACE have no print or filament operation |
| `heaters_and_dryer_off_verified` | Heater targets are zero, current temperatures are below 50 degrees Celsius, and drying is stopped |
| `klipper_stopped_and_port_released` | Klipper is stopped and the ownership check printed `PORT_FREE` |
| `source_version_reviewed` | The probe exactly matches the tested source application and bootloader |
| `rollback_path_reviewed` | Both images passed inspection, and you understand that physical stock rollback remains untested |

11. Check JSON syntax. No output and exit status zero indicate valid JSON. This does not approve the maintenance conditions.
```sh
python3 -m json.tool "$ACE_EVIDENCE/reviewed-profile.json" >/dev/null
```
12. Display the local plan.
```sh
python3 tools/ace_usb/ace_iap.py plan \
  --profile "$ACE_EVIDENCE/reviewed-profile.json"
```

If more than 30 minutes pass, create a new evidence directory and repeat the probe. Never reuse stale evidence or edit its timestamp.
Never commit the profile, probe, audit, or result files.

## One transfer attempt

Run this command only with the reviewed local profile:
```sh
python3 tools/ace_usb/ace_iap.py flash \
  --image-id opencubic-gen1 \
  --profile "$ACE_EVIDENCE/reviewed-profile.json" \
  --probe "$ACE_EVIDENCE/probe.json" \
  --device "$ACE_DEVICE" \
  --log "$ACE_EVIDENCE/flash.jsonl" \
  --result "$ACE_EVIDENCE/result.json"
```

The tool sends the transfer once. It does not replay uncertain writes or restart printer services automatically.
`VERSION_CHANGED_AND_READY` confirms an observed runtime transition. It does not verify flash readback, NFC, or filament movement.

1. Confirm the successful result. Continue only when `UPDATE_VERIFIED` appears.
```sh
python3 -c 'import json, sys; result=json.load(open(sys.argv[1])); assert result.get("outcome")=="VERSION_CHANGED_AND_READY"; print("UPDATE_VERIFIED")' "$ACE_EVIDENCE/result.json"
```
2. Start Klipper. Confirm that it becomes ready in the printer interface.
```sh
/etc/init.d/S60klipper start
```
3. Perform the documented supervised functional checks. Resume printing only after those checks pass.

## Uncertain results and recovery

- Keep the evidence private and leave printer control stopped. Inspect the actual state before choosing a recovery action.
- Do not blindly rerun the command. Do not power-cycle during an active write.
- This updater requires the normal application state. It cannot generally rescue a device stuck in its bootloader.
- Stock rollback has not been physically tested. The steps on this page do not use it.
- The guided backend has a separate, explicitly untested route from `CV1.3.863` / boot `V1.0.1` to the stock image. It needs the extra flag `--accept-untested-stock-route`. See [remove and restore](restore.md).
- The low-level updater accepts `--image-id stock-gen1-863` only with a matching reviewed profile.
- Do not bypass that boundary by changing source versions or copying another device's profile.

## Offline tests

```sh
python3 -m unittest discover -s tools/ace_usb -p 'test_*.py'
```

The tests need no printer connection or private device profile. For NFC support, see [the support table](nfc.md).
