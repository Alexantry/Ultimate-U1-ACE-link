# Start here

[简体中文](quick-start.zh-CN.md) · **[Manual installation](installation.md)**

Use Windows 10 or Windows 11. You do not need programming knowledge, local Python, Codex, or an API key.
The wizard has **English** and **中文** prompts. It enters the commands for you.
For tags supported by the specified OpenCubic firmware, you do not need to find or enter NFC keys.

> [!CAUTION]
> **Do not copy old SnapAce `filament_feed.py` or `extruder.py` onto U1 firmware 2.0.**
> **This project replaces the original SnapAce software installation steps.** Use the upstream guide for hardware connections only.

## 1. Prepare before an update or installation

1. Finish the current print and all filament operations.
2. For a first installation, use normal Unload to remove filament from all four U1 heads. Remove filament from all four ACE inlets too.
3. Turn off heating and ACE drying. Unloading can heat a nozzle. Wait until all nozzles and the bed are below 50°C.
4. Confirm that the hardware is **ACE Pro Gen 1**, not ACE 2 Pro.
5. Prepare the verified ACE-to-USB cable and four PTFE paths. Turn both devices off before connecting hardware. Turn them on after the connections are complete.
6. Connect the computer and U1 to the same local network. Both need internet access for their firmware download stages.
7. If U1 has custom changes, save a private backup before any U1 firmware update. The later project backup does not protect that earlier update.

**Existing project installation:** an ordinary update does not require emptying all four channels. The devices must still be idle and cold.
Use the [SnapAce hardware guide](https://github.com/BlackFrogKok/SnapAce#pinout-and-wiring) for the cable arrangement. A normal charging cable is not a substitute.

**You do not need to install ACE firmware separately before opening the wizard.**
The same workflow can prepare U1 firmware and then check ACE firmware.
You must still perform the hardware connections and the U1 screen actions yourself.

## 2. Download and extract

1. Download [the project ZIP](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/refs/heads/main/downloads/Ultimate-U1-ACE-link-v0.1.6.zip).
2. Open the Windows Downloads folder.
3. Right-click the ZIP and select **Extract All**.
4. Select **Extract**. Open the extracted `Ultimate-U1-ACE-link` folder.
5. Double-click **START-HERE.cmd**.
6. Select **2. English**. Enter menu numbers and press Enter.

Do not run the launcher inside the ZIP viewer.
If Windows hides extensions, the file can appear as `START-HERE`, with type **Windows Command Script**.
Files ending in `.html` are instructions, not installation programs.

![Download, extract, and start](images/first-steps.en.svg)

**START-HERE.en.html** is the English offline guide. **START-HERE.html** is the Chinese offline guide.
You do not need to double-click a Python file or open PowerShell for the guided path.
To inspect and enter each command yourself, use **[manual installation](installation.md)**. It still runs the readable printer installer.

## 3. Choose the correct menu

| Menu | Choose it when | What happens |
| --- | --- | --- |
| **1. U1 is ready** | U1 has `2.0.0-paxx12-24`, Advanced Mode is on, and Root Access is Open. | Check ACE firmware when needed, then install or update the U1 integration. |
| **2. Prepare U1 firmware USB** | The required U1 firmware is not installed. | Download and verify the U1 file, prepare a FAT32 USB drive, and guide the screen steps. Then continue in the same window. |
| **3. Manual installation** | You prefer command instructions. | Open the local manual in your selected language and exit without connecting to the printer. |
| **4. ACE firmware** | You need ACE maintenance or the result of an earlier ACE update. | Inspect the saved result first. Complete ACE maintenance, then exit. This choice does not install the U1 integration. |

Menu 2 needs a removable USB drive that already uses **FAT32**, with at least 300 MB free.
The wizard does not format a drive. It shows its letter, label, and size before copying.
Follow [U1 preparation](u1-preparation.md) for the exact screen steps.
After updating, reconnect Wi-Fi if necessary. The printer address can change.

**Customized or different firmware needs a separate compatibility review. Do not overwrite it merely to pass this installer.**
The required version is fixed. It is not necessarily the newest upstream release.
After menu 4, reopen the wizard and select menu 1 if you also need to install or update the U1 integration.

## 4. Enter the connection information

| Prompt | What to enter |
| --- | --- |
| Printer address | The current IP address on the U1 Wi-Fi screen. Enter the address only, without `http://` or `/firmware-config/`. |
| First SSH connection | Compare the address with the printer screen. Follow [the first-connection instructions](installation.md#confirm-the-connection). Stop if an existing host key changed unexpectedly. |
| `password:` | The printer's SSH root password, followed by Enter. This is not the Wi-Fi or Snapmaker account password. |
| Numbered question | Enter the listed number, then press Enter. |

The upstream default SSH username is `root`; its default password is `snapmaker`. Use your own password if it was changed. [Upstream SSH instructions](https://snapmakeru1-extended-firmware.pages.dev/ssh_access)
**Password entry shows no characters or asterisks. This is normal.**
Each SSH connection can request the password again. The wizard does not save it.

## 5. Follow the ACE firmware stage

For a new installation, this stage appears automatically.
Select automatic checking unless you already know the specified OpenCubic CFW 1.1.1 is installed and NFC works.
U1 downloads the pinned images and checks their size, SHA-256, and format.
The wizard then checks ACE identity, source version, and idle state.

The tested update route is **ACE Pro Gen 1: `V1.3.856` / boot `V1.0.1` → OpenCubic CFW 1.1.1, reporting `CV1.3.863`**.
Another source version is not a supported automatic update route. Do not guess or force it.
The version string `CV1.3.863` alone does not prove the exact community build.

Read the source and target before confirming one update. Keep power and USB connected until the result is known.
See [the ACE prompts and recovery instructions](ace-wizard.md).

## 6. Review initial tube distances, then install

> [!IMPORTANT]
> **The installer cannot measure tube lengths or filament tension.**
> **Do not copy example distances as universal settings.**

The first installation asks for A and B. Existing installations preserve their current settings.

![Fast-feed and retraction lengths](images/length-guide.en.svg)

| Letter | Meaning |
| --- | --- |
| **A** | Retract from the head while keeping the filament tip inside ACE and its rear tube. |
| **B** | Feed quickly from a known starting position. End this stage before the head; use a value smaller than A. |

Use [the initial setup and calibration procedure](configuration.md#calibrate-the-ptfe-paths) to select initial values for your tube arrangement.
Review and measure the layout before installation. Verify the values with all four slots after installation.
The tested arrangement used A = 1250 mm and B = 1150 mm. These are reference values only.
The speed defaults are 200 for fast feed, 50 for head approach, and 80 for retraction.
Forward take-up starts disabled on a new installation. Enable it only after normal loading and unloading have been checked.

Review the displayed settings. Confirm installation only after the machine checks and initial distance review pass.
The installer saves the files it changes, sets **Filament Detection → External**, and verifies the installation after a service restart.
**External** is the option name. `extended` is used in firmware names and configuration paths.
No U1 OpenRFID or NFC key setup is required for this workflow.

## 7. Wait for success, then test

Wait until the window reports a complete project installation success.
An ACE firmware success message alone does not mean the U1 integration is installed.

1. Insert filament into one empty ACE inlet. Keep your hands clear of the rollers.
2. Wait for the short bite and NFC recognition to finish.
3. Confirm that automatic full loading does not start. Check the material information, or enter it manually for an unrecognized spool.
4. Select that slot's **Load** on U1. Wait for completion.
5. Select **Unload**. Confirm the filament remains in ACE and the material data stays available.
6. Without removing or reinserting filament, select **Load** again.
7. After this slot passes, check the other three slots one at a time.

The installer does not run these physical tests. All four slots share the distance settings.
Stop if filament catches, a drive slips, or the printer reports an error.
See [daily use](daily-use.md) and [validation limits](validation.md).

## If a stage stops

| Stage or message | Next action |
| --- | --- |
| Missing OpenSSH Client | Install the Windows component using the steps below. Do not install Python. |
| File transfer or connection failed before installation | Check the current IP, local network, Root Access, and SSH password. |
| Printer hot, busy, drying, or using ACE | Finish the operation normally. Turn heating and drying off. Wait until temperatures are below 50°C. |
| No unique ACE interface | Check power, generation, and the verified cable. Connect only one ACE. Do not guess a serial port. |
| U1 firmware update error on the screen | Stop. Keep the exact error and use [the U1 recovery guidance](u1-preparation.md). This is not a host-installer rollback. |
| ACE update result is missing or the computer disconnected | Keep power and USB connected. Reopen the same package version and select **menu 4**. Read the saved result; do not resend the update. |
| U1 integration installation may have started, but no success result arrived | Keep the window and diagnostic file. Do not repeat installation. Use [host recovery](update-and-rollback.md) to inspect the backup and service state. |

ACE firmware maintenance and U1 host installation have different recovery paths.
`Automatic rollback VERIFIED` refers to host files and services; it does not roll back ACE firmware.
Do not publish private configuration, credentials, or unredacted diagnostics.

### Install the Windows OpenSSH Client if needed

1. Select **Start**. Search for **Optional Features** and open that settings page.
2. Select **View features** or **Add a feature**.
3. Search for **OpenSSH**. Select **OpenSSH Client**, then complete the displayed installation steps.
4. Run **START-HERE.cmd** again.

Do not select OpenSSH Server. A managed computer can require its administrator to add the component.
See [Microsoft's component instructions](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse).

## Development

The user supplied requirements and performed physical tests. **OpenAI Codex** wrote and integrated the code, installer, and documentation.
Users do not need Codex or another AI assistant to install or use the project.
Upstream contributions and licenses remain listed in [THIRD_PARTY.md](../THIRD_PARTY.md).
