#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=${0:A:h}
INSTALL_DIR="$HOME/Library/Application Support/SystemSync"
LEGACY_INSTALL_DIR="$HOME/Library/Application Support/RedLanSyncDashboard"
PLIST="$HOME/Library/LaunchAgents/com.redwang.systemsync.plist"
LABEL="com.redwang.systemsync"
LEGACY_LABEL="com.redwang.lansyncdashboard"
LOG_DIR="$HOME/Library/Logs"
PYTHON_BIN="$(command -v python3)"
BACKUP_DIR="$(mktemp -d)"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR" "$INSTALL_DIR"

for runtime_file in config.json runtime-state.json; do
    if [[ -f "$INSTALL_DIR/$runtime_file" ]]; then
        cp "$INSTALL_DIR/$runtime_file" "$BACKUP_DIR/$runtime_file"
    elif [[ -f "$LEGACY_INSTALL_DIR/$runtime_file" ]]; then
        cp "$LEGACY_INSTALL_DIR/$runtime_file" "$BACKUP_DIR/$runtime_file"
    fi
done

/usr/bin/ditto "$SCRIPT_DIR" "$INSTALL_DIR"

for runtime_file in config.json runtime-state.json; do
    if [[ -f "$BACKUP_DIR/$runtime_file" ]]; then
        cp "$BACKUP_DIR/$runtime_file" "$INSTALL_DIR/$runtime_file"
    fi
done
rm -rf "$BACKUP_DIR"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$INSTALL_DIR/server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/SystemSync.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/SystemSync.error.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$UID/$LEGACY_LABEL" 2>/dev/null || true
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
BOOTSTRAPPED=0
BOOTSTRAP_LOG="$(mktemp)"
for attempt in 1 2 3; do
    if launchctl bootstrap "gui/$UID" "$PLIST" 2>"$BOOTSTRAP_LOG"; then
        BOOTSTRAPPED=1
        break
    fi
    sleep 1
    launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
done
if [[ "$BOOTSTRAPPED" != "1" ]]; then
    echo "SystemSync LaunchAgent bootstrap failed after retrying." >&2
    cat "$BOOTSTRAP_LOG" >&2 || true
    rm -f "$BOOTSTRAP_LOG"
    exit 1
fi
rm -f "$BOOTSTRAP_LOG"
launchctl enable "gui/$UID/$LABEL"
launchctl kickstart -k "gui/$UID/$LABEL"

echo "SystemSync installed: http://127.0.0.1:8765"
