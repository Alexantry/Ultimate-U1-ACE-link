# ACE Gen1 firmware: guided or manual preparation

**[Use the bilingual ACE firmware wizard](ace-wizard.md) · [中文向导说明](ace-wizard.zh-CN.md)**

The Windows wizard now handles downloads, checks, private profiles, and the supported update transaction.
First-time users can follow its prompts before host integration. No shell commands or profile editing are required.
The standalone `installer.py` still installs host integration only; ACE maintenance uses a separate controlled backend.

## Manual alternative

The detailed command procedure below remains available for source review and manual maintenance.
Do not run this manual procedure at the same time as a guided update.

**Skip flashing when the intended OpenCubic Gen1 build already runs and NFC works.** A reported version alone does not identify every community build.

The supported reference is unmodified **OpenCubic Gen1 CFW 1.1.1**, distributed in release `v1.0.2`. It does not contain the separate UID or tunnel experiments.

Only **ACE Pro Gen1 with the USB JSON protocol** is covered. ACE 2 Pro uses a different protocol.

The only physically tested upgrade route is:

| Source application | Source bootloader | Target |
| --- | --- | --- |
| `V1.3.856` | `V1.0.1` | Exact OpenCubic Gen1 CFW 1.1.1 image reporting `CV1.3.863` |

Other source or boot combinations are not validated by this project. Do not change probe values or invent a compatibility review.

The stock rollback image has been prepared and checked offline. **A physical rollback has not been tested.**

## Images and licenses

| Purpose | Upstream file | SHA-256 |
| --- | --- | --- |
| Multi-brand NFC | [OpenCubic v1.0.2 release](https://github.com/Jupsi/OpenCubic/releases/tag/v1.0.2), `ACE_V1.3.863_20260716.bin`, 113720 bytes, reports `CV1.3.863` | `95e0b6ddb1e77d624d127ac91d9b3e21caf58adc5e1598faf2be3feacf9b4048` |
| Stock rollback reference | [Community-hosted original](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/originalFirmware/ACE_V1.3.863_20250518.bin), 105652 bytes, reports `V1.3.863` | `3f3676ba357749b3d0367922cb7f6b0dedc9b3d104c1c29e719ac3e563f5eb63` |

No image is included or covered by this repository's GPL license. OpenCubic keeps its firmware source private.

The stock reference is not your device backup. Its hash is not a vendor signature or a recovery guarantee.

See [THIRD_PARTY.md](../THIRD_PARTY.md).

## Connect to the supported U1

First complete the upload steps in [Installation](installation.md#4-transfer-the-project). Keep that PowerShell session open.

1. Open an interactive SSH shell in the uploaded directory.

   ```powershell
   ssh -t $PrinterTarget "cd '$RemoteDir' && exec sh"
   ```

2. Confirm root privileges.

   ```sh
   id -u
   ```

   The result must be `0`.

3. Confirm the project directory.

   ```sh
   pwd
   test -f tools/ace_usb/ace_iap.py && echo PACKAGE_OK
   ```

   Continue only when `PACKAGE_OK` appears.

4. Verify Python and pyserial.

   ```sh
   python3 -c 'import sys, serial; assert sys.version_info >= (3, 9); print(sys.version); print(serial.__version__)'
   ```

   Both versions must print without an exception. The supported firmware should already provide pyserial.

   If this check fails, stop and repair the prerequisite environment. Do not continue with an untested Python executable.

All remaining shell commands run on the U1 inside this SSH session. No additional Windows Python installation is needed.

The tools do not open another SSH connection.

## Offline preparation

The tools require Python 3.9 or newer. Live serial commands also require an existing pyserial installation.

The following commands start in the repository root. Only the fetch command downloads files. Tests, `inspect`, and `plan` do not open serial ports.

1. Download the pinned community image.

   ```sh
   python3 tools/ace_usb/fetch_firmware.py opencubic-gen1
   ```

2. Download the pinned stock reference.

   ```sh
   python3 tools/ace_usb/fetch_firmware.py stock-gen1-863
   ```

3. Inspect the community image.

   ```sh
   python3 tools/ace_usb/ace_iap.py inspect --image-id opencubic-gen1
   ```

4. Inspect the stock reference.

   ```sh
   python3 tools/ace_usb/ace_iap.py inspect --image-id stock-gen1-863
   ```

5. Check the locked plan.

   ```sh
   python3 tools/ace_usb/ace_iap.py plan --image-id opencubic-gen1
   ```

The fetch helper checks the fixed URL, size, and SHA-256. It refuses to overwrite an invalid existing file.

`inspect` also validates CRC, vector table, generation, and size limits. These checks establish file identity and format, not device compatibility.

The shipped profile reports `write_enabled: false`.

## Before any live probe

The tools do not move filament, scan NFC, or stop drying. These maintenance conditions must already be satisfied.

1. Wait until printing has finished.
2. Verify that the U1 and ACE are idle.
3. Verify that every heater target is zero.
4. Verify that every current heater temperature is below 50 degrees Celsius.
5. Verify that ACE drying is stopped.
6. List stable serial-device names.

   ```sh
   ls -l /dev/serial/by-id/
   ```

7. Assign the intended ACE path.

   ```sh
   ACE_DEVICE='/dev/serial/by-id/REPLACE_WITH_YOUR_ACE_DEVICE_NAME'
   ```

   Replace the final component with your own listed ACE device name. Do not select the U1 MCU or another serial device.

8. Confirm that the selected path exists.

   ```sh
   ls -l "$ACE_DEVICE"
   ```

9. Stop Klipper.

   ```sh
   /etc/init.d/S60klipper stop
   ```

10. Check exclusive serial ownership.

   ```sh
   python3 -c 'import sys; sys.path.insert(0, "tools/ace_usb"); from ace_iap import require_unused_device; require_unused_device(sys.argv[1]); print("PORT_FREE")' "$ACE_DEVICE"
   ```

   `PORT_FREE` means no other process currently owns the selected character device. This check does not open the serial port.

   An occupied-port error lists the owning process IDs. Stop the identified ACE diagnostic program, then repeat this check.

   Do not kill an unidentified process. The live tool repeats this ownership check when opening serial.

11. Verify that ACE power and its USB connection are stable.

Do not identify a device only by its numbered `ttyACM` name. Do not reuse another person's device identity.

`ACE_DISABLE_FEED_ASSIST` is not a pure stop command. The inherited helper can also retract 5 mm at speed 10.

## Read-only device probe

Probe records contain device identity and state. Store them outside the repository with private permissions.

1. Restrict permissions for new evidence files.

   ```sh
   umask 077
   ```

2. Create a private evidence directory.

   ```sh
   ACE_EVIDENCE=$(mktemp -d /tmp/ace-review.XXXXXX)
   ```

3. Run one read-only probe.

   ```sh
   python3 tools/ace_usb/ace_iap.py probe \
     --device "$ACE_DEVICE" \
     --output "$ACE_EVIDENCE/probe.json" \
     --log "$ACE_EVIDENCE/probe.jsonl"
   ```

4. Display the private probe record.

   ```sh
   python3 -m json.tool "$ACE_EVIDENCE/probe.json"
   ```

5. Review the exact model and slot count.
6. Match the application and boot versions against the tested route above.
7. Review the ready state and stopped dryer.
8. Review the physical USB identity.

`probe` requests only `get_info`, `iap_version`, and `get_status`. It does not enter IAP.

Stop if the source or boot combination is unreviewed. ACE responses cannot establish the U1 heater conditions.

## Exit after probing only

Use this branch only if you ran `probe` and **never ran `flash` or another IAP command**. It restores normal operation without a firmware change.

Use it when your source version is unsupported or you choose not to flash. An uncertain update must follow the failure section instead.

For the supported upgrade, skip this section and continue to profile generation.

1. Capture a fresh read-only status.

   ```sh
   python3 tools/ace_usb/ace_iap.py probe \
     --device "$ACE_DEVICE" \
     --output "$ACE_EVIDENCE/resume-probe.json" \
     --log "$ACE_EVIDENCE/resume-probe.jsonl"
   ```

2. Verify the idle result.

   ```sh
   python3 -c 'import json, sys; sys.path.insert(0, "tools/ace_usb"); from ace_iap import ready_state; data=json.load(open(sys.argv[1])); status=data["snapshot"]["status"]; assert ready_state(status); assert all(slot.get("status") in ("ready", "empty") for slot in status["slots"]); print("READ_ONLY_READY")' "$ACE_EVIDENCE/resume-probe.json"
   ```

   Continue only when `READ_ONLY_READY` appears. An exception means you must inspect the state before restoring control.

3. Start Klipper.

   ```sh
   /etc/init.d/S60klipper start
   ```

4. Confirm that Klipper becomes ready in the printer interface.

Stop this firmware workflow here. Do not continue into profile generation after restarting Klipper.

## Per-device write profile

The shipped template cannot authorize a write. The draft generator copies identity fields from the fresh probe and leaves every authorization field disabled.

It accepts only the physically tested upgrade route above. It performs no network, serial, or service operations.

1. Create a locked draft from the probe.

   ```sh
   python3 tools/ace_usb/prepare_profile.py \
     --probe "$ACE_EVIDENCE/probe.json" \
     --output "$ACE_EVIDENCE/profile.draft.json"
   ```

   Success reports `write_enabled: false` and `all_checks_false: true`.

2. Copy the draft for manual review.

   ```sh
   cp "$ACE_EVIDENCE/profile.draft.json" "$ACE_EVIDENCE/reviewed-profile.json"
   ```

3. Calculate the probe digest.

   ```sh
   sha256sum "$ACE_EVIDENCE/probe.json"
   ```

4. Compare that digest with `probe_sha256` in the draft.

   ```sh
   python3 -m json.tool "$ACE_EVIDENCE/profile.draft.json"
   ```

5. Generate a UTC review timestamp.

   ```sh
   date -u '+%Y-%m-%dT%H:%M:%S+00:00'
   ```

6. Open the review copy in the editor.

   ```sh
   vi "$ACE_EVIDENCE/reviewed-profile.json"
   ```

7. Press `i` to enter editing mode.
8. Replace `reviewed_at_utc: null` with the generated timestamp as a JSON string.
9. Set each completed check to `true` using the table below.
10. Set `write_enabled` to `true` only after every check is complete.
11. Press Escape to leave editing mode.
12. Type `:wq` and press Enter to save.

The actual JSON field includes quotes: `"reviewed_at_utc": null`. Replace only `null`, keeping a comma when another field follows.

Keep the automatically copied identity fields unchanged. JSON booleans are lowercase `true` and `false`, without quotes.

| Check | Meaning before setting true |
| --- | --- |
| `idle_state_verified` | U1 and ACE have no print or filament operation |
| `heaters_and_dryer_off_verified` | Heater targets are zero, current temperatures are below 50 degrees Celsius, and drying is stopped |
| `klipper_stopped_and_port_released` | Klipper is stopped and the ownership check printed `PORT_FREE` |
| `source_version_reviewed` | The probe exactly matches the tested source application and bootloader |
| `rollback_path_reviewed` | Both images passed inspection, and you understand that physical stock rollback remains untested |

The draft already contains the serial path, device identity, USB identity, probe digest, and pinned image digest. Do not replace them with example values.

13. Check JSON syntax.

   ```sh
   python3 -m json.tool "$ACE_EVIDENCE/reviewed-profile.json" >/dev/null
   ```

   No output and exit status zero indicate valid JSON. This does not approve the maintenance conditions.

14. Display the local plan.

   ```sh
   python3 tools/ace_usb/ace_iap.py plan \
     --profile "$ACE_EVIDENCE/reviewed-profile.json"
   ```

The plan remains offline. The flash command performs full identity and freshness validation before opening serial.

If more than 30 minutes pass, create a new evidence directory and repeat the probe. Never reuse stale evidence or edit its timestamp.

Never commit the profile, probe, audit, or result files. The downloaded binaries also remain outside version control.

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

The tool rejects stale profiles, mismatched identities, altered files, and non-ready devices. It also rejects redundant updates to the same reported version.

It sends the transfer once and validates IAP replies. It then requires the expected version and consecutive ready observations.

It does not replay uncertain writes or restart printer services automatically.

`VERSION_CHANGED_AND_READY` confirms an observed runtime transition. It does not verify flash readback, NFC, or filament movement.

After successful verification:

1. Confirm the successful result.

   ```sh
   python3 -c 'import json, sys; result=json.load(open(sys.argv[1])); assert result.get("outcome")=="VERSION_CHANGED_AND_READY"; print("UPDATE_VERIFIED")' "$ACE_EVIDENCE/result.json"
   ```

   Continue only when `UPDATE_VERIFIED` appears.

2. Start Klipper.

   ```sh
   /etc/init.d/S60klipper start
   ```

3. Confirm that Klipper becomes ready in the printer interface.
4. Perform the documented supervised functional checks.
5. Resume printing only after those checks pass.

## Uncertain results and recovery

On failure, keep the evidence private and leave printer control stopped. Inspect the actual state before choosing a recovery action.

Do not blindly rerun the command. Do not power-cycle during an active write.

This updater requires the normal application state. It cannot generally rescue a device stuck in its bootloader.

Stock rollback is prepared, but it has not been physically tested. This guide does not authorize an untested rollback route.

The general updater accepts `--image-id stock-gen1-863` only with a matching reviewed profile. The public draft generator deliberately does not create that profile.

Do not bypass that boundary by changing source versions or copying another device's profile.

## Offline tests

```sh
python3 -m unittest discover -s tools/ace_usb -p 'test_*.py'
```

The original 84 protocol/IAP tests use fake transports and synthetic images. Five downloader tests use mocked network responses.

Seven additional tests check locked draft generation, freshness, source compatibility, and refusal to overwrite evidence.

Tests need no binary download, pyserial installation, printer connection, or private device profile.

## NFC recognition

The ACE firmware decodes supported tags and returns metadata.
For tags supported by the pinned OpenCubic firmware, users do not need to find or enter NFC keys.
Use manual material details for unsupported or unrecognized tags. See [the support table](nfc.md).

External mode disables the U1's internal readers. It does not restrict the ACE firmware's supported tag formats.
