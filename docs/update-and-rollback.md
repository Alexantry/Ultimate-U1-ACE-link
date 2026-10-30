# Update and rollback

The same `install` command performs a clean installation or an update.
The installer accepts known baseline modules and previously recorded managed modules.
An unrecognized manual change stops the operation.

## Keep a private backup

The installer stores backups under `/userdata/ultimate-u1-ace-link/backups/`.
Each successful installation records its backup identifier.
These backups belong to your printer.
Do not publish them with an issue report.

1. Set a backup directory outside the project.

```powershell
$BackupDir = Join-Path (Split-Path $ProjectDir -Parent) "Ultimate-U1-ACE-private-backups"
```

2. Create that backup directory.

```powershell
New-Item -ItemType Directory -Force $BackupDir
```

3. Copy the printer's managed backups.

```powershell
scp -O -r "${PrinterTarget}:/userdata/ultimate-u1-ace-link/backups" "$BackupDir"
```

A host backup does not contain an ACE firmware backup.
It also does not replace a separate copy of your full printer configuration.
Keep any private NFC configuration outside the public project directory.

## Update this project

For a guided update, extract the new archive and double-click `START-HERE.cmd`.
The launcher detects an existing ACE installation and keeps its current settings.
Use the manual procedure below if you maintain settings yourself.

1. Finish the current print.
2. Download the intended project version.
3. Extract it into a new local directory.
4. In the existing PowerShell session, enter the new directory containing `installer.py`.

```powershell
$NewProjectDir = Read-Host "Path to the new folder containing installer.py"
Set-Location -LiteralPath $NewProjectDir
```

5. Reset the project directory variable.

```powershell
$ProjectDir = (Get-Location).Path
```

6. Copy your private settings file into the new directory's `config` folder.
7. Review any changed configuration options.
8. Keep `apply_existing_settings` false to preserve existing managed parameters.
9. Transfer the new directory with [the installation procedure](installation.md#4-transfer-the-project).
10. Complete the [idle preparation](installation.md#5-check-before-installation).
11. Run `check` with your local settings file.
12. Review the effective configuration.
13. Run `install` with the same settings file.
14. Confirm that the printer and ACE return to ready.

Set `apply_existing_settings` to `true` only when you intend to replace parameter values.
The installer preserves unrelated configuration and the U1 OpenRFID user file.
It does not merge arbitrary modifications in the four managed Python modules.

## Roll back the latest installation

1. Complete the [idle preparation](installation.md#5-check-before-installation).
2. Read the installation status.

```powershell
ssh $PrinterTarget "cd '$RemoteDir' && python3 installer.py status"
```

3. Restore the latest managed backup.

```powershell
ssh $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback"
```

4. Wait for the rollback result.
5. Read the restored status.

```powershell
ssh $PrinterTarget "cd '$RemoteDir' && python3 installer.py status"
```

The optional `--backup` value must match the latest managed backup identifier.
The installer does not allow arbitrary jumps across backup generations.
Another rollback can restore the preceding managed generation when its receipt is available.

Rollback refuses files that changed after installation.
This protects later manual edits from silent replacement.
Preserve those edits before you resolve a rollback refusal.

## Upgrade U1 firmware separately

U1 firmware upgrades can remove system modifications and the persistence marker.
The upstream [persistence guide](https://snapmakeru1-extended-firmware.pages.dev/data_persistence) describes this behavior.

1. Save private copies of your settings and backups.
2. Check this project's compatibility table for the target U1 release.
3. Follow the upstream firmware upgrade procedure.
4. Confirm Wi-Fi, Advanced Mode, and Root Access after the reboot.
5. Run this project's read-only installation check.
6. Reinstall only when the check accepts the new baseline.

Do not reinstall the U1 2.0 port over an unsupported firmware release.
Restoring host files does not roll back U1 firmware or ACE firmware.

## After an interrupted installation

1. Read the installer error message.
2. Check whether the installer reports a successful restoration.
3. Keep the printer idle if restoration did not complete.
4. Preserve the reported backup directory.
5. Use [troubleshooting](troubleshooting.md) to identify the failed check.

The installer attempts to restore its changed files after an installation failure.
That result must be checked before normal printer use resumes.

## Recover when normal status is unavailable

Use this procedure only when the normal rollback cannot obtain printer status.
It bypasses the initial online idle check, not the firmware, backup, or installed-file checks.

1. Confirm directly that no print or movement is active.
2. Wait for the printer to cool.
3. Run the explicit offline recovery command.

```powershell
ssh $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback --offline-recovery --confirm-idle-and-cold"
```

4. Check the recovery result before normal use.

The command stops Klipper before file restoration.
It still requires a valid ready state after restoration.
Do not use this option to bypass an active-print refusal.

If no installation receipt exists, recovery also requires the backup identifier from the failed installation.

1. Enter that backup identifier.

```powershell
$BackupId = Read-Host "Backup identifier reported by the failed installation"
```

2. Run recovery with that identifier after the same idle and cooling checks.

```powershell
ssh $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback --backup '$BackupId' --offline-recovery --confirm-idle-and-cold"
```
