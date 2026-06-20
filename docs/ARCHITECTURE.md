# Architecture

Red LAN Sync Dashboard is intentionally small:

```text
Mac browser UI
  -> Python dashboard server on TCP 8765
    -> local Syncthing REST API on 127.0.0.1:8384
    -> Windows companion agent on TCP 8766
      -> Windows Syncthing REST API
      -> Windows disk and power APIs
```

## Components

- `server.py`: HTTP server, Syncthing API bridge, Wake-on-LAN sender, job runner, and pairing API.
- `project_packager.py`: cross-platform filename planner, safe-copy worker, and report writer.
- `static/`: browser dashboard.
- `windows/LanSyncAgent.ps1`: Windows companion service.
- `windows/install-agent.ps1`: Windows installer, firewall rule, scheduled task, and desktop wake shortcut.
- `generate_windows_config.py`: writes the tokenized Windows companion config.

## Trust model

- Private secrets stay in ignored runtime config files.
- Mutating API actions require localhost or the shared companion token.
- The dashboard is designed for trusted LAN use, not public internet exposure.
- Syncthing remains the file synchronization engine; this project orchestrates setup, visibility, and project hygiene.

## Project safety

The normalization workflow never renames the source folder. It builds a new destination folder and writes a report with mappings, skipped files, collisions, and optional After Effects helper scripts.
