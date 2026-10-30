# Changes

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
