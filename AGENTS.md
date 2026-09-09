# 仓库工作约定

## 工程入口

- 根目录的 `esp32-c6-pico.kicad_pro`、`.kicad_pcb`、`.kicad_sch`、`power-io.kicad_sch` 和 `.kicad_dru` 是可编辑工程；`output/` 是导出结果。
- 按任务需要阅读 [README.md](README.md)、[FABRICATION.md](FABRICATION.md) 和 [tools/README.md](tools/README.md)。历史生成、布线脚本不能无损重建当前 PCB，使用前先检查内容，不直接覆盖最终工程。

## 当前布局约定

后续用户明确调整设计时，同步更新相关工程、说明及检查条件。

- 板框为 20.0 × 29.0 mm，四层、标称 0.8 mm；L2 保留 GND 参考，遵守现有天线和射频禁布区。
- 陶瓷天线横放在板头右侧，馈电焊盘与 R6 对齐，Codex 图标位于左侧；AE1 的开路端铜箔不能接地。20.0 × 3.8 mm 净空是样板设计选择，性能尚未实测。
- 正面 `LOGO_CODEX`、背面 `LOGO_KZL` 是可编辑丝印图形组；源图和参数在 [docs/logo/](docs/logo/)。背面图形按背面视角显示，保持铜层禁布区；不要恢复已替换的 `2.4 GHz` / `NO COPPER` 丝印。
- 晶振及负载电容位于主控右侧；XTAL_P 串联器件按模组原理图采用 R18 = 0 Ω、0402 电阻（原 L4，对应官方模组 R4）。射频、晶振信号保持正面且不使用过孔，保留晶振下方的接地参考和禁布区。
- Flash、USB TVS、排针在背面，两颗按键在正面。Flash U3 使用 W25Q32JVSNIQ、150 mil SOIC-8（3.9 × 4.9 mm 本体，无中心焊盘）；USB 防反灌 D5 使用 at820_tiga 同款 BAT760-7 / SOD-323。排针针距 2.00 mm、列中心距 17.50 mm，1 脚朝天线；左右排针已各向内移动 0.30 mm，焊盘铜外缘距侧边各 0.575 mm。翻面时保持编号与网络顺序，功能丝印在背面。
- USB 输入已删除 F1 保险丝，不设置替代磁珠；VBUS_USB 直接接 D5 阳极，保留 D5 防反灌。
- 射频供电滤波电感 L2（2 nH、0402）位于 B.Cu，中心 (111.55, 112.65) mm；+3V3 在背面接入，V3A 经 (110.50, 112.80) mm 的双面盖油过孔回正面。C11、C19、C20 保持正面，保留芯片侧去耦；不要恢复左排针旁的旧 L2 占位。
- USB 走线尽量短、平行、自然等长，不为数值等长添加蛇形。整理器件时兼顾对齐、焊接空间与短连线。
- 射频匹配 R/C（C2、C3、C16、C17、C18、R6）保持英制 0201；其余全部 39 个电阻、电容统一英制 0402（公制 1005），包括 C8、C19、C20、C22、C23 和 R18、R17、R1–R5。保持容量、阻值、网络和 DNP 状态；大容量电源电容最低 10V，核对实际偏压下的有效容量，维护 [POWER_PASSIVES.md](POWER_PASSIVES.md) 与 BOM。电感和其他器件不随该阻容约定替换。
- 原理图 U1 外围在主页面通过实线直接连接：供电去耦、EN/BOOT、晶振、Flash、USB 串阻、UART、RGB 驱动。电源输入、USB 接口及排针留在第二页；标签辅助标注和跨页连接，不代替本地外围的实线。
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
