# Configuration

There is no config file. Edit the constants at the top of `claude_usage.py` (or of the installed copy, `~/.local/bin/claude-usage-monitor`) and restart the app.

| Constant | Default | What it does |
|----------|---------|--------------|
| `POLL_SECONDS` | `90` | How often to fetch usage. The countdowns tick every second regardless. Very short intervals may get rate-limited by the endpoint; if you see `HTTP 429`, raise it further |
| `ALERT_AT` | `90` | Send a desktop notification when a limit reaches this % **used**. Once per limit per reset window |
| `LIMITS` | session, weekly all, weekly Sonnet, weekly Opus | Which API fields are shown and their labels. Rows with no data are hidden |
| `CSS` | | Colours, bar thickness, font sizes. `alpha(@window_bg_color, 0.55)` sets window opacity: lower is more transparent, `1.0` is solid |

The bar and tray ring are green below 70 % used, amber from 70 %, red from 90 % (`level_of()`).

## Command-line flags

- `--demo`: fake data, nothing read or sent.
- `--hidden`: start in the tray without showing the window.

## Autostart

`./install.sh --autostart` writes `~/.config/autostart/claude-usage-monitor.desktop` with `--hidden`. Delete that file to stop it starting at login.
