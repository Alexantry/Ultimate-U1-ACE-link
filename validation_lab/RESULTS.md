# VM software validation / 虚拟机软件验证

**The released v0.1.6 package passed 11 software checks in a disposable Linux VM.**
**已发布的 v0.1.6 安装包在一次性 Linux 虚拟机中通过 11 项软件检查。**

**This is not a physical U1 or ACE installation test.**
**这不是 U1 或 ACE 的实机安装验证。**

## Recorded run / 运行记录

- Date / 日期: 2026-10-30.
- [VM workflow and results / 虚拟机运行及结果](https://github.com/Alexantry/Ultimate-U1-ACE-link/actions/runs/41062760723).
- Tested lab commit / 测试代码提交: `7c04778cb8ed65552877f8e2a0519629442e4c88`.
- [Recorded result JSON / 保存的 JSON 结果](results/v0.1.6-linux-vm.json).
- [Separate offline checks / 独立离线检查](https://github.com/Alexantry/Ultimate-U1-ACE-link/actions/runs/41062760776): Python 3.11, Python 3.12, and Windows PowerShell 5.1 jobs passed.
- Package / 安装包: `Ultimate-U1-ACE-link-v0.1.6.zip`.
- SHA-256: `2c018540275022a9e821a19bbe78df622e34df6f9b2de07f675ab88150250bd3`.

The test extracts the published ZIP. It does not substitute an installer or change its payload.
All test connections stay inside the VM. No printer or ACE is connected.

测试直接解压已发布的 ZIP，不替换安装器，不改写安装内容。所有测试连接均在虚拟机内进行，没有连接打印机或 ACE。

## Passed checks / 已通过的检查

| Check | 检查内容 | Result / 结果 |
| --- | --- | --- |
| Package integrity and SSH | 安装包校验、真实 SSH 连接及主机密钥校验 | PASS / 通过 |
| English first installation | 英文向导首次安装，真实文件传输与写入 | PASS / 通过 |
| Manual parameter update | 通过真实命令行安装器修改 A/B/C 参数 | PASS / 通过 |
| Chinese update | 中文向导更新后保留 A/B/C 参数和送料代码 | PASS / 通过 |
| Busy-state refusal | 模拟打印中拒绝安装，文件和服务状态不变 | PASS / 通过 |
| Heater-state refusal | 模拟加热中拒绝安装，文件和服务状态不变 | PASS / 通过 |
| Concurrent-install refusal | 独立进程占用安装锁时，第二次安装被拒绝 | PASS / 通过 |
| Automatic recovery | 模拟服务启动失败后，自动恢复文件、安装记录和服务 | PASS / 通过 |
| Full rollback chain | 连续回退至安装前，核对原文件、权限和检测模式 | PASS / 通过 |
| Chinese reinstallation | 回退后使用中文向导重新安装 | PASS / 通过 |
| Package unchanged | 测试后原安装包内容未变，串口写入和 HTTP 写操作均为零 | PASS / 通过 |

A/B/C in this test are synthetic tube-layout values. Do not copy them to your printer.
本次测试的 A/B/C 为模拟管路参数，请勿照抄到打印机。

## What the VM proves / 虚拟机验证范围

The test uses real OpenSSH, SCP, Linux files, file permissions, locks, backups, and rollback.
It executes the released PowerShell wizard and Python installer.
Only the input answers and hardware responses are supplied by the lab.
The original RFID service scripts run in the guest.

The simulated service captures its configuration and module hashes only when it starts successfully.
The run recorded 8 successful loads and 18 start/stop actions, including one failed start.
Each install and rollback checks this service boundary. Disk writes alone cannot satisfy it.

测试使用真实 SSH、SCP、Linux 文件、权限、安装锁、备份和回退，执行已发布的 PowerShell 向导及 Python 安装器。
实验程序提供向导输入和模拟硬件状态；原版 RFID 服务脚本在虚拟机内实际执行。
模拟服务只在成功启动时读取配置和模块哈希。本轮记录了 8 次成功加载、18 次停启操作，其中包含一次故意注入的启动失败。
每次安装和回退均核对服务停启及加载结果，不能仅凭文件写入成功通过检查。

The RFID service check covers inactive readers, switching to External mode, and restoration.
It does not test a running physical reader. The zero-byte serial result applies to the KEEP path only.
RFID 服务检查覆盖读卡进程未运行时切换到 External 模式及回退，不代表真实读卡器运行验证。
串口零写入结果仅适用于本次保留既有 ACE 固件的路径。

## What still needs hardware / 仍需实机验证的项目

| Not tested by this VM | 此虚拟机未验证 |
| --- | --- |
| U1 firmware boot and screen update | U1 固件启动及触摸屏升级 |
| Real Klipper and MCU startup | 真实 Klipper 和控制板启动 |
| ACE firmware writing and USB timing | ACE 固件实际刷写及 USB 通信时序 |
| NFC tag reading and filament movement | NFC 实际读卡、上料、退料及消松 |
| Full Windows-to-printer interactive installation | Windows 到打印机的完整交互安装，包括密码及屏幕操作 |

The ACE step uses the branch for an already installed target firmware. It does not flash firmware.
The VM runs PowerShell on Linux. Separate Windows tests do not turn this into a Windows-to-printer test.

ACE 步骤选择“已安装指定固件”的路径，没有执行刷写。虚拟机内运行的是 Linux 版 PowerShell。
独立的 Windows 离线测试不能替代 Windows 到真实打印机的完整安装测试。

See [lab scope / 实验范围](README.md) and [fixture sources / 模拟环境与来源](FIXTURES.md).
