# 日常进料、退料与远程控制

[English](daily-use.md) · [管路校准](configuration.zh-CN.md) · [NFC](nfc.zh-CN.md)

## 你做什么，会发生什么

| 你做什么 | 会发生什么 |
| --- | --- |
| 把耗材插进空的 ACE 入口，手离开滚筒 | ACE 咬住耗材、读取 NFC 标签，然后停住等待，不会自动送到打印头。 |
| 在 U1 上检查材料详情 | 没有标签或读不出的料卷，请手动填写。 |
| 在 U1 上选择打印头，点正常的“进料” | ACE 先快速送料，再慢速送到打印头传感器检测到耗材为止，U1 完成热端上料。 |
| 对该打印头点正常的“退料” | U1 把耗材从热端退出，ACE 回抽，耗材头留在 ACE 及其后方料管内。 |
| 不拔出耗材，再次点进料 | 直接开始进料。只要 ACE 入口仍有耗材，材料信息就保留。 |

- 每个动作完成后再发下一个指令。
- 重启后或位置不确定时，可能全程使用较慢速度。

> [!IMPORTANT]
> **新安装默认关闭回送消松，校准后才能启用。**
> 它把耗材朝 U1 方向送回一段，消除松圈。它没有张力传感器，也不会单独驱动滚筒。

实测示例是以 80 mm/s 回抽 1250 mm，再以 50 mm/s 回送 300 mm。
这不是通用距离，见[管路校准](configuration.zh-CN.md)。

## 远程操作

**远程屏幕。** 开启 **Firmware Config → Web → Remote Screen Access**，再打开这台打印机的 `/screen/` 页面，像在实体屏幕上一样点进料或退料。
安装器不会自动开启它。见 [v24 远程屏幕说明](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/remote_screen.md)。

**网页控制台。** 以第 1 槽为例，只发送下面**一个**指令，并按打印机提示操作。第 2、3、4 槽分别用 `EXTRUDER=1`、`2`、`3`。

进料：

```gcode
AUTO_FEEDING EXTRUDER=0 LOAD=1
```

退料：

```gcode
AUTO_FEEDING EXTRUDER=0 UNLOAD=1
```

- 不要同时发送进料和退料指令。
- 不要用 `ACE_FEED` 或 `ACE_RETRACT` 代替。它们只移动耗材，不执行热端流程。
- 可选的 [AFC 面板](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/afc-lite.md)需要另外开启 AFC Stub 设置，本项目安装后默认不提供。
