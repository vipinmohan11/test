# YouTube feed reset (Android, one tap)

Tap one home-screen button and it:

1. reads your **Subscriptions → All** list, so those channels are never touched
2. opens the YouTube **Home** feed
3. taps ⋮ → **Not interested** on every video from a channel you're **not**
   subscribed to, scrolling as it goes
4. stops after 60 videos, or when you tap the button (or the notification's
   **Stop**) again, then shows a notification with the count

YouTube uses those taps to retrain your recommendations. It drives the real
YouTube app through Android's UI automation (ADB and
[uiautomator2](https://github.com/openatx/uiautomator2)). It doesn't need root,
doesn't use the YouTube API and never sees your Google password.

Built for a Galaxy S23 Ultra, YouTube 21.38.130, English UI, Home feed only.
Everything runs on the phone. You don't need a PC.

## 1. Install three apps from F-Droid

- [Termux](https://f-droid.org/packages/com.termux/) (the Play Store build is outdated)
- [Termux:Widget](https://f-droid.org/packages/com.termux.widget/): the home-screen button
- [Termux:API](https://f-droid.org/packages/com.termux.api/): the "running / finished" notifications

## 2. One-time phone settings

1. **Settings → About phone → Software information** → tap **Build number** 7 times.
2. **Settings → Developer options** → turn on **Wireless debugging**. Wi-Fi
   has to be on (any network; it doesn't need internet).
3. **Settings → Apps → Termux → Battery** → **Unrestricted**. Do the same for
   Termux:API. Otherwise One UI kills them while YouTube is in front.
4. **Settings → Apps → Termux → Permissions** → allow **Notifications**.

## 3. Install and pair (once)

In Termux:
```bash
pkg install -y git
git clone https://github.com/vipinmohan11/test.git
cd test/youtube-not-interested
bash termux-setup.sh
```
If the repo is private, git asks for a username and password. Use a GitHub
[personal access token](https://github.com/settings/tokens) as the password.

Then pair Termux with the phone:

1. Put Termux and Settings side by side (Recent apps → Termux icon → **Open in
   split screen view**). The pairing code disappears if you switch apps.
2. Settings → Developer options → **Wireless debugging** → **Pair device with
   pairing code**.
3. In Termux: `adb pair localhost:<port shown>` and type the 6-digit code.

You won't have to type a port again. The scripts find the wireless-debugging
port themselves, then switch ADB to fixed port 5555 so later runs connect
instantly until the phone reboots. The first time that happens, Android may
ask **"Allow USB debugging?"**: tick **Always allow** and tap **Allow**.

## 4. Test once

```bash
./yt.sh run --dry-run
```
This reads your subscriptions (it prints how many it's protecting), opens
YouTube Home, scrolls, and prints `WOULD` / `skip` for each video without
tapping anything. Check that:

- the number of protected channels is about how many you subscribe to
  (`subscriptions.json` has the list)
- your subscribed channels show as `skip [allowed: ...]`

If it finds no videos or no subscriptions, run `./yt.sh dump` and
`./yt.sh sync-subs` and send the output plus the `dumps/ui-*.xml` file.

## 5. Add the button

Long-press the home screen → **Widgets** → **Termux:Widget** → drag it out →
choose **YouTube Reset**.

- **Tap once:** starts. The screen stays on while it runs; leave the phone alone.
- **Tap again**, or **Stop** in the notification: stops.
- If it can't connect, the "finished" notification says why. Usually Wireless
  debugging is off: turn it on and tap again.

The log of the latest run is in `last-run.log`. Every marked video is appended
to `marked.jsonl`.

## 6. Settings: `config.toml`

| Setting | What it does |
|---|---|
| `mark_everything` | `true` (the default): mark every video not protected below |
| `protect_subscriptions` | Never mark channels you subscribe to (list refreshes weekly) |
| `max_per_run` | Stop after this many (default 60) |
| `block_keywords` | Mark any video whose title, channel or description contains one of these |
| `block_channels` | Mark every video from these channels |
| `allow_keywords` / `allow_channels` | Extra things to never mark, beyond your subscriptions |
| `also_dont_recommend_channel` | Use "Don't recommend channel" instead (stronger) |
| `skip_shorts` | Ignore the Shorts shelf |
| `delay_min` / `delay_max` | Random pause between taps |

## Tips

- One run a day is plenty. The feed takes a day or two to react, and huge
  bursts look like a bot.
- Subscribed to a new channel? Run `./yt.sh sync-subs` so it's protected right
  away; otherwise the list refreshes itself every 7 days.
- Also clean up **Settings → Manage all history** in YouTube; watch history is
  a stronger signal than "Not interested".
- Undo mistakes under **myactivity.google.com → Other activity → YouTube
  "Not interested" feedback**.
- Keep the phone unlocked when you tap the button. It keeps the screen on
  by itself, but it can't get past the lock screen.
- Until the phone reboots, ADB listens on port 5555 on your Wi-Fi. Any new
  device that tries to connect still needs you to tap Allow on the phone, but
  on public Wi-Fi you can turn off Wireless debugging when you're done.

## Tests

```bash
python -m unittest      # offline; no ADB connection needed
```
