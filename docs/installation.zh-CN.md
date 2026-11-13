# 手动安装

[English](installation.md) · [双语安装向导](quick-start.zh-CN.md) · [故障与恢复](update-and-rollback.zh-CN.md)

每次复制一整块命令，粘贴到 Windows PowerShell。此方法不运行 Windows 安装向导，但仍会在 U1 上运行可阅读的 `installer.py` 和 ACE 维护程序。
不需要编程、电脑端 Python、AI 助手或 NFC 密钥。不想复制命令，请使用 `START-HERE.cmd`。

> [!CAUTION]
> **不要把旧 SnapAce 的 `filament_feed.py` 或 `extruder.py` 覆盖到 U1 2.0。**
> **只使用 SnapAce 的硬件接线说明。不要混用不同版本的安装器、manifest 和 payload。**

本文针对当前完整安装包。旧包请使用[其对应版本说明](install-options.md)。
离线手册是 `MANUAL-INSTALL.zh-CN.html` 和 `MANUAL-INSTALL.html`。

## 1. 准备机器

1. 结束打印和所有进退料动作。关闭加热、烘干，等每个喷头和热床低于 **50 °C**。
2. 首次安装：按设备正常操作把四路耗材从打印头和 ACE 入口取出。退料可能重新加热，结束后再次关闭加热、烘干，等温度低于 50 °C。更新已有集成：保留现有料位。
3. 按 [U1 固件和访问设置](u1-preparation.zh-CN.md)安装 **`2.0.0-paxx12-24`**，开启 **Advanced Mode**，将 **Root Access** 设为 **Open**。
4. **关闭 ACE 和 U1，并断开两台设备的电源。** 按 [SnapAce 硬件指南](https://github.com/BlackFrogKok/SnapAce#pinout-and-wiring)接好 **ACE Pro 第一代**的连接线和四根对应槽位的 PTFE 管。
5. 开机。让 U1 和电脑在同一局域网，记录 U1 Wi-Fi 页显示的地址。
6. 保持电源和 USB 稳定。**不要预先完成另一套 ACE 刷机教程。** 下面第 5 步会检查 ACE 固件。

U1 版本、访问设置、ACE 代际或接线不符合要求时，停止。不支持 ACE 2 Pro。
安装器会设置 **External**、保存原文件并核对服务。不用手动选择读卡器，也不用设置 U1 OpenRFID 密钥。
受支持的 NFC 解码由 [OpenCubic](https://github.com/Jupsi/OpenCubic) 提供。本项目把数据同步到 U1，见[支持表](nfc.zh-CN.md)。

<a id="prepare-windows-powershell"></a>
## 2. 下载、解压并打开 PowerShell

1. 从[当前安装包入口](../README.zh-CN.md)下载完整 ZIP。不要下载单个 `.py` 文件。
2. 右键 ZIP，选择“全部解压缩”。打开包含 `installer.py` 的 `Ultimate-U1-ACE-link` 文件夹，在文件资源管理器地址栏复制它的完整路径。
3. 点击“开始”，搜索 **Windows PowerShell**，打开普通窗口。不需要管理员模式。
4. 下面所有代码块都粘贴到这个窗口。每次复制一整块（不含三个反引号），按回车，等它完成。
5. 出现红色 `STOP` 或报错时，**停止后面的步骤**，阅读对应说明。不要因为没显示成功就重复写入操作。

核对 ZIP：运行 `Get-FileHash -LiteralPath '你的ZIP完整路径' -Algorithm SHA256`（保留单引号），把结果与 [SHA256SUMS](../downloads/SHA256SUMS) 中同名 ZIP 的值对比。不一致时停止，重新下载完整包。
可以用记事本查看源码，不要修改。私人备份放在项目文件夹之外。

复制下面整块。窗口询问路径时，粘贴解压后的文件夹路径：
```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = (Read-Host '粘贴解压后包含 installer.py 的文件夹完整路径').Trim().Trim('"')
Set-Location -LiteralPath $ProjectDir
$ProjectDir = (Get-Location).Path
if (-not (Test-Path -LiteralPath (Join-Path $ProjectDir 'installer.py') -PathType Leaf)) {
    throw 'STOP: Select the folder containing installer.py'
}
$Manifest = Get-Content -LiteralPath (Join-Path $ProjectDir 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (@($Manifest.files).Count -ne 4 -or @($Manifest.files.payload | Select-Object -Unique).Count -ne 4) {
    throw 'STOP: Expected four unique payload entries'
}
foreach ($Entry in $Manifest.files) {
    if ($Entry.payload -notin @('payload/ace.py','payload/filament_feed.py','payload/filament_detect.py','payload/extruder.py')) {
        throw 'STOP: Unexpected payload path'
    }
    if ((Get-FileHash -LiteralPath (Join-Path $ProjectDir $Entry.payload) -Algorithm SHA256).Hash -ne $Entry.sha256) {
        throw 'STOP: Payload checksum mismatch'
    }
}
Write-Host ('Package version: ' + $Manifest.release)
```

**完成标准：** 显示安装包版本，没有 `STOP`。四个 payload 的校验值与 manifest 一致。

<a id="set-connection-variables"></a>
<a id="confirm-the-connection"></a>
## 3. 连接 U1

Windows 需要 **OpenSSH 客户端**。不要安装 OpenSSH 服务器。
找不到 `ssh.exe` 或 `scp.exe` 时，打开 Windows“可选功能”→“查看功能/添加功能”→搜索 OpenSSH →安装 **OpenSSH 客户端**。然后重新打开 PowerShell，从第 2 步开始。

复制下面整块。只输入 U1 屏幕上的数字地址，例如 `192.0.2.10`。示例不是你的打印机地址。不要加 `http://`、端口或网页路径。
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
```

**完成标准：** 输出包含 `uid=0(root)`。

- **首次连接。** SSH 可能询问 `Are you sure you want to continue connecting`。本步骤没有独立校验指纹。只在可信的本地网络上、确认地址与 U1 屏幕一致后，输入 `yes` 并按回车。
- **主机密钥变化。** 以前记录的主机密钥意外变化时，停止。不要删除该警告来绕过身份检查。
- **密码。** 输入时不显示字符或星号。改过密码就用自己的密码，否则见[上游原厂 SSH 凭据](https://snapmakeru1-extended-firmware.pages.dev/ssh_access)。不要把密码写进命令或配置文件。

<a id="4-transfer-the-project"></a>
## 4. 上传需要的文件

这一块把固定的文件清单上传到 U1 上一个唯一的目录。它不会上传工作文件夹里无关的备份或 `.git` 目录。
```powershell
$TransferDir = Join-Path ([IO.Path]::GetTempPath()) ('UltimateU1Manual-' + [guid]::NewGuid().ToString('N'))
$PublicFiles = @('installer.py','manifest.json','LICENSE','THIRD_PARTY.md','SOURCES.json',
    'payload/ace.py','payload/filament_feed.py','payload/filament_detect.py','payload/extruder.py',
    'tools/ace_usb/wizard_backend.py','tools/ace_usb/ace_iap.py','tools/ace_usb/protocol.py',
    'tools/ace_usb/prepare_profile.py','tools/ace_usb/fetch_firmware.py',
    'tools/ace_usb/images.json','tools/ace_usb/device-profile.json','config/settings.example.json')
foreach ($Name in $PublicFiles) {
    $Source = Get-Item -LiteralPath (Join-Path $ProjectDir $Name)
    if ($Source.PSIsContainer -or ($Source.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'STOP: Expected a regular package file'
    }
    $Destination = Join-Path $TransferDir $Name
    New-Item -ItemType Directory -Force -Path (Split-Path $Destination -Parent) | Out-Null
    Copy-Item -LiteralPath $Source.FullName -Destination $Destination
}
$RemoteDir = '/userdata/ultimate-u1-ace-stage-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
scp.exe -O -r "$TransferDir" "${PrinterTarget}:$RemoteDir"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Upload failed' }
Write-Host ('Printer: ' + $PrinterAddress)
Write-Host ('RemoteDir: ' + $RemoteDir)
ssh.exe $PrinterTarget "ls '$RemoteDir/installer.py' '$RemoteDir/manifest.json' '$RemoteDir/tools/ace_usb/wizard_backend.py'"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Uploaded files are missing' }
```

**完成标准：** 显示三个远程文件路径，没有报错。

- 把显示的 **Printer** 和 **RemoteDir** 两行复制到私人笔记。关窗后的恢复需要它们。
- **保持这个 PowerShell 窗口打开。** 后面的代码块使用它的变量。如果已经关窗，先按[独立状态查询步骤](update-and-rollback.zh-CN.md#read-installation-status)操作，再开始新的上传或写入。

<a id="ace-firmware"></a>
## 5. 检查或准备 ACE 固件

- **不要编辑设备 profile、NFC 密钥文件或固件 JSON。**
- U1 下载并校验固定的上游固件，因此 U1 必须能访问 GitHub。安装包不包含固件二进制。
- 检查会暂时停止并恢复 Klipper。它不发送进退料命令，但初始化可能触发 ACE 动作。手离开滚筒。

先复制下面整块。它定义后续操作，并读取上次 ACE 事务。如果该事务仍在运行，它只读取结果，不重复刷写：
```powershell
function Read-U1Json([string]$Command) {
    $Raw = & ssh.exe -o ConnectTimeout=15 $PrinterTarget "cd '$RemoteDir' && $Command"
    if ($LASTEXITCODE -ne 0) { throw 'STOP: Remote command failed. Do not repeat a write.' }
    return (($Raw -join "`n") | ConvertFrom-Json)
}
function Show-AceResult($Result) {
    $Result | Format-List state,code,operation,source_firmware,boot_firmware,target_firmware,ready,service_restored,flash_attempted,needs_material_review | Out-Host
}
function Wait-AceResult($Result) {
    for ($Attempt = 0; $Attempt -lt 60; $Attempt++) {
        Show-AceResult $Result
        if ($Result.state -notin @('PREPARING','STARTING','RUNNING','RECOVERING')) { return $Result }
        if ($Result.operation -notmatch '^[a-f0-9]{32}$') { throw 'STOP: Invalid operation identifier' }
        $Result = Read-U1Json ('python3 tools/ace_usb/wizard_backend.py result --operation ' + $Result.operation + ' --wait-seconds 30')
    }
    throw 'STOP: Still waiting. Read the saved result later; do not repeat a write.'
}
function Confirm-AceMaterial($Result) {
    if ($Result.needs_material_review) {
        $Result.material_changes | ConvertTo-Json -Depth 8 | Out-Host
        if ((Read-Host '核对当前料卷与材料变化；一致请输入 YES，否则输入 STOP') -cne 'YES') { throw 'STOP: Material review not accepted' }
    }
}
$AceFirmwareAccepted = $false
$AceResult = Wait-AceResult (Read-U1Json 'python3 tools/ace_usb/wizard_backend.py result')
if ($AceResult.state -eq 'UNSUPPORTED') { throw 'STOP: Unsupported ACE; do not change version evidence' }
if ($AceResult.state -notin @('NONE','PREPARED','ALREADY_TARGET','FAILED_SAFE','CANCELLED_SAFE','SUCCEEDED')) {
    throw 'STOP: An unresolved ACE transaction needs recovery'
}
Confirm-AceMaterial $AceResult
```

| 显示的 `state` | 怎么做 |
| --- | --- |
| `NONE` | 没有历史事务。在下面选 A 或 B。 |
| `SUCCEEDED`、`PREPARED`、`ALREADY_TARGET`、`CANCELLED_SAFE` | 仍要为当前设备选 A 或 B。旧的成功记录不能证明当前 ACE 的身份。 |
| `FAILED_SAFE` | 解决网络、冷却或设备问题。选 B 重新准备。不要跳过检查。 |
| `UNSUPPORTED` | 来源版本不受支持。停止。不要改检测记录，也不要强刷。 |
| `NEEDS_ATTENTION`、`ERROR`，或查询失败 | 停止安装，按 [ACE 中断处理](update-and-rollback.zh-CN.md#ace-interruption)操作。 |

如果显示材料变化，`field` 是项目名，`before` 是旧值，`after` 是新值。后缀 `_0`、`_1`、`_2`、`_3` 对应第 1、2、3、4 槽。四项数组使用相同的槽位顺序。
只有新数据与实际料卷一致时才输入 `YES`。没有变化就不会要求确认。

### A. 已安装指定固件，而且 NFC 正常

只有确知这台 ACE 运行 **OpenCubic CFW 1.1.1 / `CV1.3.863`** 时才运行这一块，然后转到第 6 步。
只看到 `CV1.3.863` 字符串不够，不同社区版本可能显示相同版本。不确定时选 B。
```powershell
if ($AceResult.state -notin @('NONE','ALREADY_TARGET','CANCELLED_SAFE','SUCCEEDED')) {
    throw 'STOP: Use fresh preparation for this ACE state; do not keep unverified firmware'
}
if ($AceResult.state -ne 'NONE' -and (-not $AceResult.ready -or -not $AceResult.service_restored)) {
    throw 'STOP: Complete preparation or recovery before keeping existing firmware'
}
if ((Read-Host '只有已知指定 OpenCubic CFW 1.1.1 且 NFC 正常时输入 KEEP') -cne 'KEEP') { throw 'STOP: Existing build not confirmed' }
$AceFirmwareAccepted = $true
```

### B. 不知道当前固件，或需要更新

确认机器空闲、所有加热目标为零、所有实际温度低于 50 °C、烘干关闭、没有 NFC 或进退料动作。
已有集成的送料辅助仍开启时，在 U1 上对该通道正常退料，等动作结束并冷却。不要为了更新已有安装而退空全部槽。
复制下面一块，等待下载、探测和恢复完成：
```powershell
$AceResult = Wait-AceResult (Read-U1Json 'python3 tools/ace_usb/wizard_backend.py prepare')
if ($AceResult.state -notin @('PREPARED','ALREADY_TARGET') -or -not $AceResult.ready -or -not $AceResult.service_restored) {
    throw 'STOP: ACE preparation did not pass. Read the state table before continuing.'
}
Confirm-AceMaterial $AceResult
```

- `ALREADY_TARGET`：**不要刷写**。确认来源确为指定 CFW 且 NFC 正常，再使用 A 块。不能确认则停止。
- `PREPARED`：确认显示 **`V1.3.856` / 引导 `V1.0.1` → `CV1.3.863`**，再执行下一块。
- 其他结果：停止。其他来源版本没有强制刷写的办法。

> [!CAUTION]
> **下一块会更新 ACE 固件。只运行一次。**
> **已校验的原厂 `1.3.863` 文件只是参考，不是你设备的备份。原厂回退未实机验证。**
> 接受此限制后才输入 `UPDATE`。保持电源和 USB 连接。不要重复命令，也不要在其他窗口操作设备。
```powershell
if ($AceResult.state -ne 'PREPARED' -or $AceResult.source_firmware -ne 'V1.3.856' -or
    $AceResult.boot_firmware -ne 'V1.0.1' -or $AceResult.target_firmware -ne 'CV1.3.863' -or
    $AceResult.operation -notmatch '^[a-f0-9]{32}$') { throw 'STOP: This update path is not prepared' }
if ((Read-Host '已读未实测原厂回退的限制，确认一次固件更新请输入 UPDATE') -cne 'UPDATE') { throw 'STOP: Update cancelled' }
$AceOperation = $AceResult.operation
$AceResult = Wait-AceResult (Read-U1Json ('python3 tools/ace_usb/wizard_backend.py start --operation ' + $AceOperation + ' --confirm-flash --accept-untested-rollback'))
if ($AceResult.state -ne 'SUCCEEDED' -or -not $AceResult.ready -or -not $AceResult.service_restored) {
    throw 'STOP: Update result is uncertain. Do not flash again or restart printing.'
}
Confirm-AceMaterial $AceResult
$AceFirmwareAccepted = $true
```

**完成标准：** `state: SUCCEEDED`、`ready: true`、`service_restored: true`。材料数据有变化时，对照料卷核对。
主机集成此时还没有安装。继续第 6 步。
如果断线或结果不明，按[恢复步骤](update-and-rollback.zh-CN.md#ace-interruption)操作。不要重跑更新块。

<a id="5-check-before-installation"></a>
## 6. 输入初值并检查安装计划

先看 [A/B/C 管路说明](configuration.zh-CN.md)。**A 是主退料距离，B 是快速送料距离，C 是退料后的消松回送距离。**

- **首次安装：** 输入根据自己四路实际管路核对过的 A、B 初值。所有槽共用这些参数，B 必须小于 A。这次核对不等于安装后的运动测试。
- **没有核对过的数值：** 没有核对过的管路测量或同布局记录时，停止。软件或 AI 不能猜出安全距离。
- **其他初值：** C 为 0。速度为快送 200、慢速寻料 50、退料 80。安装后先逐槽测试，再启用消松回送。
- **已有集成：** 本流程保留原参数，包括 C。不要求重新输入 A、B，也不会用模板覆盖原值。

首次安装要求 ACE 入口和打印头都无料。已有安装保持当前料位。机器必须空闲、冷却，烘干和送料辅助关闭。
代码块根据你的回答生成设置 JSON。**不用手工改 JSON 标点。**
```powershell
if (-not $AceFirmwareAccepted) { throw 'STOP: Complete the ACE firmware step first' }
$Status = Read-U1Json 'python3 installer.py status'
$Status | ConvertTo-Json -Depth 8 | Out-Host
if ($Status.existing_ace -isnot [bool]) { throw 'STOP: Invalid host status' }
$Settings = Get-Content -LiteralPath (Join-Path $TransferDir 'config/settings.example.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$Settings.apply_existing_settings = $false
$Settings.forward_takeup_length = 0
if (-not $Status.existing_ace) {
    if (@($Status.serial_candidates).Count -ne 1) { throw 'STOP: One unique ACE interface is required' }
    $A = 0; $B = 0
    if (-not [int]::TryParse((Read-Host '输入已核对的 A 退料初值（整数毫米，2 至 2499）'), [ref]$A) -or $A -lt 2 -or $A -gt 2499) { throw 'STOP: Invalid A' }
    if (-not [int]::TryParse((Read-Host '输入已核对的 B 快段初值（整数毫米，大于 0 且小于 A）'), [ref]$B) -or $B -lt 1 -or $B -ge $A) { throw 'STOP: Invalid B' }
    $Settings.feed_length = $A
    $Settings.retract_length = $A
    $Settings.fast_load_length = $B
}
if ((Read-Host '已核对四路路径及速度并同意安装后逐槽验证，输入 YES') -cne 'YES') { throw 'STOP: Settings review not accepted' }
$Settings.calibrated_acknowledged = $true
$SettingsPath = Join-Path $TransferDir 'config/settings.local.json'
[IO.File]::WriteAllText($SettingsPath, ($Settings | ConvertTo-Json -Depth 8), (New-Object System.Text.UTF8Encoding($false)))
scp.exe -O "$SettingsPath" "${PrinterTarget}:$RemoteDir/config/settings.local.json"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Settings upload failed' }
$Plan = Read-U1Json 'python3 installer.py check --settings config/settings.local.json'
if ($Plan.compatible -ne $true -or $Plan.read_only -ne $true -or $Plan.calibration_acknowledged -ne $true) {
    throw 'STOP: Host check did not pass'
}
$Plan.effective_settings | Format-List | Out-Host
```

**完成标准：** 没有 `STOP`，`effective_settings` 与你预期的数值一致。

- 首次安装前，`managed: false` 和 `ace_version: null` 是正常的。已有集成的参数必须与原配置一致。
- `filament_detection: external` 是安装计划；只读检查还没有应用它。
- 如果因未知的核心文件改动或不兼容版本被拒绝，保留原文件并停止。不要覆盖文件来绕过拒绝。

## 7. 安装一次并核对结果

核对摘要和机器状态后，复制下面一块。输入 `INSTALL` 确认一次安装。等待命令结束。不要重复命令：
```powershell
if (-not $AceFirmwareAccepted -or $Plan.compatible -ne $true) { throw 'STOP: Complete the checks first' }
if ((Read-Host '摘要正确、设备空闲冷却，确认安装一次请输入 INSTALL') -cne 'INSTALL') { throw 'STOP: Installation cancelled' }
$InstallResult = Read-U1Json 'python3 installer.py install --settings config/settings.local.json'
$InstallResult | ConvertTo-Json -Depth 8 | Out-Host
if ($InstallResult.installed -ne $true -or $InstallResult.ready_samples -lt 3) {
    throw 'STOP: Installation success is not confirmed'
}
Write-Host ('Backup: ' + $InstallResult.backup)
$FinalStatus = Read-U1Json 'python3 installer.py status'
$FinalStatus | ConvertTo-Json -Depth 8 | Out-Host
```

**完成标准：** `installed: true`、`ready_samples: 3`，最终状态 `klipper_state: ready`、`managed: true`、`filament_detection: external`。
`internal_rfid_enabled` 和 `openrfid_running` 都必须是 `false`。保存显示的 `Backup` 编号。
服务重启时短暂显示 Klipper disconnected 是正常的。确认成功后才开始测试。

## 8. 每次只测试一槽

1. 按[日常操作与验收](daily-use.zh-CN.md)对四个槽逐一操作：插入并等待短咬料和 NFC → U1 进料 → 退料 → 不重新插入，再次进料。
2. 核对品牌、类型和颜色。确认退料后材料信息保留。手离开滚筒。出现打滑、卡料或异常结果时停止。
3. 然后按[参数说明](configuration.zh-CN.md)校准 C。不要把 1250、1150、300 当作通用距离。
4. 所有槽通过之前，不要安排无人值守打印。

**失败或断线：** 使用[独立查询与恢复说明](update-and-rollback.zh-CN.md)。不要立即重复安装块。
本流程不证明全部 NFC 标签、ACE 内部校准或原厂回退已验证。见[验证范围](validation.md)。
