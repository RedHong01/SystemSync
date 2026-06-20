# Red LAN Sync Dashboard

A local-first control panel for a Mac/Windows Syncthing pair. It adds project-safe filename auditing, safe-copy normalization, device presence, Wake-on-LAN, storage target selection, and a browser UI for pairing new devices on the same LAN.

## What it does

- Shows Syncthing progress, connection type, folder state, and recent operations.
- Scans project folders for Windows/macOS filename problems before sync.
- Creates a normalized copy instead of mutating the source project.
- Writes `_CrossPlatformReport` with mapping JSON/CSV and After Effects relink helper scripts.
- Reports local and Windows disk capacity through the Windows companion agent.
- Registers per-project Syncthing folders to a target disk/path on Windows.
- Adds new sync folders from the naming workflow or storage workflow.
- Sends Wake-on-LAN packets when firmware and network settings support it.
- Adds a pairing page for new computers or Android Syncthing clients.
- Checks the configured GitHub repository for newer tool architecture releases and shows an update preview bubble.
- Switches the web UI between Chinese and English.

## Requirements

- Python 3.10 or newer on the Mac controller.
- Syncthing installed and running on each desktop node.
- Windows PowerShell 5+ for the companion agent.
- The two devices must be on the same LAN for direct sync and Wake-on-LAN.

## Quick start on Mac

Copy `config.example.json` to `config.json`, then fill in your device IDs, LAN addresses, and sync paths.

```sh
cp config.example.json config.json
python3 server.py
```

Open:

```text
http://127.0.0.1:8765
```

Install as a login service:

```sh
./install-mac-service.sh
```

Optional Dock shortcut:

```sh
./mac/install-dock-shortcut.sh
```

## Windows companion

Generate the paired Windows config on the Mac:

```sh
python3 generate_windows_config.py
```

Copy the `windows` folder to the Windows computer, open Administrator PowerShell in that folder, and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-agent.ps1
```

The companion listens on TCP 8766, reports device and disk state, records power events when Windows exposes them, and registers project folders on the selected target disk.

## Pairing more devices

Open the dashboard, go to `Pairing`, copy the Mac Syncthing device ID and LAN dashboard URL, then configure the new device:

- Windows/macOS: install Syncthing, add the Mac device ID, then paste the new device ID into the dashboard and click `Add Device and Share lan-sync`.
- Android: install a Syncthing client, add the Mac device ID, then approve the Android device from the dashboard.
- iPhone/iPad: use Safari to access the dashboard for monitoring and actions. iOS is not a reliable always-on Syncthing file node.

## GitHub update preview

Set `github_repo` and `current_version` in `config.json`:

```json
{
  "github_repo": "YOUR_GITHUB_USER/RedLanSyncDashboard",
  "current_version": "0.1.0"
}
```

When a newer GitHub Release exists, the dashboard shows a small update preview bubble with the release notes and link.

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Figma update workflow](docs/FIGMA_UPDATE_WORKFLOW.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT
