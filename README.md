# SystemSync / 红色局域网同步控制台

SystemSync 是一个本地优先的 Mac/Windows Syncthing 局域网同步控制台。它在 Syncthing 之上增加工程文件命名检查、安全副本规范化、双端状态、Wake-on-LAN、目标磁盘选择、新设备配对、GitHub 更新预览，以及中英文网页界面。

SystemSync is a local-first LAN control panel for a Mac/Windows Syncthing pair. It adds project-safe filename auditing, safe-copy normalization, device presence, Wake-on-LAN, storage target selection, new device pairing, GitHub update previews, and a bilingual Chinese/English web UI.

## 功能 / What It Does

- 显示 Syncthing 同步进度、连接方式、文件夹状态和最近任务。
- Shows Syncthing progress, connection type, folder state, and recent operations.
- 在同步前扫描工程文件夹，检查 Windows/macOS 文件名兼容问题。
- Scans project folders for Windows/macOS filename problems before sync.
- 默认创建规范化副本；也可单独预览源路径改名清单，确认后才把源工程名称同步为规范名。
- Creates a normalized copy by default; source-path renames are previewed separately and applied only after confirmation.
- 写入 `_CrossPlatformReport`，包含映射 JSON/CSV 和 After Effects 重新链接辅助脚本。
- Writes `_CrossPlatformReport` with mapping JSON/CSV and After Effects relink helper scripts.
- 在网页控制台集中查看规范化副本、重命名映射、冲突消解、跳过项和风险提醒，避免多个安全副本难以追踪。
- Reviews normalized copies, rename mappings, collision resolutions, skipped items, and risk notes directly in the web console so safe copies remain traceable.
- 通过 Windows companion agent 回报 Windows 磁盘容量和设备状态。
- Reports Windows disk capacity and device state through the Windows companion agent.
- 可把大型工程注册为单独 Syncthing 文件夹，并指定 Windows 目标磁盘/路径。
- Registers large projects as separate Syncthing folders with a chosen Windows target disk/path.
- 检测 Adobe/Unity 工程、字体、插件、预设和外部路径依赖，并把项目本地依赖打包进 `_DependencyBundle` 同步到另一端。
- Detects Adobe/Unity projects, fonts, plugins, presets, and external-path dependencies, then bundles project-local dependencies into `_DependencyBundle` for sync.
- 可从命名检查或存储页面新增同步文件夹。
- Adds new sync folders from either the naming workflow or the storage workflow.
- 在固件和网络支持时发送 Wake-on-LAN 唤醒包。
- Sends Wake-on-LAN packets when firmware and network settings support it.
- 提供新电脑或 Android Syncthing 客户端的配对页面。
- Provides a pairing page for new computers or Android Syncthing clients.
- Mac Dock 与 Windows 桌面/开始菜单使用同一类 `SystemSync` 智能启动器：Mac 本机优先用 `127.0.0.1`，Windows/其他设备优先用 Mac 局域网 IP，`system-sync.local` 只是 hosts 可用时的可选别名。
- The Mac Dock and Windows desktop/Start Menu use the same kind of `SystemSync` smart launcher: Mac prefers `127.0.0.1`, Windows and other devices prefer the Mac LAN IP, and `system-sync.local` is only an optional alias when hosts is configured.
- 检查配置的 GitHub 仓库是否有新版本，并显示更新预览气泡。
- Checks the configured GitHub repository for newer tool architecture releases and shows an update preview bubble.
- 支持网页控制台中文/英文切换。
- Switches the web UI between Chinese and English.
- 在网页控制台和系统启动器中使用同一套应用图标，并支持从网页刷新 Mac Dock 启动器。
- Uses the same app icon in the web console and system launchers, with web actions to refresh the Mac Dock launcher.

## 要求 / Requirements

- Mac 控制端需要 Python 3.9 或更新版本。
- Python 3.9 or newer on the Mac controller.
- 每台桌面节点都需要安装并运行 Syncthing。
- Syncthing installed and running on each desktop node.
- Windows companion agent 需要 Windows PowerShell 5+。
- Windows PowerShell 5+ for the companion agent.
- 两台设备需要在同一个局域网内，才能获得直连同步和 Wake-on-LAN 的最佳效果。
- The two devices should be on the same LAN for direct sync and Wake-on-LAN.

## Clone 快速复刻 / Clone Quick Setup

第一次 clone 后，Mac 控制端运行 `./setup.sh`。它会创建缺省配置、安装后台服务、刷新 Dock 入口、生成 Windows 配对包，并在 `sync_root` 存在时把 Windows 工具包复制到 `_tools/SystemSyncWindows`。

After cloning for the first time, run `./setup.sh` on the Mac controller. It creates the default config, installs the background service, refreshes the Dock launcher, generates the Windows pairing package, and copies the Windows tools to `_tools/SystemSyncWindows` when `sync_root` exists.

```sh
git clone https://github.com/RedHong01/SystemSync.git
cd SystemSync
./setup.sh
```

然后填写或确认设备 ID、局域网地址和同步路径。完整流程见 [Clone 复刻部署 / Clone setup](docs/CLONE_SETUP.md)。

Then fill in or confirm your device IDs, LAN addresses, and sync paths. See [Clone 复刻部署 / Clone setup](docs/CLONE_SETUP.md) for the full flow.

```sh
python3 server.py
```

打开 / Open:

```text
http://127.0.0.1:8765
```

Windows 安装 companion 后，直接点击桌面或开始菜单里的智能启动器。Mac 和 Windows 都可以手动输入 Mac 局域网 IP fallback：

After installing the Windows companion, click the smart launcher on the desktop or Start Menu. On both Mac and Windows, use the Mac LAN IP fallback for manual entry:

```text
http://192.168.0.243:8765
```

手动安装为登录后自动启动服务 / Manual login-service install:

```sh
./install-mac-service.sh
```

手动刷新 Dock 智能启动器 / Manual Dock smart launcher refresh:

```sh
./mac/install-dock-shortcut.sh
```

## Windows 伴随服务 / Windows Companion

`./setup.sh` 会自动生成配对后的 Windows 配置；手动兜底命令是：

`./setup.sh` automatically generates the paired Windows config on the Mac; the manual fallback command is:

```sh
python3 generate_windows_config.py
```

把 `windows` 文件夹复制到 Windows 电脑，在该文件夹内用管理员 PowerShell 运行：

Copy the `windows` folder to the Windows computer, open PowerShell in that folder, and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

`setup.ps1` 会在需要时请求管理员权限，然后安装 companion、创建防火墙规则、计划任务、Startup 兜底项、桌面入口和开始菜单入口。Companion 默认监听 TCP 8766，用于回报设备/磁盘状态、记录 Windows 可暴露的电源事件，并在选定目标磁盘上注册工程文件夹。`generate_windows_config.py` 还会生成 `OpenSystemSyncDashboard.generated.url`，Windows 可在 companion 尚未恢复时直接打开 Mac 统一控制台。

`setup.ps1` requests administrator permission when needed, then installs the companion, firewall rule, scheduled task, Startup fallback, desktop entry, and Start Menu entry. The companion listens on TCP 8766, reports device and disk state, records power events when Windows exposes them, and registers project folders on the selected target disk. `generate_windows_config.py` also creates `OpenSystemSyncDashboard.generated.url` so Windows can open the unified Mac dashboard even before the companion is restored.

## 配对更多设备 / Pairing More Devices

打开控制台，进入 `Pairing`，复制 Mac Syncthing 设备 ID 和局域网控制台 URL，然后配置新设备。

Open the dashboard, go to `Pairing`, copy the Mac Syncthing device ID and LAN dashboard URL, then configure the new device.

- Windows/macOS：安装 Syncthing，添加 Mac 设备 ID，再把新设备 ID 粘贴到控制台并点击 `Add Device and Share lan-sync`。
- Windows/macOS: install Syncthing, add the Mac device ID, then paste the new device ID into the dashboard and click `Add Device and Share lan-sync`.
- Android：安装 Syncthing 客户端，添加 Mac 设备 ID，再从控制台批准 Android 设备。
- Android: install a Syncthing client, add the Mac device ID, then approve the Android device from the dashboard.
- iPhone/iPad：用 Safari 访问控制台做监控和操作。iOS 不适合作为稳定常驻 Syncthing 文件节点。
- iPhone/iPad: use Safari to access the dashboard for monitoring and actions. iOS is not a reliable always-on Syncthing file node.

## GitHub 更新预览 / GitHub Update Preview

在 `config.json` 中设置 `github_repo`；当前运行版本由程序内置 `APP_VERSION` 决定：

Set `github_repo` in `config.json`; the current running version comes from the built-in `APP_VERSION`:

```json
{
  "github_repo": "RedHong01/SystemSync"
}
```

当 GitHub Release 出现更新版本时，控制台会显示小型更新预览气泡，并附带 release notes 和链接。

When a newer GitHub Release exists, the dashboard shows a small update preview bubble with release notes and a link.

## 文档语言规则 / Documentation Language Rule

所有 README、GitHub 项目首页、贡献说明、安全说明、部署说明、架构说明和其他面向用户/开发者的说明文件，都必须保持中英文双语。

All README files, GitHub homepage content, contributing notes, security notes, deployment guides, architecture notes, and other user/developer-facing documentation must remain bilingual in Chinese and English.

## Repo 架构更新规则 / Repo Architecture Update Rule

每次功能、API、部署方式、目录结构、前端模块、Mac Dock 入口或 Windows companion agent 有更新后，都必须同步更新 GitHub repo 中的 `README.md`、`docs/ARCHITECTURE.md`、`docs/DEPLOYMENT.md` 和相关 release/update 说明。

Every time a feature, API, deployment flow, directory structure, front-end module, Mac Dock entry, or Windows companion agent changes, the GitHub repo must also update `README.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, and any relevant release/update notes.

## 文档 / Docs

- [架构 / Architecture](docs/ARCHITECTURE.md)
- [事件流 / Event flow](docs/EVENT_FLOW.md)
- [Clone 复刻部署 / Clone setup](docs/CLONE_SETUP.md)
- [部署 / Deployment](docs/DEPLOYMENT.md)
- [多端开发 / Multi-endpoint development](docs/MULTI_ENDPOINT_DEVELOPMENT.md)
- [工程依赖审计 / Project dependency audit](docs/DEPENDENCY_AUDIT.md)
- [Windows D 盘迁移与续传 / Windows D-drive migration and resume](docs/WINDOWS_D_DRIVE_MIGRATION.md)
- [Figma 更新流程 / Figma update workflow](docs/FIGMA_UPDATE_WORKFLOW.md)
- [安全 / Security](SECURITY.md)
- [贡献 / Contributing](CONTRIBUTING.md)

## 许可证 / License

MIT
