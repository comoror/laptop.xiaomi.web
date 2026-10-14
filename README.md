# laptop.xiaomi.web

小米笔记本插件（xiaomi.laptop.p52）三个引导页的网页版：
「控制笔记本」（远程控制）、「管理笔记本文件」与「智能玩法」，各含中/英两套，共 6 个静态 HTML。
后期从插件 MainPage 直接跳转到本网页，网页内容独立维护、独立发布。

版式以设计稿为唯一标准：1568px 宽的设计稿按 **2x** 落 CSS —— 页面逻辑宽度 784、
左右留白 52、内容宽 680、大标题 64、主标题 40、正文 28、列表与步骤正文 24、图注 20、
图片卡片 680×448、圆角 24。模板里的 viewport 写成 `width=784`，
手机上由系统整体缩放显示，观感与设计稿一致；深色模式跟随系统。

## 目录结构

```
templates/page.html   页面模板（骨架 + 全部 CSS，文案位置由脚本注入）
i18n/zh.json          全部中文文案（两个页面都在这一个文件里）
i18n/en.json          全部英文文案
assets/images/        页面用到的截图（WebP，带 alpha；源自设计稿导出的 1020px PNG）
assets/fonts/         MiSans 网页字体子集 + misans.css（由 tools/build_font.py 生成）
tools/build_font.py   字体子集生成脚本（可选，改文案加了新字才需要跑）
build.py              生成脚本（纯 Python 标准库，无第三方依赖）
dist/                 生成结果，不入库；部署上传的就是这个目录
```

## 字体：MiSans（小米官方字体）

页面不依赖系统字体，字体随页面上线，所有设备看到的字形都与设计稿一致：

- `assets/fonts/` 里是 **MiSans 精简子集**：`misans-regular.woff2`（57KB，正文全部用字）
  \+ `misans-medium.woff2`（**9KB**，只含 500 字重标题用到的 69 字）+ 0.5KB 的 `misans.css`。
  **每字重只发 1 个请求，合计约 67KB。**
- Medium 之所以能这么小：模板里只有 `.main-title` / `.section-title` / `.faq-title` 是
  `font-weight:500`，其余（页面大标题、功能标题、步骤标题、正文、清单、FAQ 问答）都是 400，
  脚本按这两类文案分别裁剪。给 500 字重的元素加新文案后重跑脚本即可自动纳入。
- `font-display:fallback`：最多 ~100ms 阻塞，字体 3 秒内到达才切换，超时保持系统字体，
  避免慢网络下"整篇换字形"闪一下。
- 为什么不是官方那套分片：官方分片是 32 个文件，PC 端（没装 MiSans）每个分片一个来回，
  实测单页 16 个字体请求、每个 1~1.9 秒，整页拖到 7.2 秒。合并后字体请求 16 → 2。
- 生成方式 `python tools/build_font.py`：先按页面用到的字符裁剪分片，再把 **CFF 轮廓转成 glyf**
  后合并——MiSans 分片是 CID-keyed CFF，fontTools 不支持直接合并，必须先转换
  （cu2qu，误差 1/1000 em，实测字形、断行与设计稿一致）。
- 模板 `<head>` 里 link 字体 CSS，`font-family` 第一位是 `"MiSans"`，后面才是
  `-apple-system / PingFang SC / Microsoft YaHei` 等系统字体兜底；
  `src` 带 `local('MiSans')`，小米设备已内置 MiSans，不会再下载。
- **改了文案、加了新字要重跑**：`python tools/build_font.py`
  （需要 `pip install fonttools brotli`；脚本会列出涉及的分片和 MiSans 未覆盖的字符）。
  不重跑也不会报错，只是新字会回退到系统字体。
- 已知：MiSans SC 的分片里没有 `？`（U+FF1F）和 `∘`（U+2218），这两个字符由系统字体兜底，
  实测与设计稿观感一致。
- 授权：MiSans 为小米官方免费商用字体，`assets/fonts/MiSans-LICENSE.txt` 为随包授权文件。
- 站点图标：`assets/favicon.svg` / `favicon.ico` / `favicon.png`（临时图标，可直接替换）。
  没有它浏览器会去请求 `/favicon.ico`，而 SPA 回退会返回整页 HTML，白耗一次请求。

## 日常工作流

```
1. 改文案：编辑 i18n/zh.json 或 i18n/en.json
2. 本地生成：python build.py        （Cloudflare CI 上是 python3 build.py）
   ※ 文案里出现了原来没有的汉字/符号时，先跑 python tools/build_font.py 补字体子集
3. 本地预览：双击 dist/ 下的 html，浏览器 F12 → 切换手机视口查看
   （页面按 784 逻辑宽度设计，手机上浏览器会整体缩放；桌面全屏看则接近设计稿 2 倍尺寸）
4. 提交推送：git add . && git commit && git push
5. 自动部署：Cloudflare Pages 自动构建并发布
```

生成的 6 个页面：

```
dist/remote_control.html        远程控制 · 中文
dist/remote_control_en.html     远程控制 · English
dist/file_manager.html          文件管理 · 中文
dist/file_manager_en.html       文件管理 · English
dist/smart_play.html            智能玩法 · 中文
dist/smart_play_en.html         智能玩法 · English
dist/index.html                 测试索引页（站点根入口，自动列出以上 6 页）
```

## 文案在哪、怎么写

`i18n/zh.json` / `en.json` 里每个页面一个 key：`remote_control`、`file_manager`、`smart_play`。

- `remote_control`：`page_title` / `main_title` / `features[]`（每项 `title` + 可选 `figures[]`）/ `faq`
- `file_manager`：`page_title` / `main_title` / `requirement` / `section_title` /
  `steps[]`（每项 `id`、可选 `num`、`title`、可选 `figures[]`）/ `faq`
- `smart_play`：`blocks[]` 顺序拼装，区块类型见 build.py 的 `render_block()`：
  `page_title` / `main_title`（可加 `"break": true` 表示跨板块大间隔）/ `section_title` /
  `body_text` / `requirement` / `list`（`items[]`，机型清单）/
  `step_title` / `step_text` / `figures` / `step`（`num` + `title` + `figures`）/ `divider`
- `faq`：`title` + `items[]`（每项 `question` + `answers[]`）；
  答案的 `level` 取 `bullet` / `check` / `sub` / `letter` / `roman` / `note`（`note` 为无标记说明行），
  条目后可跟 `figures[]`；`letter`、`roman` 的序号（`a.` / `i.`）写在文案里。

图片放在 `assets/images/`，JSON 里只写文件名（HTML 输出成 `images/xxx.webp`）。

- 格式为 **WebP（quality 85，保留 alpha）**：截图的四边是透明的，要透出卡片的灰底，
  所以不能拍平到白底。36 张共约 840KB；同内容 PNG 是 6.7MB，手机网络下会明显拖慢
  甚至加载失败，这是换 WebP 的原因。
- 尺寸 1020px 宽（卡片 680 CSS px 的 1.5 倍图）；拿到更高清的原图，同名覆盖即可，
  不用改文案（原图素材在仓库外的 `米家插图/`）。
- 懒加载：**前 2 张直接加载**（保证首屏一定有图），其余 `loading="lazy"`。
  全站图片虽只有 840KB，但 remote_control 一页就 416KB，全部预加载会让手机首屏明显变慢。
  若某些手机自带浏览器的懒加载不可靠导致图片不显示，把 `build.py` 里的
  `EAGER_FIGURES` 调大即可（调成很大就等于全部直接加载）。
- `<img>` 带 `width/height`，避免加载过程中页面跳动。
- 构建会生成 `dist/_headers`：`/images/*`、`/fonts/*` 缓存一天，HTML 保持 `must-revalidate`
  （改文案立刻生效）。

## 点击看大图（灯箱）

- 每张图外层是 `<a class="zoom" href="images/xxx.webp">`（由 `render_figures()` 生成）：
  - **有 JS**：点一下进入页内全屏灯箱，再点任意位置（或按 Esc）回到原页面；
  - **没 JS / JS 被拦**：退回浏览器默认行为，直接打开原图，行为不变。
- 放大缩小走**系统原生手势**：viewport 是 `width=784` 且没有写 `user-scalable=no`，
  所以双指缩放、双击放大在页面和灯箱里都可用，不需要自己实现手势。
- 实现只有模板末尾约 30 行原生 JS + 一段 `.lightbox` 样式，**无任何第三方依赖**，
  6 个页面共用（改模板即全站生效）。`build.py` 仍是纯标准库。

## 文案里怎么写链接

在 i18n JSON 的文案字符串中使用 `[[显示文字|目标地址]]`，build.py 会自动转成 `<a>` 标签：

```
页面互跳：[[使用平板和手机，管理笔记本文件|file_manager.html]]
页内锚点：[[打开文件服务|#step1]]          （跳到 file_manager 页的步骤1）
外部链接：[[HyperOS官网|https://hyperos.mi.com/]]
```

英文页的链接目标要带 `_en` 后缀（如 `remote_control_en.html`），中英页面互不串门。

不需要跳转、只想让文字用链接色（设计稿里的高亮词，如「以下版本」）时，写成 `((显示文字))`，
build.py 会输出 `<span class="hl">显示文字</span>`。

## Cloudflare 部署配置（Workers 新版流程）

Cloudflare 新版控制台将 Git 部署引导到 Workers（表单标题"设置您的应用程序"），
静态目录由仓库根部的 `wrangler.jsonc` 指定（`assets.directory = ./dist`）。
连接 GitHub 仓库后，表单填写：

| 配置项 | 值 |
|---|---|
| 项目名称 | `laptop-xiaomi-web`（需与 wrangler.jsonc 中 name 一致） |
| 构建命令 | `python3 build.py` |
| 部署命令 | `npx wrangler deploy`（保持默认） |

- `main` 分支 push → 自动部署到生产（在项目的 Custom domains / Domains 里绑定你自己的域名）
- 其他分支 push → 自动生成独立预览地址，验收后再合并到 `main`

若控制台仍是经典 Pages 流程：Framework preset 选 None，
Build command `python3 build.py`，Build output directory 填 `dist`，效果相同。

### 线上 URL 行为（由 wrangler.jsonc 决定）

| 访问地址 | 结果 |
|---|---|
| `https://<域名>/` | 200 · 测试索引页（列出 6 个页面入口，点击即达） |
| `https://<域名>/remote_control.html` | 200 · 直接打开该页（无重定向） |
| `https://<域名>/任意未匹配路径`（含无扩展名形式） | 200 · 回退到测试索引页 |

配置：`html_handling: "none"`（.html 为唯一规范地址，不重定向）
+ `not_found_handling: "single-page-application"`（未匹配路径与根路径回退到 index.html）。

## 与插件 RN 版的差异记录

1. **中英文件名互换（插件侧疑似线上 bug）**：插件里
   `RemoteControlPage.js` 装的是**英文**内容，`RemoteControlPage_en.js`
   装的是**中文**内容，而 MainPage 按 `isChinese ? 'RemoteControlPage' : 'RemoteControlPage_en'`
   路由——即中文用户目前会被路由到英文远控页。网页版按语言正确对应，
   不受此问题影响；建议后续插件版本顺带修复。
2. **深色模式答案文字**：RN 版深色模式下 FAQ 答案文字仍是黑色（opacity 黑），
   在深色背景上几乎不可见；网页版答案文字已随主题适配（深色下为白色半透明）。
3. **页内跳转方式**：RN 版 FAQ 里的「小米账号」「打开文件服务」用
   `scrollTo` 像素值定位，页面改版即失效；网页版改为语义锚点（`#step1`）。

## 后续接入插件（最后一步，改动极小）

插件 MainPage.js 中对应入口的 `navigation.navigate(targetPage)` 替换为：

```js
const lang = isChinese ? '' : '_en';
Host.ui.openWebView(`https://<你的域名>/remote_control${ lang }.html`);
Host.ui.openWebView(`https://<你的域名>/file_manager${ lang }.html`);
Host.ui.openWebView(`https://<你的域名>/smart_play${ lang }.html`);   // 智能玩法页入口
```

网页图片与文案全部托管在服务器上，以后更新页面内容只需改本仓库并推送，
无需再发插件版本。
