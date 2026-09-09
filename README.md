# ESP32-C6 Pico · Rev A

已完成 **20.0 × 29.0 mm、四层、标称 0.8 mm** 的 PCB 布局布线。使用 ESP32-C6 QFN40、4 MB 外置 Flash、横向 RFANT5220110A0T 陶瓷天线和 USB-C 原生 USB Serial/JTAG。本轮将板宽缩至 20 mm，沿用右侧天线和左侧 Codex 图标布局；继续跳过独立 QA，最终 DRC 仍有两项原有孔距违规。

天线本体在板头右侧横向放置，末端铜箔向左展开、保持开路；板头全层不铺铜区域为 **20.0 × 3.8 mm**。AE1 馈电焊盘与 R6 对齐，正面馈线直接向下连接，不再从匹配网络折返向左。Codex 图标移至左侧；Flash U3、USB TVS D4 和排针位于背面，两颗按键位于正面。

六颗 Flash 串联电阻 R17、R1–R5 已改为 0402，在背面排成一行，中心间距 1.20 mm。Flash U3 与 TVS D4 各向 USB 方向移动 0.80 mm，为焊盘外过孔和这排电阻留出空间；板框不变。C7 在主控 VDD_SPI 扇出旁的正面，C13 位于 3.3V 供电脚附近，保留短去耦连接。RGB 缓冲器 U4 与串阻 R15 按新的焊接间距微调。排针功能标注统一保留在背面，正面左侧的重复标注已清除。

2026-09-09：在天线右移后的 20.5 × 29 mm 版上，将左右板边各收窄 **0.25 mm**，当前板框为 **20 × 29 mm**，面积从 594.5 mm² 降至 **580.0 mm²（减少约 2.44%）**。两列排针位置与 18.10 mm 列间距保持不动，焊盘外缘距两侧板边均为 **0.275 mm**，满足当前 0.25 mm 规则。器件、过孔及走线几何保持输入版本。贴装坐标原点同步更新到新板框左下角 (99.00, 137.50) mm。

天线与晶振名义本体边缘最近距离约 **5.100 mm**，低于历史 8.5 mm 项目几何目标。延续用户要求跳过独立 QA；该历史门槛保持不变。射频和晶振信号仍在正面且不换层，晶振规则区保留；3.8 mm 净空及右侧天线布局尚需实板射频验证。

正面天线旁原 `2.4 GHz` / `NO COPPER` 丝印替换为 **Codex 图标**；背面加入用户个人 logo 的单色人物图形，并将 `REV A` 移到旁边。两个 logo 都是可编辑丝印图形组，背面按正常观看方向镜像放置。原图、SVG、来源和尺寸记录见 [docs/logo/README.md](docs/logo/README.md)。

直接用 KiCad 10 打开 `esp32-c6-pico.kicad_pro`。如编辑器仍显示修改前的内容，请关闭旧窗口并重新打开磁盘文件，避免旧窗口覆盖新文件。

当前封装约定：**射频匹配的 6 个电阻/电容保持 0201，其余全部 38 个电阻/电容统一 0402**，包括 C19、C20、C23 等大容量电源电容及 Flash 串阻。容量、阻值、网络和 DNP 状态保持不变。大容量电源电容保留最低 10V 额定耐压要求，实际料号与偏压下的有效容量仍需核对。变更清单见 [POWER_PASSIVES.md](POWER_PASSIVES.md) 和 [全部阻容封装表](output/passive-packages.csv)。

主原理图已把 ESP32-C6 的供电去耦、上电复位、BOOT、晶振、Flash、USB 串阻、UART 与 RGB 驱动沿芯片引脚用实线连接。电源输入、USB 接口与排针位于第二页。逐引脚网表与重排前一致。

此前尝试了 **18 × 30 mm**：目标尺寸的器件摆放可以容纳，但布线候选仍有 18 处未连接，该轮主工程保留了 20.5 × 32.5 mm，后续从板头收短到 32.0 mm。此前候选、剩余问题和原始检查结果见 [SHRINK_TRIAL.md](SHRINK_TRIAL.md)。

## 已完成的电路

- USB-C 正反插数据连接、CC1/CC2 独立 5.1 kΩ 下拉、USBLC6-2SC6 静电保护、22 Ω 串联电阻及选装 EMI 电容。
- AP2112K-3.3 稳压、输入保护、肖特基防反灌、主电源及各供电脚的去耦；RF 电源使用独立 LC 滤波。
- CHIP_EN 的 10 kΩ / 1 µF 上电延时，RESET、BOOT 按键，GPIO8/9 上拉与 UART0 备用下载接口。
- W25Q32JVZPIQ 外置 Flash，真正接通 VDD_SPI；40 MHz / 8 pF 晶振，两个外壳脚接地，并保留负载调试与串联电感。
- 芯片端 CLCCL 射频网络、天线端 π 网络、低电容 ESD 选装位，以及陶瓷天线开路端调谐铜箔。
- WS2812B-2020 RGB 灯及 SN74LV1T125 电平转换，GPIO21 驱动。

## 检查与交付文件

2026-09-09 使用 KiCad 10.0.4 重新填铜并检查：**ERC 0 项；原理图一致性 0 项；未连接 0 项；DRC 2 项，均为输入版本已有的 C12、C21 接地焊盘与 U1 散热过孔重叠**。本轮没有新增 DRC 违规。独立 QA 按用户要求未运行；`output/qa.json` 明确记录 `not_run`，不沿用旧版通过数量。最新报告见 `output/drc-final.json`、`output/erc.json` 和 `output/layout-20x29mm.json`。

原先 65 项一致性报错来自 PCB 器件字段缺失。现已按原理图为 65 个器件同步 141 处字段，包括 MPN、AssemblyNote 和 Datasheet；新增字段隐藏显示，保留封装库自带的额外字段。原理图、网络连接、封装、器件值和 DNP 状态保持不变。已重新填铜，并在重新加载磁盘 PCB 后启用 `--schematic-parity` 验证为 0 项；QA 新增逐字段比较与一致性报告检查，后续 DRC 命令也必须带此参数。

USB 保持简洁路径，没有加入蛇形等长补偿。两根线在按键上方换到底层，经过靠近连接器的 TVS，再换回正面连接 USB-C 焊盘。接受自然扇出带来的少量长度差；QA 长度统计区分铜层，并计入标称过孔贯穿长度。

全板信号走线统一为 **0.15 mm**（含 USB、射频、晶振及芯片扇出），非 GND 电源走线统一为 **0.20 mm**；GND 保留原有线宽。`Power` 网络类覆盖 `+3V3`、`+5V`、`V3A`、`VBUS_FUSED`、`VBUS_USB`、`VDD_SPI`，其他信号使用 `Default`。自定义规则同时限制最小和最大线宽，独立 QA 核对每段走线与实际网络类；相关局部路径已按新宽度调整。线宽统一不代表阻抗或载流能力已经实测达标。

外围焊盘内的过孔已改为焊盘外短线扇出，并检查正反面的阻焊开窗；孔边间距至少 0.10 mm。仅保留 U1 中心接地焊盘 9 个、U3 中心接地焊盘 2 个填孔盖铜过孔。为腾出局部扇出空间，调整了 C7、C11、C27、R2、R3、R7、R16，其中 R16 改到正面。

| 文件 | 用途 |
| --- | --- |
| `esp32-c6-pico.kicad_sch` / `power-io.kicad_sch` | 两张可编辑原理图 |
| `esp32-c6-pico.kicad_pcb` | 已布线 PCB，含叠层和禁布区 |
| `esp32-c6-pico.kicad_dru` | 固定线宽、焊盘孔距与晶振下方的非接地过孔禁布规则 |
| `output/pcb-front.svg` / `pcb-back.svg` | 正反面布线预览 |
| `output/width-20mm-comparison.png` / `.svg` | 本轮 20.5 → 20.0 mm 板宽对比 |
| `output/antenna-right-29mm-comparison.png` / `.svg` | 历史 28 → 29 mm 与天线右移对比 |
| `output/antenna-28mm-comparison.png` / `.svg` | 历史 32 → 28 mm 压缩对比 |
| `output/antenna-layout-comparison.png` / `.svg` | 此前天线末端铜箔调整的历史对比 |
| `output/usb-routing-comparison.png` / `.svg` | 此前删除 USB 蛇形的历史局部对比 |
| `output/layout-repack-comparison.png` / `.svg` | 此前换面布局及缩短板框的历史对比 |
| `output/crystal-isolation-comparison.png` / `.svg` | 此前天线前移并加长板框的历史对比 |
| `output/crystal-down-headers-comparison.png` / `.svg` | 此前晶振下移、排针换面与尺寸调整对比 |
| `output/board-3d-top.png` / `board-3d-bottom.png` | 含最新 logo 的正反面 3D 布局预览 |
| `docs/logo/` | 个人原图、两面丝印 SVG、图形来源和放置参数 |
| `output/assembly-front.svg` / `assembly-back.svg` | 带位号的装配视图 |
| `POWER_PASSIVES.md` / `output/power-passives.csv` | 当前 0402 约定、封装变更记录和选料说明 |
| `output/passive-packages.csv` | 全部 44 个电阻/电容及 11 个实际封装变化 |
| `output/bom.csv` | BOM；`Populate=NO` 表示不装 |
| `output/placement.csv` | 双面贴装坐标，已排除 DNP；坐标原点为板左下角 |
| `output/via-in-pad.csv` | 保留的 11 个散热焊盘内孔，须填孔盖铜 |
| `FABRICATION.md` | 必须确认的工艺、阻抗与样板验证项目 |

板上共 65 个器件位，默认装配 59 个。默认不装 D1、L3、C17、C18、C27、C28。3D 图为布局示意，部分标准库封装缺少 3D 模型；器件是否装配以 BOM 和二维装配图为准。

## 接口与下载

**从正面看**，USB 朝下、天线朝上时，J2 在左、J3 在右，两列 1 脚均靠近天线；从背面观察时左右对调，编号不倒序。排针塑料座和长针在背面，正面为焊接端。针距为 **2.00 mm**，两列中心距为 **18.10 mm**；这些尺寸不能按 2.54 mm 面包板间距处理。

| 脚号 | J2（左列） | J3（右列） |
| --- | --- | --- |
| 1 | GND | 5V 输出* |
| 2 | 3V3 输出 | GND |
| 3 | GPIO0 | GPIO10 |
| 4 | GPIO1 | GPIO11 |
| 5 | GPIO2 | GPIO15 |
| 6 | GPIO3 | UART0 TX / GPIO16 |
| 7 | GPIO4 | UART0 RX / GPIO17 |
| 8 | GPIO5 | GPIO18 |
| 9 | GPIO6 | GPIO19 |
| 10 | GPIO7 | GPIO20 |
| 11 | GPIO8 | GPIO22 |
| 12 | GPIO9 / BOOT | GPIO23 |

*5V 引脚实际电压等于 USB 电压扣除 F1 和 D5 压降，不是精密 5.00 V。F1 保护稳压器和 5V 引脚支路；RGB 灯和电平转换器接 USB 原始电源。3V3/5V 引脚按电源输出使用，不要在连接 USB 时再向这些引脚注入外部电源。所有 GPIO 为 3.3 V 逻辑。

USB 下载使用芯片内置 USB Serial/JTAG（GPIO12=D-，GPIO13=D+）。需要手动进入下载模式时：按住 BOOT，点按 RESET，再松开 BOOT。UART0 备用下载时，使用 3.3 V 电平的串口适配器，交叉连接 TX/RX 并共地。GPIO4、5、8、9、15 是启动配置脚，外接电路不能在复位时强制成错误电平。

## 设计边界

这是一版用于验证的样板设计，尚未进行上电、测温或射频实测。横向天线、轴向开路端铜箔、20.0 × 3.8 mm 净空和缩短后的地平面均属于本工程的样板选择；3.8 mm 不是厂商保证的最小净空，原参考板的增益、带宽和方向图不能直接套用。匹配、效率和通信表现需在实际板卡及外壳中验证。

射频匹配、晶振负载与名义阻抗均需结合实际叠层、装配和外壳确认。保留的 11 个中心散热焊盘内孔仍须填孔盖铜，普通盖油不能替代；具体工艺与实板验证要求见 `FABRICATION.md`。

`tools/` 保留了设计过程与验证脚本。`verify_design.py` 可重跑网络与规则核对；布局生成和布线脚本会重建或修改 PCB，不能当成对最终布线无损的更新命令。

## 依据

- [Espressif ESP32-C6 原理图设计指南](https://docs.espressif.com/projects/esp-hardware-design-guidelines/zh_CN/latest/esp32c6/schematic-checklist.html)：供电、启动配置、晶振、USB 与射频匹配。
- [Espressif ESP32-C6 PCB 布局指南](https://docs.espressif.com/projects/esp-hardware-design-guidelines/zh_CN/latest/esp32c6/pcb-layout-design.html)：接地参考层、芯片底部接地、射频与时钟路径。
- 工程内 `docs/C127611_CAA3DCCF3A021118096CAD99FC50242A.pdf`，Walsin `ASC_RFANT5220110A0T_V13` 第 3–4 页：天线焊盘、开路端铜箔与测试板几何。
- [Eaton E9X 数据手册](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-e9x-crystal-resonator-mhz-data-sheet-elx1389-en.pdf)：Y1 的频率、负载、电气规格与引脚。
- [TI SN74LV1T125 数据手册](https://www.ti.com/lit/ds/symlink/sn74lv1t125.pdf)：RGB 控制信号电平转换。
- [Nexperia PESD5V0F1BL-Q 数据手册](https://assets.nexperia.com/documents/data-sheet/PESD5V0F1BL-Q.pdf)：低电容天线 ESD 选装器件。
