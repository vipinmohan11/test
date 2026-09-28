# YouTube "Not interested" automation (Android)

Scrolls your YouTube **Home** feed and, for each video that matches your rules,
opens the ⋮ menu and taps **Not interested** (or **Don't recommend channel**).
YouTube uses those taps to retrain your recommendations.

It drives the real YouTube app through Android's UI automation (ADB and
[uiautomator2](https://github.com/openatx/uiautomator2)). It doesn't need root,
doesn't use the YouTube API and never sees your Google password.

Built for a Galaxy S23 Ultra running YouTube 21.38.130 with English UI text,
Home feed only.

Everything runs on the phone in Termux. You don't need a PC.

## 1. One-time phone settings

1. **Settings → About phone → Software information** → tap **Build number** 7 times.
2. **Settings → Developer options** → turn on **Wireless debugging**.
   Wi-Fi has to be on (any network works; it doesn't need internet).
3. **Settings → Apps → Termux → Battery** → **Unrestricted**. Otherwise One UI
   kills Termux while YouTube is in front.

## 2. Install Termux and this project

1. Install **Termux** from [F-Droid](https://f-droid.org/packages/com.termux/).
   The Play Store build is outdated and broken.
2. In Termux:
   ```bash
   pkg install -y git
   git clone https://github.com/vipinmohan11/test.git
   cd test/youtube-not-interested
   bash termux-setup.sh
   ```
   If the repo is private, git asks for a username and password. Use a GitHub
   [personal access token](https://github.com/settings/tokens) as the password.

## 3. Pair Termux with the phone (once per install)

1. Put Termux and Settings side by side (Recent apps → Termux icon → **Open in
   split screen view**). The pairing code disappears if you switch apps.
2. Settings → Developer options → **Wireless debugging** → **Pair device with
   pairing code**. It shows a 6-digit code and `IP:port`.
3. In Termux: `adb pair localhost:<that port>` and type the code.
4. Back on the Wireless debugging screen, note the port under **IP address &
   Port**. It's a different port from the pairing one.

You only pair once. The **connect** port changes every time Wi-Fi or wireless
debugging turns off and on. `./yt.sh` asks for it when it isn't connected.

## 4. Calibrate once, then run

```bash
cd ~/test/youtube-not-interested
./yt.sh dump
```
`dump` opens YouTube on the Home tab and saves `dumps/ui-*.xml` plus a
screenshot. Switch back to Termux to see the list of videos it recognised. If it
finds 0, send that XML file so the labels can be fixed.

```bash
./yt.sh run --dry-run   # opens YouTube, scrolls, prints what it WOULD mark
./yt.sh run --max 20    # does it for real
```
`run` opens YouTube itself, so start it from Termux and leave the phone alone
until it finishes. Keep the screen on and unlocked. To stop early, pull down
the notification shade, open Termux and press **Ctrl+C** (Volume-down + C).

Every video it marks is logged to `marked.jsonl`.

## 5. Choose what to mark: `config.toml`

| Setting | What it does |
|---|---|
| `block_keywords` | Mark any video whose title, channel or description contains one of these |
| `block_channels` | Mark every video from these channels |
| `allow_keywords` / `allow_channels` | Never mark these (overrides the block rules) |
| `mark_everything` | Mark **every** feed video except allowed ones: a hard reset |
| `also_dont_recommend_channel` | Use "Don't recommend channel" instead (stronger) |
| `skip_shorts` | Ignore the Shorts shelf |
| `delay_min` / `delay_max` | Random pause between taps |

## Tips

- Keep runs small (20 to 30 videos a day). Big bursts look like a bot and the
  feed needs time to adjust anyway.
- Also clean up **Settings → Manage all history** in YouTube; watch history is
  a stronger signal than "Not interested".
- Undo mistakes under **myactivity.google.com → Other activity → YouTube
  "Not interested" feedback**.
- The screen must stay on and unlocked while it runs.

## Tests

```bash
python -m unittest      # offline; no ADB connection needed
```
