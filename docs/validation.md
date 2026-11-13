# Validation and limits

## Versions these results apply to

| Item | Version |
| --- | --- |
| U1 firmware | `v2.0.0-paxx12-24` |
| ACE hardware | ACE Pro Gen 1 |
| ACE firmware | `CV1.3.863` / OpenCubic `1.1.1` |
| Host implementation | `port7-forward-takeup` |

## Physically tested

| Item | Result |
| --- | --- |
| Insert filament | Recognition runs. Automatic full loading does not start. |
| Bambu tag | Brand, type, and color transfer to the U1. |
| Unload on slot 4 (software index 3) | 1250 mm retraction at speed 80, then 300 mm forward take-up at speed 50. The user confirmed the result. |
| Reload on slot 4 | 850 mm fast at speed 200, then slow at speed 50 until the head sensor detected filament. Final state `load_finish`. |
| Material data | Unchanged through the unload and reload cycle. |
| ACE firmware transfer | `V1.3.856` / boot `V1.0.1` to the pinned OpenCubic target. |
| Read-only `status` command | Passed on the tested U1 firmware. |

## Not physically tested

| Item | Status |
| --- | --- |
| Every slot, spool, and tag format | Not covered. The recorded check used slot 4. |
| Windows launcher | No complete physical installation test, including interactive SSH password entry. |
| U1 firmware preparation on USB | No end-to-end physical U1 update test. |
| Guided ACE firmware orchestration (new in v0.1.3) | Offline checks only. |
| Fresh installation with the generic installer | No separate physical acceptance test. |
| Stock ACE firmware rollback, internal calibration readback | Not established. The rollback is offered as an untested option. |
| Removal of this project from the U1 (`installer.py remove`) | Offline checks only. On the tested U1, the firmware originals exist and match the reviewed hashes. Removal itself was not run. |
| Return of the U1 to official Snapmaker firmware | Not tested. The official file's size and SHA-256 were checked against the pinned values. |

The installer, host integration, USB tool, and Windows tools also have automated offline tests. Those tests use simulated devices and do not prove physical behavior.

## Control limits

- An acknowledged stop does not guarantee an immediate mechanical stop. Keep access to the ACE power switch during initial transport tests.
- ACE firmware can limit the requested speed.
- Forward take-up has no tension sensor. A smaller loose loop on one spool does not prove correct tension for another.
- Different PTFE paths require separate calibration.

## Repeat the acceptance check

1. Finish any print before the test.
2. Clear the printer movement area.
3. Keep your hands away from the rollers.
4. Insert filament into one empty ACE inlet.
5. Wait for NFC recognition to finish.
6. Confirm that automatic full loading does not start.
7. Select that slot's Load command on the U1.
8. Confirm that the U1 reports load completion.
9. Select that slot's Unload command on the U1.
10. Observe the loose filament after forward take-up.
11. Select Load again without removing the filament.
12. Confirm that the U1 reports load completion.
13. Compare the material data with the initial values.

Stop the test if the filament snags or the controller reports an error.
Record the slot number, workflow state, and visible movement for troubleshooting.
