# ACE firmware: follow the bilingual wizard

[简体中文](ace-wizard.zh-CN.md) · [Start here](quick-start.md) · [Manual firmware procedure](ace-firmware.md)

The Windows wizard prepares ACE firmware before the host integration.
You do not need to type commands, edit a device profile, or install Python on Windows.
The U1 runs the maintenance tools through its existing SSH access.
OpenCubic adds the [supported NFC formats](nfc.md) to ACE.
For those formats, you do not need to find or enter NFC keys.

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

1. Finish printing and all filament operations.
2. For a first project installation, unload all four U1 heads. Remove filament from all four ACE inlets.
3. Turn off heating and drying. Let all printer heaters cool below 50 °C after unloading.
4. Turn off both devices before connecting hardware. Connect the verified ACE Gen 1 USB cable and the four PTFE paths. Then turn the devices on.
5. Complete [U1 preparation](u1-preparation.md) if required. Confirm Advanced Mode is on and Root Access is Open.
6. Keep ACE power and its USB cable connected during maintenance.
7. Keep hands clear of the rollers during firmware maintenance and restart.

An update of an existing project installation does not require empty inlets.
It still requires idle, cold equipment, with heating and drying off.

The program checks idle state, heater targets, temperatures, dryer state, and serial ownership.
It does not issue load or unload commands to make a failed check pass.
Device or service initialization can still trigger ACE behavior. Keep hands clear of the rollers.
Use the normal printer controls to finish an active operation before retrying preparation.

## Follow the prompts

1. Extract the complete project ZIP.
2. Double-click **START-HERE.cmd**. Select English or Chinese.
3. Select the task from the table below.
4. Enter the printer's current IP address and SSH root password when requested. See [connection instructions](quick-start.md#4-enter-the-connection-information).
5. Read any saved result from an earlier ACE update before new maintenance.
6. Confirm the displayed preparation conditions.
7. Wait while the tool downloads, verifies, and checks the device.
8. Read the displayed source version, boot version, and target. Confirm that your device is ACE Pro Gen 1.
9. Confirm one firmware update only if the displayed combination is correct.
10. Keep power connected and wait for the verified result.

| Task | Main menu choice | After ACE completes |
| --- | --- | --- |
| Install this project on a prepared U1 | **1. U1 is ready** | Continue to the host integration steps in the same window. |
| Prepare U1 first, then install this project | **2. Prepare U1 firmware USB** | Complete the U1 screen steps, then continue through ACE and host integration. |
| Maintain ACE only, or inspect the last ACE result | **4. ACE firmware** | Complete ACE maintenance. To install host integration, reopen the wizard and select menu 1. |

You do not need to complete a separate manual ACE installation before menu 1 or 2.
Menu 3 opens the manual instructions in the selected language and exits.

Preparation temporarily stops Klipper to obtain exclusive ACE access.
It restores and checks printer readiness after a completed probe-only operation.
Starting a firmware update launches a separate worker for the stored transaction on U1.
That worker can continue if the computer's SSH connection is lost.

> [!CAUTION]
> **Do not start a second update because progress stopped appearing on the computer.**
> **Do not disconnect ACE power during an active write.**
> Reopen the wizard from **the same package version** and use menu **4** to read the last result.
> When a transaction exists, this path reads its saved result. It does not automatically repeat the write.

## What counts as success?

After a firmware write, the tool must observe the expected runtime transition and consecutive ready responses.
It must then restore Klipper and check the U1 configuration, sensors, and retained material data.
An update must reach complete success before host installation can continue.
If the correct firmware was already installed, use the confirmed-build path instead of another write.

New NFC decoding can change a nonempty brand, type, or color, such as Generic becoming Bambu.
The wizard shows such changes and asks you to compare them with the installed spools before host installation.
It does not overwrite the new data with the old Generic label.
Loss of previously available material data is not treated as a successful preservation check.

These checks are not a full firmware readback or a measurement of ACE internal calibration.
They do not prove every NFC format works.
After host installation, complete a supervised [load → unload → reload check](daily-use.md) for each slot, one slot at a time.
Compare a supported tag's brand, material, and color with its spool label.
Keep your calibrated tube settings; a firmware update does not measure a new tube path.
For a first installation, review initial distances before installation and verify them with these four-slot tests.

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

**ACE firmware success is not host integration success.**
If the later host installation fails, follow [host update and rollback](update-and-rollback.md).
`Automatic rollback VERIFIED` refers to host files and services. It does not mean ACE firmware was restored.

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
