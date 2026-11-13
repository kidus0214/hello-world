#!/bin/bash
# Stops the dashboard service and removes ClipForge.app. Your clips and config stay.
set -euo pipefail

LABEL="com.clipforge.dashboard"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/Applications/ClipForge.app"
echo "ClipForge service and app removed. The repo folder (clips, config) was left untouched."
