# 更新、断线查询与回退

[English](update-and-rollback.md) · [手动安装](installation.zh-CN.md) · [故障排查](troubleshooting.zh-CN.md)

本页命令在 **Windows PowerShell** 里运行，不需要以前的窗口还开着。

- **ACE 固件维护和 U1 主机适配安装是两个独立的事务。**
- 主机备份不能回退 ACE 或 U1 固件。
- 结果未知时：保持设备空闲，不打印，不重发安装或刷写命令。

<a id="read-installation-status"></a>
## 1. 新开窗口并连接

1. 点击“开始”，搜索并打开 **Windows PowerShell**。
2. 准备 U1 屏幕当前的 IP 和记录的 **RemoteDir**。安装目录名含 `stage`，手动调参目录名含 `tuning`。向导失败时会显示该目录，电脑私人日志里也记有 `Remote stage`。
3. 粘贴下面整块。先输入 IP 和 SSH 密码，再粘贴记录的完整目录。
4. 首次连接的身份核对和隐藏密码输入，见[确认连接](installation.zh-CN.md#confirm-the-connection)。

**不要猜目录。** 找不到记录时，保留错误窗口、屏幕信息和文件。不要用一个只是看起来最新的目录执行写入。
```powershell
$ErrorActionPreference = 'Stop'
Get-Command ssh.exe, scp.exe -CommandType Application | Out-Host
$PrinterAddress = (Read-Host '输入 U1 屏幕 Wi-Fi 页显示的 IPv4 地址').Trim()
if ($PrinterAddress -notmatch '^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$' -or
    @($PrinterAddress.Split('.') | Where-Object { [int]$_ -gt 255 }).Count -gt 0) {
    throw 'STOP: Invalid IPv4 address'
}
$PrinterTarget = 'root@' + $PrinterAddress
ssh.exe $PrinterTarget 'id'
if ($LASTEXITCODE -ne 0) { throw 'STOP: SSH connection failed' }
$RemoteDir = (Read-Host '粘贴上次记录的 RemoteDir 路径').Trim()
if ($RemoteDir -notmatch '^/userdata/ultimate-u1-ace-(?:stage|tuning)-[0-9]{8}-[0-9]{6}(?:-[a-f0-9]{8})?$') {
    throw 'STOP: Use the exact recorded staging directory'
}
ssh.exe $PrinterTarget "ls '$RemoteDir/installer.py' '$RemoteDir/manifest.json' '$RemoteDir/tools/ace_usb/wizard_backend.py'"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Recorded package files are unavailable' }
```

**期望：** 显示 `uid=0(root)` 和三个文件路径。
目录或文件不存在时，不要从其它版本拼文件。先确认原事务的结果，再上传替换包或开始任何写入。

### 先读 ACE 状态，再读主机状态

这条查询不会打开串口、恢复服务或启动刷写：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result --wait-seconds 30"
if ($LASTEXITCODE -ne 0) { throw 'STOP: ACE result query failed' }
```

| ACE 结果 | 怎么做 |
| --- | --- |
| `PREPARING`、`STARTING`、`RUNNING`、`RECOVERING` | 保持供电，稍后重复同一条 `result` 查询。 |
| `NEEDS_ATTENTION`、`ERROR` 或查询失败 | 转到 [ACE 中断处理](#ace-interruption)。不要因为读不到 Klipper 就重启或回退。 |
| `NONE` | 没有 ACE 事务。 |

安全终态还必须有 `ready: true` 和 `service_restored: true`。

只有在没有未决 ACE 事务时，才读取主机状态：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py status"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Host status is unavailable; do not start a write' }
```

- 期望 `klipper_state: ready`。安装后 `managed` 为 `true`。
- `ace_version` 是本项目的模块版本，不是 ACE 固件版本。
- `status` 读取的是当前状态。**它不能证明失联的安装程序已经结束，也不能证明那次安装成功。**
- 原进程可能还在运行时，继续等待并保留记录。不要回退，也不要再次安装。

<a id="ace-interruption"></a>
## 2. ACE 固件操作中断

**最简单的路径：** 解压同一版本的安装包，运行 `START-HERE.cmd`，选择 **菜单 4：ACE 固件**。
它先读取保存的事务，不会自动重刷。
只有在任何写入之前就失败的情况，它才可能提供“检查并恢复服务”。

| 结果 | 怎么做 |
| --- | --- |
| 正在运行 | 保持 ACE、U1 和 USB 的供电与连接，继续查询。 |
| `SUCCEEDED` 且服务已恢复 | 核对材料变化。ACE 维护已完成，主机安装另行核对。 |
| `FAILED_SAFE` | 解决网络、空闲或冷却条件，再用同一版本安装包重新准备。 |
| `NEEDS_ATTENTION` 且 `flash_attempted: false` | 菜单 4 可提供仅检查的恢复。确认一次，然后等待。 |
| `NEEDS_ATTENTION` 且 `flash_attempted: true` | **不要重刷，不要自动刷回原厂包，不要强行启动 Klipper。** 保留记录，停止正常使用。 |
| 版本不支持或记录损坏 | 停止。不要编辑 JSON、删除事务或改动上报的版本。 |

不用向导时，继续使用第 1 节的只读 `result` 查询。
仅检查的恢复要求 `NEEDS_ATTENTION`、`flash_attempted: false`，并且后台任务已停止。先确认这三项。
下面的命令只恢复尚未开始写入的维护状态，不更新固件：
```powershell
$Raw = & ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result"
if ($LASTEXITCODE -ne 0) { throw 'STOP: ACE query failed' }
$SavedAce = ($Raw -join "`n") | ConvertFrom-Json
if ($SavedAce.state -ne 'NEEDS_ATTENTION' -or $SavedAce.flash_attempted -ne $false -or
    $SavedAce.operation -notmatch '^[a-f0-9]{32}$') { throw 'STOP: Probe-only recovery is not available' }
$OperationId = $SavedAce.operation
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py recover --operation $OperationId"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Do not repeat recovery; query its result' }
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result --operation $OperationId --wait-seconds 30"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Read the saved result later; do not repeat recovery' }
```

**期望的最终结果：** `CANCELLED_SAFE`、`ready: true`、`service_restored: true`。

- `RECOVERING`：只重复第 1 节的 `result` 查询，不要重复 `recover`。
- 已经尝试过刷写时，后台会拒绝恢复。不要改它的记录。
- 其它故障可能需要人工维护，普通安装步骤不能保证恢复。见 [ACE 技术维护说明](ace-firmware.md#uncertain-results-and-recovery)。

<a id="after-an-interrupted-installation"></a>
## 3. 主机安装中断

查看原窗口或私人日志里的最后结果：

| 结果 | 含义和操作 |
| --- | --- |
| `installed: true`、`ready_samples: 3` | 安装程序报告成功。再核对当前状态和实际功能。 |
| `Automatic rollback VERIFIED` | 安装失败，但恢复已验证。先解决导致失败的问题，再重试。 |
| `automatic rollback FAILED` | 恢复未完成。保持空闲，保存 `Backup ID` 和错误信息。 |
| 只有 SSH 断线，没有最终结果 | 成功与否未知。不要重发命令。先读取状态，确认原进程的结果。 |

ACE 的 `SUCCEEDED` 不等于主机安装成功。原安装还在运行时不要回退。

## 4. 更新本项目

1. 完成打印和耗材操作。关闭烘干，把所有加热目标设为零，冷却到 50 °C 以下。
2. 送料辅助仍在工作时，对该槽正常退料，等动作结束后再次冷却。不需要退空所有槽。
3. 保存私人配置和备份。下载完整的新安装包，解压到新文件夹。
4. 向导用户：运行新包的菜单 1。它默认保留现有参数。
5. 手动用户：从[手动安装](installation.zh-CN.md)第 2 步开始，用新窗口和新目录。先检查计划，再安装一次。
6. 不要把旧 JSON 整份复制到新模板。不要仅为了更新就把 `apply_existing_settings` 改为 `true`。有意调整参数见[参数说明](configuration.zh-CN.md)。

核心文件上的未知改动会被拒绝，不会自动合并。保留这些改动，不要为了绕过检查而覆盖它们。

## 5. 保存私人备份

安装器的备份在 `/userdata/ultimate-u1-ace-link/backups/`。
第 1 节连接成功后，把它复制到电脑“文档”里一个唯一的新文件夹：
```powershell
$BackupDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) ('Ultimate-U1-ACE-private-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $BackupDir | Out-Null
scp.exe -O -r "${PrinterTarget}:/userdata/ultimate-u1-ace-link/backups" "$BackupDir"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Backup copy failed' }
Write-Host $BackupDir
```

保存显示的路径。备份可能包含私人配置，不要公开发布。
这是主机文件备份，不是 ACE 固件、U1 固件或整台设备的完整镜像。

## 6. 回退最近一次主机安装

只有原安装程序已结束、没有未决 ACE 事务、机器空闲且已冷却时才使用。
正常回退还要求 ACE 就绪、烘干关闭、送料辅助关闭。不要跳过这些条件。
先按第 1 节连接并查询。确认最近的备份就是要恢复的目标，然后运行一次：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Rollback failed; preserve the error' }
```

- 期望 `rolled_back: true` 和备份编号。然后按第 1 节再次查询状态。
- 回退到安装本项目之前的状态后，`managed: false` 和 `ace_version: null` 可以是正常的。
- 安装后被手工改过的文件会导致拒绝，这是为了保护后来的改动。不要盲目删除这些文件。

## 7. Klipper 无法就绪时的主机恢复

**这不能恢复 ACE 固件，也不能绕过正在进行的打印或未决的 ACE 事务。**

只有原安装程序已结束、运动已停止、烘干和加热已关闭、实际温度低于 50 °C 时才使用。
屏幕或独立观察无法确认已冷却、无运动时，停止。网络读不到状态，不能当作设备空闲的证据。

第 1 节能连上 SSH，但正常的 `status` 无法就绪时，下面的命令会跳过最初的在线就绪检查。
固件、备份、文件哈希、ACE 事务和恢复后就绪检查仍然保留：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback --offline-recovery --confirm-idle-and-cold"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Recovery failed; preserve the error' }
```

提示 `No managed installation; offline recovery requires an explicit backup ID` 时，只使用本次失败操作的窗口或日志里的准确 `Backup ID`：
```powershell
$BackupId = (Read-Host '输入本次失败时显示的备份编号').Trim()
if ($BackupId -notmatch '^[0-9]{8}T[0-9]{12}Z$') { throw 'STOP: Invalid backup identifier' }
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback --backup '$BackupId' --offline-recovery --confirm-idle-and-cold"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Recovery failed; do not try another backup at random' }
```

期望 `rolled_back: true`。恢复仍然失败时，停止并保留错误信息。不要随意换其它备份编号尝试。
本页不能保证所有固件、文件或硬件故障都能自动恢复。

## U1 固件升级是另一项工作

先保存私人配置和备份，并确认本项目支持目标固件。
按 [U1 固件准备](u1-preparation.zh-CN.md)操作。重启后重新核对 Wi-Fi、Advanced Mode 和 Root Access。
只有本项目的检查接受目标固件后才重新安装。恢复主机文件不能回退 U1 或 ACE 固件。
