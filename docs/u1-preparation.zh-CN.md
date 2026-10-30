# U1 固件准备：已放进同一个安装流程

[English](u1-preparation.md) · [新手向导](quick-start.zh-CN.md) · **[手动安装入口](installation.md)**

向导会自动准备准确的 U1 扩展固件文件，并逐步提示屏幕操作。
使用的是**上游原版固件**，不是把本项目塞进固件后生成的新镜像。
此步骤不刷写 ACE。
完成 U1 准备后，同一安装器会提供独立的[双语 ACE 固件步骤](ace-wizard.zh-CN.md)。

> [!IMPORTANT]
> **首次固件更新仍要在 U1 屏幕确认，Advanced Mode 和 Root Access 也要在屏幕打开。**
> 这些动作已纳入向导提示；不能在尚未开放访问时，声称电脑已替你完成了它们。

## 准备什么

- 能联网的 Windows 10 或 Windows 11 电脑。
- 一个已经是 **FAT32** 格式的可移动 U 盘，至少空闲 300 MB。
- 已完整解压的本项目安装包。
- 已结束打印的 U1。已有自定义配置时，先保存私人备份。

本项目稍后的安装备份，不能保护发生在它之前的固件更新。
已使用准确的支持版本时，选择“已经准备好”的路径。
有其他自定义固件或较新版本时，不要为了通过检查就直接覆盖。

## 跟着同一个窗口操作

1. 完整解压项目压缩包。
2. 双击 **START-HERE.cmd**。
3. 选择中文或 English。
4. 选择准备 U1 固件的路径。
5. 把 FAT32 U 盘插入电脑。
6. 在列表中选择它，核对盘符、名称和容量。
7. 确认目标 U 盘。
8. 等待下载、SHA-256 校验、复制和复制后校验全部完成。
9. 在 Windows 中弹出 U 盘，再拔出。
10. 把 U 盘插入 U1。
11. 在 U1 屏幕点 **设置 → 关于 → 固件版本 → 本地更新**。
12. 选择 `U1_extended_2.0.0-paxx12-24_upgrade.bin`，确认更新。
13. 等待更新完成并重启，期间保持供电。
14. 点 **设置 → 维护 → Advanced Mode**，开启并按要求完成重启。
15. 点 **设置 → 维护 → Root Access**，阅读提示，向下滚动点 **Agree / 同意**，设为 **Open**。
16. 检查 Wi-Fi，必要时重连，记下现在显示的 IP 地址。
17. 完成后回到电脑的同一个向导，继续安装。

下一阶段会询问打印机地址、SSH 密码及适合自己管路的长度。
随后自动执行兼容检查、备份、安装和验证。
准备 U 盘的阶段不会连接打印机，也不会触发机器动作。

## U 盘文件会怎样处理

向导**不格式化磁盘、不使用固定内部硬盘、不覆盖内容不同的同名文件**。
只把校验成功的固件复制到已选 U 盘第一层，其余文件保留。
如果有同名冲突，先自行检查该文件，再决定如何处理。
找不到合适的盘时，换用 FAT32 可移动 U 盘，不要改程序强制选择系统盘。

下载文件缓存在当前 Windows 用户的 Local AppData 项目文件夹。
完整且校验一致的文件可复用；未完成或校验失败的文件不会用于安装。
向导不会执行下载的脚本。

## 固件身份和校验值

| 项目 | 固定内容 |
| --- | --- |
| 上游版本 | `v2.0.0-paxx12-24` |
| 文件名 | `U1_extended_2.0.0-paxx12-24_upgrade.bin` |
| 大小 | `253893376` 字节 |
| SHA-256 | `42dcf59e06ef0f6fab20745883322f24ddd3c1a09da07449b356dd9dab943070` |

[上游发布页和校验值](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/tag/v2.0.0-paxx12-24) · [准确下载地址](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/download/v2.0.0-paxx12-24/U1_extended_2.0.0-paxx12-24_upgrade.bin)

这是用于识别上游文件的校验值，不是 Snapmaker 的签名。
本项目压缩包不包含 U1 固件二进制，许可边界见[第三方项目说明](../THIRD_PARTY.md)。

## 不想运行向导

自己从上游发布页下载同一文件，检查 SHA-256，复制到 FAT32 U 盘第一层。
完成上面第 11–16 步后，进入 **[手动源码安装](installation.md)**。
[完整机器准备指南](before-you-start.zh-CN.md)保留了文件资源管理器、U 盘及屏幕的详细操作。

## 为什么这次不直接发布全合一新固件

把本项目和访问默认值写进镜像，会形成不同于原版 v24 的新固件。
它需要独立版本标识、源码及许可核查、恢复验证和实机测试，而且首次仍需屏幕确认升级。
本次采用准确的已测上游基线，把准备工作自动化，不把未经验证的新镜像冒充原版固件。

依据：[v24 安装说明](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/install.md)、[Advanced Mode 要求](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/firmware_config.md)、[SSH 访问说明](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/ssh_access.md)。
