# 设计过程脚本

最终可编辑工程是上一级目录中的 KiCad 文件；`output/` 仅保留最终交付和检查结果。

`verify_design.py` 是核对入口：读取原理图导出的 `output/netlist.xml`、最终 PCB、ERC/DRC 报告，核对逐焊盘网络、封装、接地参考层、关键走线层和 USB 长度，并更新 QA/焊盘内孔清单。板框和天线净空尺寸从 PCB 几何读取，当前检查横放天线、20.0 × 29.0 mm 板框、20.0 × 3.8 mm 全层净空及末端铜箔的几何连续性。同时检查 Flash / TVS 在背面、两颗按键在正面，以及 USB 的换层数量和跨层路径连通性。晶振隔离检查还核对 8.5 mm 的项目本体间距目标、2.4 mm 的时钟引脚间距、各接地焊盘 1 mm 内的接地过孔，以及第二层填铜对晶振参考区和本体投影的完整覆盖。另检查排针在背面、编号从板头向下排列、2.00 mm 针距和 18.10 mm 列中心距。另核对两个 logo 图形组仅位于正确丝印层、旧天线文字已替换、图形距板边至少 0.25 mm。它不修改 PCB，也不验证射频性能。

`--board` 和 `--output-dir` 可用于隔离候选板的核对；对应目录需提供原理图网表及 ERC / DRC 报告。

器件字段核对逐项比较 PCB 与网表中的 Value、MPN、AssemblyNote、Datasheet 等原理图实例字段，包括空值；封装库自带的额外字段保留。DRC 必须启用 `--schematic-parity`，其结果也纳入 QA。仅检查走线的 DRC 报告不能代替原理图一致性检查。

封装核对覆盖全部 44 个电阻、电容：射频匹配的 C2、C3、C16、C17、C18、R6 为 0201，其余 38 个为 0402。定义与变更记录见 [POWER_PASSIVES.md](../POWER_PASSIVES.md)。

线宽核对覆盖全部走线和圆弧：信号固定 0.15 mm，非 GND 电源固定 0.20 mm，同时检查实际网络类及默认布线宽度。电源网络集合维护在 `build_pcb.py` 的 `POWER_NETS`，项目 `Power` 类与 `.kicad_dru` 应同步；GND 不参与固定线宽检查。QA 的 `track_width_policy` 保存各网络实际线宽和线段数量。

核对还包括正反面 SMD 阻焊开窗到孔边的 0.10 mm 间距，涵盖同网络及 DNP 焊盘；仅按固定位置保留 U1 的 9 个和 U3 的 2 个中心接地孔。工程的 `.kicad_dru` 使用 `physical_hole_clearance` 补上同网络孔距检查，独立 QA 再核对阻焊扩展与这 11 个工艺例外。规则语义见 [KiCad 10 自定义规则文档](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#custom-design-rules)。

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

2026-09-09 的 29 mm 布局迭代按用户要求跳过独立 QA，`output/qa.json` 记录 `not_run`。板框和净空检查尺寸已同步；历史 8.5 mm 天线/晶振目标仍保留，当前约 5.100 mm，不应将该版描述为 QA 通过。
