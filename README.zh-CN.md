# Ultimate U1-ACE link

让 **Anycubic ACE Pro 第一代**连接 **Snapmaker U1**，在打印机屏幕上完成进退料并保留 NFC 材料信息。

**本项目使用 OpenAI Codex 完成开发和文档整理。安装者不需要会编程，也不需要安装 Codex。**

> [!CAUTION]
> **禁止把旧 SnapAce 的 `filament_feed.py` 或 `extruder.py` 覆盖到 U1 2.0。**
>
> **本项目替代原 SnapAce 的软件安装步骤。** 上游项目只需参考**硬件接线部分**。

## 先选安装方式

| 希望跟着提示完成 | 希望先看清每条命令 |
| --- | --- |
| **[双语安装向导](docs/quick-start.zh-CN.md)** | **[手动源码安装](docs/installation.md)** |
| 双击启动，选择中文或 English。 | 先查看源码，再逐条执行命令。 |

**[原版 v0.1.0 安装包与说明](docs/install-options.md#retained-v010)继续保留，文件未被覆盖。**

## 第一次使用，只从这里开始

### [下载 v0.1.1 安装包](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/refs/heads/main/downloads/Ultimate-U1-ACE-link-v0.1.1.zip)

1. 先按[机器准备说明](docs/before-you-start.zh-CN.md)接好设备、准备固件。
2. 下载上面的安装包。
3. 对压缩文件点右键，选择“全部解压缩”。
4. 打开解压后的文件夹，双击 **START-HERE.cmd**，选择 **中文** 或 **English**。

接下来跟着所选语言的窗口操作即可，**不需要自己输入命令或修改配置文件**。
不熟悉下载、解压和双击操作，请看[逐步图文指南](docs/quick-start.zh-CN.md)。
安装包里的 **START-HERE.html**（中文）和 **START-HERE.en.html**（英文）也可以双击打开，离线阅读。

**不想使用双击向导？** [手动安装方式](docs/installation.md)保留了可逐条查看的命令，并说明如何先检查源码。
手动方式仍会运行开源的 `installer.py`，不会启动 Windows 向导。
[原版 v0.1.0、固定校验值和对应说明](docs/install-options.md#retained-v010)也已保留，新版没有覆盖它。

![下载、解压、启动示意图](docs/images/first-steps.svg)

## 安装向导会帮你做好什么？

- 自动传文件、检查版本、保存备份。
- 自动寻找 ACE 接口；已有接口和参数会保留。
- 自动把后台 **Filament Detection** 设置为 **External（外部）**，并处理内置读卡服务。
- 自动设置必要的持久化、ACE 配置和模块。
- 自动重启相关软件服务，核对连接、设置和材料信息。

后台选项的准确名称是 **External**；`extended` 是扩展固件和配置文件的名称。
你不用再手动找这个选项。

你需要输入打印机地址和密码。首次安装还需确认适合自己管路的长度；已有安装默认保留原参数。
速度等通用值已经预填。回送消松在首次安装时默认关闭，测试后再启用。

## 需要什么设备？

> [!IMPORTANT]
> **先完成以下机器准备，再运行安装。**
> **当前验证的是 ACE Pro 第一代和下表中的准确 U1 固件版本，不包含 ACE 2 Pro。**

| 项目 | 已验证的要求 |
| --- | --- |
| 电脑 | Windows 10 或 Windows 11，与打印机在同一网络。 |
| U1 | 扩展固件 `2.0.0-paxx12-24`；Advanced Mode 开启，Root Access 为 Open。 |
| ACE | ACE Pro 第一代，正确的 USB 连接和四路料管。 |
| ACE NFC 固件 | `CV1.3.863` / OpenCubic `1.1.1`。 |

刷 U1 固件、准备 ACE 固件和制作连接线属于前置准备，主安装向导不自动执行这些工作。

## 这些功能已整合

空槽插料只短咬料并识别 NFC；点击 U1“进料”才长送。头端传感器控制最终到料停止。
退料后保留材料信息；不拔出 ACE 就可以再次进料。可选的向前回送可减少松圈。
回送不是独立驱动滚筒，也没有张力检测。

## 项目是谁做的？

用户提出需求、观察设备并完成实机测试；**OpenAI Codex 编写和整合代码、安装工具及文档**。
本项目基于 [SnapAce](https://github.com/BlackFrogKok/SnapAce)、[U1 扩展固件](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware)、[Snapmaker U1 Klipper](https://github.com/Snapmaker/u1-klipper)、[OpenCubic](https://github.com/Jupsi/OpenCubic) 等项目。
[项目来源与许可](THIRD_PARTY.md)列明上游作者、贡献和改进范围。

安装不需要 Codex、ChatGPT 订阅或 API 密钥。仓库不提供 NFC 密钥，所需专有密钥由用户自行寻找。
英文说明按 ASD-STE100 简洁写作原则编写，不宣称正式认证。

[参数说明](docs/configuration.md) · [NFC 说明](docs/nfc.md) · [回退与更新](docs/update-and-rollback.md) · [验证范围](docs/validation.md) · [English](README.md)
