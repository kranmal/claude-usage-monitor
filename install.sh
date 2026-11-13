#!/usr/bin/env bash
# Install / remove Claude Usage Monitor for the current user.
#   ./install.sh [--autostart]     --autostart: start hidden in the tray at login
#   ./install.sh --uninstall
set -euo pipefail
BIN="$HOME/.local/bin/claude-usage-monitor"
ICON="$HOME/.local/share/icons/hicolor/scalable/apps/claude-usage-monitor.svg"
APP="$HOME/.local/share/applications/local.claude.UsageMonitor.desktop"
AUTO="$HOME/.config/autostart/claude-usage-monitor.desktop"
here="$(cd "$(dirname "$0")" && pwd)"

[[ "$(uname -s)" == "Linux" ]] || { echo "Claude Usage Monitor only supports Linux." >&2; exit 1; }

if [[ "${1:-}" == "--uninstall" ]]; then
  rm -f "$BIN" "$ICON" "$APP" "$AUTO"
  echo "Removed $BIN, $ICON, $APP and $AUTO"; exit 0
fi

mkdir -p "$(dirname "$BIN")" "$(dirname "$ICON")" "$(dirname "$APP")"
install -m 0755 "$here/claude_usage.py" "$BIN"
install -m 0644 "$here/assets/claude-usage-monitor.svg" "$ICON"
sed "s|@EXEC@|$BIN|" "$here/claude-usage-monitor.desktop" > "$APP"
echo "Installed: $BIN"
echo "Menu entry: $APP"
if [[ "${1:-}" == "--autostart" ]]; then
  mkdir -p "$(dirname "$AUTO")"
  sed "s|@EXEC@|$BIN --hidden|" "$here/claude-usage-monitor.desktop" > "$AUTO"
  echo "Autostart: $AUTO (starts hidden in the tray)"
fi
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
python3 - <<'PY' 2>/dev/null || echo "WARNING: missing GTK4 / libadwaita / pycairo Python bindings. See README > Requirements."
import gi, cairo
gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
PY
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "Note: add ~/.local/bin to PATH to run 'claude-usage-monitor'.";; esac
