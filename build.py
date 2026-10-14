#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态页生成脚本（纯 Python 标准库，无第三方依赖）

数据流：
    templates/page.html  +  i18n/zh.json / en.json  +  assets/images/
        │
        ▼  python build.py
    dist/            ← 6 个静态 HTML + images/，整个目录上传即为网站

改文案只改 i18n/*.json；改版式改 templates/page.html 或本文件的渲染函数。
"""

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
I18N_DIR = ROOT / "i18n"
TEMPLATE_PATH = ROOT / "templates" / "page.html"
ASSETS_DIR = ROOT / "assets" / "images"
FONTS_DIR = ROOT / "assets" / "fonts"
DIST_DIR = ROOT / "dist"

# (i18n 中的页面 key, 语言, 输出文件名)
PAGES = [
    ("remote_control", "zh", "remote_control.html"),
    ("remote_control", "en", "remote_control_en.html"),
    ("file_manager",   "zh", "file_manager.html"),
    ("file_manager",   "en", "file_manager_en.html"),
    ("smart_play",     "zh", "smart_play.html"),
    ("smart_play",     "en", "smart_play_en.html"),
]

LANG_ATTR = {"zh": "zh-CN", "en": "en"}

# 前几张图片直接加载，其余懒加载（见 render_figures 说明）
EAGER_FIGURES = 2
_fig_index = 0


def reset_figures():
    """每个页面开始渲染前重置图片序号（决定哪几张不懒加载）。"""
    global _fig_index
    _fig_index = 0

# FAQ 条目层级 → (标记字符, CSS 类)；letter/roman 的序号写在文案里
LEVELS = {
    "bullet": ("•", "lvl-bullet"),
    "check":  ("∘", "lvl-check"),
    "sub":    ("•", "lvl-sub"),
    "letter": ("",  "lvl-letter"),
    "roman":  ("",  "lvl-roman"),
    "note":   ("",  "lvl-note"),   # 无标记的说明行（如「如果您安装的是电脑管家 5.8.x」）
}

# 文案中的链接写法：[[显示文字|目标地址]]，目标可以是
#   页面互跳:  file_manager.html / remote_control_en.html
#   页内锚点:  #step1
#   外部链接:  https://hyperos.mi.com/
LINK_RE = re.compile(r"\[\[([^\]|]+)\|([^\]]+)\]\]")
# 文案中的高亮写法：((显示文字))，渲染成绿色无下划线文字（不是链接）
HL_RE = re.compile(r"\(\(([^()]+)\)\)")


def esc(text):
    """HTML 转义，防止文案中的 < > & 破坏页面结构。"""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(text):
    """转义文案，再把 [[文字|地址]] 转成 <a>、((文字)) 转成高亮。"""
    escaped = esc(text)
    escaped = LINK_RE.sub(
        lambda m: '<a href="%s">%s</a>' % (esc(m.group(2)), esc(m.group(1))),
        escaped,
    )
    return HL_RE.sub(lambda m: '<span class="hl">%s</span>' % m.group(1), escaped)


def webp_size(path):
    """读取 WebP 尺寸（纯标准库；用于给 <img> 写 width/height，避免图片加载时页面跳动）。

    解析不了就返回 None，不影响生成。
    """
    try:
        with open(path, "rb") as fh:
            data = fh.read(32)
    except OSError:
        return None
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X":                     # 带 alpha 的扩展格式（本项目用的这种）
        w = int.from_bytes(data[24:27], "little") + 1
        h = int.from_bytes(data[27:30], "little") + 1
        return w, h
    if chunk == b"VP8 ":                     # 有损
        w = int.from_bytes(data[26:28], "little") & 0x3FFF
        h = int.from_bytes(data[28:30], "little") & 0x3FFF
        return w, h
    if chunk == b"VP8L":                     # 无损
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def render_figures(figures):
    """图片列表 → <figure> 片段（图注渲染在卡片内部，见模板 CSS）。

    图片包一层 <a class="zoom" href="图片地址">：
    - 有 JS 时点一下进页内灯箱（再点一下回到原页面，双指可缩放）
    - 没 JS / JS 被拦时退回浏览器默认行为，直接打开原图

    懒加载策略：前 EAGER_FIGURES 张直接加载（保证首屏一定有图），其余 loading="lazy"。
    全站图片虽有 840KB，但 remote_control 一页就 416KB，全部预加载会让手机端首屏明显变慢。
    """
    global _fig_index
    out = []
    for fig in figures or []:
        caption = fig.get("caption", "")
        size = webp_size(ASSETS_DIR / fig["img"])
        dims = ' width="%d" height="%d"' % size if size else ""
        lazy = "" if _fig_index < EAGER_FIGURES else ' loading="lazy"'
        _fig_index += 1
        out.append(
            '<figure><a class="zoom" href="images/%s" aria-label="%s">'
            '<img src="images/%s" alt="%s"%s decoding="async"%s></a>'
            "<figcaption>%s</figcaption></figure>"
            % (fig["img"], esc(caption), fig["img"], esc(caption), dims, lazy, esc(caption))
        )
    return "\n".join(out)


def render_answers(answers):
    """FAQ 答案条目（带层级缩进），条目后可跟图片。"""
    out = []
    for ans in answers:
        mark, cls = LEVELS.get(ans.get("level", "bullet"), LEVELS["bullet"])
        mark_html = '<span class="mark">%s</span>' % mark if mark else ""
        out.append(
            '<div class="a-item %s">%s<div class="a-text">%s</div></div>'
            % (cls, mark_html, fmt(ans["text"]))
        )
        fig_html = render_figures(ans.get("figures"))
        if fig_html:
            out.append(fig_html)
    return "\n".join(out)


def render_faq(faq):
    items = []
    for item in faq["items"]:
        items.append(
            '<div class="faq-item"><div class="faq-q">%s</div>%s</div>'
            % (fmt(item["question"]), render_answers(item["answers"]))
        )
    return '<section class="faq"><h2 class="faq-title">%s</h2>%s</section>' % (
        fmt(faq["title"]),
        "".join(items),
    )


def render_step_title(step):
    """步骤标题：可选 num（渲染成定宽序号，与标题之间留出设计稿的间距）。

    step 既可以是 file_manager 的 steps 条目（title），
    也可以是 smart_play 的 step_title / step 区块（title 或 text）。
    """
    num = step.get("num")
    text = step.get("title", step.get("text", ""))
    if num:
        return '<div class="step-title"><span class="num">%s</span>%s</div>' % (
            esc(num),
            fmt(text),
        )
    return '<div class="step-title">%s</div>' % fmt(text)


def render_remote_control(data):
    """远控页：页面标题 → 主标题 → 功能1/2/3/4 → 分割线 → 常见问题。"""
    parts = [
        '<h1 class="page-title">%s</h1>' % fmt(data["page_title"]),
        '<h2 class="main-title">%s</h2>' % fmt(data["main_title"]),
    ]
    for feat in data["features"]:
        parts.append(
            '<section class="feature"><div class="feature-title">%s</div>%s</section>'
            % (fmt(feat["title"]), render_figures(feat.get("figures")))
        )
    parts.append('<hr class="divider">')
    parts.append(render_faq(data["faq"]))
    return "\n".join(parts)


def render_file_manager(data):
    """文件管理页：标题 → 主标题 → 设备要求 → 分割线 → 小节标题 → 步骤1/2/3 → 分割线 → 常见问题。"""
    parts = [
        '<h1 class="page-title">%s</h1>' % fmt(data["page_title"]),
        '<h2 class="main-title">%s</h2>' % fmt(data["main_title"]),
        '<div class="requirement">%s</div>' % fmt(data["requirement"]),
        '<hr class="divider">',
        '<h2 class="section-title">%s</h2>' % fmt(data["section_title"]),
    ]
    for step in data["steps"]:
        sid = ' id="%s"' % step["id"] if step.get("id") else ""
        parts.append(
            '<section class="step"%s>%s%s</section>'
            % (sid, render_step_title(step), render_figures(step.get("figures")))
        )
    parts.append('<hr class="divider">')
    parts.append(render_faq(data["faq"]))
    return "\n".join(parts)


def render_block(block):
    """智能玩法页的通用区块渲染（区块类型见 i18n/smart_play.json 的 blocks）。"""
    kind = block["type"]
    if kind == "page_title":
        return '<h1 class="page-title">%s</h1>' % fmt(block["text"])
    if kind == "main_title":
        cls = "main-title break" if block.get("break") else "main-title"
        return '<h2 class="%s">%s</h2>' % (cls, fmt(block["text"]))
    if kind == "section_title":
        return '<h2 class="section-title">%s</h2>' % fmt(block["text"])
    if kind == "body_text":
        return '<div class="body-text">%s</div>' % fmt(block["text"])
    if kind == "requirement":
        return '<div class="requirement">%s</div>' % fmt(block["text"])
    if kind == "list":
        lis = "".join("<li>%s</li>" % fmt(i) for i in block["items"])
        return '<ul class="model-list">%s</ul>' % lis
    if kind == "step_title":
        return render_step_title(block)
    if kind == "step_text":
        return '<div class="step-text">%s</div>' % fmt(block["text"])
    if kind == "figures":
        return render_figures(block.get("figures"))
    if kind == "step":
        sid = ' id="%s"' % block["id"] if block.get("id") else ""
        return '<section class="step"%s>%s%s</section>' % (
            sid,
            render_step_title(block),
            render_figures(block.get("figures")),
        )
    if kind == "divider":
        return '<hr class="divider">'
    sys.exit("unknown block type: %s" % kind)


def render_smart_play(data):
    """智能玩法页：按 blocks 顺序拼装（机型清单 / 步骤 / 管理文件小节混排）。"""
    return "\n".join(render_block(b) for b in data["blocks"])


RENDERERS = {
    "remote_control": render_remote_control,
    "file_manager": render_file_manager,
    "smart_play": render_smart_play,
}


def page_display_title(page_data):
    """取页面标题：优先 page_title；智能玩法页的标题在 blocks 里。"""
    if page_data.get("page_title"):
        return page_data["page_title"]
    for block in page_data.get("blocks", []):
        if block.get("type") == "page_title":
            return block["text"]
    return ""


def render_index():
    """测试索引页：列出全部页面入口（标题自动取自 i18n，保持同步）。"""
    cache = {
        lang: json.loads((I18N_DIR / ("%s.json" % lang)).read_text(encoding="utf-8"))
        for lang in set(p[1] for p in PAGES)
    }
    items = []
    for page_key, lang, out_name in PAGES:
        title = page_display_title(cache[lang][page_key])
        suffix = "（中文）" if lang == "zh" else " (English)"
        items.append(
            '<li><a href="%s">%s</a></li>' % (out_name, esc(title + suffix))
        )
    return (
        '<h1 class="page-title">laptop.xiaomi.web</h1>'
        '<h2 class="main-title">页面索引 / Page Index</h2>'
        '<ul class="index-list">%s</ul>'
        '<p class="index-note">开发测试用入口页；正式使用时插件直接跳转到具体页面，'
        "此页不会被用户看到。</p>" % "\n".join(items)
    )


def main():
    if not TEMPLATE_PATH.exists():
        sys.exit("template not found: %s" % TEMPLATE_PATH)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    DIST_DIR.mkdir(exist_ok=True)

    for page_key, lang, out_name in PAGES:
        data_path = I18N_DIR / ("%s.json" % lang)
        if not data_path.exists():
            sys.exit("i18n file not found: %s" % data_path)
        lang_data = json.loads(data_path.read_text(encoding="utf-8"))
        if page_key not in lang_data:
            sys.exit('missing key "%s" in %s' % (page_key, data_path.name))

        page_data = lang_data[page_key]
        reset_figures()
        body = RENDERERS[page_key](page_data)
        html = (
            template.replace("{{LANG}}", LANG_ATTR[lang])
            .replace("{{TITLE}}", esc(page_data["html_title"]))
            .replace("{{BODY}}", body)
        )
        out_path = DIST_DIR / out_name
        out_path.write_text(html, encoding="utf-8")
        print("generated dist/%s" % out_name)

    # 测试索引页：访问站点根路径时的入口
    index_html = (
        template.replace("{{LANG}}", "zh-CN")
        .replace("{{TITLE}}", esc("页面索引 - laptop.xiaomi.web"))
        .replace("{{BODY}}", render_index())
    )
    (DIST_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("generated dist/index.html")

    # 复制图片到 dist/images/（HTML 使用相对路径引用）
    if not ASSETS_DIR.exists():
        sys.exit("assets not found: %s" % ASSETS_DIR)
    img_out = DIST_DIR / "images"
    if img_out.exists():
        shutil.rmtree(img_out)
    shutil.copytree(ASSETS_DIR, img_out)
    print("copied %d images -> dist/images/" % len(list(img_out.iterdir())))

    # 复制 MiSans 字体子集到 dist/fonts/（页面 head 里 link 引用）
    if not FONTS_DIR.exists():
        sys.exit("fonts not found: %s" % FONTS_DIR)
    font_out = DIST_DIR / "fonts"
    if font_out.exists():
        shutil.rmtree(font_out)
    shutil.copytree(FONTS_DIR, font_out)
    print("copied %d font files -> dist/fonts/" % len(list(font_out.iterdir())))

    # 站点图标：没有它浏览器会去请求 /favicon.ico，而 SPA 回退会返回整页 HTML（白白多一次请求）
    for name in ("favicon.ico", "favicon.svg", "favicon.png"):
        src = ASSETS_DIR.parent / name
        if src.exists():
            shutil.copyfile(src, DIST_DIR / name)
    print("copied favicon.ico / favicon.svg / favicon.png -> dist/")

    # 静态资源缓存头（Cloudflare 支持 dist/_headers）。
    # HTML 保持默认的 must-revalidate（改文案立刻生效），图片/字体缓存一天，
    # 省掉手机端每次进页面都要重新校验 36 张图的往返。
    (DIST_DIR / "_headers").write_text(
        "/images/*\n  Cache-Control: public, max-age=86400\n\n"
        "/fonts/*\n  Cache-Control: public, max-age=86400\n",
        encoding="utf-8",
    )
    print("generated dist/_headers")
    print("done.")


if __name__ == "__main__":
    main()
