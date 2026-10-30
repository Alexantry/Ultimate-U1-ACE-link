# VM fixture sources and boundaries

This directory supports a disposable GitHub-hosted Linux VM experiment. It is not a printer image.
Do not copy `guest.py`, the laboratory service, or these fixture trees onto a printer.

## Public source files

The eight files below are byte-preserved source extracts from the already verified
[paxx12 U1 v2.0.0-paxx12-24 release](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/tag/v2.0.0-paxx12-24).
The source firmware asset SHA-256 is `42dcf59e06ef0f6fab20745883322f24ddd3c1a09da07449b356dd9dab943070`.
The firmware binary itself is not included or downloaded by this laboratory.

The production manifest independently checks the firmware marker file and accepted module hashes.
The production installer independently checks both RFID service scripts and the RFID tweak.
The experiment does not relax those checks. `fixtures/manifest.json` records sizes and SHA-256 values for all eight files.

| File beneath `fixtures/root/` | SHA-256 |
| --- | --- |
| `home/lava/klipper/klippy/extras/filament_feed.py` | `174395bc9dd6cd559fe5ea00d83703560ee744ed8863e33083d1a2aa2bd53709` |
| `home/lava/klipper/klippy/extras/filament_detect.py` | `4d1a554fd33e6f474db5be2ea14e79f56ad7ecf7a4f95b8000b8e2676e2d375b` |
| `home/lava/klipper/klippy/kinematics/extruder.py` | `2085de67fb9a7d6c799a958c2a2ece639cc8f136f9dec792fa68eb2c359ce8f5` |
| `home/lava/klipper/klippy/extras/print_task_config.py` | `8298babc42526ef4a4026207927e91c52fd1ca5f1e1afe6b1f08b0dbdced82c0` |
| `etc/init.d/S59rfid-support` | `60214bc1e0188774004e32fc2a1ae860c39d7a2c89c49da8b09a119a2b94eafd` |
| `etc/init.d/S99openrfid` | `4eaf41a2c6e2c0cd72232c3f08723d3b2a3a058ae81a49d3738bdcb2b689f512` |
| `usr/local/bin/extended-config.py` | `65f7f122b7a669eb4ae66591dc6159ed4547ba16ff4a4d302849b039cab3e3df` |
| `usr/local/share/firmware-config/tweaks/klipper/disable-rfid-reader.cfg` | `80387430b72f73bcc459d6d5e895c2ab2c4bde58dcaf8967f871551a8dd585d3` |

The Klipper source belongs to Snapmaker and the upstream Klipper contributors and uses GPLv3.
The stock `extruder.py` is also identified by the previously audited upstream blob `6978d8a1b33c4b767e0f0cd783a2b50b6ed115dd`.
The four paxx12 shell/Python/config files retain their original `GPL-3.0-or-later` headers and copyright notices.
See the repository [license](../LICENSE), [third-party notices](../THIRD_PARTY.md), and
[recorded source provenance](../SOURCES.json). The recorded Snapmaker source commit establishes
license provenance; it is not a claim that every extracted file equals that commit.

No private printer configuration, NFC key, device identity, raw printer log, or firmware binary is copied.
The `openrfid_user.cfg` path in the guest is created from a fixed synthetic text canary with no key.

## What is actual

- The published installer, production manifest, and production payload remain unmodified.
- SSH and SCP use real operating-system processes and transfer real files.
- The Linux guest uses real ownership, modes, file locks, atomic replacement, fsync, backup, and rollback.
- `/home/lava/printer_data` is an actual bind mount of `/oem/printer_data`.
- The original S59/S99 RFID services and `extended-config.py` execute as shipped.
- The synthetic serial target is a real PTY character device, discovered through a deliberately synthetic USB identity tree.

## What is simulated

- The HTTP responder is a limited Moonraker substitute on guest loopback port 80.
- `S60klipper` is a laboratory service wrapper. It does not start Klipper, MCU firmware, motors, heaters, or a printer daemon.
- Material values, cold/idle state, head sensors, and ACE status are synthetic.
- Configuration, module hashes, and the version string are captured only at a successful simulated service start.
  HTTP responses keep that captured view until the next successful start. Writing files alone does not update it.
  `load_generation` and `service_actions` let the driver verify the restart boundary.
  The version is parsed from source; the modules are not executed. This does not prove that real Klipper loaded them.
- The USB VID/PID and serial identity are synthetic. The PTY is not an ACE emulator and never returns NFC or flash results.
- The tested host flow selects the known-target/KEEP branch. It does not prove ACE firmware preparation or flashing.
- Any unexpected bytes written to the synthetic serial endpoint cause the final assertions to fail.

This experiment cannot establish ARM firmware boot, real MCU initialization, physical USB timing,
NFC tag recognition, actual travel, spool tension, or successful firmware flashing.

## Guest API and isolation gates

All guest commands must run in the same private mount namespace on a disposable GitHub Actions VM.
The program rejects non-Linux/non-root contexts, missing `CI=true` or `GITHUB_ACTIONS=true`, a different
repository, missing run identity, or the host's initial mount namespace.

The driver must first create `/run/ultimate-u1-ace-link-vm-lab/permission.json` as a root-owned regular
file with mode 0600. It must contain exactly `schema: 1`, `scope: "vm-software-flow"`, the string
`run_id` from `GITHUB_RUN_ID`, and a 32-character lowercase hexadecimal `token` matching
`U1_ACE_LAB_TOKEN`. Setup does not create or repair this authorization marker.
The SSH service must pass these laboratory environment values to its child sessions.

| Command | Purpose |
| --- | --- |
| `guest.py setup` | Initialize once, verify fixture hashes, and install the isolated filesystem. |
| `guest.py serve --ready-file /run/ultimate-u1-ace-link-vm-lab/ready.json` | Keep HTTP and the PTY alive. |
| `guest.py snapshot` | Read laboratory state, file identities, service actions, load generation, and the last simulated loaded view. |
| `guest.py set-state idle` | Return synthetic status to idle and capture an unchanged-files checkpoint. |
| `guest.py set-state busy` / `hot` | Inject a rejected printer state and capture a checkpoint. |
| `guest.py set-state service-failure` | Fail the next service start once; later rollback starts may recover. |
| `guest.py assert installed` | Verify actual installed hashes, External mode, RFID symlink, and canary preservation. |
| `guest.py assert baseline` / `rolled-back` | Require original bytes, modes, ownership, links, and absent files to be restored. |
| `guest.py assert guarded` | Require checkpoint files and service-action count to remain unchanged. |
| `guest.py assert unchanged` | Require checkpoint files unchanged while permitting recovery service actions. |
| `guest.py assert service-recovered` | Require the one-shot failure to be consumed and service state restored. |

The namespace uses a private bind mount over `/sys/dev/char` for the synthetic identity lookup.
It does not pass through USB devices or enumerate a physical ACE. The HTTP service accepts no
POST operations and does not implement G-code or firmware commands.
