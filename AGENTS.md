# 仓库工作约定

## 第一版 PCB 提交快照（2026-09-11）

- 保留用户在居中后继续调整的 PCB：R19 现为 (115.70, 120.40) mm，R15 现为 (115.70, 122.36) mm；相关短线和图形按当前文件保留，USB / 按键仍居中，D2 位号隐藏。重新填铜并更新坐标、二维预览和检查报告。
- 当前 ERC 0、DRC 错误 0 / 丝印警告 1、未连接 0、一致性问题 0，独立 QA 39/53；未放宽规则，未进行实板测试。当前证据见 [第一版提交快照](output/first-pcb-revision.json)。下文居中记录及其前后对比图、旧 3D 图是各自时点的历史记录。

## 最新 PCB 局部微调（2026-09-10）

- 在用户已基本完成的第一版 layout 上居中：J1 向右 1.00 mm 至 X=110.00 mm；SW1 / SW2 各向右 0.50 mm 至 X=107.15 / 112.85 mm，两键间距和 Y=125.10 mm 不变；RST / BOOT 丝印随按键移动。D2 仅隐藏位号丝印，封装轮廓和极性标记保留。
- 为避让 USB 定位孔及按键庭院，D4 另向右 0.20 mm、向下 0.10 mm，R15 向右 0.50 mm；只修整局部短线和既有过孔。其余 54 个器件的位置、所有器件的网络/参数/封装/安装面、89 个过孔总数、板框、射频、晶振与禁布区保持输入状态；本轮未修改原理图。后续不要用历史生成脚本覆盖用户 layout。
- 重新填铜后，ERC 0、DRC 错误 0、未连接 0、原理图一致性 0；保留输入板头 AE1 与图形的同一项丝印重叠警告。独立 QA 39/53，与本轮输入基线相同，无新增失败项，不能称全部通过。新网表、检查报告、贴装坐标和二维预览已更新；旧 3D 图属于历史记录。见 [居中记录](output/usb-buttons-centered.json) 和 [前后对比](output/usb-buttons-centered-comparison.png)。下文先前状态保留为历史参考。

## 最新原理图状态（2026-09-10，仅原理图）

- RGB 控制已切回 GPIO8（U1.14，与 J2.7 共用），D6 阴极接 GPIO8；GPIO21 / U1.34 已标记不连接。R9 上拉在原理图中移到 D6 阴极侧，接 +3V3；R19 在阳极侧接 VBUS_USB。用户已确认以官方 DevKitC-1 v1.4 为准，当前 R9 = 3.3 kΩ 上拉到 3.3 V、R19 = 10 kΩ 上拉到 5 V、R15 = 0 Ω 串联接入 DIN；两颗上拉均保留。BOM、设计清单、阻容清单和检查条件已同步。
- 此次只编辑原理图及派生记录，PCB 由用户自行 layout；下面的 GPIO21 布局说明和 DRC / QA 数字属于此前 PCB 状态。新网表 ERC 0、主控外围实线检查通过，PCB 尚未同步，未重跑 DRC / QA。见 [GPIO8 原理图记录](output/rgb-gpio8-schematic.json)。
- 当前第二页原理图的 J3 从 1 到 12 为 GPIO1、GPIO0、GPIO23、GPIO22、GPIO20、GPIO19、GPIO18、U0TXD、U0RXD、GPIO15、+5V、GND；这是本轮输入已有的脚序，已同步设计清单。D2 输入原理图已选标准 `LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm`，设计清单与 BOM 已同步；本轮未更改 D2 封装。

## 工程入口

- 根目录的 `esp32-c6-pico.kicad_pro`、`.kicad_pcb`、`.kicad_sch`、`power-io.kicad_sch` 和 `.kicad_dru` 是可编辑工程；`output/` 是导出结果。
- 按任务需要阅读 [README.md](README.md)、[FABRICATION.md](FABRICATION.md) 和 [tools/README.md](tools/README.md)。历史生成、布线脚本不能无损重建当前 PCB，使用前先检查内容，不直接覆盖最终工程。

## 当前布局约定

后续用户明确调整设计时，同步更新相关工程、说明及检查条件。

- 板框为 18.0 × 29.0 mm，四层、标称 0.8 mm；L2 保留 GND 参考，遵守现有天线和射频禁布区。
- 陶瓷天线横放在板头右侧，馈电焊盘与 R6 对齐，Codex 图标位于左侧；AE1 的开路端铜箔不能接地。18.0 × 3.8 mm 净空是样板设计选择，性能尚未实测。
- 正面 `LOGO_CODEX`、背面 `LOGO_KZL` 是可编辑丝印图形组；源图和参数在 [docs/logo/](docs/logo/)。背面图形按背面视角显示，保持铜层禁布区；不要恢复已替换的 `2.4 GHz` / `NO COPPER` 丝印。
- 晶振及负载电容位于主控右侧；XTAL_P 串联器件按模组原理图采用 R18 = 0 Ω、0402 电阻（原 L4，对应官方模组 R4）。射频、晶振信号保持正面且不使用过孔，保留晶振下方的接地参考和禁布区。
- Flash、USB TVS、排针在背面，两颗按键在正面。Flash U3 使用 W25Q32JVSNIQ、150 mil SOIC-8（3.9 × 4.9 mm 本体，无中心焊盘）；USB 防反灌 D5 使用 at820_tiga 同款 BAT760-7 / SOD-323。排针针距 2.00 mm、列中心距 15.50 mm，1 脚朝天线；在此前两侧各内移 0.30 mm 的基础上，J2 又向右移动 2.00 mm，左板边同步收至 X=101.00 mm；J2 / J3 中心 X=102.25 / 117.75 mm，焊盘铜外缘距侧边仍各 0.575 mm。翻面时保持编号与网络顺序，功能丝印在背面。
- 最新排针顺序（板头为 1 脚）：J2 为 GPIO2、GPIO3、GPIO4、GPIO5、GPIO6、GPIO7、GPIO8、GPIO9_BOOT、GPIO10、GPIO11、+3V3、GND；J3 为 GPIO1、GPIO0、GPIO15、U0TXD、U0RXD、GPIO18、GPIO19、GPIO20、GPIO22、GPIO23、+5V、GND。GPIO5 的 U1.11 → J2.4 已完成，不再预留手动连接。当前 ERC 0、原理图一致性 0；工程仍处在右排针重新布线的过程中，DRC 5 项违规、9 项未连接、QA 45/53，与 RGB 改动前的同一工程基线（DRC 5、未连接 9、QA 44/52）逐项一致。引脚历史见 [引脚同步记录](output/pin-layout-sync.json)，USB 验证见 [USB 同步记录](output/usb-layout-sync.json)。C8、R8 保持背面的现有避让位置；C28 已随 USB 电路简化删除。
- USB 输入已删除 F1 保险丝，不设置替代磁珠；VBUS_USB 直接接 D5 阳极，保留 D5 防反灌。
- 射频供电滤波电感 L2（2 nH、0402）位于 B.Cu，中心 (111.55, 112.65) mm；+3V3 在背面接入，V3A 经 (110.50, 112.80) mm 的双面盖油过孔回正面。C11、C19、C20 保持正面，保留芯片侧去耦；不要恢复左排针旁的旧 L2 占位。
- USB 已删除 R12、R13、C27、C28，U1.18 / U1.19 直接连接 USB_D− / USB_D+；保留 CC 下拉和 D4 TVS，不恢复旧 USB_MCU_D± 网络。当前 59 个器件位、55 个默认装配，验证见 [USB 同步记录](output/usb-layout-sync.json) 与 [RGB 二极管驱动记录](output/rgb-diode-drive.json)。USB 走线尽量短、平行、自然等长，不为数值等长添加蛇形。整理器件时兼顾对齐、焊接空间与短连线。
- RGB 驱动按官方 ESP32-C6-DevKitC-1 v1.4 结构：GPIO21 → D6（1N4148WS / SOD-323，阴极朝 MCU）→ 数据节点，R19 = 10 kΩ 上拉到 VBUS_USB，再经 R15 = 330 Ω 接 D2.DIN。SN74LV1T125（U4）、其去耦 C26 和 GPIO21 下拉 R16 已删除，不要恢复；D6 在背面原 U4 位置，R19、R15 在 D2 右侧的正面空位，R15 需避开 (115.78, 122.8) mm 的接地过孔，R19 不占用背面排针功能丝印区。
- 射频匹配 R/C（C2、C3、C16、C17、C18、R6）保持英制 0201；其余全部 34 个电阻、电容统一英制 0402（公制 1005），包括 C8、C19、C20、C22、C23 和 R18、R17、R1–R5、R19。保持容量、阻值、网络和 DNP 状态；大容量电源电容最低 10V，核对实际偏压下的有效容量，维护 [POWER_PASSIVES.md](POWER_PASSIVES.md) 与 BOM。电感和其他器件不随该阻容约定替换。
- 原理图 U1 外围在主页面通过实线直接连接：供电去耦、EN/BOOT、晶振、Flash、USB 直连引出、UART、RGB 驱动。电源输入、USB 接口及排针留在第二页；标签辅助标注和跨页连接，不代替本地外围的实线。
- 信号走线（含 USB、射频和晶振）一律 0.15 mm，非 GND 电源走线一律 0.20 mm；GND 保留原有线宽。维护网络类及 `.kicad_dru` 中的固定线宽规则，扇出处也不得缩颈。
- 普通过孔孔边到两面 SMD 阻焊开窗至少 0.10 mm，包括同网络及 DNP 焊盘；普通孔双面盖油。仅允许 U1 的 9 个中心散热焊盘内孔，必须填孔盖铜；SOIC-8 Flash 无中心焊盘，不再保留 U3 的焊盘内孔例外。

## 验证与交付

- 原理图修改后重新导出 `output/netlist.xml` 并运行 ERC。PCB 修改后先重新填铜，再运行 DRC 和独立 QA；不得通过放宽规则或忽略违规来获得通过结果。
- 以下命令在仓库根目录执行；QA 依赖与当前工程一致的网表、ERC 和 DRC 报告：

```sh
flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --schematic-parity --format json --exit-code-violations -o output/drc-final.json esp32-c6-pico.kicad_pcb
flatpak run --command=python3 org.kicad.KiCad tools/verify_design.py
```

- 按修改范围更新预览、装配坐标、BOM 和相关说明；历史对比图保留为历史记录。临时文件、备份和实验日志放在已忽略的 `tmp/` 中。
- 交付说明改动、验证结果和文件路径。硬件实验保留原始命令与输出，重试另存日志；未进行的实板、射频或工艺验证不得声称已通过。
- 仅修改文档时检查内容、链接与格式，无需重跑电路检查。

## 其他

- **禁止全量文本 Diff**：绝对不要直接执行未受限的 `git diff` 或读取整个 `.kicad_sch`/`.kicad_pcb` 文件的变更，这会迅速耗尽 Token 与上下文窗口。
- **变更检查策略**：
  1. 先使用 `git status` 或 `git diff --stat` 确认修改涉及的文件列表。
  2. 优先通过导出/渲染原理图与 PCB 图片（或使用视觉 Diff 工具/脚本）进行视觉对比。
  3. 若必须查看文本，必须严格使用 `git diff -L <regex>` 锁定特定元件或网络块，禁止通篇输出。
