# 设计过程脚本

最终可编辑工程是上一级目录中的 KiCad 文件；`output/` 仅保留最终交付和检查结果。

`verify_design.py` 是核对入口：读取原理图导出的 `output/netlist.xml`、最终 PCB、ERC/DRC 报告，核对逐焊盘网络、封装、接地参考层、关键走线层和 USB 长度，并更新 QA/焊盘内孔清单。板框和天线净空尺寸从 PCB 几何读取，当前检查横放天线、20.0 × 29.0 mm 板框、20.0 × 3.8 mm 全层净空及末端铜箔的几何连续性。同时检查 Flash / TVS 在背面、两颗按键在正面，以及 USB 的换层数量和跨层路径连通性。晶振隔离检查还核对 8.5 mm 的项目本体间距目标、2.4 mm 的时钟引脚间距、各接地焊盘 1 mm 内的接地过孔，以及第二层填铜对晶振参考区和本体投影的完整覆盖。另检查排针在背面、编号从板头向下排列、2.00 mm 针距和 17.50 mm 列中心距，并核对排针标称 2.00 mm 宽塑料座及焊盘铜外缘距侧边分别至少 0.25 mm、0.575 mm。另核对两个 logo 图形组仅位于正确丝印层、旧天线文字已替换、图形距板边至少 0.25 mm。它不修改 PCB，也不验证射频性能。

`--board` 和 `--output-dir` 可用于隔离候选板的核对；对应目录需提供原理图网表及 ERC / DRC 报告。

2026-09-09 L2 迁移后，QA 增加背面安装、C11 保持正面及 V3A 到 U1.2/U1.3/C11/C19/C20 的跨层连通性检查。`rf_supply_filter` 记录输出路径和换层数量；长度按铜线中心线加标称过孔贯穿长度估算，不代表寄生参数或射频性能验证。本轮输入重新检查为 45/51，迁移后为 46/52，六项既有失败不变；DRC、未连接和原理图一致性均为 0。范围与备份见 [L2 迁移记录](../output/l2-back-migration.json)。

器件字段核对逐项比较 PCB 与网表中的 Value、MPN、AssemblyNote、Datasheet 等原理图实例字段，包括空值；封装库自带的额外字段保留。DRC 必须启用 `--schematic-parity`，其结果也纳入 QA。仅检查走线的 DRC 报告不能代替原理图一致性检查。

封装核对覆盖全部 45 个电阻、电容：射频匹配的 C2、C3、C16、C17、C18、R6 为 0201，其余 39 个为 0402。晶振串联器件按模组图由原 L4 更正为 R18 = 0 Ω；QA 同时核对其电阻符号、数值、装配状态及 U1.39 / Y1.1 / C4.1 的连接。定义与变更记录见 [POWER_PASSIVES.md](../POWER_PASSIVES.md)。

线宽核对覆盖全部走线和圆弧：信号固定 0.15 mm，非 GND 电源固定 0.20 mm，同时检查实际网络类及默认布线宽度。电源网络集合维护在 `build_pcb.py` 的 `POWER_NETS`，项目 `Power` 类与 `.kicad_dru` 应同步；GND 不参与固定线宽检查。QA 的 `track_width_policy` 保存各网络实际线宽和线段数量。

核对还包括正反面 SMD 阻焊开窗到孔边的 0.10 mm 间距，涵盖同网络及 DNP 焊盘；仅按固定位置允许 U1 的 9 个中心接地孔；SOIC-8 U3 无中心焊盘。工程的 `.kicad_dru` 使用 `physical_hole_clearance` 补上同网络孔距检查，独立 QA 再核对阻焊扩展与这 9 个 MCU 工艺例外。规则语义见 [KiCad 10 自定义规则文档](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#custom-design-rules)。

其他脚本保留布局生成、扇出、局部布线和视图生成过程，部分会重建或修改 PCB。设计中间文件已归档到本地 `tmp/routing-history/`，不纳入 Git 仓库；历史脚本里的中间文件路径不代表可直接执行的一键重建流程。修改最终工程请优先使用 KiCad，并先备份。

`tune_usb.py` 已停用，执行时仅提示退出。当前 USB Full-Speed 主干采用短而平行的直线，不为几毫米的长度差添加蛇形补偿。

`add_vippo.py` 同样已停用，避免再次将过孔插入外围 QFN 焊盘。历史布局/布线脚本不能无损重建当前的局部扇出；使用它们生成候选板后仍需完整运行 DRC 和独立 QA。

本机验证命令（Debian，KiCad Flatpak；在仓库根目录执行）：

```sh
flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --schematic-parity --format json --exit-code-violations -o output/drc-final.json esp32-c6-pico.kicad_pcb
flatpak run --command=python3 org.kicad.KiCad tools/verify_design.py
```

Windows 验证示例（PowerShell）：

```powershell
& 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe' sch export netlist --format kicadxml -o output/netlist.xml esp32-c6-pico.kicad_sch
& 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe' sch erc --format json --exit-code-violations -o output/erc.json esp32-c6-pico.kicad_sch
& 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe' pcb drc --schematic-parity --format json --exit-code-violations -o output/drc-final.json esp32-c6-pico.kicad_pcb
& 'C:\Program Files\KiCad\10.0\bin\python.exe' tools\verify_design.py
```

`redraw_schematic.py` 从当前设计清单和内嵌符号重画两页原理图，不生成 PCB。使用前备份，之后重新导出网表、ERC 并同步 PCB 符号路径。它使用仓库内两份标准电源符号，来源见 `libs/README.md`。原 `build_schematic.py` 历史生成入口已停用。

`verify_schematic_wiring.py` 独立读取主原理图的实线与引脚位置，不把标签或电源别名当作连线，核对 U1 的关键外围可以沿线追踪。该检查与原理图/PCB 符号路径核对均已纳入 `verify_design.py`。

2026-09-09 的 29 mm 布局迭代曾跳过独立 QA。此后的晶振串联电阻修正已重新运行 QA，该次检查为 43/48 通过，保留五项已有失败条件。历史 8.5 mm 天线/晶振目标仍保留，该轮约 5.100 mm；不得将该版描述为 QA 全部通过。详情见 [外围电路复核](../docs/ESP32_C6_SCHEMATIC_REVIEW.md)。

2026-09-09 排针内移后，列中心距检查改为 17.50 mm，并新增塑料座与焊盘距侧边的检查。当前 `output/qa.json` 为 **44/49 通过**，DRC、未连接和原理图一致性均为 0。由于旧报告的 PCB 哈希与输入文件不符，已重新检查修改前备份：43/48，五项失败条件与当前相同。当前既有失败项是 MCU 接地孔数量、天线匹配器件共轴、天线/晶振间距、晶振接地过孔距离和 11 个散热孔清单；不可沿用历史报告中的两项孔距违规。详细范围及备份路径见 [排针内移记录](../output/headers-inward.json)。

2026-09-09 Flash / 二极管封装替换：当前 QA **45/51**，重新建立的输入基线为 43/49；保留六项既有失败（含一颗普通过孔未显式双面盖油）。新增 SOIC-8 的八引脚/无 EPAD 核对及 BAT760-7 封装与极性核对；U1 九孔要求保持，当前实有七孔。ERC、DRC、未连接及原理图一致性均为 0。`redraw_schematic.py` 已移除 U3.9 的生成逻辑；修改该脚本没有重建最终原理图或 PCB。随后按用户要求删除 F1，USB 电源直接接 D5 阳极，移除 `VBUS_FUSED` 的网表和网络类配置；64 个器件位、58 个默认装配，QA 仍为 45/51。核对包含 F1 确实删除和 D5 的 USB 输入连接。当前证据见 [封装替换记录](../output/package-changes.json)。
