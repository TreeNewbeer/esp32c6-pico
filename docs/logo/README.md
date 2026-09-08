# PCB 丝印图形

2026-09-08：正面以 Codex 图标替换天线旁的 `2.4 GHz` 和 `NO COPPER`；背面加入用户提供的个人 logo。图形以可编辑的 KiCad 图形组保存在 PCB 中，不作为电气器件加入 BOM。

| 图形 | 来源 / 文件 | PCB 图形组 | 丝印层 | SVG 画布尺寸 |
| --- | --- | --- | --- | --- |
| Codex | [单色 SVG](codex-silkscreen.svg) | `LOGO_CODEX` | F.SilkS | 2.8 × 2.8 mm |
| 个人 logo | [原始 JPG](logo.jpg)、[丝印 SVG](personal-silkscreen.svg) | `LOGO_KZL` | B.SilkS | 约 6.43 × 8.20 mm |

Codex 图标采用 [LobeHub 图标仓库的 Codex 单色矢量文件](https://github.com/lobehub/lobe-icons/blob/master/packages/static-svg/icons/codex.svg)，属于社区整理的 OpenAI Codex 标识，并非本项目自创商标。图形来源及 SHA-256、放置坐标、尺寸记录在 [layout.json](layout.json)。

个人图形依据 `logo.jpg` 的中央人物描摹为单色轮廓，省去背景建筑、飞船等细节，保留头部、眼睛、胸前 K 标记与服装形状。主要轮廓约 0.12 mm；K 以实心徽章中的留白呈现。原始 JPG 保留不变，SVG 为便于丝印而整理的版本。

SVG 按正常观看方向保存。背面图形在 PCB 坐标中镜像，从板背面看时方向正确。`REV A` 移到图形旁边；两面的 logo 均只使用丝印层。删除 `NO COPPER` 文字后，天线铜层禁布区仍由 PCB 规则区和工程说明定义。

KiCad 中可按上述名称选中图形组，统一移动或缩放；修改尺寸后需检查丝印细节、焊盘间距与板边余量。当前 PCB、装配资料和 3D 预览以仓库根目录的工程及 `output/` 为准。历史布局生成脚本不包含最终图形组，不能无损重建当前板卡。
