# 使用、修改与分享许可

[English](licensing.md)

审查日期：**2026-10-30**。范围是已标明来源的上游代码，以及本项目公开源码包。
本文记录能够核实的许可证据，不是对所有地区法律、第三方资产或未来版本的绝对保证。

> [!IMPORTANT]
> **本项目源码包使用 GPLv3；这不等于外部固件镜像也全部属于 GPLv3。**
> 在遵守 GPLv3 的前提下，可以使用、修改和分享受该许可覆盖的源码，也可以用于商业用途。
> 一个固件能公开下载，不代表我们就获得了重新分发、改许可或商业打包该固件的权利。

## 这个源码包可以怎样使用？

仓库附带完整的 [GNU GPL 第 3 版许可证](../LICENSE)。
本次核对的已包含源码没有额外的“仅限非商业使用”或“禁止分享”限制。
GPLv3 允许为提供副本收费，不要求所有使用都免费或非商业。
只在自己设备上使用、私下修改，并不要求公开私人修改。
如果把修改后的版本交给别人，则需要履行分发义务。

分享原源码或修改版时，应做到：

1. 保留已有版权声明、许可声明和无担保说明。
2. 附带 GPLv3 许可证全文。
3. 明确标出你的修改及相关日期。
4. 对受 GPL 覆盖的组合源码遵守一致的 GPLv3 条件。
5. 提供与你分发的内容相对应的源码。
6. 同时提供该源码所需的构建和安装脚本。
7. 不给接收者的 GPL 权利额外加限制。
8. 不把私人密钥、凭据或打印机备份一起公开。

GPLv3 第 4、5 节规定源码分发；分发编译后的目标代码或二进制时，还需遵守第 6 节。
第 6 节在适用情况下还要求提供安装信息。
当前项目提供可阅读的源码及构建、安装工具，不把完整打印机固件当作本项目源码包的一部分。
依据见[上游完整 GPLv3 文本](https://github.com/BlackFrogKok/SnapAce/blob/34a06e87bcd59ca3ebc845ed32a794627505437c/LICENSE)。

## 已包含的代码，分别来自哪里？

| 来源 | 核对到的许可证据 | 本项目包含的内容 |
| --- | --- | --- |
| SnapAce，提交 `34a06e87bcd59ca3ebc845ed32a794627505437c` | [该提交的 GPLv3 LICENSE](https://github.com/BlackFrogKok/SnapAce/blob/34a06e87bcd59ca3ebc845ed32a794627505437c/LICENSE) | 改编后的 ACE 控制代码和 U1 集成改动。 |
| Snapmaker U1 Klipper | [官方提交 `93cb12fa` 的 GPLv3 COPYING](https://github.com/Snapmaker/u1-klipper/blob/93cb12faebf6e74c51bbc5f0be66e95124af14c8/COPYING) | 指定固件基线的 U1 核心模块，以及仅用于测试的源码夹具。 |
| Paxx12 U1 扩展固件，提交 `417e6394f62366e010a3f76f8e567f67db770165` | [该提交的 GPLv3 LICENSE](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/417e6394f62366e010a3f76f8e567f67db770165/LICENSE) | 主机适配使用的固件基线改动和公开 RFID 补丁。 |
| ACE 第一代 USB/IAP 研究，提交 `ec8f37bf9928e7814efaafe6aaa794c69f8216d1` | [GPLv3 LICENSE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/LICENSE)与[授权范围 NOTICE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md) | 改编后的 USB/IAP 协议和更新工具源码，以及使用合成数据的离线测试。 |
| Ultimate U1-ACE link 新增贡献 | [本项目 LICENSE](../LICENSE)与[修改声明](../THIRD_PARTY.md) | 主机改动、安装器、Windows 工具、测试、示意图和文档。 |

核对到的上述 GPL 许可证内容一致，都是 GPLv3 正文。
没有发现这些已包含源码另有商业使用禁令。
[SOURCES.json](../SOURCES.json)记录来源身份及公开文件校验值；[manifest.json](../manifest.json)另行记录允许安装的版本和文件。

U1 核心代码基线来自指定版本的扩展固件。
引用官方 Klipper 提交是为了确认许可和来源，不表示每个提取文件都与该提交逐字节相同。
`payload/extruder.py` 保留了 Kevin O'Connor 的原始版权及 GPL 声明。
打印任务配置测试夹具保留了 GPL 声明；协议常量夹具标明了来源、摘取日期及仅供测试的范围。
包内修改声明列出了本项目的改动和日期。

## OpenRFID：独立运行组件和参考来源

OpenRFID 使用 [GPLv3](https://github.com/suchmememanyskill/OpenRFID/blob/f2608fa1a2d28abce80c7f1a8fbf7aa184f22bbd/LICENSE)。
2026-10-30 检查了当前许可证，并确认与该固定许可提交一致。

本包没有包含 OpenRFID 的标签解码器、认证实现或用户配置文件。
本次检查的 payload 与测试夹具中，也没有发现导入 OpenRFID 解码器或携带其实现文件。
与提取的上游参考代码比较后，未发现这些被审查文件存在大段完全相同的实现代码。
这种比较用于辅助核对当前范围，不能证明全部历史来源关系。

OpenRFID 是 U1 已有的独立组件，也是文档和技术参考来源。
ACE 路径接收的是 ACE 固件已经解码的信息。
[NFC 指南](nfc.zh-CN.md)说明 ACE 的识别流程及支持范围，不包含密钥填写步骤或专有密钥。
未来如果实际复制 OpenRFID 代码，仍需保留相应通知、署名和许可条件。

## OpenCubic：固件和 Qt 刷写工具不是同一种许可

固定版本的 [OpenCubic README](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/README.md#firmware-source)明确说，固件源码保持私有。
许可部分把 Qt 刷写工具标为 MIT，把固件二进制描述为按现状提供、使用风险自负。
本次查看的仓库根目录和刷写工具目录中，没有独立许可证文件。
**不能把 Qt 工具的 MIT 描述套用到 ACE 固件。**

| 材料 | 当前能核实的许可或用途证据 | 本项目的处理方式 |
| --- | --- | --- |
| OpenCubic ACE 固件 | 官方说明邀请用户下载并刷写；未找到明确、全面的固件再分发或商业授权。 | 不在本包内分发、修改或重新许可。 |
| OpenCubic Qt 刷写工具 | 上游 README 标为 MIT。 | 本项目没有包含该 Qt 工具的源码或可执行文件。 |
| 本项目的 USB 工具 | 基于另一个明确使用 GPLv3 的 ACE 协议研究项目。 | 作为本项目 GPLv3 源码发布。 |

[官方刷写指南](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/docs/how-to-flash.md)说明了上游预期的“用户下载并使用”流程。
但它没有提供不受限制的固件再分发、修改或商业使用许可。
ACE 研究项目的 [NOTICE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md)也明确排除了第三方固件镜像，不把这些镜像纳入它的 GPL 授权。

可选下载工具只在用户明确选择后，从标明的上游地址取得镜像。
它核对公开的大小和校验值；这证明文件一致性，不证明版权授权。
下载工具本身的源码许可，不会变成下载所得固件的许可。
本次查看的固件条款中，没有另行找到自动下载的明确许可条款。
不能仅凭链接可访问、下载成功或“按现状提供”，推导出额外权利。
要重新分发或商业打包这些固件，应先取得足够的许可依据。

## 完整 U1 固件和 Anycubic 原厂固件

Paxx12 的[许可声明](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/417e6394f62366e010a3f76f8e567f67db770165/README.md#license)说明：主项目使用 GPLv3，个别工具和依赖需要看各自许可。
这不能证明完整升级镜像中的每个原厂组件，都统一采用同一许可证。
完整 U1 镜像混合了原厂内容及其他依赖；本次审计没有逐一确认其中所有组件的再分发权利。

Anycubic 原厂镜像仍是第三方厂商的材料。
社区仓库保存了一份镜像，不会因此产生新的授权。
[ACE 研究项目 NOTICE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md)明确说明了这一点。
这两类完整固件都不包含在本源码包的 GPL 授权承诺里。

助手工具可以引导用户从固定上游地址下载，并核对校验值。
这样保留了上游资产边界，不代表固件获得了不受限制的使用权。
如果以后制作包含首启自动设置的修改版 U1 镜像，需要另外审查组件许可和分发条件。

## 已保留的安装包检查结果

本次检查了本地保留的 **v0.1.0** 和 **v0.1.1** 压缩包。
两者均包含项目 LICENSE 和 THIRD_PARTY 说明。
两者都没有包含固件 `.bin`、NFC 密钥文件、OpenRFID 用户配置或 OpenCubic Qt 刷写工具。
SOURCES.json 中记录的源码校验值与本次检查的文件一致。

这些结论只覆盖检查过的包。
后续新增文件或发布新包时，需要重新核对，不能直接沿用旧包结论。
[旧版保留政策](install-options.md)与新版本的审查结果应分别说明。

## 私人数据和署名

真实 NFC 密钥和私人密钥文件的哈希值不得公开。
公开源码、固件镜像的校验值用于完整性检查，不是私人密钥文件的审计记录。
打印机备份、专属设备写入配置、凭据和包含私人信息的原始日志，不应进入公开包。

本项目使用 OpenAI Codex 辅助开发。
这不能替代上游版权、许可要求和署名，也不会消除这些义务。
本项目不声称是 Snapmaker 或 Anycubic 官方发布。

本次审计为已确认来源的包含源码找到了相容的 GPLv3 依据。
它不保证外部固件、商标、私人密钥及未来新增内容的全部法律权利。
