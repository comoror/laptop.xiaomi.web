# 给 AI 智能体的工程说明

本文件面向**AI 智能体 / 代码助手**：在本仓库做任何改动前先读一遍，按这里的约定工作。
面向人的简短介绍见 `README.md`。

## 协作约定（重要）

- **不要自动提交或推送**。改完先汇报，等用户明确说"提交"再 `git commit`/`git push`。
- 一次改动若包含多个主题，按逻辑拆成多个提交；同一文件里拆不开的，可先生成部分改动提交、
  再还原完整版提交（本仓库历史里用过这种做法）。
- **文案以文档为准**：《控制笔记本 v1.1》《管理笔记本文件 v1.1》。设计稿与文档冲突时用文档，
  并把差异记录到工作区的 `设计稿与文档差异汇总.md`（同步到飞书文档给设计师）。
- 中文文案**句末不加句号**；设计稿里的「以下型号」按文档改成「其他型号」且去链接。
- 中英文案**必须同步修改**，不要只改一边。
- 任何改动后都要跑 `python build.py` 重新生成 `dist/`，并确认 7 个页面构建成功、图片引用 0 缺失。
- 不要引入 JS、第三方依赖、webfont —— 产物必须保持纯 HTML + CSS。

## 项目

小米笔记本插件（`xiaomi.laptop.p52`）三个引导页的网页版：控制笔记本、管理笔记本文件、
智能玩法，各含中/英两套，外加一个测试索引页，**共 7 个静态 HTML**（6 内容页 + index）。

产物是**纯 HTML + CSS**：0 个 `<script>`、0 个图片链接、无第三方依赖、不加载字体文件。

## 构建

```bash
python build.py          # Cloudflare CI 上是 python3 build.py
```

- 纯 Python 标准库，无第三方依赖。
- 输入：`templates/page.html` + `i18n/{zh,en}.json` + `assets/`；输出：`dist/`（**不入库**，见 `.gitignore`）。
- 模板里的 `{{BODY}}` 是正文占位符，其余由 `build.py` 注入。
- 构建还会生成 `dist/_headers`：`/images/*` 缓存一天，HTML 不加长缓存。

`build.py` 主要函数：

| 函数 | 作用 |
|---|---|
| `render_figures()` | 图片区块：`<figure><div class="shot"><img…></div><figcaption>…</figcaption></figure>` |
| `render_answers()` / `render_faq()` | FAQ 条目，按 `level` 出标记，条目后可跟图 |
| `render_step_title()` | 步骤标题，`num` 渲染成定宽序号，`final:true` 加 `is-final` |
| `render_remote_control()` / `render_file_manager()` / `render_smart_play()` | 三个页面骨架 |
| `render_block()` | 智能玩法页的区块拼装 |
| `render_index()` | 索引页 |

## 排版（设计稿 1568px @2x → 页面 1x × 2）

页面逻辑宽度 **784**，左右留白 **52**，内容宽 **680**，卡片 **680×448**，圆角 **24**。
全部尺寸写成 `calc(N * var(--s))`。

| 元素 | 字号 / 行高 | 备注 |
|---|---|---|
| `.page-title` 大标题 | 64 / 84.8 | `margin-bottom:108`，字重 400 |
| `.main-title` 主标题 | 40 / 53 | `margin-bottom:44`，`margin-right:-52` |
| `.section-title` / `.faq-title` | 40 / 53 | 字重 500 |
| `.body-text` / `.requirement` / `.feature-title` / `.step-title` | 28 / 37.2 | |
| `.step-text` / `.model-list li` | 24 / 40 | |
| `.a-item` FAQ 条目 | 24 / 44 | |
| `figcaption` 图注 | 20 / 28 | 卡片下方，`margin-top:16` |
| `.step-title.is-final` / `.feature-title.is-link` | 30 / 40 | 收尾/跳转那一行 |
| `.index-title` | 52 / 69 | 仅索引页 |

主标题 `margin-right: -52`：设计稿该文本层宽 380（内容列 340），即允许借用右侧留白。
右侧留白只有 52，**不能借更多**——否则文本层超出视口，会被 `body` 的 `overflow-x: hidden`
裁掉（英文长标题曾被切掉 "from"）。视口 784 时文本层 732，中文标题字宽 720，
单行并留 12px，与设计稿一致。

## 缩放与 viewport

```css
:root { --s: 1px; --s: min(1px, calc(100vw / 784)); }
```

- 视口 ≥784：`--s = 1px`，页面与设计稿 1:1；
- 更窄：整页等比缩小。

模板 viewport：`width=784,user-scalable=no,viewport-fit=cover`。
米家 App 的 WebView **不认** viewport meta，会按 784 原尺寸渲染（看起来 2 倍大），
`--s` 就是这种场景的兜底。

**滚动条必须隐藏**：`100vw` 包含传统滚动条宽度（实测 26px），滚动条一占位，
`100vw`(784) 就大于可用宽度(758)，页面比可用区域宽 26px，超出部分被裁。

```css
html { scrollbar-width: none; }
html::-webkit-scrollbar { width: 0; height: 0; }
```

## 交互约束

| 约束 | 实现 | 历史问题 |
|---|---|---|
| 不双指/双击缩放 | `html { touch-action: pan-y }` + `user-scalable=no` | 页面以约 50% 显示，双指落屏浏览器立即接管视觉缩放，观感是"整页突然放大" |
| 不横向平移 | `touch-action: pan-y`（`pan-x pan-y` 仍放行横向）+ `body { overflow-x: hidden }` | 内嵌 WebView 视觉视口比布局视口宽几 px 时能左右挪动；`overflow-x` 管不到视觉视口平移 |
| 不显示滚动条 | 见上节 | `vw` 与可用宽度差 26px |

- `touch-action` 在祖先链上取交集，**必须写在 `html` 上**，写在子元素上无效。
- iOS WebKit 不支持网页屏蔽双指缩放（系统级无障碍），该约束只在 Android / 米家 App(Android) 生效。
- 页面已无任何 JS；图片外层是 `<div class="shot">`（灰底/圆角/上下裁切），不是 `<a>`。
  若将来要"看图放大"，三条路：恢复灯箱 / 允许页面缩放 / 图片改回可点开原图。

## 颜色

| 变量 | 浅色 | 暗色 |
|---|---|---|
| `--bg` | `#ffffff` | `#000000`（对齐米家 App 暗色，纯黑） |
| `--title` 大标题 | `#333333` | `#ffffff` |
| `--heading` 主/小节标题 | `#000000` | `#ffffff` |
| `--sub` 说明文字 | `#4d4d4d` | `#b3b3b3` |
| `--body` 正文 | `rgba(0,0,0,.5)` | `rgba(255,255,255,.6)` |
| `--caption` 图注 | `#999999` | `#8c8c8c` |
| `--img-bg` 卡片 | `#f7f7f7` | `#141414` |
| `--divider` | `#e6e6e6` | `rgba(255,255,255,.15)` |
| `--link` | `#00B884` | `#00B884` |

暗色通过 `@media (prefers-color-scheme: dark)` 覆盖 `:root`；`html` 与 `body` 都上背景，
避免 WebView 回弹区/安全区露出白底。

## 字体

**不指定字体，用系统默认**：

```css
font-family: system-ui, sans-serif;
```

`system-ui` 是操作系统的 UI 字体：小米/HyperOS 上就是 MiSans（与设计稿一致），
Windows 上是 Segoe UI + 微软雅黑，iOS 上是苹方，Android 上是 Roboto/Noto。
页面**不加载任何字体文件**（无 `@font-face`、无 woff、无字体 CDN）。

- 中日韩字体每字 1em 宽，**换字体不影响断行、居中、卡片尺寸、页面高度**，只影响字形。
- Windows 雅黑只有 400/700，`font-weight:500` 会落到 400（标题略轻，不会假加粗）。
- 历史：曾用 `"MiSans", -apple-system, …` 的显式字体栈，后按需求改为 `system-ui`；
  更早版本还自托管过 MiSans woff2 子集（`tools/build_font.py`，67KB），为去网络请求已移除。
- 设计稿是 MiSans 画的，所以在 Windows 上预览时墨迹尺寸会差几个百分点
  （实测大标题墨迹高 124 vs 设计稿 118），属预期；小米设备上无差异。

## 图片

- 放 `assets/images/`，JSON 里只写文件名，输出成 `images/xxx.webp`。
- **WebP quality 85，保留 alpha**：截图四边透明，要透出卡片灰底，不能拍平白底。
  **34 张 794KB**，被引用 68 处（中/英页复用）。
- 尺寸 1020×720（卡片 680 的 1.5 倍图），更高清原图同名覆盖即可（原图在仓库外 `米家插图/`）。
- 懒加载：前 `EAGER_FIGURES = 2` 张直接加载，其余 `loading="lazy"`；`<img>` 带 `width/height` 防跳动。
- 图注在灰框**下方**（设计稿在框内，按需求外移），因此不需要"图注超行数补高"的逻辑。

## 文案结构（i18n）

`i18n/zh.json` / `en.json` 每页一个 key：`remote_control`、`file_manager`、`smart_play`。

- `remote_control`：`page_title` / `main_title` / `features[]`（`title` + 可选 `figures[]`）/ `faq`
- `file_manager`：`page_title` / `main_title` / `requirement` / `section_title` /
  `steps[]`（`id`、可选 `num`、`title`、可选 `figures[]`）/ `faq`
- `smart_play`：`blocks[]` 顺序拼装，类型：`page_title` / `main_title`（可 `"break": true`）/
  `section_title` / `body_text` / `requirement` / `list` / `step_title` / `step_text` /
  `figures` / `step`（`num` + `title` + `figures`）/ `divider`
- `faq`：`title` + `items[]`（`question` + `answers[]`）；答案 `level` 取
  `bullet` / `check` / `sub` / `letter` / `roman` / `note`，条目后可跟 `figures[]`；
  `letter`、`roman` 的序号（`a.` / `i.`）写在文案里。

特殊标记：

- 步骤加 `"final": true` → `.step-title.is-final`，字号 30/40；
- 标题含 `[[链接]]` → 自动加 `is-link`，同样 30/40。

链接写法：`[[显示文字|目标地址]]`（页面互跳/锚点/外链），英文页目标带 `_en`；
只想上链接色不跳转写 `((显示文字))` → `<span class="hl">`。

## 部署

两个环境，入口都是索引页：

| 环境 | 地址 | 更新方式 |
|---|---|---|
| 测试版 | https://laptop.0310298.com/index.html | `main` push 自动部署（Cloudflare） |
| 正式版 | https://pc.mi.com/iot_help/index.html | 手动上传 `dist/` 下 7 个 HTML |

### Cloudflare（自动，测试版）

`wrangler.jsonc`：`assets.directory = ./dist`，`html_handling: "none"`，
`not_found_handling: "single-page-application"`。

| 配置项 | 值 |
|---|---|
| 项目名 | `laptop-xiaomi-web` |
| 构建命令 | `python3 build.py` |
| 部署命令 | `npx wrangler deploy` |

`main` push 自动上生产；其它分支生成预览地址。URL 行为：`/` 与未匹配路径 → 索引页；
`/xxx.html` 直出，不重定向。

### FDS（手动，正式版）

线上目录 `https://pc.mi.com/iot_help/`，扁平放置。**样式内联，改模板后 7 个 HTML 全要换**：

```
index.html  remote_control.html  remote_control_en.html
file_manager.html  file_manager_en.html  smart_play.html  smart_play_en.html
```

`images/`、`favicon.*`、`_headers` 没改就不用重传。

注意：**push 只更新测试版**。正式版（pc.mi.com）必须在各自验证通过后手动上传；
用户说"提交"时，不要顺带声称正式版已更新。

## 验证方法

本机 Chrome 的 `--dump-dom` 返回空，**不要用它取渲染结果**，用截图 + 像素测量：

```powershell
# 与设计稿同尺度（1568 宽）渲染
chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --blink-settings=preferredColorScheme=1 --force-device-scale-factor=2 \
  --window-size=784,1600 --virtual-time-budget=25000 \
  --user-data-dir=<tmp> --screenshot=<out.png> file:///<repo>/dist/<page>.html
```

- 亮/暗色用 `--blink-settings=preferredColorScheme=1|0` 固定，避免系统主题干扰。
- `--hide-scrollbars` 决定版式宽度（784 vs 758），对比两次截图时参数必须一致。
- 逐带（band）测文字墨迹高度与 x 范围，与设计稿导出图（`remote_control.png` 等，1568 宽）比对。
- 懒加载会让截图偶发缺图，需要更大 `--virtual-time-budget` 或重渲染一次。
- 检查元素是否溢出：临时注入脚本遍历 `getBoundingClientRect().right`，用整页背景色
  （绿/红）与色条宽度输出结果，再读像素。

## 与插件 RN 版的差异

1. **中英文件名互换（插件侧疑似线上 bug）**：插件里 `RemoteControlPage.js` 装的是**英文**内容，
   `RemoteControlPage_en.js` 装的是**中文**内容，而 MainPage 按
   `isChinese ? 'RemoteControlPage' : 'RemoteControlPage_en'` 路由——中文用户目前会被路由到
   英文远控页。网页版按语言正确对应，不受影响；建议后续插件版本顺带修复。
2. **深色模式答案文字**：RN 版深色下 FAQ 答案文字仍是黑色，在深色背景上几乎不可见；
   网页版答案文字已随主题适配。
3. **页内跳转方式**：RN 版 FAQ 用 `scrollTo` 像素值定位，改版即失效；网页版用语义锚点（`#step1`）。

## 接入插件

MainPage.js 中对应入口的 `navigation.navigate(targetPage)` 替换为：

```js
const lang = isChinese ? '' : '_en';
Host.ui.openWebView(`https://<域名>/remote_control${ lang }.html`);
Host.ui.openWebView(`https://<域名>/file_manager${ lang }.html`);
Host.ui.openWebView(`https://<域名>/smart_play${ lang }.html`);
```

网页内容与图片全部托管在服务器上，后续更新只需改本仓库并推送，无需再发插件版本。

## 已知限制 / 待办

- 英文页大标题在 MiSans 下折两行（MiSans 拉丁字面偏宽）；要单行需改英文文案。
- 图注行高统一 28（设计稿两份稿子 14/16 不一致）。
- favicon 是临时图标，待替换官方图标。
- 设计稿内部问题（「副标题」占位图层、图注行高不一致、智能玩法画板名残留等）
  与设计稿/文档差异，汇总在工作区 `设计稿与文档差异汇总.md`。
- iOS 无法屏蔽双指缩放（系统行为），Android 完整生效。

## 不要改回去

| 别做 | 原因 |
|---|---|
| 加回 webfont / 字体子集 | 首屏多一次字体请求，CJK 等宽不需要 |
| 图注放回灰框内 | 会引出"图注超行补高"的 hack（已删） |
| 把 `--s` 换成写死 px | 米家 App WebView 会显示成 2 倍大 |
| 主标题负边距超过 -52 | 超出视口被裁，英文长标题会被切 |
| 去掉 `touch-action` / `user-scalable=no` / 滚动条隐藏 | 分别对应"双指乱缩放"/"左右可拖动"/"vw 差 26px"三个已修复问题 |
| 移除图片 `width/height` | 加载过程页面跳动 |
| 移除 `overflow-x: hidden` | 兜底：任何意外横向溢出都会变成可左右拖的横条 |
