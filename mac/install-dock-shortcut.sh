#!/bin/zsh
set -euo pipefail

APP_DIR="$HOME/Applications/Red LAN Sync.app"
EXECUTABLE="$APP_DIR/Contents/MacOS/RedLanSync"
PLIST="$APP_DIR/Contents/Info.plist"

mkdir -p "$APP_DIR/Contents/MacOS"

cat > "$PLIST" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>RedLanSync</string>
    <key>CFBundleIdentifier</key>
    <string>local.red.lansync.dashboard</string>
    <key>CFBundleName</key>
    <string>Red LAN Sync</string>
    <key>CFBundleDisplayName</key>
    <string>Red LAN Sync</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
</dict>
</plist>
EOF

cat > "$EXECUTABLE" <<'EOF'
#!/bin/zsh
/usr/bin/open "http://127.0.0.1:8765"
EOF

chmod +x "$EXECUTABLE"

if ! /usr/bin/defaults read com.apple.dock persistent-apps 2>/dev/null | /usr/bin/grep -q "Red LAN Sync.app"; then
    /usr/bin/defaults write com.apple.dock persistent-apps -array-add "<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>$APP_DIR</string><key>_CFURLStringType</key><integer>0</integer></dict></dict><key>tile-type</key><string>file-tile</string></dict>"
    /usr/bin/killall Dock
fi

echo "Dock shortcut installed: $APP_DIR"
