# 手动安装：逐块复制命令

[English](installation.md) · [双语安装向导](quick-start.zh-CN.md) · [故障与恢复](update-and-rollback.zh-CN.md)

此方法不运行 Windows 安装向导，但会在 U1 上运行可阅读的 `installer.py` 和 ACE 维护程序。
你不需要编程、电脑端 Python、AI 助手或 NFC 密钥。需要会复制整块文字、按提示输入数字，并核对设备屏幕。
如果不想复制命令，请使用 `START-HERE.cmd`。

> [!CAUTION]
> **不要把旧 SnapAce 的 `filament_feed.py` 或 `extruder.py` 覆盖到 U1 2.0。**
> **只使用 SnapAce 的硬件接线说明。不要混用不同版本的安装器、manifest 和 payload。**

本文针对当前完整安装包。旧包请使用[其对应版本说明](install-options.md)，不要照本文混装。
中文离线手册是 `MANUAL-INSTALL.zh-CN.html`，英文版是 `MANUAL-INSTALL.html`。

## 1. 先准备机器，再打开命令窗口

1. 结束打印和所有进退料动作。关闭加热、烘干，等喷头和热床实际温度均低于 **50 °C**。
2. 首次安装时，按设备正常操作把四路耗材从打印头及 ACE 入口取出。退料可能重新加热；结束后再次关闭加热、烘干，等待实际温度低于 50 °C。已有本项目的用户更新时保留现有料位，不要求全部退空。
3. 按 [U1 固件和访问设置](u1-preparation.zh-CN.md)安装 **`2.0.0-paxx12-24`**，开启 **Advanced Mode**，将 **Root Access** 设为 **Open**。
4. **关闭 ACE 和 U1，并断开两台设备的电源。** 按 [SnapAce 硬件指南](https://github.com/BlackFrogKok/SnapAce#pinout-and-wiring)完成 **ACE Pro 第一代**的连接线及四根对应槽位的 PTFE 管。
5. 接线完成后开启设备，恢复同一局域网连接，记录 U1 Wi-Fi 页的当前 IP。
6. 保持电源和 USB 稳定。后文先上传公共程序，再由 U1 检查 ACE 固件；**不需要预先完成另一套 ACE 刷机教程**。

U1 版本、访问开关、ACE 代际或接线不符合要求时，先停止。本文不支持 ACE 2 Pro。
安装器会自动设置 **External**、保存原文件并核对服务状态。无需先手改读卡设置，也无需设置 U1 OpenRFID 密钥。
受支持的 NFC 格式由 [OpenCubic](https://github.com/Jupsi/OpenCubic)提供；本项目负责同步到 U1，详见 [支持表](nfc.zh-CN.md)。

<a id="prepare-windows-powershell"></a>
## 2. 下载、解压并打开 PowerShell

1. 从[当前安装包入口](../README.zh-CN.md)下载完整 ZIP。不要下载单个 `.py` 文件。
2. 右键 ZIP，选择“全部解压缩”。打开包含 `installer.py` 的 `Ultimate-U1-ACE-link` 文件夹。
3. 在文件资源管理器地址栏单击，复制该文件夹的完整路径，稍后粘贴。
4. 点击 Windows“开始”，搜索 **Windows PowerShell**，打开普通窗口；不需要“以管理员身份运行”。
5. 以下代码块全部粘贴到这个 **Windows PowerShell** 窗口。每次复制一整块，按回车，等完成再继续。不要复制三条反引号。
6. 如果出现红色 `STOP` 或报错，**停止后面的步骤**。读对应说明；不要因为没有成功就重发刷写或安装命令。

建议核对 ZIP：在 PowerShell 输入 `Get-FileHash -LiteralPath '你的ZIP完整路径' -Algorithm SHA256`，与 [SHA256SUMS](../downloads/SHA256SUMS)中同名 ZIP 的值对比。路径外的单引号保留；如果不一致，停止并重新下载完整包。
你可以用记事本查看源码；无需修改它们。将私人备份放在项目文件夹之外。

复制下面整块。窗口询问路径时粘贴刚才复制的文件夹路径，再按回车：
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

**完成标准：** 显示当前包版本，没有 `STOP`。四个核心文件的校验值已与 manifest 比较。

<a id="set-connection-variables"></a>
<a id="confirm-the-connection"></a>
## 3. 建立连接

电脑需要 Windows 自带的 **OpenSSH 客户端**。若下面提示找不到 `ssh.exe` 或 `scp.exe`，打开 Windows“可选功能”→“查看功能/添加功能”→搜索 OpenSSH →安装 **OpenSSH 客户端**，然后重新打开 PowerShell，从第 2 步开始。不要安装 OpenSSH 服务器。

复制下面整块。只输入屏幕上的数字 IP，例如 `192.0.2.10`，不要加 `http://`、端口或网页路径。示例不是你的打印机地址。
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
第一次连接可能显示 `Are you sure you want to continue connecting`。这是首次信任该设备，不代表本步骤已独立校验指纹。仅在可信本地网络上，并确认 IP 与 U1 屏幕一致后输入 `yes`，按回车。
若显示原有主机密钥发生变化，停止并核对设备身份，不要删除提示来绕过检查。
密码输入时不显示字符或星号，这是正常现象。原厂 root 密码见 [上游 SSH 说明](https://snapmakeru1-extended-firmware.pages.dev/ssh_access)；修改过密码则用自己的密码。不要把密码写进命令或配置文件。

<a id="4-transfer-the-project"></a>
## 4. 只上传需要的公共文件

以下代码从本包复制固定文件到临时文件夹，再上传到 U1 的唯一新目录。不会把整个工作文件夹里的备份或 `.git` 目录上传。
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

**完成标准：** 打印三个远程文件路径，没有报错。
把显示的 **Printer** 和 **RemoteDir** 两行复制到你自己的私人笔记。断线或关窗后恢复需要它们。
**保持这个 PowerShell 窗口打开。** 后续命令使用本窗口的变量。若已经关窗，先按[独立恢复入口](update-and-rollback.zh-CN.md#read-installation-status)查询原结果，不要重新上传后猜测上次是否成功。

<a id="ace-firmware"></a>
## 5. 检查或准备 ACE 固件

本节使用与双语向导相同的受控后台，**不需要编辑设备 profile、NFC 密钥或刷机 JSON**。
ACE 固件文件由 U1 从固定上游下载并校验；U1 必须能访问 GitHub。安装包不包含固件二进制。
检查会暂时停止并恢复 Klipper。程序不发送进退料命令，但设备初始化可能触发自身动作，手要离开滚筒。

先复制下面整块。这只定义后续操作并查询上次 ACE 事务；正在运行的事务只继续查询，不重复刷写：
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
| `NONE` | 没有历史事务，按下面 A 或 B 选择。 |
| `SUCCEEDED`、`PREPARED`、`ALREADY_TARGET`、`CANCELLED_SAFE` | 仍按 A 或 B 核对当前固件；旧成功记录不能单独证明当前 ACE 身份。 |
| `FAILED_SAFE` | 检查网络、冷却和设备状态；选择 B 重新准备，不跳过检查。 |
| `UNSUPPORTED` | 来源版本不受支持，停止；不要改检测记录或强刷。 |
| `NEEDS_ATTENTION`、`ERROR`，或查询失败 | 停止安装，按[ACE 中断处理](update-and-rollback.zh-CN.md#ace-interruption)。 |

若显示材料变化，`field` 是项目名，`before` 是变化前，`after` 是变化后。字段尾号 `_0`、`_1`、`_2`、`_3` 对应第 1、2、3、4 槽；四项数组也按此槽位顺序。只在新数据与实际料卷一致时输入 `YES`。无材料变化时不会要求此确认。

### A. 已知安装了指定固件，而且 NFC 已正常工作

仅当你能确认这台 ACE 运行 **OpenCubic CFW 1.1.1 / `CV1.3.863`** 时，运行下面一块，然后转到第 6 步。
只看见 `CV1.3.863` 字符串不够；不同社区修改版可能显示相同版本。不确定时选 B。
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

### B. 不知道当前固件，或需要准备指定版本

先确认机器空闲、所有加热目标为零、实际温度低于 50 °C、烘干关闭、无 NFC/进退料动作。
已有集成若送料辅助仍开启，可在 U1 对相应槽正常退料，等动作结束后重新冷却。不要为了更新而退空全部槽。
复制下面一块，等待下载、探测和恢复完成：
```powershell
$AceResult = Wait-AceResult (Read-U1Json 'python3 tools/ace_usb/wizard_backend.py prepare')
if ($AceResult.state -notin @('PREPARED','ALREADY_TARGET') -or -not $AceResult.ready -or -not $AceResult.service_restored) {
    throw 'STOP: ACE preparation did not pass. Read the state table before continuing.'
}
Confirm-AceMaterial $AceResult
```

如果得到 `ALREADY_TARGET`，**不要刷写**。确认来源确为指定 CFW 且 NFC 已正常工作，再使用上面的 A 块；不能确认则停止。
如果得到 `PREPARED`，确认显示 **`V1.3.856` / 引导 `V1.0.1` → `CV1.3.863`**，再执行下一块。
其他情况停止。不同源版本不能强制套用这个流程。

> [!CAUTION]
> **下一块会更新 ACE 固件。只运行一次。**
> **原厂 `1.3.863` 文件只是已校验的参考，不是你设备的备份；原厂回退未实机验证。**
> 接受此限制后输入 `UPDATE`。期间不要断电、拔 USB、重发命令或在其它窗口操作设备。
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

**完成标准：** `state: SUCCEEDED`、`ready: true`、`service_restored: true`；如材料有变化，已对照料卷确认。
固件更新成功不等于主机集成已经安装；继续第 6 步。
如果断线或结果不明，先看[恢复步骤](update-and-rollback.zh-CN.md#ace-interruption)，不要重跑上面的更新块。

<a id="5-check-before-installation"></a>
## 6. 输入初值，生成设置并检查

先核对 [A/B/C 管路说明](configuration.zh-CN.md)。**A 是主退料距离，B 是快速送料距离，C 是退料后回送距离。**
首次安装输入根据自己四路路径核对过的 A、B 初值；并非声称已经完成安装后的运动测试。所有槽共用这些参数，B 必须小于 A。
若没有可核对的管路测量或同布局记录，先停止，不能用软件或 AI 猜一个安全值。
首次安装 C 固定为 0，速度为快送 200、慢速寻料 50、退料 80。稍后逐槽实测，再按参数说明启用消松。
已有集成会保留原参数，包括 C；无需重复输入 A、B，下面的模板不会覆盖原值。

首装必须四个 ACE 入口及四个打印头都无料。已有集成保持当前料位。机器必须空闲、冷却、烘干与送料辅助关闭。
以下代码根据你的回答生成 JSON，**不用手工改逗号或配置项**：
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

**完成标准：** 没有 `STOP`；显示 `effective_settings` 的参数与预期相符。
初次主机状态里 `managed: false`、`ace_version: null` 可以正常。已有集成的有效参数应与旧设置一致。
`filament_detection: external` 是安装计划，不代表只读检查已改好设置。
如果拒绝未知核心文件改动或不兼容版本，保留原文件，停止。不要覆盖文件来绕过检查。

## 7. 安装一次并核对结果

确认摘要与机器状态后复制下面一块；确认时输入 `INSTALL`。之后等到命令结束，不重复输入：
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
最终 `internal_rfid_enabled`、`openrfid_running` 均应为 `false`。保存显示的 `Backup` 编号。
软件服务重启时短暂显示 Klipper disconnected 是正常的；只有明确报告成功后才开始测试。

## 8. 每次只测试一槽

按[日常操作与验收](daily-use.zh-CN.md)对四个槽逐一完成：插入短咬料与 NFC → U1 进料 → 退料 → 不拔插再进料。
核对类型、颜色和品牌，确认退料后材料信息保留。手离开滚筒，有打滑、卡料或异常立即停止。
再按[参数说明](configuration.zh-CN.md)校准 C；不要把 1250、1150、300 直接当作所有机器的通用数值。
完成各槽验证前，不安排无人值守打印。

**中途失败或断线：** 使用[独立查询与恢复说明](update-and-rollback.zh-CN.md)，不要直接再次执行安装块。
本流程不证明全部 NFC 标签、ACE 内部校准或固件原厂回退已验证。见[验证范围](validation.md)。
