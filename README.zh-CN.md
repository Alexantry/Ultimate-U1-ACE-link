# Ultimate U1-ACE link

[下载 v0.1.0 安装包](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/refs/heads/main/downloads/Ultimate-U1-ACE-link-v0.1.0.zip) · [SHA-256 校验值](https://github.com/Alexantry/Ultimate-U1-ACE-link/blob/main/downloads/SHA256SUMS)

[English](README.md) · [安装指南](docs/installation.md) · [参数与校准](docs/configuration.md) · [故障排查](docs/troubleshooting.md)

让 Anycubic ACE Pro 第一代通过 USB 与 Snapmaker U1 配合使用。本项目基于 SnapAce，整合了 U1 2.0 适配、NFC 材料同步、传感器送料、退料后向前回送，以及材料信息保留。

当前实现为 `port7-forward-takeup`，包含 2026 年 10 月 28–30 日完成的整合工作。安装器只安装和检查软件，不自动执行送料、退料或其他运动测试。

## 先完成前置项目

| 顺序 | 前置项目 | 要求 |
| --- | --- | --- |
| 1 | [SnapmakerU1-Extended-Firmware](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware) | 已验证版本为 `v2.0.0-paxx12-24`。 |
| 2 | U1 访问设置 | 开启 Advanced Mode、Root Access，并确认 Wi-Fi 与 SSH 可用。 |
| 3 | ACE Pro 第一代固件 | 已验证 NFC 路径使用 `CV1.3.863` / OpenCubic `1.1.1`。已有对应固件时不必重复刷写。 |
| 4 | [SnapAce 硬件接线](https://github.com/BlackFrogKok/SnapAce#pinout-and-wiring) | 按上游硬件说明准备 USB 连接与四路 PTFE 管。 |
| 5 | 本项目 | 按[安装指南](docs/installation.md)安装兼容的软件模块。 |

**不要先把旧 SnapAce 的 `filament_feed.py`、`extruder.py` 覆盖到 U1 2.0。** 本项目替代原项目的软件安装步骤，继续沿用其硬件连接基础。

![系统连接概念图](docs/images/system.svg)

图示只表达连接关系，不是线缆制作尺寸图。

## 当前行为

下表为已验证的参考参数，不能直接当作所有管长的通用值。保守安装模板默认关闭退料后的回送动作。

| 操作 | 行为 |
| --- | --- |
| 向空 ACE 入口插入线材 | 短距离咬料并识别 NFC，不自动长送 1250 mm。 |
| 在 U1 点击进料，且起点已知 | 先发送 1150 mm、速度 200，再以速度 50 送到头端传感器检测到线材。 |
| 在 U1 点击退料 | 先完成热端退料，再由 ACE 回抽 1250 mm、速度 80。 |
| 正常回抽完成 | 向 U1 方向回送 300 mm、速度 50，减少外部松圈。 |
| 不拔插，直接再次进料 | 快段自动扣除先前回送量：850 mm、速度 200，再以速度 50 寻找头端。 |
| 重启、断连或位置不确定 | 全程使用速度 50，正常终点仍由头端传感器决定。 |
| 只从头端退出，ACE 入口仍有料 | 保留品牌、材质、子类型和颜色。 |
| 线材真正退出 ACE 入口 | 确认入口为空后清除对应材料信息。 |

速度是发送给 ACE 的命令值，单位为 mm/s，不是实测速度。ACE 固件可能限速。2500 mm 是总寻料故障上限，不是要求每次都送满的长度。

![进退料参数概念图](docs/images/feed-cycle.svg)

## NFC 的职责与限制

ACE 固件负责读卡，本项目接收已解码的材料信息并同步到 U1。U1 的 **External** 设置用于关闭内置读卡路径，避免两个来源冲突；它并不限制 ACE 只能读取 OpenSpool。

品牌名称转换不等于新增物理标签支持。能否读取某卷耗材，仍取决于 ACE 固件、标签格式、位置和所需认证信息。不能据此宣称 ACE 支持 OpenRFID 的所有品牌标签。

仓库不包含 NFC 密钥，也不提供密钥取得链接。所需专有密钥由用户自行寻找。保留 U1 的 `openrfid_user.cfg` 不代表其中的密钥会传给 ACE。详见 [NFC 指南](docs/nfc.md)。

## 回送功能的边界

这里的“回送”是把线材向 U1 方向送回一小段，用来消除外部松圈。它不是独立驱动收卷滚筒，也没有“检测到收紧就停止”的张力反馈。

本项目没有修改 ACE 传动比或电机固件。长度可配置，下一次快段会自动扣除成功记录的回送距离。取消、失败或断连后不会凭旧记录继续高速送料。

## 安装与维护

英文指南提供完整的 Windows PowerShell、SCP、SSH 操作步骤，不需要 AI 工具参与。

- [安装](docs/installation.md)：前置版本、访问设置、传输、只读检查与安装。
- [参数与校准](docs/configuration.md)：设置 JSON、管长测量和回送距离调整。
- [NFC](docs/nfc.md)：ACE 与 U1 两条读卡路径、品牌和隐私边界。
- [更新与回退](docs/update-and-rollback.md)：保留参数、备份和最近版本回退。
- [故障排查](docs/troubleshooting.md)：连接、材料识别和进退料问题。

安装前先执行 `python3 installer.py check --settings config/settings.local.json`。安装与更新共用 `install` 命令；回退使用 `rollback`。这些命令在 U1 上通过 SSH 运行。

首次安装前需要四个 ACE 入口和四个 U1 头端传感器均为空。已有 ACE 集成的更新不要求退出四路耗材，而是逐字段核对原材料信息和传感器状态。首次安装可能清除空槽在界面上残留的旧材料标签，安装器会报告这一变化。

## 验证范围

整合候选版本在部署前通过 **194 项离线测试**。实机记录确认了**第 4 槽**完整退料、回送 300 mm、不拔插再次上料的流程；用户确认退料效果可以。

该次上料完成到 `load_finish`，记录中的材料信息保持不变。这不是四个槽、全部料盘或所有标签格式的全面认证。详见[验证记录范围](docs/validation.md)。

## 基础项目与致谢

- [BlackFrogKok/SnapAce](https://github.com/BlackFrogKok/SnapAce)：最初的 ACE 与 U1 连接、控制和硬件方案。
- [SnapmakerU1-Extended-Firmware](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware)：U1 扩展固件、配置界面和材料接口。
- [Snapmaker/U1-klipper](https://github.com/Snapmaker/U1-klipper)：U1 原有 Klipper 与耗材工作流。
- [OpenCubic](https://github.com/Jupsi/OpenCubic)：已验证 ACE NFC 路径所需的上游固件。
- [OpenRFID](https://github.com/suchmememanyskill/OpenRFID)：标签格式生态与材料命名参考。

各项目保留各自的许可与权利。主机软件许可不授予第三方固件或专有 NFC 密钥的再分发权。

英文操作文档参考 [ASD-STE100 Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf) 的简洁写作原则，不宣称正式合规或认证。
