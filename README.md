# laptop.xiaomi.web

小米笔记本插件（xiaomi.laptop.p52）两个引导页的网页版：
「控制笔记本」（远程控制）与「管理笔记本文件」，各含中/英两套，共 4 个静态 HTML。
后期从插件 MainPage 直接跳转到本网页，网页内容独立维护、独立发布。

## 目录结构

```
templates/page.html   页面模板（骨架 + 全部 CSS，文案位置由脚本注入）
i18n/zh.json          全部中文文案（两个页面都在这一个文件里）
i18n/en.json          全部英文文案
assets/images/        页面用到的 PNG 截图（复制自插件 resources/images/static/）
build.py              生成脚本（纯 Python 标准库，无第三方依赖）
dist/                 生成结果，不入库；部署上传的就是这个目录
```

## 日常工作流

```
1. 改文案：编辑 i18n/zh.json 或 i18n/en.json
2. 本地生成：python build.py        （Cloudflare CI 上是 python3 build.py）
3. 本地预览：双击 dist/ 下的 html，浏览器 F12 → 切换手机视口查看
4. 提交推送：git add . && git commit && git push
5. 自动部署：Cloudflare Pages 自动构建并发布
```

生成的 4 个页面：

```
dist/remote_control.html        远程控制 · 中文
dist/remote_control_en.html     远程控制 · English
dist/file_manager.html          文件管理 · 中文
dist/file_manager_en.html       文件管理 · English
```

## 文案里怎么写链接

在 i18n JSON 的文案字符串中使用 `[[显示文字|目标地址]]`，build.py 会自动转成 `<a>` 标签：

```
页面互跳：[[使用平板和手机，管理笔记本文件|file_manager.html]]
页内锚点：[[打开文件服务|#step1]]          （跳到 file_manager 页的步骤1）
外部链接：[[HyperOS官网|https://hyperos.mi.com/]]
```

英文页的链接目标要带 `_en` 后缀（如 `remote_control_en.html`），中英页面互不串门。

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

插件 MainPage.js 中两处 `navigation.navigate(targetPage)` 替换为：

```js
const lang = isChinese ? '' : '_en';
Host.ui.openWebView(`https://<你的域名>/remote_control${ lang }.html`);
Host.ui.openWebView(`https://<你的域名>/file_manager${ lang }.html`);
```

网页图片与文案全部托管在服务器上，以后更新页面内容只需改本仓库并推送，
无需再发插件版本。
