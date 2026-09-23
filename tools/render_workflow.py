"""Render the overview as SVG + PNG. Optional build-only dependency: Pillow."""
from pathlib import Path
import os
import html
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
dest = root / "docs"
dest.mkdir(exist_ok=True)
W, H = 1800, 2790
im = Image.new("RGB", (W, H), "#0d1523")
draw = ImageDraw.Draw(im)
fonts = [os.environ.get("WORKFLOW_FONT", ""),
         str(Path(os.environ.get("WINDIR", "/nonexistent")) / "Fonts/msyh.ttc"),
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]
font = next((f for f in fonts if f and Path(f).is_file()), None)
if not font:
    raise SystemExit("Set WORKFLOW_FONT to a Chinese-capable TTF/TTC font")
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<rect width="100%" height="100%" fill="#0d1523"/>',
       '<style>text{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif}</style>']


def text(x, y, value, size=25, fill="#dbe7f5"):
    draw.text((x, y), value, font=ImageFont.truetype(font, size), fill=fill)
    svg.append(f'<text x="{x}" y="{y+size}" font-size="{size}" fill="{fill}">{html.escape(value)}</text>')


def card(x, y, w, h, title, lines, accent="#58d6ca"):
    draw.rounded_rectangle((x, y, x+w, y+h), radius=20, fill="#172437", outline="#32455f", width=2)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="#172437" stroke="#32455f" stroke-width="2"/>')
    draw.rounded_rectangle((x+18, y+23, x+24, y+h-23), radius=3, fill=accent)
    svg.append(f'<rect x="{x+18}" y="{y+23}" width="6" height="{h-46}" rx="3" fill="{accent}"/>')
    text(x+44, y+20, title, 30, accent)
    for i, line in enumerate(lines):
        text(x+44, y+70+i*38, line, 25)


def arrow(x1, y1, x2, y2, color="#7c91ad"):
    draw.line((x1, y1, x2, y2), fill=color, width=4)
    svg.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{color}" stroke-width="4" fill="none"/>')
    if x1 == x2:
        points = [(x2-9,y2-13), (x2+9,y2-13), (x2,y2)]
    else:
        direction = 1 if x2>x1 else -1
        points = [(x2-13*direction,y2-9), (x2-13*direction,y2+9),(x2,y2)]
    draw.polygon(points, fill=color)
    svg.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="{color}"/>')


text(70, 40, "AI VIDEO  /  从创意到完整影片", 47, "#ffffff")
text(72, 112, "完整制作与30秒内快速样片 · 一套可续跑、可审查、可交付的流程", 27, "#9db2ce")
card(70, 175, 1660, 153, "01  输入与一次预检", ["故事脚本 / 一两句描述 ＋ 目标时长 ＋ 可选参考图", "核对工具、账户、预算、声音、路径与既有授权；只询问真正缺失的必要条件"])
arrow(480, 330, 480, 352); arrow(1320, 330, 1320, 352)
card(70, 355, 805, 218, "完整版  A · 制作圣经", ["叙事目标、剧情起承转合、影片风格", "色彩 / 光线 / 配乐 / 对白 / 语气与停顿", "实体ID：人物、场景、物品及不变特征"], "#69b7ff")
card(925, 355, 805, 218, "轻量版  A · 快速创意", ["默认15秒，最多30秒；默认竖屏", "一个视觉主张，前1–2秒就抓住注意", "少主体、少场景；代理直接做创意决定"], "#ffc77c")
arrow(480, 575, 480, 610); arrow(1320, 575, 1320, 610)
card(70, 615, 805, 218, "完整版  B · 多角度设定", ["人物：正面 / 侧面 / 四分之三 / 背面", "场景：空间轴线、正反打、出入口、光源", "物品：结构、纹样、功能、数量与归属"], "#69b7ff")
card(925, 615, 805, 218, "轻量版  B · 最少必要资产", ["一个视觉锚点，必要的人物或产品参考", "通常3–4个生成源镜头；最多4个", "不做完整图册，不逐镜等待用户确认"], "#ffc77c")
arrow(480, 835, 480, 870); arrow(1320, 835, 1320, 870)
card(70, 875, 805, 218, "完整版  C · 逐镜执行脚本", ["景别 / 画面提示词 / 运镜 / 动作起止", "对白 / 情绪 / 声音 / 衔接 / 验收条件", "整数帧分配；总时长包含片头和片尾"], "#69b7ff")
card(925, 875, 805, 218, "轻量版  C · 短视频节奏", ["强开头 → 2–3个变化 → 清楚的视觉回收", "音乐与少量文字优先，按需保留对白", "用剪辑选段提速，不靠重复生成堆镜头"], "#ffc77c")
arrow(480, 1095, 480, 1132); arrow(1320, 1095, 1320, 1132)
card(70, 1135, 1660, 175, "02  Codex内置生图 → 干净的单镜首帧", ["先审设定，再生成分镜；锁定身份、服饰、道具和空间关系，按需制作尾帧", "首帧有错先修图；拼图只用于审阅，不直接当视频首帧；保存到项目并记录出处"])
arrow(900, 1312, 900, 1347)
card(70, 1350, 1660, 175, "03  Kling动态生成 → 持久化任务与费用", ["读取实时模型能力 → 兼容上传 → 保存请求 / 预留预算 → 一次提交 → 立即保存ID与回执", "查询原任务并下载；失败和断网不等于未收费；中断续跑不重发已成功镜头"])
arrow(900, 1527, 900, 1562)
card(70, 1565, 1660, 137, "04  实际动态验收：动作真的发生了吗？", ["检查身份、手部接触、物体去向、纹样几何、运镜与邻镜连续性；风险区间密集审看"])
arrow(330, 1704, 330, 1739); arrow(900, 1704, 900, 1739); arrow(1470, 1704, 1470, 1739)
card(70, 1742, 520, 180, "通过", ["记录源片哈希、采用入出点", "保存实际审看范围与限制"], "#58d6ca")
card(640, 1742, 520, 180, "局部可用", ["取可靠区间，保持完整动作", "合理变速，标明后期修复"], "#ffc77c")
card(1210, 1742, 520, 180, "未达标 / 不确定", ["定位问题；按规则请求重试", "不自动扣费；保留可续跑状态"], "#ff8c99")
text(1225, 1940, "获准后返回修图或针对性生成", 23, "#ff8c99")
arrow(330, 1925, 330, 1998); arrow(900, 1925, 900, 1998)
card(70, 2002, 1660, 175, "05  声音与精确剪辑", ["旁白 / 配乐 / 环境声分轨；实际发音与画面逐句对应；音乐避让、响度处理", "精确源入出点；字幕和品牌UI后期添加；真实第0帧封面；保留原素材与旧版本"])
arrow(900, 2179, 900, 2214)
card(70, 2217, 1660, 175, "06  检查实际导出的MP4", ["技术：全片解码、尺寸帧率、目标帧数、音轨、字幕、响度；视觉：首尾帧与所有切点", "声音：可播放时真实听审；失败局部修复后再查。技术通过不能替代视觉与听审。"])
arrow(900, 2394, 900, 2429)
card(70, 2432, 1660, 175, "07  交付可播放的完整影片", ["MP4 ＋ 封面；按需附SRT、制作脚本、提示词、费用与QA记录", "清楚说明未完成项、原生/升采样分辨率、后期修复；用户终验与内部验收分开"])
text(72, 2660, "快，来自范围清楚和主动决策；稳，来自可恢复任务和实际成片验收。", 29, "#b6c9e0")
text(72, 2720, "开源技能与辅助工具  ·  MIT  ·  不含原项目媒体与账户信息", 22, "#7e96b3")
svg.append("</svg>")
(dest / "workflow.svg").write_text("\n".join(svg), encoding="utf-8")
im.save(dest / "workflow.png")
print("Rendered docs/workflow.svg and docs/workflow.png")
