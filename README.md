# laptop.xiaomi.web

小米笔记本插件（xiaomi.laptop.p52）三个引导页的网页版：
**控制笔记本**、**管理笔记本文件**、**智能玩法**，各含中/英两套，共 6 个内容页 + 1 个索引页。

页面是纯 HTML + CSS（无 JS、无第三方依赖、不加载字体文件）：
图片不可点击，页面不允许双指缩放和横向平移。

## 在线地址

| 环境 | 地址 | 更新方式 |
|---|---|---|
| 测试版 | https://laptop.0310298.com/index.html | push 到 `main` 自动部署（Cloudflare） |
| 正式版 | https://pc.mi.com/iot_help/index.html | 手动上传 `dist/` 下 7 个 HTML |

## 日常维护

改文案 → 生成 → 提交 → 部署：

```bash
# 1. 改文案
#    i18n/zh.json / i18n/en.json

# 2. 生成到 dist/
python build.py

# 3. 预览
#    双击 dist/ 下的 HTML，F12 切手机视口看

# 4. 发布
git push          # 自动部署到测试版 laptop.0310298.com
#    正式版 pc.mi.com/iot_help/ 需手动上传 dist/ 下 7 个 HTML
```

## 目录

```
templates/page.html   页面模板（含全部 CSS）
i18n/                 中英文案
assets/images/        截图（WebP，带透明边）
assets/favicon.*      站点图标（临时图标，可替换官方）
build.py              生成脚本（纯标准库）
dist/                 生成结果，不入库
```

## 几点要注意

- **样式内联在每个 HTML 里**：改模板后 7 个页面全变，上传时 7 个都要替换。
- **设计稿 1568px 宽按 2x 落 CSS**：页面逻辑宽度 784，尺寸统一写成 `calc(N * var(--s))`，
  小屏等比缩小（兜住不认 viewport meta 的内嵌 WebView）。
- **只用系统字体**：小米/HyperOS 命中 MiSans，其它平台回落苹方、雅黑、系统无衬线。
- **暗色跟随系统**，背景纯黑 `#000`，与米家 App 暗色界面衔接。
- **文案里的特殊写法**：`[[文字|链接]]` 跳转、`((文字))` 只上链接色。

排版数值、手势约束、图片规格、部署配置、验证方法与「别改回去」清单等工程细节，
见 [`AGENTS.md`](AGENTS.md)（面向 AI 协作者与深入排查用）。
