# 日常进料、退料与远程控制

[English](daily-use.md) · [管路校准](configuration.zh-CN.md) · [NFC](nfc.zh-CN.md)

## 插入耗材

1. 把耗材插进一个空的 ACE 入口。
2. 手离开滚筒。
3. 等待短咬料、预进料和 NFC 识别结束。
4. 在 U1 检查材料详情；无芯片或读不出的料卷请手动填写。

结束后耗材停在 ACE 附近，不会因为插入就自动长送到挤出头。
识别动作由 ACE 固件控制，本项目不承诺所有标签使用同一个固定短进料长度。

## 送到挤出头

1. 在 U1 屏幕选择对应打印头。
2. 点正常“进料”。
3. 按屏幕提示等待完整动作结束，不重复点击。

起点已知时，ACE 先快速送设定距离，再慢速寻找头端传感器。
传感器到料后结束 ACE 的输送阶段，U1 继续完成热端上料流程。
重启后或起点不确定时，可能全程使用较慢速度。

## 退料和消除松圈

1. 在对应打印头执行正常“退料”。
2. 等待 U1 先从热端退出材料。
3. 等待 ACE 回抽设定距离。
4. 如果启用了回送消松，再等待这段动作完成。
5. 确认耗材仍留在 ACE 及后方管路内。

只要入口仍有耗材，材料信息就保留。下次直接点进料，无需为了重新识别而拔插。

> [!IMPORTANT]
> **新装默认关闭回送消松；必须校准后启用。**
> 其原理是把耗材朝 U1 方向送回一段，吸收料盘附近的松圈；不是滚筒独立补转，也没有张力传感器。

实测示例是退料 `1250 mm / 80 mm/s`，再回送 `300 mm / 50 mm/s`。
这不是适合所有料管的通用参数，调整方法见[管路校准](configuration.zh-CN.md)。

## 在电脑上远程操作

最直观的方式是使用 U1 的可选远程屏幕。
在 **Firmware Config → Web → Remote Screen Access** 开启后，打开这台打印机的 `/screen/` 页面。
按与实体屏幕相同的方式点进料或退料。
本项目安装器不会自动开启远程屏幕，设置依据见[固定 v24 远程屏幕说明](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/remote_screen.md)。

也可以通过网页控制台调用完整的 U1 原生流程。
例如第 1 槽，单独发送以下一个指令，并按打印机提示操作。

进料：

```gcode
AUTO_FEEDING EXTRUDER=0 LOAD=1
```

退料：

```gcode
AUTO_FEEDING EXTRUDER=0 UNLOAD=1
```

| ACE 槽号 | `EXTRUDER` 填写 |
| --- | --- |
| 1 | 0 |
| 2 | 1 |
| 3 | 2 |
| 4 | 3 |

不要把两个指令一起发送。不要用底层 `ACE_FEED` 或 `ACE_RETRACT` 代替完整热端进退料流程。
可选 [AFC 耗材面板](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/afc-lite.md)需要另开 AFC Stub，本项目不保证任何默认网页都有它。
