# 架构 / Architecture

SystemSync 刻意保持小型、可本地部署、易审计。

SystemSync is intentionally small, locally deployable, and easy to audit.

```text
Mac Dock launcher
  -> mac/OpenDashboard.sh
  -> Python dashboard server on TCP 8765
    -> local Syncthing REST API on 127.0.0.1:8384
    -> Windows companion agent on TCP 8766
      -> Windows Syncthing REST API
      -> Windows disk and power APIs
Windows browser
  -> OpenDashboard.ps1 smart launcher
  -> /auth token cookie
  -> Mac dashboard server on TCP 8765
```

## 组件 / Components

- `server.py`：HTTP server、Syncthing API bridge、Wake-on-LAN sender、任务 runner 和配对 API。
- `server.py`: HTTP server, Syncthing API bridge, Wake-on-LAN sender, job runner, and pairing API.
- `project_packager.py`：跨平台文件名规划、安全副本 worker 和报告写入器。
- `project_packager.py`: cross-platform filename planner, safe-copy worker, and report writer.
- `/api/normalizations` 与 `/api/normalizations/report`：扫描并读取 `_CrossPlatformReport`，让网页集中管理规范化副本和改名映射。
- `/api/normalizations` and `/api/normalizations/report`: scan and read `_CrossPlatformReport` folders so the web UI can manage normalized copies and rename mappings in one place.
- `dependency_auditor.py`：工程依赖扫描器，负责 Adobe 文件、Unity 工程、字体、插件、外部路径线索和 `_DependencyBundle` 打包。
- `dependency_auditor.py`: project dependency scanner for Adobe files, Unity projects, fonts, plugins, external path signals, and `_DependencyBundle` packaging.
- `scripts/preflight.py`：clone 后部署预检，检查配置、Syncthing、Windows 包和 Unity/Adobe 应用检测。
- `scripts/preflight.py`: post-clone deployment preflight for config, Syncthing, the Windows package, and Unity/Adobe app detection.
- `static/`：浏览器控制台前端。
- `static/`: browser dashboard.
- `static/app-icon.svg`：网页 favicon、侧边栏品牌图标和 Dock 快捷方式卡片使用的共享应用图标。
- `static/app-icon.svg`: default shared app icon used by the web favicon, sidebar brand mark, and Dock shortcut card.
- `runtime-assets/app-icon.*`：网页上传的本机自定义图标，不提交到 Git；Mac Dock 安装脚本会优先使用它。
- `runtime-assets/app-icon.*`: local custom icon uploaded from the web UI and ignored by Git; the Mac Dock installer prefers it when present.
- `mac/generate_app_icon.py`：用 Python 标准库生成 macOS `.iconset` PNG 文件，供 `iconutil` 打包为 `.icns`。
- `mac/generate_app_icon.py`: generates macOS `.iconset` PNG files with the Python standard library so `iconutil` can package them into `.icns`.
- `mac/OpenDashboard.sh`：macOS 智能启动器，自动检测本机控制台、文字域名和 Mac IP fallback，必要时 kickstart LaunchAgent。
- `mac/OpenDashboard.sh`: macOS smart launcher that detects the local controller, friendly alias, and Mac IP fallback, and kickstarts the LaunchAgent when needed.
- `mac/install-dock-shortcut.sh`：创建/刷新 macOS Dock `.app` 智能启动器，并写入同一套应用图标。
- `mac/install-dock-shortcut.sh`: creates or refreshes the macOS Dock `.app` smart launcher and applies the shared app icon.
- `windows/LanSyncAgent.ps1`：Windows companion service。
- `windows/LanSyncAgent.ps1`: Windows companion service.
- `windows/OpenDashboard.ps1`：Windows 智能启动器，自动测试文字域名和 Mac IP fallback，并用配对 token 打开可操作网页会话。
- `windows/OpenDashboard.ps1`: Windows smart launcher that tests the friendly alias and Mac IP fallback, then opens an authenticated browser session with the pairing token.
- `windows/DependencyScan.ps1`：Windows 字体、Adobe 应用、Unity Editor 和插件清单扫描函数，供 companion API 和独立检查脚本复用。
- `windows/DependencyScan.ps1`: Windows font, Adobe app, Unity Editor, and plugin inventory functions shared by the companion API and standalone check script.
- `windows/install-agent.ps1`：Windows 安装器、防火墙规则、计划任务和桌面唤醒快捷方式。
- `windows/install-agent.ps1`: Windows installer, firewall rule, scheduled task, and desktop wake shortcut.
- `windows/install-agent.ps1` 还会把 `dashboard_alias` 映射到 Mac IP，并生成文字域名网页管理快捷方式。
- `windows/install-agent.ps1` also maps `dashboard_alias` to the Mac IP and creates the friendly-domain dashboard shortcut.
- `generate_windows_config.py`：生成带 token 的 Windows companion 配置。
- `generate_windows_config.py`: writes the tokenized Windows companion config.

## 信任模型 / Trust Model

- 私有密钥保存在被忽略的运行时配置文件中。
- Private secrets stay in ignored runtime config files.
- 自定义图标保存在被忽略的 `runtime-assets/` 中，属于本机运行时状态。
- Custom icons are stored in ignored `runtime-assets/` as local runtime state.
- 会修改系统状态的 API action 需要 localhost、shared companion token header，或由 `/auth` 设置的 HttpOnly 浏览器会话 cookie。
- Mutating API actions require localhost, the shared companion token header, or an HttpOnly browser session cookie set by `/auth`.
- 控制台设计用于可信局域网，不用于公网暴露。
- The dashboard is designed for trusted LAN use, not public internet exposure.
- Syncthing 仍然是文件同步引擎；本项目负责设置编排、可视化和工程卫生检查。
- Syncthing remains the file synchronization engine; this project orchestrates setup, visibility, and project hygiene.
- 网页客户端由 Mac 控制端提供；其他设备推荐使用 Mac 局域网 IP，hosts 别名 `system-sync.local` 只是可选入口。`127.0.0.1` 只代表当前正在使用的那台电脑。
- The web client is served by the Mac controller; other devices should prefer the Mac LAN IP, while the hosts alias `system-sync.local` is only an optional entry. `127.0.0.1` only means the computer currently using it.

## 工程安全 / Project Safety

默认规范化流程不会重命名源文件夹。它会创建新的目标文件夹，并写入包含映射、跳过文件、冲突和可选 After Effects 辅助脚本的报告。网页会扫描同步根目录和当前目标路径下的 `_CrossPlatformReport`，集中展示历史安全副本、改名映射、跳过项和风险提醒。源路径改名是独立确认动作：后端先返回改名清单和 plan hash，前端展示后，用户再次确认才会在源工程内按层级执行原地改名。

The default normalization workflow never renames the source folder. It builds a new destination folder and writes a report with mappings, skipped files, collisions, and optional After Effects helper scripts. The web UI scans `_CrossPlatformReport` folders under the sync root and current destination path, then centralizes historical safe copies, rename mappings, skipped items, and risk notes. Source-path renaming is a separate confirmed action: the backend first returns a rename list and plan hash, the UI displays it, and only a second user confirmation applies in-place renames inside the source project.

依赖审计会把项目本地字体和 Adobe 辅助资产复制到 `_DependencyBundle`，但不会自动安装系统字体或第三方 Adobe 插件。系统字体和插件以清单形式记录，方便另一端人工确认授权、版本和安装方式。

Dependency audit copies project-local fonts and Adobe helper assets into `_DependencyBundle`, but does not auto-install system fonts or third-party Adobe plugins. System fonts and plugins are recorded as manifests so the other endpoint can review licensing, versions, and installation steps.

## Repo 架构更新规则 / Repo Architecture Update Rule

每次功能、API、部署方式、目录结构、前端模块、Mac Dock 入口或 Windows companion agent 发生变化时，本架构文档必须跟着更新。

Every time a feature, API, deployment flow, directory structure, front-end module, Mac Dock entry, or Windows companion agent changes, this architecture document must be updated in the same change.
