# 准备 U1 固件

[English](u1-preparation.md) · [新手向导](quick-start.zh-CN.md) · **[手动安装入口](installation.zh-CN.md)**

向导会下载准确的 U1 扩展固件（**上游原版文件**），校验后复制到 U 盘。然后你在 U1 屏幕上完成更新，并打开 Advanced Mode 和 Root Access。
这一步不刷写 ACE。[ACE 固件步骤](ace-wizard.zh-CN.md)在同一个向导里随后进行。

> [!IMPORTANT]
> **首次固件更新必须在 U1 屏幕上确认。**
> **远程安装前，还必须在屏幕上打开 Advanced Mode 和 Root Access。**

## 准备什么

- 能联网的 Windows 10 或 Windows 11 电脑，以及已完整解压的本项目安装包。
- 一个已经是 **FAT32** 格式的可移动 U 盘，至少空闲 300 MB。向导不格式化磁盘。
- 空闲并已冷却的 U1：打印和全部耗材动作已结束，加热和 ACE 烘干已关闭，喷嘴和热床低于 50℃。
- 第一次安装时：用正常退料操作退出四个打印头里的耗材，取出四个 ACE 入口的耗材，然后再次等待加热器冷却。只是更新本项目时，不要求清空入口。
- 已有自定义配置时，在固件更新前自己保存一份备份。本项目稍后的安装备份保护不了它。

U1 已经是准确的支持版本时，改选菜单 **1. U1 已准备好**。有其他自定义固件或较新版本时，不要为了通过安装检查就直接覆盖。

## 向导步骤

1. 完整解压项目压缩包。双击 **START-HERE.cmd**，选择语言，再选择 **2. 准备 U1 固件 U 盘**。
2. 把 FAT32 U 盘插入电脑。在列表中选择它，核对盘符、名称和容量，然后确认。
3. 等待下载、SHA-256 校验、复制和复制后校验全部完成，然后在 Windows 中**弹出** U 盘。
4. 把 U 盘插入 U1。在 U1 屏幕点 **设置 → 关于 → 固件版本 → 本地更新**。
5. 选择 `U1_extended_2.0.0-paxx12-24_upgrade.bin`，确认更新。等待更新完成并重启，期间保持供电。
6. 点 **设置 → 维护 → Advanced Mode**，开启并按要求完成重启。
7. 点 **设置 → 维护 → Root Access**，阅读提示，向下滚动点 **Agree / 同意**，设为 **Open**。
8. 检查 Wi-Fi，必要时重连，记下现在显示的打印机 IP 地址。
9. 回到电脑上的同一个向导继续。它会询问打印机地址和 SSH 密码。

向导不会覆盖名称相同但内容不同的文件。先自己检查该文件，再重试。找不到合适的盘时，换用 FAT32 可移动 U 盘。不要改程序强制选择其他磁盘。

U1 更新失败时，保存屏幕显示的报错原文，按 [Snapmaker 固件更新故障说明](https://wiki.snapmaker.com/en/snapmaker_u1/troubleshooting/firmware-update-failed)处理。不要尝试随机固件文件。主机适配的回退不能撤销 U1 固件更新。

## 固件身份和校验值

| 项目 | 固定内容 |
| --- | --- |
| 上游版本 | `v2.0.0-paxx12-24` |
| 文件名 | `U1_extended_2.0.0-paxx12-24_upgrade.bin` |
| 大小 | `253893376` 字节 |
| SHA-256 | `42dcf59e06ef0f6fab20745883322f24ddd3c1a09da07449b356dd9dab943070` |

[上游发布页和校验值](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/tag/v2.0.0-paxx12-24) · [准确下载地址](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/download/v2.0.0-paxx12-24/U1_extended_2.0.0-paxx12-24_upgrade.bin)

这个校验值用于识别上游文件，不是 Snapmaker 的签名。本项目压缩包不包含 U1 固件二进制，见[第三方项目说明](../THIRD_PARTY.md)。

## 不想运行向导

自己从上游发布页下载同一个文件，使用前检查 SHA-256：

1. 在文件资源管理器中，按住 **Shift**，右键刚下载的 `.bin` 文件，点 **复制文件地址／复制为路径**。
2. 按 **Windows 键 + R**，输入 `powershell`，按回车。
3. 复制下面这一行到打开的窗口，按回车。出现 `Paste the file path` 时，粘贴刚复制的路径，再按回车。

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath ((Read-Host "Paste the file path").Trim('"'))
```

把完整的 `Hash` 值与上表的 SHA-256 比较，字母大小写不影响结果。**两者不一致时，不要使用这个文件**。从准确的上游地址重新下载。
把校验通过的文件复制到 FAT32 U 盘第一层，完成向导步骤的第 4–8 步，再进入 **[手动源码安装](installation.zh-CN.md)**。

依据：[v24 安装说明](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/install.md)、[Advanced Mode 要求](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/firmware_config.md)、[SSH 访问说明](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/ssh_access.md)。
