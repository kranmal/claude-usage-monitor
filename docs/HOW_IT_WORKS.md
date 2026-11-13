# How it works

## Data source

Claude Code's `/usage` view is backed by an OAuth-authenticated endpoint:

```
GET https://api.anthropic.com/api/oauth/usage
Authorization: Bearer <Claude Code access token>
anthropic-beta: oauth-2025-04-20
```

The response contains one object per limit, each with a `utilization` (% used) and a `resets_at` timestamp:

| Key | Meaning |
|-----|---------|
| `five_hour` | current session window |
| `seven_day` | weekly limit, all models |
| `seven_day_sonnet` / `seven_day_opus` | per-model weekly limits, when your plan has them (otherwise `null`) |

**This endpoint is undocumented.** It was working at the time of writing; Anthropic may change it without notice. The app treats any unexpected shape as an error and shows it in the status line rather than crashing.

## Credentials

The token comes from `~/.claude/.credentials.json` (`claudeAiOauth.accessToken`), the file Claude Code maintains.

- The file is only ever **read**. The app does not refresh the token, because refreshing rotates the refresh token and could log Claude Code out.
- The token is sent to `api.anthropic.com` and nowhere else.
- When it expires, the status line says so; running `claude` once refreshes it and the monitor recovers on the next poll.

## Tray icon

GTK 4 has no tray API, so the app speaks the D-Bus **StatusNotifierItem** protocol directly (`org.kde.StatusNotifierItem`) and exposes the right-click menu via **dbusmenu** (`com.canonical.dbusmenu`). The icon is drawn with cairo and sent as an ARGB32 pixmap whenever the numbers change. KDE Plasma hosts this natively; GNOME needs the AppIndicator/KStatusNotifierItem extension.

## Alerts

Notifications are sent with `notify-send`. An alert is remembered per `(limit, reset time)`, so you get one per window and a fresh one after it resets.
