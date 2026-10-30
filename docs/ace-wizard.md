# ACE firmware: follow the bilingual wizard

[简体中文](ace-wizard.zh-CN.md) · [Start here](quick-start.md) · [Manual firmware procedure](ace-firmware.md)

The Windows wizard prepares ACE firmware before the host integration.
You do not need to type commands, edit a device profile, or install Python on Windows.
The U1 runs the maintenance tools through its existing SSH access.

> [!IMPORTANT]
> **Use this workflow only with ACE Pro Gen 1. It does not support ACE 2 Pro.**
> **U1 must first run the supported extended firmware, with Advanced Mode and Root Access enabled.**
> **The wizard does not bypass an unsupported ACE source version.**

## What is included

The package contains the readable maintenance tools and bilingual prompts.
It contains **no firmware binary, NFC key, or private device profile**.
When you select firmware preparation, the tool downloads the exact images from their recorded upstream locations.
It checks their size, SHA-256, and firmware format before a write can start.
The U1 needs internet access to GitHub for this download. The computer stays connected to the same local network.

| Purpose | Pinned upstream file | SHA-256 |
| --- | --- | --- |
| Target: OpenCubic Gen 1 CFW 1.1.1 | `ACE_V1.3.863_20260716.bin`, 113720 bytes, [release v1.0.2](https://github.com/Jupsi/OpenCubic/releases/tag/v1.0.2) | `95e0b6ddb1e77d624d127ac91d9b3e21caf58adc5e1598faf2be3feacf9b4048` |
| Stock reference | `ACE_V1.3.863_20250518.bin`, 105652 bytes, [pinned community-hosted file](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/originalFirmware/ACE_V1.3.863_20250518.bin) | `3f3676ba357749b3d0367922cb7f6b0dedc9b3d104c1c29e719ac3e563f5eb63` |

The stock file is a reference, not a backup of your ACE.
**Physical stock rollback has not been tested. The wizard does not automatically attempt it.**
The source license does not license downloaded images. See [licensing](licensing.md).

## Which starting versions can the wizard update?

| Detected ACE state | Wizard action |
| --- | --- |
| Gen 1, application `V1.3.856`, bootloader `V1.0.1` | Permit preparation for the exact target after all checks pass. |
| Already reports `CV1.3.863` | Do not reflash. Ask you to confirm that the intended OpenCubic build is already installed and NFC works. |
| Another source version, bootloader, generation, or an unclear identity | Stop. Do not guess, alter the probe, or force the profile. |

The target reports runtime version `CV1.3.863`.
That string alone cannot distinguish every community build.
Do not confirm the existing-build question unless you know what was installed.
A fresh probe can also match a successful installation receipt from this wizard within the last 24 hours.
The ACE identity, reported device information, and target image hash must match.
An old success record alone does not verify the currently connected ACE.

## Before you start

1. Complete the U1 preparation path if required.
2. Connect the verified ACE Gen 1 USB cable and the four PTFE paths.
3. Finish printing and all filament operations.
4. Turn off heating and drying. Let all printer heaters cool below 50 °C.
5. Keep ACE power and its USB cable connected.
6. Keep hands clear of the rollers during firmware maintenance and restart.

The program checks idle state, heater targets, temperatures, dryer state, and serial ownership.
It does not issue load or unload commands to make a failed check pass.
Device or service initialization can still trigger ACE behavior. Keep hands clear of the rollers.
Use the normal printer controls to finish an active operation before retrying preparation.

## Follow the prompts

1. Extract the complete project ZIP.
2. Double-click **START-HERE.cmd**.
3. Select English or Chinese.
4. For a new installation, follow the ACE firmware stage when it appears.
5. To maintain ACE separately, select the ACE firmware option in the main menu.
6. Enter the printer address and SSH password when requested.
7. Read any previous-update result before starting new maintenance.
8. Confirm the displayed preparation conditions.
9. Wait while the tool downloads, verifies, and checks the device.
10. Read the detected hardware, source version, boot version, and target.
11. Confirm one firmware update only if the displayed combination is correct.
12. Keep power connected and wait for the verified result.
13. Continue with host integration when the wizard offers it.

Preparation temporarily stops Klipper to obtain exclusive ACE access.
It restores and checks printer readiness after a completed probe-only operation.
Starting a firmware update launches a separate worker for the stored transaction on U1.
That worker can continue if the computer's SSH connection is lost.

> [!CAUTION]
> **Do not start a second update because progress stopped appearing on the computer.**
> **Do not disconnect ACE power during an active write.**
> Reopen the wizard from **the same package version** and use menu **4** to read the last result.
> It reads the existing transaction instead of repeating the write.

## What counts as success?

The tool must observe the expected runtime transition and consecutive ready responses.
It must then restore Klipper and check the U1 configuration, sensors, and retained material data.
Only a complete success result permits the guided workflow to continue.

New NFC decoding can change a nonempty brand, type, or color, such as Generic becoming Bambu.
The wizard shows such changes and asks you to compare them with the installed spools before host installation.
It does not overwrite the new data with the old Generic label.
Loss of previously available material data is not treated as a successful preservation check.

These checks are not a full firmware readback or a measurement of ACE internal calibration.
They do not prove every NFC format works.
After host installation, complete one supervised [load → unload → reload check](daily-use.md).
Compare a supported tag's brand, material, and color with its spool label.
Keep your calibrated tube settings; a firmware update does not measure a new tube path.

## If preparation or updating stops

| Result | What to do |
| --- | --- |
| Download or checksum failure | Check the network. No failed image is used for a firmware write. |
| Printer hot, busy, drying, or using ACE | Finish that operation normally. Wait for the required state, then prepare again. |
| Unknown ACE version or device | Keep the existing firmware. Save the reported versions for compatibility review. |
| Existing `CV1.3.863`, but build origin is unknown | Do not confirm it as the tested build. Keep the firmware unchanged. |
| Update still running | Leave power connected. View the same transaction's result again. |
| Connection lost | Reopen the same package version and inspect the previous result. Do not repeat the write. |
| Uncertain result after updating started | Leave printer control stopped and preserve the private evidence. Follow the displayed recovery information. |

An uncertain write is not a successful update, even if some data was sent.
The tool will not automatically flash the stock image, clear the transaction, or restart printing.
If a worker stopped **before any firmware write**, menu **4** can offer a probe-only recovery.
Confirm that recovery once. Wait for it to check ACE and restore the service.
This option does not flash firmware. It is unavailable after a write was attempted.
Cases outside the validated path can require the [manual maintenance and recovery procedure](ace-firmware.md#uncertain-results-and-recovery).
Do not edit stored evidence to bypass a refusal.

Private transaction records stay on the printer.
They are stored below `/userdata/ultimate-u1-ace-link/ace-firmware/`.
New host installation and rollback refuse to run while an unresolved firmware transaction remains.
Do not run an older installer or a separate manual maintenance tool at the same time.
Do not publish device identities, credentials, NFC keys, or unredacted maintenance logs.

## Validation scope

The original firmware transfer route was physically tested on the stated source and boot versions.
The new guided orchestration is checked with simulated devices, services, downloads, and failures.
It has not received a separate end-to-end physical acceptance test.
The four production feed, unload, and NFC integration modules remain unchanged.
