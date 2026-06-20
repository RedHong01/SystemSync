# Figma 更新流程 / Figma Update Workflow

当控制台 UI 先在 Figma 中设计，再更新到这个本地局域网控制台时，使用这套流程。

Use this workflow when the dashboard UI is designed in Figma and then updated in this local LAN console.

## 1. Figma 设计规则 / Design Rules in Figma

- 每个控制台页面建立一个顶层 frame：`Overview`、`Naming`、`Devices`、`Storage` 和 `Pairing`。
- Build one top-level frame for each dashboard screen: `Overview`, `Naming`, `Devices`, `Storage`, and `Pairing`.
- 把可复用控件做成 components：buttons、nav tabs、badges、disk rows、forms 和 compact list rows。
- Keep reusable controls as components: buttons, nav tabs, badges, disk rows, forms, and compact list rows.
- 图层使用语义化命名，例如 `SyncPercent`、`AddDeviceForm`、`LanguageSelect` 和 `DiskRow`。
- Name layers semantically. Good names are `SyncPercent`, `AddDeviceForm`, `LanguageSelect`, and `DiskRow`.
- 如果文字代表 UI token，尽量保留英文；应用会通过 `static/app.js` 做本地化。
- Keep text in English where possible if it represents a UI token; the app will localize text through `static/app.js`.
- 优先使用 color、spacing、type variables/tokens，不要随手写临时值。
- Prefer variables/tokens for color, spacing, and type instead of ad hoc values.

## 2. 交付包含 node-id 的 Figma URL / Hand Off a Node-Specific Figma URL

分享包含 `node-id` 的 URL，例如：

Share a URL that includes `node-id`, for example:

```text
https://figma.com/design/FILE_KEY/FileName?node-id=123-456
```

更新流程需要精确的 frame node。只有文件级 URL 不够。

The update process needs the exact frame node. A file-level URL is not enough.

## 3. 更新实现 / Update the Implementation

控制台前端在：

The dashboard front end lives here:

```text
static/index.html
static/styles.css
static/app.js
```

实现规则：

Implementation rules:

- 保留 `server.py` 的 API contract。
- Preserve API contracts from `server.py`.
- 所有可见用户文案都放在 `static/app.js` 的 `i18n` 字典里。
- Keep all visible user-facing strings in the `i18n` dictionary in `static/app.js`.
- 不要把私人设备 ID 或 token 硬编码进已提交文件。
- Do not hardcode private device IDs or tokens into committed files.
- 首屏必须是可操作控制台。这不是 landing page。
- Keep the first screen operational. This is a control console, not a landing page.
- 每次 Figma 驱动更新后都验证桌面和移动端布局。
- Validate desktop and mobile layouts after every Figma-driven update.

## 4. 验证清单 / Verification Checklist

运行：

Run:

```sh
python3 -m py_compile server.py project_packager.py generate_windows_config.py
node --check static/app.js
python3 server.py
```

然后检查：

Then check:

- `http://127.0.0.1:8765/api/overview`
- `http://127.0.0.1:8765/api/pairing`
- 中文和英文语言切换。
- Language switch between Chinese and English.
- 约 390px 的移动端宽度。
- Mobile width around 390px.
- 配对表单、存储表单和工程注册表单不能溢出。
- Pairing form, storage form, and project registration form do not overflow.

## 5. 可选 Figma-to-code 路径 / Optional Figma-to-code Path

使用 Codex 的 Figma connector 时：

When using Codex with the Figma connector:

1. 用 `get_design_context` 读取 frame。 / Read the frame with `get_design_context`.
2. 对比生成的 design context 和现有控制台结构。 / Compare the generated design context against the existing dashboard structure.
3. 手动更新 `index.html`、`styles.css` 和 `app.js`，并保留 API 行为。 / Update `index.html`, `styles.css`, and `app.js` manually, preserving API behavior.
4. 部署 Mac service 前运行验证清单。 / Run the verification checklist before deploying the Mac service.
