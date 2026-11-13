# Changes

## Unreleased — runout continuation (`port8-runout-continue`)

This revision changes what happens when a spool becomes empty during a print.
It has offline checks only. It has not received a physical test.

Cause of the fault: when the end of the filament left the ACE, the ACE refused
to start feed assist at the next tool change (`empty`). The host treated this as
an error and paused the print, although filament remained in the tube.

- Continue the print when an ACE slot is empty. Feed assist is skipped for that slot.
- Let the U1 head sensor pause the print when the filament end reaches the head.
- At the discard position, push out the filament that remains below the head sensor
  (`runout_flush_length`, default 50 mm; `runout_flush_speed`, default 150 mm/min).
- Set all nozzle heaters to off while the printer waits (`runout_heaters_off`, default 1).
  The bed temperature does not change.
- Load and resume automatically when the same ACE slot receives new filament
  (`runout_auto_resume`, default 1). The host waits `runout_resume_settle` seconds
  (default 8) and until the ACE is ready, so that the ACE can grip the filament and read its tag.
- Keep the print paused when the new tag reports a different material type.
- Keep the material data of a slot during a print while its filament end still feeds the head.

Installer: read configuration links that the firmware adds for its own options, such as
the AFC stub (`extended/klipper/afc.cfg`). The link must point into
`/usr/local/share/firmware-config`. The installer does not write these files.
Before this change, the installer stopped with `Unexpected symlink` on such printers.

Remove and restore (new; see `docs/restore.md`):

- `installer.py remove-check` and `remove` return the U1 to the files shipped in the extended firmware.
  The originals come from the read-only firmware layer and must match reviewed hashes.
  Removal makes a backup first and restores the previous state if it fails.
- The ACE backend has a second route, `--route stock`, from the pinned OpenCubic build to vendor `V1.3.863`.
  It needs the extra flag `--accept-untested-stock-route`. This write has never been done on a device.
- The wizard has menu 5, Restore: remove this project, return the ACE to vendor firmware,
  or prepare a USB drive with official Snapmaker `V2.0.0`.

Optional settings go in the `[ace]` section of `ace.cfg`. All have defaults.


## 0.1.6 — 2026-10-30

This revision checks the full beginner workflow in both languages.
The four production transport and NFC modules remain unchanged.

- Put idle, cooling, and hardware checks before firmware maintenance.
- Separate tasks required before opening the wizard from tasks the wizard prepares.
- Provide complete English and Chinese manual installation and recovery instructions.
- Open the matching local manual from the wizard. End ACE-only maintenance without starting host installation.
- Distinguish review of initial tube settings from physical calibration after installation.
- Explain Windows file extraction, OpenSSH setup, password entry, expected results, and stop conditions.
- Include both manual languages and recovery pages in the offline package. Render flow diagrams as readable steps.
- Keep the supported OpenCubic workflow free of user-supplied NFC keys and preserve every earlier archive.

The revised workflow has offline checks. It has not received a new end-to-end physical installation test.

## 0.1.5 — 2026-10-30

This is a documentation revision. Installer behavior and production modules are unchanged.

- List supported brands and tag formats on both home pages. Credit OpenCubic for multi-brand NFC decoding.
- Distinguish upstream-confirmed formats, implemented but untested formats, and unsupported formats.
- Remove unrelated U1 internal-reader key-entry tutorials and instructions to obtain NFC keys.
- State that supported OpenCubic tags need no user-supplied NFC keys. Keep the Bambu physical-test evidence separate.
- Update bilingual offline guides and retain every earlier archive.

## 0.1.4 — 2026-10-30

This is a documentation correction. Installer behavior and production modules are unchanged.

- State that this project physically verified Bambu brand, filament type, and color recognition and synchronization.
- Mark Anycubic and open tag formats as not physically tested by this project.
- Explain that ACE decodes the tags. The U1 integration queries the decoded results and converts them into U1 material settings.
- Update both languages and the offline guides. Preserve every earlier archive.

## 0.1.3 — 2026-10-30

ACE firmware preparation is now part of the bilingual Windows workflow.
Users can prepare the required ACE firmware without editing a device profile or entering shell commands.

- Download the exact OpenCubic Gen 1 target and stock reference from their pinned upstream locations.
- Verify image identities and formats before the known source-version upgrade path can be selected.
- Check current device identity, U1 idle and heater state, ACE readiness, drying, and serial ownership.
- Run one update in a persistent U1 transaction, with read-only result inspection after a lost connection.
- Keep uncertain writes stopped for review, without automatic retry or stock rollback.
- Check preserved U1 configuration and material data; request review when new NFC decoding changes nonempty metadata.
- Keep the manual firmware procedure and all previous release archives available.

Firmware binaries and private evidence remain outside the public package.
The four production transport/NFC modules are unchanged.
The new guided orchestration has offline tests but no separate end-to-end physical acceptance test.

## 0.1.2 — 2026-10-30

This release puts U1 preparation and installation in one bilingual workflow.
The four production transport and NFC modules remain unchanged.

- Download the original pinned U1 firmware, verify SHA-256, and prepare a selected FAT32 USB drive.
- Guide the required screen update, Advanced Mode, Root Access, and Wi-Fi checks before host installation.
- Put manual installation at the top of both homepages, in the wizard menu, and in an offline manual.
- Expand daily-operation, NFC, private-key, and four-path tube-calibration guides in English and Chinese.
- Distinguish ACE tag support from the separate U1 internal OpenRFID key configuration.
- Retain both earlier release archives without modification.

The preparation stage does not flash the printer remotely or automatically approve access.
ACE firmware preparation remains separate. New USB and wizard paths have offline tests, not a complete physical installation test.

## 0.1.1 — 2026-10-30

This release adds a guided Windows installation for new users.
The four production transport and NFC modules remain unchanged.

- Select Chinese or English after double-clicking `START-HERE.cmd`.
- Read offline instructions in `START-HERE.html` or `START-HERE.en.html`.
- Transfer files and prepare settings without manual commands or JSON edits.
- Set External detection and verify the internal-reader service state.
- Back up the previous reader mode, configuration link, and service state.
- Identify one matching ACE USB interface while preserving existing settings.
- Add step-by-step prerequisite instructions and explicit OpenAI Codex attribution.
- Check the guided launcher with simulated SSH and SCP operations.
- Retain the original v0.1.0 archive, fixed checksum, and manual source procedure.
- Put critical restrictions in prominent alerts before the relevant steps.

The launcher does not flash firmware or determine physical tube lengths.
Its offline tests do not replace a complete physical installation check.

## 0.1.0 — 2026-10-30

This release packages the tested `port7-forward-takeup` integration.
The four production modules retain their tested source bytes.

- Adapt the SnapAce integration to the pinned U1 2.0 firmware.
- Transfer ACE material data to U1 with brand and subtype information.
- Keep material data until the ACE inlet becomes empty.
- Wait for the U1 Load command after the short insertion movement.
- Use a fast stage before the head-sensor approach.
- Apply optional forward take-up after confirmed retraction.
- Deduct the completed take-up distance from the next fast stage.
- Add a separate installer with version checks, private backups, and rollback.
- Add standalone instructions, configuration tables, and connection diagrams.
- Package the corrected optional USB updater without firmware images or NFC keys.

The generic installer and packaging tools are new in this release.
Their offline checks supplement the recorded physical tests of the production modules.
They do not establish a fresh physical installation test for every supported configuration.
