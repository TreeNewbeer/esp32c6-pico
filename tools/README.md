# 设计过程脚本

最终可编辑工程是上一级目录中的 KiCad 文件；`output/` 仅保留最终交付和检查结果。

`verify_design.py` 是核对入口：读取原理图导出的 `output/netlist.xml`、最终 PCB、ERC/DRC 报告，核对逐焊盘网络、封装、接地参考层、关键走线层和 USB 长度，并更新 QA/焊盘内孔清单。它不修改 PCB。

其他脚本保留布局生成、扇出、局部布线和视图生成过程，部分会重建或修改 PCB。设计中间文件已归档到本地 `tmp/routing-history/`，不纳入 Git 仓库；历史脚本里的中间文件路径不代表可直接执行的一键重建流程。修改最终工程请优先使用 KiCad，并先备份。

本机验证命令（PowerShell）：

```powershell
& 'C:\Program Files\KiCad\10.0\bin\python.exe' tools\verify_design.py
```
