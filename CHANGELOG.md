# Changes

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
