# 使用、修改与分享许可

[English](licensing.md)

审查日期：**2026-10-30**。本页记录能够核实的许可证据，不是法律意见。

> [!IMPORTANT]
> **本项目源码包使用 GPLv3；这不等于外部固件镜像也全部属于 GPLv3。**
> 在遵守 GPLv3 的前提下，可以使用、修改和分享受该许可覆盖的源码，也可以用于商业用途。
> 一个固件能公开下载，不代表我们就获得了重新分发、改许可或商业打包该固件的权利。

## 本项目自己的代码

本仓库的源码按 [GNU GPL 第 3 版](../LICENSE)发布。
没有额外的“仅限非商业使用”或“禁止分享”限制。
私人使用不要求公开你的修改。

本项目使用 OpenAI Codex 辅助开发。这不能替代上游版权、许可条件或署名。
本项目不是 Snapmaker 或 Anycubic 的官方发布。

## 上游组件

本包包含的代码：

| 来源 | 许可 | 固定的证据 | 本项目用于 |
| --- | --- | --- | --- |
| SnapAce，提交 `34a06e87bcd59ca3ebc845ed32a794627505437c` | GPLv3 | [LICENSE](https://github.com/BlackFrogKok/SnapAce/blob/34a06e87bcd59ca3ebc845ed32a794627505437c/LICENSE) | 改编后的 ACE 控制代码和集成改动。 |
| Snapmaker U1 Klipper，提交 `93cb12fa` | GPLv3 | [COPYING](https://github.com/Snapmaker/u1-klipper/blob/93cb12faebf6e74c51bbc5f0be66e95124af14c8/COPYING) | U1 核心模块和仅用于测试的夹具。 |
| Paxx12 U1 扩展固件，提交 `417e6394f62366e010a3f76f8e567f67db770165` | GPLv3 | [LICENSE](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/417e6394f62366e010a3f76f8e567f67db770165/LICENSE) | 固件基线改动和公开的 RFID 补丁。 |
| ACE 第一代 USB/IAP 研究，提交 `ec8f37bf9928e7814efaafe6aaa794c69f8216d1` | GPLv3 | [LICENSE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/LICENSE) 和 [NOTICE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md) | 改编后的 USB/IAP 协议和更新工具源码。 |
| Ultimate U1-ACE link 新增贡献 | GPLv3 | [LICENSE](../LICENSE) 和[修改声明](../THIRD_PARTY.md) | 主机改动、安装器、Windows 工具、测试、示意图和文档。 |

相关但**不包含**在本包内的材料：

| 材料 | 许可证据 | 固定的证据 |
| --- | --- | --- |
| OpenRFID | GPLv3。本包不含 OpenRFID 的解码器、认证代码或用户配置。 | [LICENSE](https://github.com/suchmememanyskill/OpenRFID/blob/f2608fa1a2d28abce80c7f1a8fbf7aa184f22bbd/LICENSE) |
| OpenCubic ACE 固件 | 源码私有。二进制按现状提供，供用户下载刷写。未找到再分发或商业授权。 | [README](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/README.md#firmware-source) 和[刷写指南](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/docs/how-to-flash.md) |
| OpenCubic Qt 刷写工具 | 上游 README 标为 MIT。这个标注不适用于固件。 | 同一份 README |
| 完整的 U1 扩展固件镜像 | 主项目为 GPLv3。镜像还包含原厂组件和各有许可的依赖。 | [许可声明](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/417e6394f62366e010a3f76f8e567f67db770165/README.md#license) |
| Anycubic 原厂 ACE 固件 | 第三方厂商的材料。社区仓库存有副本，不会产生新的授权。 | [ACE 研究项目 NOTICE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md) |

[SOURCES.json](../SOURCES.json) 记录来源身份及公开文件的校验值，[manifest.json](../manifest.json) 记录安装允许清单。

## 可以分发什么，不可以分发什么

可以：

- 按 GPLv3 使用、修改和分享本项目源码，包括商业用途。GPLv3 允许为提供副本收费。

本项目没有找到允许下列行为的授权。要这样做，请先取得权利人许可：

- 重新分发、修改、改许可或商业打包 OpenCubic ACE 固件镜像。
- 把完整 U1 固件镜像或 Anycubic 原厂固件当作本项目 GPL 授权覆盖的内容来分发。它们不在授权范围内。
- 把链接可访问、下载成功、校验值一致或“按现状提供”的声明当作许可。
- 把 Qt 刷写工具的 MIT 标注套用到固件上。
- 公开私人 NFC 密钥或私人密钥文件的哈希值。

可选下载工具直接从上游取得你选择的固件镜像，并核对大小和校验值。
这只证明文件完整，不证明版权授权。下载工具自身的许可，不是它下载内容的许可。

本包不含固件 `.bin` 文件、NFC 密钥、OpenRFID 配置或 OpenCubic Qt 刷写工具。
保留的 `v0.1.0` 和 `v0.1.1` 压缩包已检查，均不含这些内容。以后的每个包都要重新检查。

## 再分发时要保留什么

1. 保留已有的版权声明、许可声明和无担保说明。
2. 附带 GPLv3 许可证全文。
3. 用醒目的声明标出你的修改及相关日期。
4. 对受 GPL 覆盖的组合作品，按与 GPLv3 一致的条件许可。
5. 提供与你分发的内容相对应的源码，以及它的构建和安装脚本。
6. 不给接收者的 GPL 权利额外加限制。
7. 不把凭据、打印机备份、设备专属的写入配置和私人诊断信息放进分享的包里。

GPLv3 第 4、5 节规定源码分发。分发目标代码或二进制时，还需遵守第 6 节。
