# Choose an installation method

The Windows launcher is optional.
Both current methods use the same open-source printer installer and reviewed payload.
Neither method requires Codex or an API key.

## [MANUAL INSTALLATION — open the complete procedure](installation.md)

You can also open **MANUAL-INSTALL.html** in the extracted package.
For Chinese, use [the Chinese manual](installation.zh-CN.md) or **MANUAL-INSTALL.zh-CN.html**.
Both files contain the matching step-by-step instructions and copyable commands. Opening a manual does not execute it.
The wizard has a separate manual-guide menu entry.

## [GUIDED INSTALLATION — use bilingual prompts](quick-start.md)

The current wizard covers U1 file preparation, screen guidance, and the supported ACE firmware update before host installation.
See [U1 preparation](u1-preparation.md) and [ACE firmware prompts](ace-wizard.md).

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
| [AceFirmware.ps1](../AceFirmware.ps1) | Guide ACE preparation, one confirmed update, and read-only result inspection. |
| [wizard_backend.py](../tools/ace_usb/wizard_backend.py) | Run persistent ACE maintenance transactions on the U1 with the existing protocol tools. |
| [installer.py](../installer.py) | Check compatibility, save backups, configure the printer, and verify the result. |
| [manifest.json](../manifest.json) | List supported firmware identities and payload hashes. |
| [payload](../payload) | Provide the four printer integration modules. |

The launcher is readable source, not a closed binary executable.
`START-HERE.cmd` applies `ExecutionPolicy Bypass` only to its PowerShell process.
It does not save a system execution-policy change.
It does not download or run another installer from the network.
The U1 preparation path downloads a pinned upstream BIN, checks its hash, and copies it to the selected USB drive.
The ACE stage downloads its pinned images on U1, checks them, and writes the selected target only after device checks and confirmation.
Neither path executes a firmware BIN on Windows. Firmware binaries are not included in this source archive.
Passwords use the system SSH client and are not saved by the launcher.
Private diagnostic files stay on the computer or printer.
No diagnostic upload occurs automatically.

## Verify the archive

Each version has its own archive name.
[SHA256SUMS](../downloads/SHA256SUMS) lists the retained and current package hashes.
The archive also includes `PACKAGE-SHA256SUMS` for its source files.
A matching hash checks file integrity; it does not replace source review or hardware validation.

## Retained v0.1.5

- [Download the unchanged v0.1.5 archive](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/55bb1ee475ddc0c0f3904b5a0d51b4af1b37ed32/downloads/Ultimate-U1-ACE-link-v0.1.5.zip).
- [Read its fixed source and instructions](https://github.com/Alexantry/Ultimate-U1-ACE-link/tree/55bb1ee475ddc0c0f3904b5a0d51b4af1b37ed32).

SHA-256: `9aefb03d418bed99735736d8ed13a96fa3706faaf13fc163b453683913be503c`.
Version 0.1.5 removed unrelated NFC key-entry guidance and credited OpenCubic's format support.
Version 0.1.6 adds a complete Chinese manual, recovery guidance, and clearer wizard task boundaries.
The production transport and NFC modules are unchanged.

## Retained v0.1.4

- [Download the unchanged v0.1.4 archive](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/c3cab67b49157fea251d44ac720ee00043b8f850/downloads/Ultimate-U1-ACE-link-v0.1.4.zip).
- [Read its fixed source and instructions](https://github.com/Alexantry/Ultimate-U1-ACE-link/tree/c3cab67b49157fea251d44ac720ee00043b8f850).

SHA-256: `9ab8c4ff1b0ef2f6319f7478a684ffec381ab21c2a666f0e7f3ea27e22b8a6e1`.
Version 0.1.4 corrected the NFC test evidence and the explanation of ACE decoding.
It used the same installer and production modules as v0.1.3.

## Retained v0.1.3

- [Download the unchanged v0.1.3 archive](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/4229c6fd384e1821268d2d61f7c2d2992bc91a9e/downloads/Ultimate-U1-ACE-link-v0.1.3.zip).
- [Read its fixed source and instructions](https://github.com/Alexantry/Ultimate-U1-ACE-link/tree/4229c6fd384e1821268d2d61f7c2d2992bc91a9e).

SHA-256: `03de055d1c38d430f83817d5687c73dc387a3f282a2c4329df0b8ce882349e39`.
Version 0.1.3 introduced the guided ACE firmware stage.

## Retained v0.1.2

- [Download the unchanged v0.1.2 archive](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/2407650dd4d5ae2fea810c4bcb8b4c81114938d6/downloads/Ultimate-U1-ACE-link-v0.1.2.zip).
- [Read its original instructions](https://github.com/Alexantry/Ultimate-U1-ACE-link/blob/2407650dd4d5ae2fea810c4bcb8b4c81114938d6/docs/installation.md).
- [Inspect its fixed source](https://github.com/Alexantry/Ultimate-U1-ACE-link/tree/2407650dd4d5ae2fea810c4bcb8b4c81114938d6).

SHA-256: `2663853d3bab97efa09b579b110af099e852ffd7aee06d3afe105ea73e8a5c1c`.
This release prepares U1 USB firmware but keeps ACE flashing in the separate manual procedure.

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

你可以选择双击向导，也可以[按中文手动步骤逐条复制命令](installation.zh-CN.md)。
离线中文手册是 **MANUAL-INSTALL.zh-CN.html**；英文手册是 **MANUAL-INSTALL.html**。
手动方式不用运行 Windows 向导，但仍会在打印机上执行开源的 `installer.py`。
所有脚本和四个核心模块都可以先在 GitHub 查看；没有封闭的安装 EXE。

原来的 **v0.1.0** 安装包、校验值和对应说明已经保留在上方固定链接中，文件未被新版覆盖。
**v0.1.1** 也保留原样。v0.1.2 增加 U1 固件准备。
**v0.1.2** 同样保留原样。v0.1.3 增加 ACE 引导更新。
**v0.1.3** 也保留原样。v0.1.4 仅更正说明，安装器行为及生产模块不变。
**v0.1.4** 同样保留。v0.1.5 删除本方案不需要的密钥填写教程，并补充 OpenCubic 支持列表和署名。
**v0.1.5** 同样保留。v0.1.6 补全中文手动安装和恢复说明，明确向导菜单的操作范围。
v0.1.0 需自己设置 **External**；v0.1.1 及之后的安装器会自动设置并检查。
请使用同一版本的文件与说明，不要混装。
