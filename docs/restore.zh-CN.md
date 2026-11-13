# 卸载与恢复出厂

[English](restore.md) · [返回首页](../README.zh-CN.md) · [更新与回退](update-and-rollback.zh-CN.md)

这一页讲怎样把 U1 和 ACE 恢复到没有本项目的状态。三件事互相独立，可以只做其中一件。

| 任务 | 做什么 | 实机验证 |
| --- | --- | --- |
| **1. 卸载本项目** | U1 恢复扩展固件自带的原始文件，仍是 `2.0.0-paxx12-24`。 | 离线测试通过，未实机验证。 |
| **2. ACE 刷回官方固件** | ACE 从 OpenCubic 刷回 Anycubic 官方 `V1.3.863`。 | **从未实机执行过。** |
| **3. U1 刷回官方固件** | U1 刷回 Snapmaker 官方 `V2.0.0`。 | 未实机验证，用的是上游记载的方法。 |

要全部恢复时，按 **2 → 1 → 3** 的顺序做：ACE 回退需要本项目还在 U1 上，卸载需要扩展固件还在。

> [!CAUTION]
> **任务 2 有把 ACE 刷坏的风险，本项目没有经过验证的救砖方法。**
> 官方 `V1.3.863` 镜像由社区托管，只核对了大小和 SHA-256，没有厂商签名，也不是你这台 ACE 的备份。
> 你的 ACE 出厂时可能是更早的版本（例如 `V1.3.856`），本项目无法恢复到那个版本。

## 用向导

1. 结束打印和进退料，关闭加热和烘干，等喷嘴和热床低于 50℃。
2. 双击 **START-HERE.cmd**，选语言，再选 **5. 恢复**。
3. 选要做的任务，按窗口提示操作。

| 恢复菜单 | 向导会做什么 |
| --- | --- |
| **1. 卸载本项目** | 连接 U1，先做只读检查并列出要恢复和删除的文件，你确认后才执行。 |
| **2. ACE 刷回官方** | 三次确认：接受风险、设备空闲、最后确认。只接受 `CV1.3.863`／引导 `V1.0.1` 的 ACE。 |
| **3. 官方 U1 固件 U 盘** | 下载并校验官方固件，复制到你选的 FAT32 U 盘。不连接打印机，不格式化。 |

## 任务 1：卸载本项目

卸载做这些事，其他文件不动：

- 从固件自带的原件恢复 `filament_feed.py`、`filament_detect.py`、`extruder.py`。
- 删除 `ace.py`、`ace.cfg`，以及 `ace.cfg` 声明的 `ace_vars.cfg`。
- 耗材识别方式是 External 时改回固件默认的 Snapmaker。你自己选的其他方式保持不变。
- 卸载前自动备份，失败时自动恢复到卸载前的状态。

卸载之后，U1 不能再通过 ACE 进退料。ACE 固件和 U1 固件版本都不变。

**开始前：四个打印头必须无料。** 先在 U1 屏幕上对每一路正常退料。

手动执行时，先按[更新与回退第 1 节](update-and-rollback.zh-CN.md#read-installation-status)连接并设好 `$PrinterTarget` 和 `$RemoteDir`。`$RemoteDir` 里要有本版本的 `installer.py`。

先做只读检查，它不改任何文件：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py remove-check"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Removal check failed; do not remove' }
```

期望 `read_only: true` 和 `removable: true`，并列出 `restore_from_firmware` 和 `delete`。
提示 `Unknown modified core` 或 `Firmware original is not a reviewed file` 时停止，不要删除或覆盖文件来绕过。

确认列表后执行一次：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py remove"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Removal failed; preserve the error' }
```

期望 `removed: true` 和备份编号。出现 `Automatic rollback VERIFIED` 表示卸载失败，但已恢复到卸载前的状态。
结果不明时不要重复执行，按[更新与回退](update-and-rollback.zh-CN.md)查询状态。

## 任务 2：ACE 刷回官方 V1.3.863

| 项目 | 要求 |
| --- | --- |
| 当前固件 | `CV1.3.863`，引导 `V1.0.1`（本项目指定的 OpenCubic） |
| 目标固件 | `ACE_V1.3.863_20250518.bin`，105652 字节，运行后显示 `V1.3.863` |
| SHA-256 | `3f3676ba357749b3d0367922cb7f6b0dedc9b3d104c1c29e719ac3e563f5eb63` |
| 来源 | [固定的社区托管文件](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/originalFirmware/ACE_V1.3.863_20250518.bin) |

- 本项目必须还装在 U1 上，工具通过它确认设备空闲并在结束后恢复 Klipper。
- 刷回后，OpenCubic 提供的多品牌 NFC 识别不再可用。
- 其他版本会被拒绝。不要修改检测结果来绕过。
- 全程保持 ACE 供电和 USB 连接，U1 保持开机。

手动执行时，同样先设好 `$PrinterTarget` 和 `$RemoteDir`。第一步只下载、校验和读取版本，不写入：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py prepare --route stock"
```

查询结果，直到状态不再是 `PREPARING`：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result --wait-seconds 30"
```

| 结果 | 含义 |
| --- | --- |
| `PREPARED`，`route: stock`，`target_firmware: V1.3.863` | 可以进入下一步。记下 `operation`。 |
| `ALREADY_TARGET` | ACE 已经是官方 `V1.3.863`，不需要写入。 |
| `UNSUPPORTED` | 当前版本不在支持范围内。停止。 |
| `NEEDS_ATTENTION` 或 `ERROR` | 停止，按[更新与回退第 2 节](update-and-rollback.zh-CN.md#ace-interruption)处理。 |

确认 `ready: true` 和 `service_restored: true` 后，执行这一次写入。三个确认参数缺一不可：
```powershell
$AceOperation = (Read-Host '输入 prepare 结果里的 operation').Trim()
if ($AceOperation -notmatch '^[a-f0-9]{32}$') { throw 'STOP: Invalid operation identifier' }
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py start --operation $AceOperation --confirm-flash --accept-untested-rollback --accept-untested-stock-route"
```

之后只做查询，**不要重发 `start`**：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result --wait-seconds 30"
```

期望 `SUCCEEDED`、`ready: true`、`service_restored: true`。其他结果一律停止并保留记录。
成功后，在正常使用前逐槽检查进料和退料。

## 任务 3：U1 刷回 Snapmaker 官方固件

方法来自[扩展固件的安装说明](https://snapmakeru1-extended-firmware.pages.dev/install)：下载官方 `.bin`，用同样的本地更新步骤安装。

| 项目 | 值 |
| --- | --- |
| 文件 | `U1_2.0.0.205_20260914173503_upgrade.bin`，216715726 字节 |
| 下载 | [Snapmaker 官方地址](https://public.resource.snapmaker.com/firmware/U1/U1_2.0.0.205_20260914173503_upgrade.bin)，列在[官方发布说明](https://wiki.snapmaker.com/en/snapmaker_u1/firmware/release_notes) |
| SHA-256 | `e6269eb0f1d9e8da74173e9da6350a14b18dd2fe5c4e8f2cabc48b0cdaf2aad7` |

Snapmaker 不公布校验值。上面的值是扩展固件上游构建时固定的，本项目下载官方文件核对过一致。

1. 先完成任务 1，卸载本项目。
2. 建议清理扩展配置：在电脑打开 `http://打印机地址/firmware-config/`，在 Recovery 里点 **Reset Extended to Defaults**。刷官方固件不会删除这些配置。
3. 下载上表的文件，并校验：
```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath ((Read-Host "Paste the file path").Trim('"'))
```
4. 结果与上表不一致就不要使用。一致后，把文件复制到 FAT32 U 盘的第一层。
5. 打印机空闲并冷却后插入 U 盘，在屏幕点 **设置 → 关于 → 固件版本 → 本地更新**，选这个文件并确认。
6. 等待更新完成并自动重启。期间不要断电或拔 U 盘。

刷回之后：

- Advanced Mode、Root Access 和扩展配置网页随扩展固件一起消失。
- 打印机提示升级到 `V2.1.0` 时先看 Snapmaker 的说明。它的 wiki 记录了[升级到 2.1.0 后黑屏的问题](https://wiki.snapmaker.com/en/snapmaker_u1/troubleshooting/touchscreen_malfunction)。
- 更新报错时按[官方升级故障说明](https://wiki.snapmaker.com/en/snapmaker_u1/troubleshooting/firmware-update-failed)处理。

## 之后想重新安装

按[快速开始](quick-start.zh-CN.md)从头再走一遍。卸载和安装时的备份都留在打印机的 `/userdata/ultimate-u1-ace-link/backups/` 里。
