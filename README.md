# ESP32-C6 Pico · Rev A

已补齐基础电路并完成 **18 × 39 mm、四层、标称 0.8 mm** 的 PCB 布局布线。使用 ESP32-C6 QFN40、4 MB 外置 Flash、RFANT5220110A0T 陶瓷天线和 USB-C 原生 USB Serial/JTAG。原始工程的本地备份位于 `backups/before-foundation-20260906/`；备份、缓存与临时工具目录不纳入 Git 仓库。

直接用 KiCad 10 打开 `esp32-c6-pico.kicad_pro`。如编辑器仍显示修改前的内容，请关闭旧窗口并重新打开磁盘文件，避免旧窗口覆盖新文件。

## 已完成的电路

- USB-C 正反插数据连接、CC1/CC2 独立 5.1 kΩ 下拉、USBLC6-2SC6 静电保护、22 Ω 串联电阻及选装 EMI 电容。
- AP2112K-3.3 稳压、输入保护、肖特基防反灌、主电源及各供电脚的去耦；RF 电源使用独立 LC 滤波。
- CHIP_EN 的 10 kΩ / 1 µF 上电延时，RESET、BOOT 按键，GPIO8/9 上拉与 UART0 备用下载接口。
- W25Q32JVZPIQ 外置 Flash，真正接通 VDD_SPI；40 MHz / 8 pF 晶振，两个外壳脚接地，并保留负载调试与串联电感。
- 芯片端 CLCCL 射频网络、天线端 π 网络、低电容 ESD 选装位，以及陶瓷天线开路端调谐铜箔。
- WS2812B-2020 RGB 灯及 SN74LV1T125 电平转换，GPIO21 驱动。

## 检查与交付文件

KiCad 10.0.4 检查结果：**ERC 0 项；DRC 0 项；PCB 未连接 0 项**。逐焊盘原理图/PCB 网络对照通过；射频、晶振和 USB 主路径均在顶层；第二层没有信号走线。详细结果与文件哈希在 `output/qa.json`。

| 文件 | 用途 |
| --- | --- |
| `esp32-c6-pico.kicad_sch` / `power-io.kicad_sch` | 两张可编辑原理图 |
| `esp32-c6-pico.kicad_pcb` | 已布线 PCB，含叠层和禁布区 |
| `output/pcb-front.svg` / `pcb-back.svg` | 正反面布线预览 |
| `output/assembly-front.svg` / `assembly-back.svg` | 带位号的装配视图 |
| `output/bom.csv` | BOM；`Populate=NO` 表示不装 |
| `output/placement.csv` | 双面贴装坐标，已排除 DNP；坐标原点为板左下角 |
| `output/via-in-pad.csv` | 与焊盘相交的过孔坐标，供塞孔盖孔审核 |
| `FABRICATION.md` | 必须确认的工艺、阻抗与样板验证项目 |

板上共 65 个器件位，默认装配 59 个。默认不装 D1、L3、C17、C18、C27、C28。3D 图为布局示意，部分标准库封装缺少 3D 模型；器件是否装配以 BOM 和二维装配图为准。

## 接口与下载

USB 朝下、天线朝上时，J2 在左，J3 在右，两列的 1 脚均靠近天线。排针间距为 **2.00 mm**，并非 2.54 mm 面包板间距。

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

这是一版用于验证的样板设计，还没有上电、测温或射频实测。天线数据手册使用 18 × 9 mm 空白区域和 30 × 18 mm 地区作为测试参考；此版保留该尺度，因此整体为 18 × 39 mm。该参考尺寸不是已证明的最小尺寸，数据手册增益也不能直接套用到本板。

射频匹配、晶振负载与名义阻抗均需结合实际叠层、装配和外壳确认。存在焊盘内过孔，必须使用相应塞孔盖孔工艺；**不要未经工艺确认就按普通四层板直接下单**。具体见 `FABRICATION.md`。

`tools/` 保留了设计过程与验证脚本。`verify_design.py` 可重跑网络与规则核对；布局生成和布线脚本会重建或修改 PCB，不能当成对最终布线无损的更新命令。

## 依据

- [Espressif ESP32-C6 原理图设计指南](https://docs.espressif.com/projects/esp-hardware-design-guidelines/zh_CN/latest/esp32c6/schematic-checklist.html)：供电、启动配置、晶振、USB 与射频匹配。
- [Espressif ESP32-C6 PCB 布局指南](https://docs.espressif.com/projects/esp-hardware-design-guidelines/zh_CN/latest/esp32c6/pcb-layout-design.html)：接地参考层、芯片底部接地、射频与时钟路径。
- 工程内 `docs/C127611_CAA3DCCF3A021118096CAD99FC50242A.pdf`，Walsin `ASC_RFANT5220110A0T_V13` 第 3–4 页：天线焊盘、开路端铜箔与测试板几何。
- [Eaton E9X 数据手册](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-e9x-crystal-resonator-mhz-data-sheet-elx1389-en.pdf)：Y1 的频率、负载、电气规格与引脚。
- [TI SN74LV1T125 数据手册](https://www.ti.com/lit/ds/symlink/sn74lv1t125.pdf)：RGB 控制信号电平转换。
- [Nexperia PESD5V0F1BL-Q 数据手册](https://assets.nexperia.com/documents/data-sheet/PESD5V0F1BL-Q.pdf)：低电容天线 ESD 选装器件。
