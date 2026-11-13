#!/bin/bash
# Sets ClipForge up on a Mac: tools, Python environment, an always-on local dashboard
# (launchd) and a ClipForge.app that opens it. Safe to run again.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${CLIPFORGE_PORT:-8787}"
LABEL="com.clipforge.dashboard"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
APP="$HOME/Applications/ClipForge.app"

if ! command -v brew >/dev/null; then
  echo "Homebrew is required: https://brew.sh" >&2
  exit 1
fi
BREW_PREFIX="$(brew --prefix)"

echo "==> Installing tools (ffmpeg with caption support, deno for yt-dlp, node for Postiz)"
# Homebrew's default ffmpeg no longer ships libass, which the burned-in captions need.
brew list ffmpeg-full >/dev/null 2>&1 || brew install ffmpeg-full
brew list deno >/dev/null 2>&1 || brew install deno
command -v node >/dev/null || brew install node
command -v python3 >/dev/null || brew install python

TOOL_PATH="$BREW_PREFIX/opt/ffmpeg-full/bin:$BREW_PREFIX/bin:/usr/local/bin:/usr/bin:/bin"

echo "==> Python environment"
python3 -m venv "$REPO/.venv"
"$REPO/.venv/bin/pip" install --quiet --upgrade pip
"$REPO/.venv/bin/pip" install --quiet -e "$REPO"

[ -f "$REPO/config.toml" ] || cp "$REPO/config.example.toml" "$REPO/config.toml"
[ -f "$REPO/.env" ] || cp "$REPO/.env.example" "$REPO/.env"
mkdir -p "$REPO/workspace" "$HOME/Library/LaunchAgents" "$HOME/Applications"

echo "==> Dashboard service (starts at login, restarts if it stops)"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$REPO/.venv/bin/clipforge</string>
    <string>serve</string>
    <string>--port</string>
    <string>$PORT</string>
  </array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$TOOL_PATH</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$REPO/workspace/dashboard.log</string>
  <key>StandardErrorPath</key><string>$REPO/workspace/dashboard.log</string>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "==> ClipForge.app"
mkdir -p "$APP/Contents/MacOS"
cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>ClipForge</string>
  <key>CFBundleIdentifier</key><string>com.clipforge.app</string>
  <key>CFBundleExecutable</key><string>ClipForge</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>0.1.0</string>
  <key>LSUIElement</key><true/>
</dict>
</plist>
EOF
cat > "$APP/Contents/MacOS/ClipForge" <<EOF
#!/bin/bash
# Make sure the dashboard service is running, then open it.
launchctl kickstart "gui/\$(id -u)/$LABEL" 2>/dev/null || true
open "http://127.0.0.1:$PORT"
EOF
chmod +x "$APP/Contents/MacOS/ClipForge"

echo
PATH="$TOOL_PATH:$PATH" "$REPO/.venv/bin/clipforge" doctor || true
echo
echo "Done. Open ClipForge from ~/Applications (or http://127.0.0.1:$PORT)."
echo "Next: add your Claude API key to $REPO/.env and review $REPO/config.toml."
echo "Posting: npm install -g postiz && postiz auth:login, then set publish.mode = \"postiz\"."
