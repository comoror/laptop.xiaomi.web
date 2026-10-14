#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 MiSans 网页字体子集（assets/fonts/）。

为什么需要它：中文字体动辄 10MB+，直接挂官网字体包会让首屏慢到不可用。
本脚本把 MiSans（小米官方字体）按「本套页面实际用到的字符」切成子集，
输出 32 个 woff2 分片 + 一份 fonts/misans.css（共约 130KB）。

什么时候要重跑：改了 i18n/*.json 或 templates/page.html，新增了原来没有的汉字/
符号时。没重跑也不会报错——子集外的字符会回退到系统字体（iPhone 上是苹方、
小米设备上是系统 MiSans），只是那一个字和设计稿不完全一致。

用法：
    python tools/build_font.py            # 增量：只补缺失的字符
    python tools/build_font.py --refresh  # 忽略缓存，重新下载分片

依赖：fontTools + brotli（pip install fonttools brotli），构建网页本身不需要。
字体授权：MiSans 为小米官方免费商用字体，见 assets/fonts/MiSans-LICENSE.txt。
"""

import argparse
import glob
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(ROOT, "assets", "fonts")
CACHE_DIR = os.path.join(ROOT, "tools", ".fontcache")

PKG = "misans"
VERSION = "5.0.0"
CDN = "https://cdn.jsdelivr.net/npm/%s@%s" % (PKG, VERSION)
API = "https://data.jsdelivr.com/v1/packages/npm/%s@%s?structure=flat" % (PKG, VERSION)

WEIGHTS = [("Regular", 400), ("Medium", 500)]


def fetch(url, path):
    """下载到本地缓存（已存在则跳过）。"""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def collect_chars():
    """页面用到的全部字符：i18n 文案 + 模板骨架。"""
    chars = set("0123456789")
    for pattern in ("i18n/*.json", "templates/*.html"):
        for path in glob.glob(os.path.join(ROOT, pattern)):
            text = open(path, encoding="utf-8").read()
            chars |= set(re.sub(r"\{\{[A-Z]+\}\}", "", text))
    return {c for c in chars if ord(c) > 0x1F}


def load_ranges():
    path = fetch("%s/raw/ranges-sc.json" % CDN, os.path.join(CACHE_DIR, "ranges-sc.json"))
    raw = json.load(open(path, encoding="utf-8"))

    def parse(spec):
        out = set()
        for part in spec.split(","):
            part = part.strip()
            if not part.upper().startswith("U+"):
                continue
            body = part[2:]
            if "-" in body:
                a, b = body.split("-")
                out.update(range(int(a, 16), int(b, 16) + 1))
            else:
                out.add(int(body, 16))
        return out

    return {s["index"]: parse(s["range"]) for s in raw["slices"]}


def compress(codes):
    """[65,66,67,70] -> 'U+41-43,U+46'"""
    codes = sorted(codes)
    out, i = [], 0
    while i < len(codes):
        j = i
        while j + 1 < len(codes) and codes[j + 1] == codes[j] + 1:
            j += 1
        out.append("U+%X" % codes[i] if j == i else "U+%X-%X" % (codes[i], codes[j]))
        i = j + 1
    return ",".join(out)


def otf_to_ttf(font, max_err=1.0):
    """CFF 轮廓转成 TrueType(glyf) 轮廓。

    MiSans 的分片是 CID-keyed CFF，fontTools 不支持合并这种表；
    转成 glyf 后就能把几十个分片合成一个文件（体积会变大，但请求数从 30+ 降到 2）。
    """
    from fontTools.ttLib import newTable
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    order = font.getGlyphOrder()
    glyph_set = font.getGlyphSet()
    glyf = newTable("glyf")
    glyf.glyphOrder = order
    glyf.glyphs = {}
    for name in order:
        pen = TTGlyphPen(glyph_set)
        glyph_set[name].draw(Cu2QuPen(pen, max_err, reverse_direction=True))
        glyf.glyphs[name] = pen.glyph()
    font["glyf"] = glyf
    font["loca"] = newTable("loca")
    glyf.compile(font)                      # 顺带算出 maxPoints / maxContours
    maxp = font["maxp"]
    maxp.tableVersion = 0x00010000
    maxp.numGlyphs = len(order)
    maxp.maxZones = 1
    for attr in ("maxTwilightPoints", "maxStorage", "maxFunctionDefs", "maxInstructionDefs",
                 "maxStackElements", "maxSizeOfInstructions", "maxComponentElements",
                 "maxComponentDepth"):
        if getattr(maxp, attr, None) is None:
            setattr(maxp, attr, 0)
    for tag in ("CFF ", "VORG"):
        if tag in font:
            del font[tag]
    if "post" in font:
        font["post"].formatType = 3.0   # 不存字形名，体积更小
    font.sfntVersion = "\x00\x01\x00\x00"
    return font


def build_merged(weight, cps, need_idx, by_index, Options, Subsetter, TTFont):
    """把一个字重的所有分片：子集化 → 转 glyf → 合并成一个字体。

    Merger 只接受文件路径，所以每片先落到 pieces/ 再合并。
    """
    from fontTools.merge import Merger

    pieces_dir = os.path.join(CACHE_DIR, "pieces")
    os.makedirs(pieces_dir, exist_ok=True)
    for f in glob.glob(os.path.join(pieces_dir, "%s-*.ttf" % weight)):
        os.remove(f)

    pieces = []
    for idx in sorted(need_idx):
        rel = by_index.get(str(idx), {}).get(weight)
        if not rel:
            continue
        src = fetch(CDN + rel, os.path.join(CACHE_DIR, os.path.basename(rel)))
        font = TTFont(src, lazy=True)
        have = set(font.getBestCmap().keys()) & cps
        font.close()
        if not have:
            continue
        font = TTFont(src)
        opts = Options()
        opts.layout_features = ["*"]
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        opts.drop_tables += ["DSIG"]
        subsetter = Subsetter(options=opts)
        subsetter.populate(unicodes=sorted(have))
        subsetter.subset(font)
        piece = os.path.join(pieces_dir, "%s-%s.ttf" % (weight, idx))
        otf_to_ttf(font).save(piece)
        pieces.append(piece)
    if not pieces:
        return None
    return Merger().merge(pieces)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="忽略缓存重新下载分片")
    args = ap.parse_args()
    if args.refresh and os.path.isdir(CACHE_DIR):
        for f in glob.glob(os.path.join(CACHE_DIR, "*.woff2")):
            os.remove(f)

    try:
        from fontTools.ttLib import TTFont
        from fontTools.subset import Subsetter, Options
    except ImportError:
        sys.exit("需要 fontTools：pip install fonttools brotli")

    chars = collect_chars()
    cps = {ord(c) for c in chars}
    print("页面用字：%d 个（汉字 %d）" % (len(cps), sum(1 for c in chars if 0x4E00 <= ord(c) <= 0x9FFF)))

    slices = load_ranges()
    need_idx = set()
    for cp in cps:
        for idx, range_cps in slices.items():
            if cp in range_cps:
                need_idx.add(idx)
    uncovered = sorted(chr(c) for c in cps
                       if not any(c in r for r in slices.values()))
    print("涉及分片：%s" % sorted(need_idx))
    if uncovered:
        print("注意：MiSans SC 未覆盖 %d 个字符，将回退系统字体：%s"
              % (len(uncovered), "".join(uncovered)))

    files = json.loads(open(fetch(API, os.path.join(CACHE_DIR, "files.json")),
                             encoding="utf-8").read())["files"]
    by_index = {}
    for item in files:
        name = item["name"]
        if not name.startswith("/lib/Normal/") or not name.endswith(".woff2"):
            continue
        base = os.path.basename(name)
        idx = base.rsplit(".", 2)[-2]
        for weight, _ in WEIGHTS:
            if base.startswith("MiSans-%s." % weight):
                by_index.setdefault(idx, {})[weight] = name

    os.makedirs(FONTS_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(FONTS_DIR, "misans-*")):
        if f.endswith((".woff2", ".css")):
            os.remove(f)

    css = ["/* MiSans（小米官方字体）子集：先按本套页面用到的字符裁剪，",
           "   再把几十个分片合并成每字重一个文件（请求数 30+ → 2）。",
           "   重新生成：python tools/build_font.py */"]
    total = 0
    for weight, css_weight in WEIGHTS:
        merged = build_merged(weight, cps, need_idx, by_index, Options, Subsetter, TTFont)
        if merged is None:
            sys.exit("没有可用的 MiSans %s 分片" % weight)
        out_name = "misans-%s.woff2" % weight.lower()
        out_path = os.path.join(FONTS_DIR, out_name)
        merged.flavor = "woff2"
        merged.save(out_path)
        glyphs = len(merged.getBestCmap())
        merged.close()
        size = os.path.getsize(out_path)
        total += size
        print("%s：合并后 %d 个字，%d KB" % (weight, glyphs, size // 1024))
        css.append(
            "@font-face{font-family:MiSans;font-style:normal;font-weight:%d;font-display:swap;"
            "src:local('MiSans'),url('%s') format('woff2');}" % (css_weight, out_name)
        )
    open(os.path.join(FONTS_DIR, "misans.css"), "w", encoding="utf-8").write("\n".join(css) + "\n")

    lic = os.path.join(FONTS_DIR, "MiSans-LICENSE.txt")
    if not os.path.exists(lic):
        try:
            fetch(CDN + "/LICENSE", lic)
        except Exception as exc:  # 授权文件拿不到不影响使用
            print("授权文件下载失败：%s" % exc)

    print("完成：2 个 woff2，共 %d KB；misans.css 已更新" % (total // 1024))
    if uncovered:
        print("提醒：如上面列出的字符需要与设计稿完全一致，请联系设计补充或改用其他字体。")


if __name__ == "__main__":
    main()
