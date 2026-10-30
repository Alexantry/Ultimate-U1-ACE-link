# Virtual-machine software installation check

This lab runs in a disposable GitHub-hosted Ubuntu virtual machine.
It never connects to a printer. All SSH and HTTP traffic for the simulated printer stays on loopback.
It does not replace physical acceptance of U1 or ACE.

The lab keeps the release installer, manifest, payload, and Windows launcher unchanged.
The Linux filesystem, SSH/SCP processes, permissions, backups, and file replacement are real.
The Moonraker responses, Klipper service, ACE identity, and material state are simulated.
PowerShell runs on Linux in this lab. Windows PowerShell 5.1 remains covered by the separate offline checks.

The expected software checks are first installation, update with preserved settings, rollback,
service-start failure recovery, and refusal when the simulated printer is busy or hot.
The workflow result records which checks actually completed.

## Run location

**Do not run this lab on a printer or a personal Linux installation.**
It creates firmware-style absolute paths inside a private mount namespace on a disposable CI VM.
The entry points require the project CI environment and a per-run permission marker.
The marker is not an authorization mechanism for operating real hardware.

Use the **VM software installation flow** workflow on the `validation/vm-software-flow` branch.
The workflow installs Linux test dependencies on its temporary runner and then removes that VM after the job.
It does not enable Windows virtualization or install a local hypervisor.

## What this cannot prove

- U1's ARM image boots or its screen update works.
- Real Klipper, MCU, and motion hardware initialize correctly.
- ACE firmware writes complete on a physical device.
- USB timing, power-loss recovery, NFC antenna/tag behavior, or spool movement is correct.
- Filament lengths or take-up tension are correct for a particular tube layout.
- A person can complete every Windows password and touchscreen prompt.

Passing this lab is reported as **VM software-flow validation**, never as full physical installation validation.
No private printer configuration, NFC key, or device log is used as a fixture.
See `FIXTURES.md` for the limited public firmware-source files used to retain the real hash checks.
