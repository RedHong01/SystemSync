# Red LAN Sync Dashboard / 红色局域网同步控制台

Red LAN Sync Dashboard 是一个本地优先的 Mac/Windows Syncthing 局域网同步控制台。它在 Syncthing 之上增加工程文件命名检查、安全副本规范化、双端状态、Wake-on-LAN、目标磁盘选择、新设备配对、GitHub 更新预览，以及中英文网页界面。

Red LAN Sync Dashboard is a local-first LAN control panel for a Mac/Windows Syncthing pair. It adds project-safe filename auditing, safe-copy normalization, device presence, Wake-on-LAN, storage target selection, new device pairing, GitHub update previews, and a bilingual Chinese/English web UI.

## 功能 / What It Does

- 显示 Syncthing 同步进度、连接方式、文件夹状态和最近任务。
- Shows Syncthing progress, connection type, folder state, and recent operations.
- 在同步前扫描工程文件夹，检查 Windows/macOS 文件名兼容问题。
- Scans project folders for Windows/macOS filename problems before sync.
- 创建规范化副本，不直接修改源工程。
- Creates a normalized copy instead of mutating the source project.
- 写入 `_CrossPlatformReport`，包含映射 JSON/CSV 和 After Effects 重新链接辅助脚本。
- Writes `_CrossPlatformReport` with mapping JSON/CSV and After Effects relink helper scripts.
- 通过 Windows companion agent 回报 Windows 磁盘容量和设备状态。
- Reports Windows disk capacity and device state through the Windows companion agent.
- 可把大型工程注册为单独 Syncthing 文件夹，并指定 Windows 目标磁盘/路径。
- Registers large projects as separate Syncthing folders with a chosen Windows target disk/path.
- 可从命名检查或存储页面新增同步文件夹。
- Adds new sync folders from either the naming workflow or the storage workflow.
- 在固件和网络支持时发送 Wake-on-LAN 唤醒包。
- Sends Wake-on-LAN packets when firmware and network settings support it.
- 提供新电脑或 Android Syncthing 客户端的配对页面。
- Provides a pairing page for new computers or Android Syncthing clients.
- 检查配置的 GitHub 仓库是否有新版本，并显示更新预览气泡。
- Checks the configured GitHub repository for newer tool architecture releases and shows an update preview bubble.
- 支持网页控制台中文/英文切换。
- Switches the web UI between Chinese and English.

## 要求 / Requirements

- Mac 控制端需要 Python 3.10 或更新版本。
- Python 3.10 or newer on the Mac controller.
- 每台桌面节点都需要安装并运行 Syncthing。
- Syncthing installed and running on each desktop node.
- Windows companion agent 需要 Windows PowerShell 5+。
- Windows PowerShell 5+ for the companion agent.
- 两台设备需要在同一个局域网内，才能获得直连同步和 Wake-on-LAN 的最佳效果。
- The two devices should be on the same LAN for direct sync and Wake-on-LAN.

## Mac 快速开始 / Quick Start on Mac

复制 `config.example.json` 为 `config.json`，然后填写设备 ID、局域网地址和同步路径。

Copy `config.example.json` to `config.json`, then fill in your device IDs, LAN addresses, and sync paths.

```sh
cp config.example.json config.json
python3 server.py
```

打开 / Open:

```text
http://127.0.0.1:8765
```

安装为登录后自动启动服务 / Install as a login service:

```sh
./install-mac-service.sh
```

可选 Dock 快捷方式 / Optional Dock shortcut:

```sh
./mac/install-dock-shortcut.sh
```

## Windows 伴随服务 / Windows Companion

在 Mac 上生成配对后的 Windows 配置：

Generate the paired Windows config on the Mac:

```sh
python3 generate_windows_config.py
```

把 `windows` 文件夹复制到 Windows 电脑，在该文件夹内用管理员 PowerShell 运行：

Copy the `windows` folder to the Windows computer, open Administrator PowerShell in that folder, and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-agent.ps1
```

Companion 默认监听 TCP 8766，用于回报设备/磁盘状态、记录 Windows 可暴露的电源事件，并在选定目标磁盘上注册工程文件夹。

The companion listens on TCP 8766, reports device and disk state, records power events when Windows exposes them, and registers project folders on the selected target disk.

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

在 `config.json` 中设置 `github_repo` 和 `current_version`：

Set `github_repo` and `current_version` in `config.json`:

```json
{
  "github_repo": "YOUR_GITHUB_USER/RedLanSyncDashboard",
  "current_version": "0.1.0"
}
```

当 GitHub Release 出现更新版本时，控制台会显示小型更新预览气泡，并附带 release notes 和链接。

When a newer GitHub Release exists, the dashboard shows a small update preview bubble with release notes and a link.

## 文档语言规则 / Documentation Language Rule

所有 README、GitHub 项目首页、贡献说明、安全说明、部署说明、架构说明和其他面向用户/开发者的说明文件，都必须保持中英文双语。

All README files, GitHub homepage content, contributing notes, security notes, deployment guides, architecture notes, and other user/developer-facing documentation must remain bilingual in Chinese and English.

## 文档 / Docs

- [架构 / Architecture](docs/ARCHITECTURE.md)
- [部署 / Deployment](docs/DEPLOYMENT.md)
- [Figma 更新流程 / Figma update workflow](docs/FIGMA_UPDATE_WORKFLOW.md)
- [安全 / Security](SECURITY.md)
- [贡献 / Contributing](CONTRIBUTING.md)

## 许可证 / License

MIT
