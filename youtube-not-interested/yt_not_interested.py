#!/usr/bin/env python3
"""Tap "Not interested" on YouTube home-feed videos that match your rules.

Drives the real YouTube Android app over ADB using uiautomator2, so it works
without root and without touching your Google account credentials.

Usage:
    python yt_not_interested.py dump                 # open YouTube Home, save screen + UI tree
    python yt_not_interested.py sync-subs            # save the channels you subscribe to
    python yt_not_interested.py run --dry-run        # show what would be marked, tap nothing
    python yt_not_interested.py run --max 30         # mark up to 30 videos
"""

import argparse
import json
import random
import re
import signal
import sys
import time
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

YOUTUBE_PKG = "com.google.android.youtube"
BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")
HERE = Path(__file__).resolve().parent
SUBS_PATH = HERE / "subscriptions.json"


# --------------------------------------------------------------------------- config

@dataclass
class Config:
    block_keywords: list = field(default_factory=list)
    block_channels: list = field(default_factory=list)
    allow_keywords: list = field(default_factory=list)
    allow_channels: list = field(default_factory=list)
    mark_everything: bool = False
    also_dont_recommend_channel: bool = False
    skip_shorts: bool = True
    protect_subscriptions: bool = True
    subs_refresh_days: float = 7
    max_per_run: int = 25
    max_scrolls: int = 40
    delay_min: float = 1.5
    delay_max: float = 3.5
    menu_button_descs: list = field(default_factory=lambda: ["Action menu", "More actions", "More options"])
    not_interested_labels: list = field(default_factory=lambda: ["Not interested"])
    dont_recommend_labels: list = field(default_factory=lambda: ["Don't recommend channel"])
    video_desc_markers: list = field(default_factory=lambda: ["play video", "views", "watching"])
    shorts_markers: list = field(default_factory=lambda: ["play short", "#shorts"])
    subscriptions_tab_descs: list = field(default_factory=lambda: ["Subscriptions"])
    subs_all_labels: list = field(default_factory=lambda: ["All"])
    subs_ignore_texts: list = field(default_factory=lambda: [
        "All", "All subscriptions", "Subscriptions", "Manage", "Most relevant", "New activity",
        "A-Z", "Today", "Videos", "Shorts", "Live", "Posts", "Continue watching", "Unwatched",
        "New content", "Home", "You", "Search", "Settings",
    ])

    @classmethod
    def load(cls, path):
        with open(path, "rb") as f:
            raw = tomllib.load(f)
        flat = {}
        for section in raw.values():
            if isinstance(section, dict):
                flat.update(section)
        known = {k: v for k, v in flat.items() if k in cls.__dataclass_fields__}
        unknown = set(flat) - set(known)
        if unknown:
            print(f"warning: ignoring unknown config keys: {', '.join(sorted(unknown))}")
        return cls(**known)


# --------------------------------------------------------------------------- UI parsing

@dataclass
class Node:
    desc: str
    text: str
    clickable: bool
    bounds: tuple  # (x1, y1, x2, y2)

    @property
    def center(self):
        x1, y1, x2, y2 = self.bounds
        return (x1 + x2) // 2, (y1 + y2) // 2


@dataclass
class Card:
    description: str
    menu: Node


def _node(el):
    m = BOUNDS_RE.match(el.get("bounds", ""))
    bounds = tuple(int(v) for v in m.groups()) if m else (0, 0, 0, 0)
    return Node(
        desc=el.get("content-desc", "") or "",
        text=el.get("text", "") or "",
        clickable=el.get("clickable") == "true",
        bounds=bounds,
    )


def _looks_like_video(desc, cfg):
    d = desc.lower()
    return len(d) > 20 and any(m.lower() in d for m in cfg.video_desc_markers)


def find_cards(xml, cfg):
    """Pair every three-dot menu button on screen with the video it belongs to."""
    root = ET.fromstring(xml)
    parent = {c: p for p in root.iter() for c in p}
    menu_descs = {d.lower() for d in cfg.menu_button_descs}

    videos = [_node(el) for el in root.iter() if _looks_like_video(el.get("content-desc", ""), cfg)]
    cards = []
    for el in root.iter():
        if (el.get("content-desc") or "").strip().lower() not in menu_descs:
            continue
        menu = _node(el)
        desc = _desc_from_ancestors(el, parent, cfg) or _desc_from_geometry(menu, videos)
        if desc:
            cards.append(Card(description=desc, menu=menu))
    return cards


def _desc_from_ancestors(el, parent, cfg, max_levels=6):
    # The video description usually lives on a sibling/cousin inside the same card container.
    cur = el
    for _ in range(max_levels):
        cur = parent.get(cur)
        if cur is None:
            return None
        found = [s.get("content-desc") for s in cur.iter() if _looks_like_video(s.get("content-desc", ""), cfg)]
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            return None  # climbed past the card into the feed list; let geometry decide
    return None


def _desc_from_geometry(menu, videos):
    # Fallback: the video whose bounds contain the button, else the nearest one above it.
    mx, my = menu.center
    for v in videos:
        x1, y1, x2, y2 = v.bounds
        if x1 <= mx <= x2 and y1 <= my <= y2:
            return v.desc
    above = [v for v in videos if v.bounds[1] <= my]
    if above:
        return max(above, key=lambda v: v.bounds[1]).desc
    return None


def parse_subscription_names(xml, cfg):
    """Channel names from the Subscriptions > All list: text inside the scrolling list, minus UI labels."""
    root = ET.fromstring(xml)
    ignore = {t.lower() for t in cfg.subs_ignore_texts}
    names = []
    for lst in root.iter():
        if lst.get("scrollable") != "true":
            continue
        for el in lst.iter():
            t = (el.get("text") or "").strip()
            if len(t) >= 2 and t.lower() not in ignore and t not in names:
                names.append(t)
    return names


# --------------------------------------------------------------------------- rules

def _contains_any(haystack, needles):
    h = haystack.lower()
    return next((n for n in needles if n and n.lower() in h), None)


def _channel_hit(haystack, names):
    # Whole-word match, so a channel called "Ted" doesn't match "trusted".
    h = haystack.lower()
    for n in names:
        if n and re.search(r"(?<!\w)" + re.escape(n.lower()) + r"(?!\w)", h):
            return n
    return None


def decide(description, cfg):
    """Return (should_mark, reason)."""
    if cfg.skip_shorts and _contains_any(description, cfg.shorts_markers):
        return False, "short"
    if hit := _channel_hit(description, cfg.allow_channels) or _contains_any(description, cfg.allow_keywords):
        return False, f"allowed: {hit}"
    if hit := _channel_hit(description, cfg.block_channels):
        return True, f"channel: {hit}"
    if hit := _contains_any(description, cfg.block_keywords):
        return True, f"keyword: {hit}"
    if cfg.mark_everything:
        return True, "mark_everything"
    return False, "no rule matched"


# --------------------------------------------------------------------------- device actions

def connect(serial):
    try:
        import uiautomator2 as u2
    except ImportError:
        sys.exit("uiautomator2 is not installed. Run: pip install -r requirements.txt")
    d = u2.connect(serial) if serial else u2.connect()
    print(f"connected: {d.info.get('productName', '?')} (sdk {d.info.get('sdkInt', '?')})")
    return d


def pause(cfg):
    time.sleep(random.uniform(cfg.delay_min, cfg.delay_max))


def tap_label(d, labels, timeout=3.0):
    for label in labels:
        el = d(text=label)
        if el.wait(timeout=timeout):
            el.click()
            return label
        timeout = 0.5  # the sheet is already open; don't wait long for the other spellings
    return None


def open_home(d):
    d.app_start(YOUTUBE_PKG)
    time.sleep(4)
    home = d(description="Home")
    if home.exists:
        home.click()
        time.sleep(2)


def sync_subscriptions(d, cfg):
    print("reading your subscriptions...")
    d.app_start(YOUTUBE_PKG)
    time.sleep(4)
    for desc in cfg.subscriptions_tab_descs:
        if d(description=desc).exists:
            d(description=desc).click()
            break
    else:
        raise RuntimeError("couldn't find the Subscriptions tab")
    time.sleep(3)
    if not tap_label(d, cfg.subs_all_labels, timeout=4):
        raise RuntimeError("couldn't find the 'All' button on the Subscriptions tab")
    time.sleep(3)

    names, stale = [], 0
    while stale < 3:
        new = [n for n in parse_subscription_names(d.dump_hierarchy(), cfg) if n not in names]
        names += new
        stale = 0 if new else stale + 1
        d.swipe_ext("up", scale=0.7)
        time.sleep(1.2)
    d.press("back")
    SUBS_PATH.write_text(json.dumps({"updated": time.time(), "channels": names}, indent=1), encoding="utf-8")
    print(f"saved {len(names)} channel(s) to {SUBS_PATH.name}")
    return names


def load_subscriptions(d, cfg, force=False):
    if not force and SUBS_PATH.exists():
        data = json.loads(SUBS_PATH.read_text(encoding="utf-8"))
        if time.time() - data.get("updated", 0) < cfg.subs_refresh_days * 86400:
            return data["channels"]
    try:
        return sync_subscriptions(d, cfg)
    except RuntimeError as e:
        print(f"subscription sync failed: {e}")
        return json.loads(SUBS_PATH.read_text(encoding="utf-8"))["channels"] if SUBS_PATH.exists() else []


def cmd_sync_subs(args):
    cfg = Config.load(args.config)
    d = connect(args.serial)
    for n in load_subscriptions(d, cfg, force=True):
        print(f"  - {n}")


def cmd_dump(args):
    d = connect(args.serial)
    if not args.no_launch:
        open_home(d)
    out = HERE / "dumps"
    out.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    xml = d.dump_hierarchy()
    (out / f"ui-{stamp}.xml").write_text(xml, encoding="utf-8")
    d.screenshot(str(out / f"screen-{stamp}.png"))
    print(f"saved dumps/ui-{stamp}.xml and dumps/screen-{stamp}.png")

    cfg = Config.load(args.config)
    cards = find_cards(xml, cfg)
    print(f"\nfound {len(cards)} video card(s) with a menu button:")
    for c in cards:
        print(f"  - {c.description[:110]}")
    if not cards:
        descs = sorted({el.get('content-desc') for el in ET.fromstring(xml).iter() if el.get('content-desc')})
        print("\nnone matched. content-desc values on screen (use these to adjust config.toml):")
        for s in descs[:60]:
            print(f"  {s[:110]!r}")


def cmd_run(args):
    cfg = Config.load(args.config)
    if args.max is not None:
        cfg.max_per_run = args.max
    if not (cfg.block_keywords or cfg.block_channels or cfg.mark_everything):
        sys.exit("config has no block_keywords/block_channels and mark_everything=false: nothing to do.")

    d = connect(args.serial)
    if cfg.protect_subscriptions:
        subs = load_subscriptions(d, cfg)
        if not subs and cfg.mark_everything:
            sys.exit("couldn't read your subscriptions, so refusing to mark everything. "
                     "Run `./yt.sh sync-subs` and send its output.")
        cfg.allow_channels = cfg.allow_channels + subs
        print(f"protecting {len(subs)} subscribed channel(s)")
    if not args.no_launch:
        open_home(d)

    # The start/stop button sends SIGTERM; finish the current line and print the summary.
    signal.signal(signal.SIGTERM, _raise_interrupt)
    stats = {"marked": 0}
    try:
        _run_loop(d, cfg, args, stats)
    except KeyboardInterrupt:
        print("\nstopped.")
    print(f"\ndone. {'would mark' if args.dry_run else 'marked'} {stats['marked']} video(s).")


def _raise_interrupt(*_):
    raise KeyboardInterrupt


def _run_loop(d, cfg, args, stats):
    log_path = HERE / "marked.jsonl"
    seen, scrolls, idle_scrolls = set(), 0, 0

    while scrolls < cfg.max_scrolls:
        acted = False
        for card in find_cards(d.dump_hierarchy(), cfg):
            if card.description in seen:
                continue
            seen.add(card.description)
            should, reason = decide(card.description, cfg)
            title = card.description[:90]
            if not should:
                print(f"  skip  [{reason}] {title}")
                continue
            idle_scrolls = 0
            if args.dry_run:
                print(f"  WOULD [{reason}] {title}")
                stats["marked"] += 1
            elif mark(d, card, cfg):
                stats["marked"] += 1
                print(f"  MARK  [{reason}] {title}")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"t": time.time(), "reason": reason, "video": card.description}) + "\n")
            else:
                print(f"  fail  [{reason}] {title}")
            if stats["marked"] >= cfg.max_per_run:
                print(f"\nreached max_per_run={cfg.max_per_run}")
                return
            if not args.dry_run:
                # Marking collapses the card and shifts the layout; re-read the screen.
                acted = True
                break
        if acted:
            continue
        d.swipe_ext("up", scale=0.6)
        pause(cfg)
        scrolls += 1
        idle_scrolls += 1
        if idle_scrolls >= 15:
            print("\n15 scrolls with nothing to mark; stopping.")
            break


def mark(d, card, cfg):
    d.click(*card.menu.center)
    pause(cfg)
    labels = cfg.not_interested_labels
    if cfg.also_dont_recommend_channel:
        labels = cfg.dont_recommend_labels + labels
    if tap_label(d, labels):
        pause(cfg)
        return True
    d.press("back")  # menu opened but had no matching option (e.g. an ad)
    pause(cfg)
    return False


# --------------------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--serial", help="ADB serial or ip:port (default: the only connected device)")
    p.add_argument("--config", default=str(HERE / "config.toml"))
    sub = p.add_subparsers(dest="cmd", required=True)
    dmp = sub.add_parser("dump", help="open YouTube Home and save a screenshot + UI tree")
    dmp.add_argument("--no-launch", action="store_true", help="capture whatever screen is open")
    sub.add_parser("sync-subs", help="read Subscriptions > All and save the channel list")
    r = sub.add_parser("run", help="scroll the home feed and mark matching videos")
    r.add_argument("--dry-run", action="store_true", help="log decisions without tapping")
    r.add_argument("--max", type=int, help="override max_per_run")
    r.add_argument("--no-launch", action="store_true", help="start from whatever screen is open")
    args = p.parse_args(argv)
    {"dump": cmd_dump, "run": cmd_run, "sync-subs": cmd_sync_subs}[args.cmd](args)


if __name__ == "__main__":
    main()
