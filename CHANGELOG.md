# Changes

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
