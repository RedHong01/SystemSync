#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
CONFIG_PATH=""
OPEN_DASHBOARD=1
COPY_WINDOWS_PACKAGE=1
RUN_PREFLIGHT=1

usage() {
    cat <<'EOF'
SystemSync macOS setup

Usage:
  ./setup.sh [--config path] [--no-open] [--no-copy-windows] [--no-preflight]

What it does:
  1. Creates config.json from config.example.json if needed.
  2. Installs/refreshed the macOS SystemSync LaunchAgent.
  3. Installs/refreshed the macOS Dock launcher.
  4. Generates the paired Windows package config.
  5. Copies the Windows package to <sync_root>/_tools/SystemSyncWindows when sync_root exists.
  6. Opens the dashboard with the OS-appropriate launcher.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --no-open)
            OPEN_DASHBOARD=0
            shift
            ;;
        --no-copy-windows)
            COPY_WINDOWS_PACKAGE=0
            shift
            ;;
        --no-preflight)
            RUN_PREFLIGHT=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ "$(/usr/bin/uname -s)" != "Darwin" ]]; then
    echo "setup.sh is for macOS. On Windows, run setup.ps1." >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required on the Mac controller." >&2
    exit 1
fi

cd "$SCRIPT_DIR"

if [[ -z "$CONFIG_PATH" ]]; then
    if [[ -f "$SCRIPT_DIR/config.json" ]]; then
        CONFIG_PATH="$SCRIPT_DIR/config.json"
    elif [[ -f "$HOME/Library/Application Support/SystemSync/config.json" ]]; then
        CONFIG_PATH="$HOME/Library/Application Support/SystemSync/config.json"
    else
        CONFIG_PATH="$SCRIPT_DIR/config.json"
    fi
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
    if [[ "$CONFIG_PATH" == "$SCRIPT_DIR/config.json" && -f "$SCRIPT_DIR/config.example.json" ]]; then
        cp "$SCRIPT_DIR/config.example.json" "$CONFIG_PATH"
        echo "Created config.json from config.example.json."
        echo "Fill in device IDs, LAN IPs, MAC addresses, and sync paths for full pairing."
    else
        echo "Config not found: $CONFIG_PATH" >&2
        exit 1
    fi
fi

chmod +x "$SCRIPT_DIR/install-mac-service.sh"
chmod +x "$SCRIPT_DIR/mac/install-dock-shortcut.sh"
chmod +x "$SCRIPT_DIR/mac/OpenDashboard.sh"

INSTALLED_CONFIG="$HOME/Library/Application Support/SystemSync/config.json"
if [[ "$CONFIG_PATH" != "$INSTALLED_CONFIG" ]]; then
    mkdir -p "$HOME/Library/Application Support/SystemSync"
    cp "$CONFIG_PATH" "$INSTALLED_CONFIG"
fi

if [[ "$RUN_PREFLIGHT" == "1" ]]; then
    python3 "$SCRIPT_DIR/scripts/preflight.py" || true
fi

"$SCRIPT_DIR/install-mac-service.sh"
"$SCRIPT_DIR/mac/install-dock-shortcut.sh"

if [[ -f "$INSTALLED_CONFIG" ]]; then
    CONFIG_PATH="$INSTALLED_CONFIG"
fi

python3 "$SCRIPT_DIR/generate_windows_config.py" --config "$CONFIG_PATH"

if [[ "$COPY_WINDOWS_PACKAGE" == "1" ]]; then
    SYNC_ROOT="$(python3 - "$CONFIG_PATH" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1]).expanduser()
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    data = {}
print(data.get("sync_root") or "")
PY
)"
    if [[ -n "$SYNC_ROOT" && -d "$SYNC_ROOT" ]]; then
        TARGET="$SYNC_ROOT/_tools/SystemSyncWindows"
        mkdir -p "$TARGET"
        /usr/bin/rsync -a "$SCRIPT_DIR/windows/" "$TARGET/"
        echo "Windows package copied to: $TARGET"
    else
        echo "Windows package generated in: $SCRIPT_DIR/windows"
        echo "Set sync_root to auto-copy it into your shared Syncthing tools folder."
    fi
fi

LOCAL_STATUS="$(/usr/bin/curl -sS -o /dev/null -w "%{http_code}" "http://127.0.0.1:8765/" || true)"
echo "Mac dashboard: http://127.0.0.1:8765 ($LOCAL_STATUS)"

LAN_URL="$(python3 - "$CONFIG_PATH" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1]).expanduser()
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    data = {}
ip = data.get("mac_ip") or ""
port = data.get("listen_port") or 8765
print(f"http://{ip}:{port}" if ip else "")
PY
)"
if [[ -n "$LAN_URL" ]]; then
    LAN_STATUS="$(/usr/bin/curl -sS -o /dev/null -w "%{http_code}" "$LAN_URL/" || true)"
    echo "LAN dashboard: $LAN_URL ($LAN_STATUS)"
fi

if [[ "$OPEN_DASHBOARD" == "1" ]]; then
    "$SCRIPT_DIR/mac/OpenDashboard.sh" --root "$SCRIPT_DIR" --config "$CONFIG_PATH" || /usr/bin/open "http://127.0.0.1:8765/"
fi

echo "SystemSync macOS setup complete."
