# YouTube "Not interested" automation (Android)

Scrolls your YouTube **Home** feed and, for each video that matches your rules,
opens the ⋮ menu and taps **Not interested** (or **Don't recommend channel**).
YouTube uses those taps to retrain your recommendations.

It drives the real YouTube app through Android's UI automation (ADB and
[uiautomator2](https://github.com/openatx/uiautomator2)). It doesn't need root,
doesn't use the YouTube API and never sees your Google password.

Built for a Galaxy S23 Ultra running YouTube 21.38.130 with English UI text.
Other phones and versions work as long as the labels in `config.toml` match.

## 1. Enable wireless debugging on the S23 Ultra

1. **Settings → About phone → Software information** → tap **Build number** 7 times.
2. **Settings → Developer options** → turn on **Wireless debugging** (and
   **USB debugging** if you'll use a cable).
3. Stay on the same Wi-Fi as the computer, or use Termux on the phone (option B).

## 2a. Option A: run from a PC or Mac (easiest)

```bash
# install adb: https://developer.android.com/tools/releases/platform-tools
pip install -r requirements.txt

# Developer options → Wireless debugging → "Pair device with pairing code"
adb pair 192.168.1.23:37xxx        # IP:port and code shown on the phone
adb connect 192.168.1.23:4xxxx     # IP:port shown on the Wireless debugging screen
adb devices                        # should list the phone
```

A USB cable also works: plug it in, accept the prompt, then `adb devices`.

## 2b. Option B: run on the phone only (Termux)

1. Install **Termux** from F-Droid (the Play Store build is outdated).
2. In Termux:
   ```bash
   pkg install python android-tools git
   pip install uiautomator2
   git clone <this repo> && cd test/youtube-not-interested
   ```
3. Split-screen Termux and Settings → Wireless debugging → **Pair device with pairing code**, then:
   ```bash
   adb pair localhost:<pairing-port>     # enter the code
   adb connect localhost:<debug-port>
   ```

## 3. Calibrate once, then run

```bash
# Open YouTube on the Home tab, then:
python yt_not_interested.py dump
```
This saves `dumps/ui-*.xml` plus a screenshot and lists the videos it can see.
If it says **found 0 video card(s)**, it prints the labels it did find. Put
them into the `[ui]` section of `config.toml`, or send the XML file for a fix.

```bash
# See what it *would* do, without tapping anything
python yt_not_interested.py run --dry-run

# Do it for real (stops after max_per_run)
python yt_not_interested.py run --max 20
```

Every video it marks is logged to `marked.jsonl`.

## 4. Choose what to mark: `config.toml`

| Setting | What it does |
|---|---|
| `block_keywords` | Mark any video whose title, channel or description contains one of these |
| `block_channels` | Mark every video from these channels |
| `allow_keywords` / `allow_channels` | Never mark these (overrides the block rules) |
| `mark_everything` | Mark **every** feed video except allowed ones: a hard reset |
| `also_dont_recommend_channel` | Use "Don't recommend channel" instead (stronger) |
| `skip_shorts` | Ignore the Shorts shelf |
| `delay_min` / `delay_max` | Random pause between taps |

If your phone isn't set to English, translate the `[ui]` labels, for example
`not_interested_labels = ["Nicht interessiert"]`.

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
python -m unittest      # offline; no phone needed
```
