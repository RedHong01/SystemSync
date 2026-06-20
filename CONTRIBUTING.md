# 贡献指南 / Contributing

感谢你改进 Red LAN Sync Dashboard。这个项目面向中文和英文社区，因此所有面向用户或开发者的说明内容都必须保持中英文双语。

Thank you for improving Red LAN Sync Dashboard. This project serves both Chinese and English readers, so all user-facing or developer-facing documentation must remain bilingual.

## 本地检查 / Local Checks

提交修改前请运行：

Run these before submitting changes:

```sh
python3 -m py_compile server.py project_packager.py generate_windows_config.py
node --check static/app.js
```

如果修改了 UI，也需要测试：

If you changed the UI, also test:

- 中文和英文语言切换。
- Chinese and English language switching.
- 约 1280px 的桌面宽度。
- Desktop width around 1280px.
- 约 390px 的移动端宽度。
- Mobile width around 390px.
- 配对、存储和命名检查流程。
- Pairing, storage, and naming workflows.

## 代码风格 / Code Style

- 除非功能确实需要，否则 Python server 保持无第三方依赖。
- Keep the Python server dependency-free unless a feature clearly needs more.
- 所有网页可见文本都放在 `static/app.js` 的 `i18n` 字典中。
- Keep all user-facing web text in the `i18n` dictionary in `static/app.js`.
- 文件操作必须保守。规范化流程不能修改源工程，只能创建安全副本。
- Keep file operations conservative. The normalization workflow must not mutate the source project.
- 不要提交私人设备 ID、IP 地址、MAC 地址、API key 或 token。
- Do not commit private device IDs, IP addresses, MAC addresses, API keys, or tokens.

## 文档规则 / Documentation Rule

- `README.md` 是 GitHub 项目首页，必须中英文双语。
- `README.md` is the GitHub project homepage and must be bilingual.
- `CONTRIBUTING.md`、`SECURITY.md`、`docs/` 下的说明文件，以及未来新增的教程、部署说明、架构说明，都必须中英文双语。
- `CONTRIBUTING.md`, `SECURITY.md`, files under `docs/`, and future tutorials, deployment guides, and architecture notes must be bilingual.
- 推荐中文在前，英文紧随其后；不要只添加一种语言的说明。
- Prefer Chinese first, followed by English; do not add documentation in only one language.
- UI 文案本身仍通过 `static/app.js` 的 `i18n` 维护。
- UI copy itself should still be maintained through `static/app.js` `i18n`.

## 合并请求 / Pull Requests

请说明：

Describe:

- 修改了什么。
- What changed.
- 测试了什么。
- What was tested.
- 任何 Syncthing 版本假设。
- Any Syncthing version assumptions.
- 任何系统特定行为。
- Any OS-specific behavior.
