# Choose an installation method

The Windows launcher is optional.
Both current methods use the same open-source printer installer and reviewed payload.
Neither method requires Codex or an API key.

## [MANUAL INSTALLATION — open the complete procedure](installation.md)

You can also open **MANUAL-INSTALL.html** in the extracted package.
It contains the same English command procedure and does not execute it.
The wizard has a separate manual-guide menu entry.

## [GUIDED INSTALLATION — use bilingual prompts](quick-start.md)

The current wizard can prepare the original U1 firmware file and guide the screen steps before host installation.
See [U1 preparation](u1-preparation.md).

| Method | What you run | Best fit |
| --- | --- | --- |
| Guided installation | Double-click `START-HERE.cmd`, then choose Chinese or English. | Users who want prompts instead of commands. |
| Manual source procedure | Enter the documented PowerShell, SCP, and SSH commands; run `installer.py` on the U1. | Users who want to inspect source and control each step. |
| Retained v0.1.0 | Use the original archive and its original instructions. | Users who need the previous package for comparison or maintenance. |

The manual method skips `START-HERE.cmd` and `Install.ps1`.
It still executes **installer.py** on the printer.
It is not a claim that no installation script runs.
See [the manual source procedure](installation.md).

## Inspect the source

| File | Purpose |
| --- | --- |
| [START-HERE.cmd](../START-HERE.cmd) | Start Windows PowerShell with the local launcher. |
| [Install.ps1](../Install.ps1) | Display prompts and transfer the selected public files. |
| [Bootstrap.ps1](../Bootstrap.ps1) | Download the pinned upstream U1 image, verify it, and prepare selected removable FAT32 USB. |
| [installer.py](../installer.py) | Check compatibility, save backups, configure the printer, and verify the result. |
| [manifest.json](../manifest.json) | List supported firmware identities and payload hashes. |
| [payload](../payload) | Provide the four printer integration modules. |

The launcher is readable source, not a closed binary executable.
`START-HERE.cmd` applies `ExecutionPolicy Bypass` only to its PowerShell process.
It does not save a system execution-policy change.
It does not download or run another installer from the network.
The optional firmware-preparation path downloads a pinned upstream BIN, checks its hash, and copies it. It does not execute that file on Windows.
Passwords use the system SSH client and are not saved by the launcher.
Private diagnostic files stay on the computer or printer.
No diagnostic upload occurs automatically.

## Verify the archive

Each version has its own archive name.
[SHA256SUMS](../downloads/SHA256SUMS) lists the retained and current package hashes.
The archive also includes `PACKAGE-SHA256SUMS` for its source files.
A matching hash checks file integrity; it does not replace source review or hardware validation.

## Retained v0.1.1

- [Download the original v0.1.1 archive](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/2f238bf2ef00b64d43a632a07fa3a46451e48f4f/downloads/Ultimate-U1-ACE-link-v0.1.1.zip).
- [Read its original instructions](https://github.com/Alexantry/Ultimate-U1-ACE-link/blob/2f238bf2ef00b64d43a632a07fa3a46451e48f4f/docs/installation.md).
- [Inspect its original source](https://github.com/Alexantry/Ultimate-U1-ACE-link/tree/2f238bf2ef00b64d43a632a07fa3a46451e48f4f).

SHA-256: `f684badeac36d7a66d47ed65c04ae0ec278e5731a5289aabaa8a7c521e86b497`.
This release has the bilingual host installer and automatic External setup, but no integrated U1 USB preparation.

## Retained v0.1.0

- [Download the original v0.1.0 archive](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/5d042a4d7263418872099f4c25d7ab67fb9ea943/downloads/Ultimate-U1-ACE-link-v0.1.0.zip).
- [Read the original v0.1.0 instructions](https://github.com/Alexantry/Ultimate-U1-ACE-link/blob/5d042a4d7263418872099f4c25d7ab67fb9ea943/docs/installation.md).
- [Inspect the original source](https://github.com/Alexantry/Ultimate-U1-ACE-link/tree/5d042a4d7263418872099f4c25d7ab67fb9ea943).

SHA-256:

```text
81c21610c49b6e5861e1676cc2662df77bff447c6d24848881a6719319b13c1e
```

> [!IMPORTANT]
> **The original package remains unchanged. It requires manual External selection and has no Windows launcher.**
> **Use its original instructions with its original files. Do not mix files from different archives.**

## 中文说明

你可以选择双击向导，也可以[逐条执行公开的手动步骤](installation.md)。
手动方式不用运行 Windows 向导，但仍会在打印机上执行开源的 `installer.py`。
所有脚本和四个核心模块都可以先在 GitHub 查看；没有封闭的安装 EXE。

原来的 **v0.1.0** 安装包、校验值和对应说明已经保留在上方固定链接中，文件未被新版覆盖。
**v0.1.1** 也保留原样。最新版增加 U1 固件准备，不会覆盖这两个旧压缩包。
旧版需自己设置 **External**；新版安装器会自动设置并检查。
请使用同一版本的文件与说明，不要混装。
