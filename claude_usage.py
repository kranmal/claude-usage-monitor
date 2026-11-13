#!/usr/bin/env python3
"""Claude usage monitor: session + weekly limits, with reset countdowns.

Reads the Claude Code OAuth token from ~/.claude/.credentials.json and queries
the (undocumented) usage endpoint used by Claude Code's /usage. Never writes or
refreshes the token -- if it has expired, run `claude` once and it refreshes.

  python3 claude_usage.py          live
  python3 claude_usage.py --demo   fake data, no network
"""
import json, os, subprocess, sys, threading, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import cairo
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

CRED = os.path.expanduser("~/.claude/.credentials.json")
URL = "https://api.anthropic.com/api/oauth/usage"
POLL_SECONDS = 30
DEMO = "--demo" in sys.argv

# (api key, label)
LIMITS = [
    ("five_hour", "Current session"),
    ("seven_day", "Weekly · all models"),
    ("seven_day_sonnet", "Weekly · Sonnet"),
    ("seven_day_opus", "Weekly · Opus"),
]

ALERT_AT = 90  # notify once per window when % used reaches this

CSS = b"""
window.background { background-color: alpha(@window_bg_color, 0.55); }
.strip button { min-height: 16px; min-width: 16px; padding: 0 2px; margin: 0; }
progressbar trough, progressbar progress { min-height: 6px; border-radius: 3px; }
progressbar.ok progress   { background: #57a773; }
progressbar.warn progress { background: #e5a50a; }
progressbar.crit progress { background: #e5484d; }
.big { font-size: 12pt; font-weight: 800; }
.small { font-size: 8pt; }
"""


class UsageError(Exception):
    pass


def fetch():
    if DEMO:
        now = datetime.now(timezone.utc)
        return {
            "five_hour": {"utilization": 42.0, "resets_at": (now + timedelta(hours=2, minutes=13)).isoformat()},
            "seven_day": {"utilization": 71.5, "resets_at": (now + timedelta(days=3, hours=5)).isoformat()},
            "seven_day_sonnet": {"utilization": 20.0, "resets_at": (now + timedelta(days=3, hours=5)).isoformat()},
            "seven_day_opus": None,
        }
    try:
        with open(CRED) as f:
            oauth = json.load(f)["claudeAiOauth"]
    except (OSError, KeyError, ValueError):
        raise UsageError("No Claude Code login found. Run `claude` and log in.")
    if oauth.get("expiresAt", 0) / 1000 < time.time():
        raise UsageError("Token expired. Run `claude` once to refresh it.")
    req = urllib.request.Request(URL, headers={
        "Authorization": "Bearer " + oauth["accessToken"],
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "claude-usage-monitor",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise UsageError("Unauthorized. Run `claude` once to refresh login.")
        raise UsageError(f"HTTP {e.code} from usage endpoint")
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise UsageError(f"Network error: {e}")


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fmt_delta(td):
    s = max(0, int(td.total_seconds()))
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s:02d}s"


def fmt_when(dt):
    local = dt.astimezone()
    today = datetime.now().astimezone().date()
    if local.date() == today:
        return local.strftime("today %H:%M")
    if local.date() == today + timedelta(days=1):
        return local.strftime("tomorrow %H:%M")
    return local.strftime("%a %d %b %H:%M")


SNI_XML = """
<node><interface name="org.kde.StatusNotifierItem">
 <method name="Activate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
 <method name="SecondaryActivate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
 <method name="ContextMenu"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
 <method name="Scroll"><arg type="i" direction="in"/><arg type="s" direction="in"/></method>
 <property name="Category" type="s" access="read"/>
 <property name="Id" type="s" access="read"/>
 <property name="Title" type="s" access="read"/>
 <property name="Status" type="s" access="read"/>
 <property name="WindowId" type="u" access="read"/>
 <property name="IconName" type="s" access="read"/>
 <property name="IconPixmap" type="a(iiay)" access="read"/>
 <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
 <property name="ItemIsMenu" type="b" access="read"/>
 <property name="Menu" type="o" access="read"/>
 <signal name="NewIcon"/><signal name="NewToolTip"/>
</interface></node>"""

MENU_XML = """
<node><interface name="com.canonical.dbusmenu">
 <method name="GetLayout"><arg type="i" direction="in"/><arg type="i" direction="in"/><arg type="as" direction="in"/>
  <arg type="u" direction="out"/><arg type="(ia{sv}av)" direction="out"/></method>
 <method name="GetGroupProperties"><arg type="ai" direction="in"/><arg type="as" direction="in"/>
  <arg type="a(ia{sv})" direction="out"/></method>
 <method name="GetProperty"><arg type="i" direction="in"/><arg type="s" direction="in"/><arg type="v" direction="out"/></method>
 <method name="Event"><arg type="i" direction="in"/><arg type="s" direction="in"/><arg type="v" direction="in"/><arg type="u" direction="in"/></method>
 <method name="EventGroup"><arg type="a(isvu)" direction="in"/><arg type="ai" direction="out"/></method>
 <method name="AboutToShow"><arg type="i" direction="in"/><arg type="b" direction="out"/></method>
 <method name="AboutToShowGroup"><arg type="ai" direction="in"/><arg type="ai" direction="out"/><arg type="ai" direction="out"/></method>
 <property name="Version" type="u" access="read"/>
 <property name="TextDirection" type="s" access="read"/>
 <property name="Status" type="s" access="read"/>
 <property name="IconThemePaths" type="as" access="read"/>
 <signal name="LayoutUpdated"><arg type="u"/><arg type="i"/></signal>
</interface></node>"""


def render_icon(pct_left, level, size=64):
    """Dark disc, ring showing % left in level colour, number centred. ARGB32 big-endian bytes."""
    from math import pi
    col = {"ok": (0.34, 0.65, 0.45), "warn": (0.90, 0.65, 0.04), "crit": (0.90, 0.28, 0.30),
           "none": (0.55, 0.55, 0.58)}[level]
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    c = cairo.Context(surf)
    mid, ring = size / 2, size * 0.095
    rad = size / 2 - ring / 2 - 1
    c.arc(mid, mid, size / 2 - 1, 0, 2 * pi)
    c.set_source_rgba(0.12, 0.12, 0.14, 0.95)
    c.fill()
    c.set_line_width(ring)
    c.arc(mid, mid, rad, 0, 2 * pi)
    c.set_source_rgba(1, 1, 1, 0.16)
    c.stroke()
    if pct_left:
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.arc(mid, mid, rad, -pi / 2, -pi / 2 + 2 * pi * max(0.02, min(1, pct_left / 100)))
        c.set_source_rgb(*col)
        c.stroke()
    txt = "–" if pct_left is None else str(int(round(pct_left)))
    c.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    c.set_font_size(size * (0.44 if len(txt) < 3 else 0.34))
    ext = c.text_extents(txt)
    c.move_to(mid - ext.width / 2 - ext.x_bearing, mid - ext.height / 2 - ext.y_bearing)
    c.set_source_rgb(1, 1, 1)
    c.show_text(txt)
    d = bytes(surf.get_data())
    out = bytearray(len(d))
    out[0::4], out[1::4], out[2::4], out[3::4] = d[3::4], d[2::4], d[1::4], d[0::4]
    return bytes(out)


class Tray:
    """Minimal StatusNotifierItem (KDE/most DEs). ok=False if no watcher is running."""

    def __init__(self, on_activate, items):
        self.ok = False
        self.on_activate = on_activate
        # items: [(label, callback)]; None label = separator. ids start at 1.
        self.items = {i + 1: it for i, it in enumerate(items)}
        self.icon = render_icon(None, "none")
        self.tip = "Claude usage"
        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION)
            node = Gio.DBusNodeInfo.new_for_xml(SNI_XML)
            self.reg_id = self.bus.register_object(
                "/StatusNotifierItem", node.interfaces[0], self._call, self._get, None)
            self.bus.register_object("/MenuBar", Gio.DBusNodeInfo.new_for_xml(MENU_XML).interfaces[0],
                                     self._menu_call, self._menu_get, None)
            name = f"org.kde.StatusNotifierItem-{os.getpid()}-1"
            Gio.bus_own_name_on_connection(self.bus, name, Gio.BusNameOwnerFlags.NONE, None, None)
            self.bus.call_sync("org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher",
                               "org.kde.StatusNotifierWatcher", "RegisterStatusNotifierItem",
                               GLib.Variant("(s)", (name,)), None, Gio.DBusCallFlags.NONE, 2000, None)
            self.ok = True
        except Exception as e:
            print("tray unavailable:", e, file=sys.stderr)

    def _call(self, conn, sender, path, iface, method, params, inv):
        if method in ("Activate", "SecondaryActivate"):
            GLib.idle_add(self.on_activate)
        inv.return_value(None)

    def _get(self, conn, sender, path, iface, prop):
        pm = GLib.Variant("a(iiay)", [(64, 64, list(self.icon))])
        return {
            "Category": GLib.Variant("s", "ApplicationStatus"),
            "Id": GLib.Variant("s", "claude-usage-monitor"),
            "Title": GLib.Variant("s", "Claude Usage"),
            "Status": GLib.Variant("s", "Active"),
            "WindowId": GLib.Variant("u", 0),
            "IconName": GLib.Variant("s", ""),
            "IconPixmap": pm,
            "ToolTip": GLib.Variant("(sa(iiay)ss)", ("", [], "Claude usage", self.tip)),
            "ItemIsMenu": GLib.Variant("b", False),
            "Menu": GLib.Variant("o", "/MenuBar"),
        }.get(prop)

    # --- com.canonical.dbusmenu ---
    def _props(self, i):
        label, _ = self.items[i]
        if label is None:
            return {"type": GLib.Variant("s", "separator")}
        return {"label": GLib.Variant("s", label), "enabled": GLib.Variant("b", True),
                "visible": GLib.Variant("b", True)}

    def _menu_get(self, conn, sender, path, iface, prop):
        return {"Version": GLib.Variant("u", 3), "TextDirection": GLib.Variant("s", "ltr"),
                "Status": GLib.Variant("s", "normal"), "IconThemePaths": GLib.Variant("as", [])}.get(prop)

    def _menu_call(self, conn, sender, path, iface, method, params, inv):
        a = params.unpack()
        V = GLib.Variant
        if method == "GetLayout":
            kids = [V("v", V("(ia{sv}av)", (i, self._props(i), []))) for i in self.items]
            root = (0, {"children-display": V("s", "submenu")}, kids)
            inv.return_value(V("(u(ia{sv}av))", (1, root)))
        elif method == "GetGroupProperties":
            ids = a[0] or list(self.items)
            inv.return_value(V("(a(ia{sv}))", ([(i, self._props(i)) for i in ids if i in self.items],)))
        elif method == "GetProperty":
            p = self._props(a[0]).get(a[1]) if a[0] in self.items else None
            inv.return_value(V("(v)", (p or V("s", ""),)))
        elif method == "Event":
            if a[1] == "clicked" and a[0] in self.items:
                cb = self.items[a[0]][1]
                if cb:
                    GLib.idle_add(cb)
            inv.return_value(None)
        elif method == "EventGroup":
            for i, ev, _d, _t in a[0]:
                if ev == "clicked" and i in self.items and self.items[i][1]:
                    GLib.idle_add(self.items[i][1])
            inv.return_value(V("(ai)", ([],)))
        elif method == "AboutToShow":
            inv.return_value(V("(b)", (False,)))
        elif method == "AboutToShowGroup":
            inv.return_value(V("(aiai)", ([], [])))
        else:
            inv.return_value(None)

    def update(self, pct_left, level, tip):
        if not self.ok:
            return
        self.icon, self.tip = render_icon(pct_left, level), tip
        for sig in ("NewIcon", "NewToolTip"):
            self.bus.emit_signal(None, "/StatusNotifierItem", "org.kde.StatusNotifierItem", sig, None)


def notify(title, body):
    try:
        subprocess.Popen(["notify-send", "-a", "Claude Usage", "-u", "critical",
                          "-i", "dialog-warning", title, body])
    except OSError:
        pass


def level_of(used):
    return "crit" if used >= 90 else "warn" if used >= 70 else "ok"


class Row(Gtk.Box):
    def __init__(self, label):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self.resets_at = None
        head = Gtk.Box(spacing=8)
        self.title = Gtk.Label(label=label, xalign=0, hexpand=True)
        self.title.add_css_class("small")
        self.left = Gtk.Label(xalign=1)
        self.left.add_css_class("big")
        head.append(self.title)
        head.append(self.left)
        self.bar = Gtk.ProgressBar()
        self.sub = Gtk.Label(xalign=0)
        self.sub.add_css_class("dim-label")
        self.sub.add_css_class("small")
        for w in (head, self.bar, self.sub):
            self.append(w)

    def set_data(self, d):
        used = float(d.get("utilization") or 0)
        used = min(100.0, max(0.0, used))
        self.used = used
        self.bar.set_fraction(used / 100)
        for c in ("ok", "warn", "crit"):
            self.bar.remove_css_class(c)
        self.bar.add_css_class(level_of(used))
        self.left.set_text(f"{100 - used:.0f}% left")
        ra = d.get("resets_at")
        self.resets_at = parse_ts(ra) if ra else None
        self.tick()

    def tick(self):
        if self.resets_at is None:
            self.sub.set_text(f"{self.used:.0f}% used · no active window")
            return
        delta = self.resets_at - datetime.now(timezone.utc)
        if delta.total_seconds() <= 0:
            self.sub.set_text(f"{self.used:.0f}% used · resetting…")
        else:
            self.sub.set_text(f"{self.used:.0f}% used · resets {fmt_delta(delta)} · {fmt_when(self.resets_at)}")


class Win(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Claude Usage", default_width=300, default_height=1)
        self.set_size_request(1, 1)  # drop Adw default 360x200 minimum
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                           margin_top=4, margin_bottom=10, margin_start=12, margin_end=8)
        strip = Gtk.Box(spacing=4, css_classes=["strip"])
        btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh now", has_frame=False)
        btn.connect("clicked", lambda *_: self.refresh())
        self.status = Gtk.Label(label="Claude Usage", css_classes=["small", "dim-label"],
                                ellipsize=3, hexpand=True, xalign=0)
        x = Gtk.Button(icon_name="window-close-symbolic", tooltip_text="Hide to tray", has_frame=False)
        x.connect("clicked", lambda *_: self.close())
        for w in (btn, self.status, x):
            strip.append(w)
        self.box.append(strip)
        self.rows = {}
        for key, label in LIMITS:
            r = Row(label)
            r.set_visible(False)
            self.rows[key] = r
            self.box.append(r)
        self.set_content(Gtk.WindowHandle(child=self.box))  # drag anywhere to move
        self.last_ok = None
        self.alerted = set()
        self.tray = Tray(self.toggle, [
            ("Show / hide window", self.toggle),
            ("Refresh now", self.refresh),
            (None, None),
            ("Quit", app.quit),
        ])
        self.connect("close-request", self._close)
        self.refresh()
        GLib.timeout_add_seconds(POLL_SECONDS, self._poll)
        GLib.timeout_add_seconds(1, self._tick)

    def toggle(self):
        if self.get_visible():
            self.set_visible(False)
        else:
            self.present()

    def _close(self, *_):
        if self.tray.ok:
            self.set_visible(False)
            return True
        return False

    def _poll(self):
        self.refresh()
        return True

    def _tick(self):
        for r in self.rows.values():
            if r.get_visible():
                r.tick()
        return True

    def refresh(self):
        def work():
            try:
                GLib.idle_add(self.apply, fetch(), None)
            except UsageError as e:
                GLib.idle_add(self.apply, None, str(e))
            except Exception as e:  # keep the UI alive on odd payloads
                GLib.idle_add(self.apply, None, f"Unexpected error: {e}")
        threading.Thread(target=work, daemon=True).start()

    def apply(self, data, err):
        if err:
            self.status.set_text(err + (f"  (showing data from {self.last_ok:%H:%M})" if self.last_ok else ""))
            return
        try:
            for key, row in self.rows.items():
                d = data.get(key)
                row.set_visible(bool(d))
                if d:
                    row.set_data(d)
        except Exception as e:
            self.status.set_text(f"Unexpected response shape: {e}")
            return
        self.last_ok = datetime.now()
        self._tray_and_alerts()
        self.status.set_text(f"Updated {self.last_ok:%H:%M:%S}" + (" · demo data" if DEMO else ""))


    def _tray_and_alerts(self):
        lines, session = [], self.rows["five_hour"]
        for key, label in LIMITS:
            r = self.rows[key]
            if not r.get_visible():
                continue
            lines.append(f"{label}: {100 - r.used:.0f}% left")
            if r.resets_at:
                lines[-1] += f" (resets {fmt_when(r.resets_at)})"
            tag = (key, r.resets_at)
            if r.used >= ALERT_AT and tag not in self.alerted:
                self.alerted.add(tag)
                notify(f"{label}: {100 - r.used:.0f}% left",
                       f"Resets {fmt_when(r.resets_at)}" if r.resets_at else "Nearly used up")
        if session.get_visible():
            self.tray.update(100 - session.used, level_of(session.used), "\n".join(lines))


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="local.claude.UsageMonitor")

    def do_activate(self):
        if not getattr(self, "_css", False):
            p = Gtk.CssProvider()
            p.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self._css = True
        first = self.get_active_window() is None
        win = self.get_active_window() or Win(self)
        if first:
            self.hold()  # stay alive in tray while window is hidden
        if first and "--hidden" in sys.argv and win.tray.ok:
            return  # autostart: tray only, click icon to open
        win.present()


if __name__ == "__main__":
    Gtk.Window.set_default_icon_name("claude-usage-monitor")
    sys.exit(App().run([sys.argv[0]]))
