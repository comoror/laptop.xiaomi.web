#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态页生成脚本（纯 Python 标准库，无第三方依赖）

数据流：
    templates/page.html  +  i18n/zh.json / en.json  +  assets/images/
        │
        ▼  python build.py
    dist/            ← 4 个静态 HTML + images/，整个目录上传即为网站

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
DIST_DIR = ROOT / "dist"

# (i18n 中的页面 key, 语言, 输出文件名)
PAGES = [
    ("remote_control", "zh", "remote_control.html"),
    ("remote_control", "en", "remote_control_en.html"),
    ("file_manager",   "zh", "file_manager.html"),
    ("file_manager",   "en", "file_manager_en.html"),
]

LANG_ATTR = {"zh": "zh-CN", "en": "en"}

# FAQ 条目层级 → (标记字符, CSS 类)；letter/roman 的序号写在文案里
LEVELS = {
    "bullet": ("•", "lvl-bullet"),
    "check":  ("∘", "lvl-check"),
    "sub":    ("•", "lvl-sub"),
    "letter": ("",  "lvl-letter"),
    "roman":  ("",  "lvl-roman"),
}

# 文案中的链接写法：[[显示文字|目标地址]]，目标可以是
#   页面互跳:  file_manager.html / remote_control_en.html
#   页内锚点:  #step1
#   外部链接:  https://hyperos.mi.com/
LINK_RE = re.compile(r"\[\[([^\]|]+)\|([^\]]+)\]\]")


def esc(text):
    """HTML 转义，防止文案中的 < > & 破坏页面结构。"""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(text):
    """转义文案并把 [[文字|地址]] 转成 <a> 标签。"""
    escaped = esc(text)
    return LINK_RE.sub(
        lambda m: '<a href="%s">%s</a>' % (esc(m.group(2)), m.group(1)),
        escaped,
    )


def render_figures(figures):
    """图片列表 → <figure> 片段。"""
    out = []
    for fig in figures or []:
        caption = fig.get("caption", "")
        out.append(
            '<figure><img src="images/%s" alt="%s" loading="lazy">'
            "<figcaption>%s</figcaption></figure>"
            % (fig["img"], esc(caption), esc(caption))
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


def render_remote_control(data):
    """远控页：页面标题 → 主标题 → 功能1/2/3 → 分割线 → 常见问题。"""
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
    """文件管理页：标题 → 主标题 → 设备要求 → 步骤1/2/3 → 常见问题。"""
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
            '<section class="step"%s><div class="step-title">%s</div>%s</section>'
            % (sid, fmt(step["title"]), render_figures(step.get("figures")))
        )
    parts.append('<hr class="divider">')
    parts.append(render_faq(data["faq"]))
    return "\n".join(parts)


RENDERERS = {
    "remote_control": render_remote_control,
    "file_manager": render_file_manager,
}


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
        body = RENDERERS[page_key](page_data)
        html = (
            template.replace("{{LANG}}", LANG_ATTR[lang])
            .replace("{{TITLE}}", esc(page_data["html_title"]))
            .replace("{{BODY}}", body)
        )
        out_path = DIST_DIR / out_name
        out_path.write_text(html, encoding="utf-8")
        print("generated dist/%s" % out_name)

    # 复制图片到 dist/images/（HTML 使用相对路径引用）
    if not ASSETS_DIR.exists():
        sys.exit("assets not found: %s" % ASSETS_DIR)
    img_out = DIST_DIR / "images"
    if img_out.exists():
        shutil.rmtree(img_out)
    shutil.copytree(ASSETS_DIR, img_out)
    print("copied %d images -> dist/images/" % len(list(img_out.iterdir())))
    print("done.")


if __name__ == "__main__":
    main()
