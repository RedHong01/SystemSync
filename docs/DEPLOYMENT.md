# Deployment

## Mac controller

1. Install and start Syncthing.
2. Copy `config.example.json` to `config.json`.
3. Fill in the local and remote device IDs, LAN IPs, MAC addresses, and sync roots.
4. Start the dashboard:

```sh
python3 server.py
```

5. Install it as a login service:

```sh
./install-mac-service.sh
```

6. Optional Dock shortcut:

```sh
./mac/install-dock-shortcut.sh
```

## Windows node

1. Install Syncthing and confirm the local GUI works.
2. Run this on the Mac:

```sh
python3 generate_windows_config.py
```

3. Copy the `windows` folder to the Windows machine.
4. Open Administrator PowerShell in that folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-agent.ps1
```

5. Confirm Windows firewall allows TCP 8766 and Syncthing ports.

## Storage target selection

In the dashboard, open `Storage`:

- Save the default Windows project root, such as `D:\LanSyncProjects`.
- Register each large project as its own Syncthing folder when you want it on a specific disk.
- Use absolute Windows paths. Relative paths are rejected by the companion agent.

## Wake-on-LAN

Wake-on-LAN requires:

- BIOS/UEFI wake support.
- Windows network adapter magic packet support.
- One online device to send the wake packet.
- LAN broadcast traffic allowed by the router.

If the remote computer is fully powered off and the adapter does not stay armed, software cannot wake it.
