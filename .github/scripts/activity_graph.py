#!/usr/bin/env python3
"""Generate an animated pixel-art contribution activity graph (last 31 days)."""
import datetime
import html
import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT_PATH", "profile/activity.svg")

W, H = 900, 340
BASE = 270          # y position of the chart floor
MAX_BLOCKS = 14     # tallest column height, in pixel blocks
PITCH, BAR_W = 25, 17

MAGENTA, RED, ORANGE = "#C22B8E", "#E4402A", "#FDA136"
INK, CREAM, DIM, MUTED = "#0A0618", "#EDEDF3", "#2A2152", "#8A84A8"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

STYLE = """
.mono{font-family:'Courier New',Consolas,'DejaVu Sans Mono',monospace}
.frame{animation:frame 6s steps(3) infinite}
@keyframes frame{0%{fill:#C22B8E}33%{fill:#E4402A}66%{fill:#FDA136}100%{fill:#C22B8E}}
.col{transform-box:fill-box;transform-origin:50% 100%;animation:grow .9s steps(6) both}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
.scan{animation:scan 7.75s steps(31) infinite}
@keyframes scan{from{transform:translateX(0)}to{transform:translateX(__SCAN__px)}}
.blink{animation:on 1s steps(1) infinite}
@keyframes on{50%{opacity:0}}
.peak{animation:peak 1.2s linear infinite}
@keyframes peak{0%,49%{transform:translateY(0)}50%,100%{transform:translateY(-4px)}}
"""


def fetch_days():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": "bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "profile-activity-graph",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "GraphQL error"))
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    return [d for d in days if d["date"] <= today][-31:]


def text(x, y, s, size=12, fill=CREAM, anchor="start", bold=False, cls="mono"):
    weight = ' font-weight="bold"' if bold else ""
    return '<text x="%s" y="%s" class="%s" font-size="%d" fill="%s" text-anchor="%s"%s>%s</text>' % (
        x, y, cls, size, fill, anchor, weight, html.escape(str(s)))


def frame(h):
    return (
        '<rect x="12" y="12" width="876" height="{ih}" fill="#0A0618"/>'
        '<g class="frame" fill="#C22B8E">'
        '<rect x="16" y="8" width="868" height="4"/><rect x="16" y="{b}" width="868" height="4"/>'
        '<rect x="8" y="16" width="4" height="{sh}"/><rect x="888" y="16" width="4" height="{sh}"/>'
        '<rect x="12" y="12" width="4" height="4"/><rect x="884" y="12" width="4" height="4"/>'
        '<rect x="12" y="{c}" width="4" height="4"/><rect x="884" y="{c}" width="4" height="4"/>'
        '</g>'
    ).format(ih=h - 24, b=h - 12, sh=h - 32, c=h - 16)


def header(title, right, sub):
    return "".join([
        text(40, 50, title, 18, ORANGE, bold=True),
        text(860, 50, right, 12, CREAM, "end"),
        text(40, 72, sub, 11, MUTED),
        '<rect class="blink" x="828" y="64" width="8" height="8" fill="%s"/>' % RED,
        text(860, 72, "REC", 11, RED, "end", True),
        '<rect x="40" y="82" width="820" height="2" fill="%s"/>' % DIM,
    ])


def wrap(body, scan_px=0):
    style = STYLE.replace("__SCAN__", str(scan_px))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'shape-rendering="crispEdges"><style>%s</style>%s%s</svg>'
    ) % (W, H, W, H, style, frame(H), body)


def render(days):
    counts = [d["contributionCount"] for d in days]
    top = max(counts) if counts else 0
    maxc = top if top > 0 else 1
    total, active = sum(counts), sum(1 for c in counts if c > 0)
    left = (W - PITCH * len(days)) // 2
    width = PITCH * len(days)
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()

    parts = [header("ACTIVITY // LAST %d DAYS" % len(days),
                    "TOTAL %d  ·  PEAK %d  ·  ACTIVE DAYS %d" % (total, top, active),
                    "@%s  ·  updated %s UTC" % (USER, today))]

    for k in (4, 8, 12):
        y = BASE - k * 10
        parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-dasharray="2 6"/>' % (
            left, y, left + width, y, DIM))
    parts.append('<rect class="scan" x="%d" y="96" width="%d" height="%d" fill="%s" opacity=".08"/>' % (
        left, PITCH, BASE - 96, ORANGE))
    parts.append('<rect x="%d" y="%d" width="%d" height="2" fill="%s"/>' % (left, BASE + 2, width, DIM))

    peak_i = counts.index(top) if top > 0 else -1
    for i, (day, c) in enumerate(zip(days, counts)):
        x = left + i * PITCH + (PITCH - BAR_W) // 2
        cx = x + BAR_W / 2
        if i % 5 == 0 or i == len(days) - 1:
            parts.append(text("%.1f" % cx, BASE + 20, day["date"][5:], 10, MUTED, "middle"))
        if c == 0:
            parts.append('<rect x="%d" y="%d" width="%d" height="8" fill="%s"/>' % (x, BASE - 8, BAR_W, DIM))
            continue
        n = max(1, round(c / maxc * MAX_BLOCKS))
        blocks = []
        for b in range(n):
            frac = (b + 1) / MAX_BLOCKS
            color = MAGENTA if frac <= 0.34 else RED if frac <= 0.67 else ORANGE
            blocks.append('<rect x="%d" y="%d" width="%d" height="8" fill="%s"/>' % (
                x, BASE - (b + 1) * 10 + 2, BAR_W, color))
        parts.append('<g class="col" style="animation-delay:%.2fs">%s</g>' % (i * 0.05, "".join(blocks)))
        label_y = BASE - n * 10 - 4
        parts.append(text("%.1f" % cx, label_y, c, 10, CREAM, "middle"))
        if i == peak_i:
            ay = label_y - 22
            parts.append(
                '<g class="peak" fill="%s"><rect x="%.1f" y="%d" width="12" height="4"/>'
                '<rect x="%.1f" y="%d" width="8" height="4"/><rect x="%.1f" y="%d" width="4" height="4"/></g>' % (
                    ORANGE, cx - 6, ay, cx - 4, ay + 4, cx - 2, ay + 8))

    legend = [(40, MAGENTA, "LOW"), (100, RED, "MID"), (160, ORANGE, "HIGH")]
    for lx, color, label in legend:
        parts.append('<rect x="%d" y="306" width="8" height="8" fill="%s"/>' % (lx, color))
        parts.append(text(lx + 14, 314, label, 10, MUTED))
    parts.append(text(860, 314, "▶ INSERT COMMITS TO CONTINUE", 10, MAGENTA, "end", cls="mono blink"))

    return wrap("".join(parts), scan_px=PITCH * len(days))


def render_error(message):
    body = "".join([
        header("ACTIVITY // NO SIGNAL", "", "@%s" % USER),
        text(450, 190, "RERUN THE WORKFLOW TO RELOAD", 14, ORANGE, "middle", True),
        text(450, 214, message, 11, MUTED, "middle"),
    ])
    return wrap(body)


def main():
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    try:
        svg = render(fetch_days())
    except Exception as exc:  # keep the workflow green and show a readable card instead
        print("activity graph failed: %s" % exc, file=sys.stderr)
        svg = render_error(str(exc)[:80])
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
