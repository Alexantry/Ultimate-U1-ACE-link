# Validation and limits

## Public installer checks

The public installer includes 35 transaction and service-state tests.
A 22-test baseline passed with Python 3.11 on Linux.
The additional tests check failure recovery, temporary-file ownership, automatic External settings, serial selection, and actual OpenRFID process exit.
These tests use temporary directories, simulated services, and simulated printer status.
They do not install files into the printer's operating paths.
The read-only `status` command also passed on the tested U1 firmware.

The optional USB tools passed 96 offline tests with simulated transport and generated test images.
The Python suites contain 325 tests across the host integration, installer, and USB tools.
The bilingual Windows launcher adds 36 offline checks using simulated SSH and SCP operations.
U1 firmware preparation adds 20 offline checks for download integrity, USB destinations, conflicts, and cancellation.
Those preparation tests use small synthetic files and a temporary folder, not real USB firmware installation.
These checks passed locally with Windows PowerShell 5.1.
The launcher has not received a complete physical installation test, including interactive SSH password entry.
The new USB preparation workflow has not received an end-to-end physical U1 update test.

The tested production modules remain byte-for-byte unchanged in this package.
A fresh installation with the generic installer has not received a separate physical acceptance test.

## Software baseline

The integrated port7 candidate passed 194 offline tests before deployment.
These tests exercise production methods through controlled transport and sensor fixtures.
They do not simulate spool friction or measure physical filament travel.

The test set covers:

- Head detection during the fast stage, stage transition, slow stage, and acknowledgement wait.
- Fresh busy-to-ready confirmation before the slow stage starts.
- A separate NFC wait budget before the movement budget.
- Travel exhaustion and movement timeout.
- Missing acknowledgements without command replay.
- Disconnects and replacement connections.
- Concurrent load requests across feeder modules.
- Cancellation, inlet removal, and new filament insertion.
- Unload failures and heater cleanup.
- Confirmed retraction before forward take-up.
- One forward take-up movement per successful unload.
- A 300 mm advance that reduces the next fast stage to 850 mm.
- Material retention during head movement.
- Material clearing after a confirmed empty inlet.
- Delayed material callbacks that must not erase a newly inserted spool.

## Recorded physical check

| Item | Observation |
| --- | --- |
| U1 firmware | `v2.0.0-paxx12-24` |
| ACE hardware | ACE Pro Gen 1 |
| ACE firmware baseline | `CV1.3.863` / OpenCubic `1.1.1` |
| Host implementation | `port7-forward-takeup` |
| Tested slot | Slot 4, software index 3 |
| Retraction request | 1250 mm at speed 80 |
| Forward take-up request | 300 mm at speed 50 |
| Reload fast request | 850 mm at speed 200 |
| Reload slow request | Maximum 1650 mm at speed 50 |
| Normal reload endpoint | Head sensor detection, followed by `stop_feed_filament` |
| Final workflow state | `load_finish` |
| Final ACE state | Connected, fresh, ready, with feed assist on index 3 |
| Material comparison | Unchanged across all 681 samples in the examined record |

The 1650 mm slow request was the remaining safety allowance.
The controller stopped the slow movement when the head sensor detected filament.
The record does not establish the exact physical slow distance.

The user confirmed that the unload result was satisfactory.
Earlier checks confirmed Bambu material transfer and insertion without automatic full loading.
Those checks do not establish complete physical coverage of every slot, spool, or tag format.

## Control limits

ACE firmware can limit requested speed.
The controller therefore uses status transitions, not distance divided by requested speed, to detect fast-stage completion.

An acknowledged stop does not guarantee an immediate mechanical stop during every ACE selector state.
Keep access to the ACE power switch during initial transport tests.

The forward take-up movement has no tension sensor endpoint.
A smaller loose loop does not prove correct tension for another spool.
Different PTFE paths require separate calibration.

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
