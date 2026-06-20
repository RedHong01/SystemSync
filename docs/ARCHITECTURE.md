# 架构 / Architecture

Red LAN Sync Dashboard 刻意保持小型、可本地部署、易审计。

Red LAN Sync Dashboard is intentionally small, locally deployable, and easy to audit.

```text
Mac browser UI
  -> Python dashboard server on TCP 8765
    -> local Syncthing REST API on 127.0.0.1:8384
    -> Windows companion agent on TCP 8766
      -> Windows Syncthing REST API
      -> Windows disk and power APIs
```

## 组件 / Components

- `server.py`：HTTP server、Syncthing API bridge、Wake-on-LAN sender、任务 runner 和配对 API。
- `server.py`: HTTP server, Syncthing API bridge, Wake-on-LAN sender, job runner, and pairing API.
- `project_packager.py`：跨平台文件名规划、安全副本 worker 和报告写入器。
- `project_packager.py`: cross-platform filename planner, safe-copy worker, and report writer.
- `static/`：浏览器控制台前端。
- `static/`: browser dashboard.
- `windows/LanSyncAgent.ps1`：Windows companion service。
- `windows/LanSyncAgent.ps1`: Windows companion service.
- `windows/install-agent.ps1`：Windows 安装器、防火墙规则、计划任务和桌面唤醒快捷方式。
- `windows/install-agent.ps1`: Windows installer, firewall rule, scheduled task, and desktop wake shortcut.
- `generate_windows_config.py`：生成带 token 的 Windows companion 配置。
- `generate_windows_config.py`: writes the tokenized Windows companion config.

## 信任模型 / Trust Model

- 私有密钥保存在被忽略的运行时配置文件中。
- Private secrets stay in ignored runtime config files.
- 会修改系统状态的 API action 需要 localhost 或 shared companion token。
- Mutating API actions require localhost or the shared companion token.
- 控制台设计用于可信局域网，不用于公网暴露。
- The dashboard is designed for trusted LAN use, not public internet exposure.
- Syncthing 仍然是文件同步引擎；本项目负责设置编排、可视化和工程卫生检查。
- Syncthing remains the file synchronization engine; this project orchestrates setup, visibility, and project hygiene.

## 工程安全 / Project Safety

规范化流程不会重命名源文件夹。它会创建新的目标文件夹，并写入包含映射、跳过文件、冲突和可选 After Effects 辅助脚本的报告。

The normalization workflow never renames the source folder. It builds a new destination folder and writes a report with mappings, skipped files, collisions, and optional After Effects helper scripts.
