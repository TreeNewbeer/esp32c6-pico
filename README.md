# ESP32-C6 Pico · Rev A

已补齐基础电路并完成 **20.5 × 32.0 mm、四层、标称 0.8 mm** 的 PCB 布局布线。使用 ESP32-C6 QFN40、4 MB 外置 Flash、横向放置的 RFANT5220110A0T 陶瓷天线和 USB-C 原生 USB Serial/JTAG。原始工程的本地备份位于 `backups/before-foundation-20260906/`；备份、缓存与临时工具目录不纳入 Git 仓库。

天线本体在板头横向居中，末端铜箔沿长轴向左展开；板头全层净空为 **20.5 × 3.5 mm**。Flash U3 和 USB TVS D4 位于背面，RESET / BOOT 两颗按键位于正面 USB 上方。天线侧 C16、R6 与馈电焊盘排在同一直线上，芯片侧两颗并联电容保留交错方向。

六颗 Flash 串联电阻 R17、R1–R5 已改为 0402，在背面排成一行，中心间距 1.20 mm。Flash U3 与 TVS D4 各向 USB 方向移动 0.80 mm，为焊盘外过孔和这排电阻留出空间；板框不变。C7 在主控 VDD_SPI 扇出旁的正面，C13 位于 3.3V 供电脚附近，保留短去耦连接。RGB 缓冲器 U4 与串阻 R15 按新的焊接间距微调。排针功能标注统一保留在背面，正面左侧的重复标注已清除。

此前以用户修整后的布线为起点，陶瓷天线 AE1 向下移动 **0.50 mm**，板头同步收短 **0.50 mm**。板框由 20.5 × 32.5 mm 改为 **20.5 × 32.0 mm**，面积由 666.25 mm² 减至 **656.00 mm²（减少约 1.54%）**。该轮只改变天线馈线端点；本次统一阻容封装另调整受影响的局部布线。晶振 Y1 与 C4、C5 位于 ESP32 右侧；排针仍从背面安装，针距 **2.00 mm**、两列中心距 **18.10 mm**。

天线下移后，与晶振名义本体边缘的最近距离从约 **9.125 mm 变为 8.655 mm**，仍满足现有 **8.5 mm** 项目几何目标。时钟相关走线总铜长约 **11.85 mm**，信号全部在正面且无过孔，晶振下方第二层接地完整。天线全层净空深度从 **4.0 mm 改为 3.5 mm**，属于优先缩短板长的样板调整；天线匹配、效率和实际干扰仍需实板验证。

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

2026-09-08 使用 KiCad 10.0.3 完成布线检查：**ERC 0 项；DRC 0 项；未连接 0 项；45 项独立 QA 通过**。逐焊盘原理图/PCB 网络对照通过；射频和晶振信号保持顶层且无过孔；USB 数据线在正反面走线，每根主数据线各两次换层；第二层没有信号走线。详细结果、实际板框/净空尺寸与文件哈希在 `output/qa.json`。

额外启用 `--schematic-parity` 时，KiCad 会报告 65 项原有的 PCB 自定义字段缺失（如 MPN、AssemblyNote）；已核对与修改前一致。这项字段同步检查不包含在上述布线 DRC 的零违规结果中。

USB 保持简洁路径，没有加入蛇形等长补偿。两根线在按键上方换到底层，经过靠近连接器的 TVS，再换回正面连接 USB-C 焊盘。接受自然扇出带来的少量长度差；QA 长度统计区分铜层，并计入标称过孔贯穿长度。

全板信号走线统一为 **0.15 mm**（含 USB、射频、晶振及芯片扇出），非 GND 电源走线统一为 **0.20 mm**；GND 保留原有线宽。`Power` 网络类覆盖 `+3V3`、`+5V`、`V3A`、`VBUS_FUSED`、`VBUS_USB`、`VDD_SPI`，其他信号使用 `Default`。自定义规则同时限制最小和最大线宽，独立 QA 核对每段走线与实际网络类；相关局部路径已按新宽度调整。线宽统一不代表阻抗或载流能力已经实测达标。

外围焊盘内的过孔已改为焊盘外短线扇出，并检查正反面的阻焊开窗；孔边间距至少 0.10 mm。仅保留 U1 中心接地焊盘 9 个、U3 中心接地焊盘 2 个填孔盖铜过孔。为腾出局部扇出空间，调整了 C7、C11、C27、R2、R3、R7、R16，其中 R16 改到正面。

| 文件 | 用途 |
| --- | --- |
| `esp32-c6-pico.kicad_sch` / `power-io.kicad_sch` | 两张可编辑原理图 |
| `esp32-c6-pico.kicad_pcb` | 已布线 PCB，含叠层和禁布区 |
| `esp32-c6-pico.kicad_dru` | 固定线宽、焊盘孔距与晶振下方的非接地过孔禁布规则 |
| `output/pcb-front.svg` / `pcb-back.svg` | 正反面布线预览 |
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

这是一版用于验证的样板设计，还没有上电、测温或射频实测。天线数据手册使用纵向天线、不同的末端铜箔形状、18 × 9 mm 空白区域和 30 × 18 mm 地区作为测试参考；当前样板采用横向天线、轴向末端铜箔和 20.5 × 3.5 mm 净空，第二层保留为地参考，器件分布和主地区长度也随本轮布局调整。3.5 mm 是当前样板的设计选择，并非厂商保证的最小净空；数据手册的增益、带宽和方向图不能直接套用。匹配、效率和通信表现需在实际板卡及外壳中验证。

射频匹配、晶振负载与名义阻抗均需结合实际叠层、装配和外壳确认。保留的 11 个中心散热焊盘内孔仍须填孔盖铜，普通盖油不能替代；具体工艺与实板验证要求见 `FABRICATION.md`。

`tools/` 保留了设计过程与验证脚本。`verify_design.py` 可重跑网络与规则核对；布局生成和布线脚本会重建或修改 PCB，不能当成对最终布线无损的更新命令。

## 依据

- [Espressif ESP32-C6 原理图设计指南](https://docs.espressif.com/projects/esp-hardware-design-guidelines/zh_CN/latest/esp32c6/schematic-checklist.html)：供电、启动配置、晶振、USB 与射频匹配。
- [Espressif ESP32-C6 PCB 布局指南](https://docs.espressif.com/projects/esp-hardware-design-guidelines/zh_CN/latest/esp32c6/pcb-layout-design.html)：接地参考层、芯片底部接地、射频与时钟路径。
- 工程内 `docs/C127611_CAA3DCCF3A021118096CAD99FC50242A.pdf`，Walsin `ASC_RFANT5220110A0T_V13` 第 3–4 页：天线焊盘、开路端铜箔与测试板几何。
- [Eaton E9X 数据手册](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-e9x-crystal-resonator-mhz-data-sheet-elx1389-en.pdf)：Y1 的频率、负载、电气规格与引脚。
- [TI SN74LV1T125 数据手册](https://www.ti.com/lit/ds/symlink/sn74lv1t125.pdf)：RGB 控制信号电平转换。
- [Nexperia PESD5V0F1BL-Q 数据手册](https://assets.nexperia.com/documents/data-sheet/PESD5V0F1BL-Q.pdf)：低电容天线 ESD 选装器件。
