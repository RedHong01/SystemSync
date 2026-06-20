# 部署 / Deployment

## Mac 控制端 / Mac Controller

1. 安装并启动 Syncthing。 / Install and start Syncthing.
2. 复制 `config.example.json` 为 `config.json`。 / Copy `config.example.json` to `config.json`.
3. 填写本机和远端设备 ID、局域网 IP、MAC 地址和同步根目录。 / Fill in the local and remote device IDs, LAN IPs, MAC addresses, and sync roots.
4. 启动控制台。 / Start the dashboard:

```sh
python3 server.py
```

5. 安装为登录后自动启动服务。 / Install it as a login service:

```sh
./install-mac-service.sh
```

6. 可选 Dock 快捷方式。 / Optional Dock shortcut:

```sh
./mac/install-dock-shortcut.sh
```

## Windows 节点 / Windows Node

1. 安装 Syncthing，并确认本地 GUI 可以打开。 / Install Syncthing and confirm the local GUI works.
2. 在 Mac 上运行。 / Run this on the Mac:

```sh
python3 generate_windows_config.py
```

3. 把 `windows` 文件夹复制到 Windows 机器。 / Copy the `windows` folder to the Windows machine.
4. 在该文件夹内打开管理员 PowerShell。 / Open Administrator PowerShell in that folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-agent.ps1
```

5. 确认 Windows 防火墙允许 TCP 8766 和 Syncthing 端口。 / Confirm Windows firewall allows TCP 8766 and Syncthing ports.

## 目标磁盘选择 / Storage Target Selection

在控制台打开 `Storage`：

In the dashboard, open `Storage`:

- 保存默认 Windows 工程根目录，例如 `D:\LanSyncProjects`。
- Save the default Windows project root, such as `D:\LanSyncProjects`.
- 如果希望大型工程落在指定磁盘上，把每个大型工程注册为单独 Syncthing 文件夹。
- Register each large project as its own Syncthing folder when you want it on a specific disk.
- 使用绝对 Windows 路径。Companion agent 会拒绝相对路径。
- Use absolute Windows paths. Relative paths are rejected by the companion agent.

## 局域网唤醒 / Wake-on-LAN

Wake-on-LAN 需要：

Wake-on-LAN requires:

- BIOS/UEFI 支持唤醒。
- BIOS/UEFI wake support.
- Windows 网卡开启 magic packet 唤醒。
- Windows network adapter magic packet support.
- 至少一台在线设备发送唤醒包。
- One online device to send the wake packet.
- 路由器允许局域网广播流量。
- LAN broadcast traffic allowed by the router.

如果远端电脑完全断电，且网卡没有保持可唤醒状态，软件无法唤醒它。

If the remote computer is fully powered off and the adapter does not stay armed, software cannot wake it.
