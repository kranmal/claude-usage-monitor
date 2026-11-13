# Troubleshooting

The status line at the top of the window shows the last error.

| Message | Cause / fix |
|---------|-------------|
| `No Claude Code login found. Run claude and log in.` | `~/.claude/.credentials.json` is missing. Install Claude Code and log in with a Pro/Max account |
| `Token expired. Run claude once to refresh it.` | The access token expired. Start `claude`; it refreshes the token and the monitor picks it up on the next poll |
| `Unauthorized. Run claude once to refresh login.` | HTTP 401. Same fix; if it persists, log out and back in inside Claude Code |
| `HTTP 429 from usage endpoint` | Polling too often. Raise `POLL_SECONDS` ([configuration](CONFIGURATION.md)) |
| `HTTP 404` / `Unexpected response shape` | Anthropic changed the undocumented endpoint. Please [open an issue](https://github.com/kranmal/claude-usage-monitor/issues) with the message |
| `Network error: ...` | No connection or proxy problem. The last good numbers stay on screen with their time |
| `(showing data from HH:MM)` | An error happened after at least one good fetch; the numbers shown are stale |

## No tray icon

- **KDE Plasma:** should work. Check the tray isn't hiding it under the `^` arrow, and run `busctl --user list | grep StatusNotifier` to confirm a watcher exists.
- **GNOME:** install the *AppIndicator and KStatusNotifierItem Support* extension.
- No tray at all: the app prints `tray unavailable` to stderr and behaves as a normal window (closing quits).

## No notifications

Alerts use `notify-send`. Install `libnotify` (Fedora) or `libnotify-bin` (Debian/Ubuntu) and test with `notify-send hello`.

## Window isn't transparent

Transparency needs a compositing desktop. On Plasma it works on both Wayland and X11. Opacity is set in the CSS ([configuration](CONFIGURATION.md)).

## Only one row shows

Weekly Sonnet/Opus rows appear only when the API reports a limit for them. Many plans have just the session and weekly-all-models limits.

## Wrong or no icon in the taskbar

Re-run `./install.sh`. The desktop file is named `local.claude.UsageMonitor.desktop` to match the app's Wayland app id.
