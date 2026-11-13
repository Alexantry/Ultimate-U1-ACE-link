# ACE firmware wizard

[简体中文](ace-wizard.zh-CN.md) · [Start here](quick-start.md) · [Manual firmware procedure](ace-firmware.md)

The Windows wizard prepares the ACE firmware before it installs the host integration. You type no commands.
The U1 downloads the firmware and runs the tools, so the U1 needs internet access to GitHub. OpenCubic adds the [supported NFC formats](nfc.md); you do not need NFC keys for them.

> [!IMPORTANT]
> **Use this workflow only with ACE Pro Gen 1. It does not support ACE 2 Pro.**
> **U1 must first run the supported extended firmware, with Advanced Mode and Root Access enabled.**
> **The wizard does not bypass an unsupported ACE source version.**

## Firmware files

| Purpose | Pinned upstream file | SHA-256 |
| --- | --- | --- |
| Target: OpenCubic Gen 1 CFW 1.1.1 | `ACE_V1.3.863_20260716.bin`, 113720 bytes, [release v1.0.2](https://github.com/Jupsi/OpenCubic/releases/tag/v1.0.2) | `95e0b6ddb1e77d624d127ac91d9b3e21caf58adc5e1598faf2be3feacf9b4048` |
| Stock reference | `ACE_V1.3.863_20250518.bin`, 105652 bytes, [pinned community-hosted file](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/originalFirmware/ACE_V1.3.863_20250518.bin) | `3f3676ba357749b3d0367922cb7f6b0dedc9b3d104c1c29e719ac3e563f5eb63` |

The wizard downloads these files and checks size, SHA-256, and firmware format before a write can start. The package itself contains no firmware binary.
The stock file is a reference, not a backup of your ACE. **Physical stock rollback has not been tested. The wizard does not automatically attempt it.** You can start it yourself as an untested advanced option: see [remove and restore](restore.md).

## Supported starting versions

| Detected ACE state | Wizard action |
| --- | --- |
| Gen 1, application `V1.3.856`, bootloader `V1.0.1` | Permit preparation for the exact target after all checks pass. |
| Already reports `CV1.3.863` | Do not reflash. Ask you to confirm that the intended OpenCubic build is already installed and NFC works. |
| Another source version, bootloader, generation, or an unclear identity | Stop. Do not guess, alter the probe, or force the profile. |

The string `CV1.3.863` alone cannot distinguish every community build. Do not confirm the existing-build question unless you know what was installed.

## Before you start

1. Finish printing and all filament operations. Turn off heating and drying.
2. For a first project installation, unload all four U1 heads and remove filament from all four ACE inlets. An update of an existing installation does not require empty inlets.
3. Let all printer heaters cool below 50 °C.
4. Turn off both devices before connecting hardware. Connect the verified ACE Gen 1 USB cable and the four PTFE paths. Then turn the devices on.
5. Complete [U1 preparation](u1-preparation.md) if required. Confirm Advanced Mode is on and Root Access is Open.
6. During maintenance and restart, keep ACE power and its USB cable connected, and keep hands clear of the rollers.

## Follow the prompts

1. Extract the complete project ZIP. Double-click **START-HERE.cmd** and select English or Chinese. Select the task from the table below.
2. Enter the printer's current IP address and SSH root password when requested. See [connection instructions](quick-start.md#4-enter-the-connection-information).
3. Read any saved result from an earlier ACE update before new maintenance.
4. Confirm the displayed preparation conditions. Wait while the tool downloads, verifies, and checks the device.
5. Read the displayed source version, boot version, and target. Confirm that your device is ACE Pro Gen 1.
6. Confirm one firmware update only if the displayed combination is correct. Keep power connected and wait for the verified result.

| Task | Main menu choice | After ACE completes |
| --- | --- | --- |
| Install this project on a prepared U1 | **1. U1 is ready** | Continue to the host integration steps in the same window. |
| Prepare U1 first, then install this project | **2. Prepare U1 firmware USB** | Complete the U1 screen steps, then continue through ACE and host integration. |
| Maintain ACE only, or inspect the last ACE result | **4. ACE firmware** | Complete ACE maintenance. To install host integration, reopen the wizard and select menu 1. |

Menu 3 opens the manual instructions in the selected language and exits. A started update keeps running on the U1 even if the computer's SSH connection is lost.

> [!CAUTION]
> **Do not start a second update because progress stopped appearing on the computer.**
> **Do not disconnect ACE power during an active write.**
> Reopen the wizard from **the same package version** and use menu **4** to read the last result.
> When a transaction exists, this path reads its saved result. It does not automatically repeat the write.

## What counts as success

An update must reach complete success before host installation can continue. If the correct firmware was already installed, use the confirmed-build path instead of another write.
New NFC decoding can change a brand, type, or color, such as Generic becoming Bambu. Compare the displayed changes with the installed spools before host installation.
After host installation, complete a supervised [load → unload → reload check](daily-use.md) for each slot, one slot at a time. Keep your calibrated tube settings.

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

An uncertain write is not a successful update, even if some data was sent. The tool will not automatically flash the stock image, clear the transaction, or restart printing.
If a worker stopped **before any firmware write**, menu **4** can offer a probe-only recovery. Confirm it once and wait. It does not flash firmware, and it is unavailable after a write was attempted.
Other cases can require the [manual maintenance and recovery procedure](ace-firmware.md#uncertain-results-and-recovery). Do not edit the stored records (below `/userdata/ultimate-u1-ace-link/ace-firmware/` on the printer) to bypass a refusal.
**ACE firmware success is not host integration success.** If the later host installation fails, follow [host update and rollback](update-and-rollback.md). `Automatic rollback VERIFIED` refers to host files and services. It does not mean ACE firmware was restored.
New host installation and rollback refuse to run while an unresolved firmware transaction remains. Do not run an older installer or a separate manual maintenance tool at the same time.
Do not publish device identities, credentials, NFC keys, or unredacted maintenance logs.
