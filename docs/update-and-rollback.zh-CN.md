# 更新、断线查询与回退

[English](update-and-rollback.md) · [手动安装](installation.zh-CN.md) · [故障排查](troubleshooting.zh-CN.md)

**先区分 ACE 固件更新和 U1 主机适配安装。** 两者不是同一事务；主机备份不能回退 ACE 或 U1 固件。
出现未知结果时，保持设备空闲，不开始打印，不重发安装或刷写。
本页命令在 **Windows PowerShell** 运行，不需要 AI，也不需要以前的窗口仍然打开。

<a id="read-installation-status"></a>
## 1. 新开窗口，重新建立查询连接

1. 点击 Windows“开始”，搜索并打开 **Windows PowerShell**。
2. 准备 U1 屏幕当前 IP，以及操作时记录的 **RemoteDir**。安装目录名称包含 `stage`，手动参数调整目录名称包含 `tuning`。向导失败时会显示该目录，电脑私人日志中也有 `Remote stage`。
3. 粘贴下面整块；先输入 IP 和 SSH 密码，再粘贴记录中的完整目录。
4. 初次 SSH 连接的身份核对和隐藏密码输入，见[连接说明](installation.zh-CN.md#confirm-the-connection)。

**不要猜目录。** 若找不到记录，先保留错误窗口、屏幕信息及现有文件；不要选择一个看似最新的目录执行写入。
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

**完成标准：** `uid=0(root)` 和三个文件路径均正常显示。
如果目录或文件不存在，不从其它版本拼文件；从同一版本重新上传的处理需要先确认上次事务，不能直接开始新安装。

### 先读 ACE 事务，再读主机状态

此查询不会访问串口、恢复服务或启动刷写：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result --wait-seconds 30"
if ($LASTEXITCODE -ne 0) { throw 'STOP: ACE result query failed' }
```

如果 ACE 显示 `PREPARING`、`STARTING`、`RUNNING` 或 `RECOVERING`，保持供电，再执行同一条 `result` 查询即可。
如果为 `NEEDS_ATTENTION`、`ERROR` 或无法查询，转到[ACE 中断处理](#ace-interruption)，不要读不到 Klipper 就去重启或回退。
安全终态也必须核对 `ready: true` 和 `service_restored: true`；`NONE` 表示没有 ACE 事务。

仅在没有未决 ACE 事务时，运行主机只读状态命令：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py status"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Host status is unavailable; do not start a write' }
```

期望 `klipper_state: ready`。已安装时 `managed: true`；`ace_version` 是本项目模块版本，不是 ACE 固件版本。
`status` 读取当前状态，**不能证明之前失联的安装进程已经结束**，也不能单独证明那次安装成功。
如果原进程可能仍在运行，继续等待并保留记录，不进行回退或再次安装。

<a id="ace-interruption"></a>
## 2. ACE 固件操作中断

**最简单的路径：** 解压同一版本安装包，双击 `START-HERE.cmd`，选择 **菜单 4：ACE 固件**，查看保存的事务结果。
此入口先查询原事务，不自动重刷。只有尚未开始写入的中断，才可能提供“检查并恢复服务”。

| 结果 | 怎么做 |
| --- | --- |
| 正在运行 | 保持 ACE、U1 和 USB 供电连接；继续查询。 |
| `SUCCEEDED` 且服务恢复 | 核对材料变化。ACE 阶段完成，主机安装结果另行核对。 |
| `FAILED_SAFE` | 按诊断修正网络、空闲或冷却条件，再在同一版本向导中重新准备。 |
| `NEEDS_ATTENTION` 且 `flash_attempted: false` | 菜单 4 可提供仅检查和恢复；确认一次，再等待结果。 |
| `NEEDS_ATTENTION` 且 `flash_attempted: true` | **不重刷、不自动刷原厂包、不强行启动 Klipper。** 保留记录，停止正常使用。 |
| 检测版本不支持或记录损坏 | 停止，不能靠编辑 JSON、删除事务或换固件编号绕过。 |

不想运行 Windows 向导时，也可以继续使用第 1 节的 `result` 查询。需要尝试仅刷写前恢复时，先确认记录确为 `NEEDS_ATTENTION`、`flash_attempted: false`，且后台任务已经停止。
下面只恢复未开始写入的维护状态，不进行固件更新：
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

**期望：** 最终为 `CANCELLED_SAFE`，`ready: true`，`service_restored: true`。
如果仍在 `RECOVERING`，只重复第 1 节的 `result` 查询，不重复 `recover`。
若 `flash_attempted` 为 `true`，此命令会拒绝；不要改记录。
超出这个范围的故障可能需要人工维护，不能承诺靠普通安装步骤恢复。高级资料见[ACE 技术维护说明](ace-firmware.md#uncertain-results-and-recovery)。

<a id="after-an-interrupted-installation"></a>
## 3. 主机安装中断

查看原窗口或私人日志中的最后结果：

| 看到什么 | 含义及操作 |
| --- | --- |
| `installed: true`、`ready_samples: 3` | 安装程序报告成功；再核对状态及实际功能。 |
| `Automatic rollback VERIFIED` | 安装失败，但原文件和状态已恢复验证。先解决导致失败的问题。 |
| `automatic rollback FAILED` | 自动恢复未完成。保持空闲，保留 `Backup ID` 和错误信息。 |
| 只有 SSH 断线，没有完整结果 | 成功与失败均未知。不要直接重发命令；先查询并核对原进程结果。 |

不要把 ACE 的 `SUCCEEDED` 当成主机安装成功。原安装没有结束时不要运行回退。

## 4. 更新本项目

1. 先完成打印及耗材动作，关闭烘干和所有加热，等待实际温度低于 50 °C。
2. 若送料辅助仍在工作，对相应槽正常退料，动作结束后重新冷却。不要求已有安装的所有槽都退空。
3. 保留私人配置及备份，下载完整新包并解压到新文件夹。
4. 向导用户运行新包的菜单 1；它默认保留现有参数。
5. 手动用户从[手动安装](installation.zh-CN.md)第 2 步开始新窗口、新目录，按顺序检查、安装一次。
6. 不把旧 JSON 整份复制到新模板，也不把 `apply_existing_settings` 改为 `true` 来“确保更新”。普通更新保留旧参数；有意调整参数见[参数说明](configuration.zh-CN.md)。

未知核心文件改动会被拒绝，不会自动合并。不要覆盖自己的改动绕过检查。

## 5. 保存私人备份

安装器备份在 `/userdata/ultimate-u1-ace-link/backups/`。第 1 节连接成功后，可将其复制到电脑“文档”内的唯一新文件夹：
```powershell
$BackupDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) ('Ultimate-U1-ACE-private-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $BackupDir | Out-Null
scp.exe -O -r "${PrinterTarget}:/userdata/ultimate-u1-ace-link/backups" "$BackupDir"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Backup copy failed' }
Write-Host $BackupDir
```

保存该路径。备份可能包含私人配置，不要上传公开仓库。
这是主机文件备份，不是 ACE 固件、U1 固件或整台设备的完整镜像。

## 6. 回退最近一次主机安装

仅当原安装已结束、没有未决 ACE 固件事务、设备空闲且冷却时执行。
先按第 1 节初始化并查询。正常回退要求 ACE 就绪、无烘干或送料辅助；不要跳过这些条件。
确认要恢复最近备份后，运行一次：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Rollback failed; preserve the error' }
```

期望输出 `rolled_back: true` 和备份编号，随后按第 1 节再次查询状态。
回退到尚未安装本项目的状态时，`managed: false`、`ace_version: null` 可以正常。
已安装后又被手工修改的文件会导致拒绝，防止覆盖后续改动。不要盲目删除这些文件。

## 7. Klipper 无法就绪时的主机恢复

**这不是 ACE 固件恢复，也不能用于绕过正在打印或未决 ACE 事务。**
只有确认原主机安装已结束、所有运动停止、烘干和加热关闭、实际温度已低于 50 °C，才考虑此路径。
如果屏幕或独立观察无法确认冷却和无运动，先停止，不能把“网络读不到状态”当成“设备空闲”。

第 1 节仍可连接 SSH，但正常 `status` 无法就绪时，命令可以跳过初始在线就绪检查；固件、备份、文件哈希、未决 ACE 事务及恢复后就绪检查仍保留：
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback --offline-recovery --confirm-idle-and-cold"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Recovery failed; preserve the error' }
```

若提示 `No managed installation; offline recovery requires an explicit backup ID`，仅使用本次失败窗口或日志的准确 `Backup ID`：
```powershell
$BackupId = (Read-Host '输入本次失败时显示的备份编号').Trim()
if ($BackupId -notmatch '^[0-9]{8}T[0-9]{12}Z$') { throw 'STOP: Invalid backup identifier' }
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback --backup '$BackupId' --offline-recovery --confirm-idle-and-cold"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Recovery failed; do not try another backup at random' }
```

期望 `rolled_back: true`。恢复仍失败时，停止后续操作并保留错误信息；不要切换不同备份编号反复尝试。
本页不保证所有固件、文件损坏或硬件故障都可自动恢复，也不需要用 AI 猜测下一条命令。

## U1 固件升级是另一项工作

升级 U1 前保存私人配置及备份，并确认目标版本在本项目兼容表内。
按[U1 固件说明](u1-preparation.zh-CN.md)操作，重启后重新核对 Wi-Fi、Advanced Mode、Root Access。
只有本项目检查接受目标固件后才重新安装。恢复主机文件不能回退 U1 或 ACE 固件。
