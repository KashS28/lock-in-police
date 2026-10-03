# Lock-In Police

A macOS menubar app that watches your desk via webcam and shames you every time you pick up your phone. Includes a Pomodoro timer, voice shaming, shame selfies, and fullscreen popups with random angry photos.

---

## What it does

When you pick up your phone during a work session:

1. **Detects the phone** — webcam scans at 2 fps using a lightweight OpenCV SSD MobileNetV2 COCO model. No GPU, no PyTorch.
2. **Plays a voice line** — macOS `say` command fires a random shame line in Samantha, Alex, or Victoria's voice.
3. **Takes a shame selfie** — saves a timestamped JPEG of you in the act to `selfies/`.
4. **Fires a fullscreen popup** — alternates between:
   - A random photo from Pexels (motivational or judgmental)
   - A shame quote + cute angry GIF sticker
5. **Type to dismiss** — the popup won't close until you type `I WILL LOCK IN` (or wait 30 seconds).

The Pomodoro timer runs 25-minute work blocks with 5-minute breaks. Detection turns off during breaks automatically.

---

## Setup

### 1. Prerequisites

- macOS 12+ (Monterey or later)
- Python 3.9 from Xcode Command Line Tools (`/usr/bin/python3`)
- Xcode Command Line Tools: `xcode-select --install`

### 2. Create the virtual environment

```bash
cd ~/Desktop/lock-in-police
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Note:** The auto-start (LaunchAgent) uses a separate venv at `~/Library/Application Support/lock-in-police/venv/` that is set up during installation. See the Auto-start section below.

### 3. Download the detection model

```bash
bash setup.sh
```

This downloads two files into `assets/`:
- `frozen_inference_graph.pb` — SSD MobileNetV2 weights
- `ssd_mobilenet_v2_coco.pbtxt` — network config

### 4. Add API keys

Create a `.env` file in the project root:

```
PEXELS_API_KEY=your_pexels_key_here
```

- **Pexels** (required for image popups): free key at [pexels.com/api](https://www.pexels.com/api/). Without it, the app falls back to quote-only popups.

### 5. Grant permissions

Two macOS permissions are required:

| Permission | Where to grant | What it's for |
|---|---|---|
| **Camera** | System Settings → Privacy & Security → Camera → enable Terminal | Webcam detection |
| **Accessibility** | System Settings → Privacy & Security → Accessibility → enable Terminal | Global `⌘⇧L` hotkey |

### 6. Run manually

```bash
source .venv/bin/activate
python3 app.py
```

The `🔒` icon appears in your menubar. Click it to start a session.

---

## Auto-start on login

The app can run automatically every time you log in via a macOS LaunchAgent.

**Install:**
```bash
bash setup.sh   # also handles LaunchAgent installation
```

Or manually:
```bash
# 1. Copy app files to Application Support (launchd can't access ~/Desktop)
cp -r ~/Desktop/lock-in-police ~/Library/Application\ Support/lock-in-police

# 2. Install the LaunchAgent
cp ~/Library/Application\ Support/lock-in-police/com.lockInPolice.agent.plist \
   ~/Library/LaunchAgents/

# Edit the plist to set correct paths, then:
launchctl load ~/Library/LaunchAgents/com.lockInPolice.agent.plist
```

**Why not just ~/Desktop?** macOS blocks LaunchAgents from accessing `~/Desktop` due to TCC (privacy) restrictions. The app must live in `~/Library/Application Support/` for auto-start to work.

**Check status:**
```bash
launchctl list | grep lockInPolice
# PID  0  com.lockInPolice.agent  → running
#  -   1  com.lockInPolice.agent  → crashed (check logs/)
```

**Logs:**
```
~/Library/Application Support/lock-in-police/logs/stdout.log
~/Library/Application Support/lock-in-police/logs/stderr.log
```

**Uninstall:**
```bash
launchctl unload ~/Library/LaunchAgents/com.lockInPolice.agent.plist
rm ~/Library/LaunchAgents/com.lockInPolice.agent.plist
```

---

## Usage

### Menubar

| Icon | Meaning |
|---|---|
| `🔒` | Idle — no active session |
| `👮 24:13` | Work block in progress, time remaining |
| `☕ 4:45` | Break in progress |
| `⏸` | Session paused |

### Menu items

| Item | Action |
|---|---|
| Start Session | Start a 25-min Pomodoro work block |
| Pause | Pause the timer and disable detection |
| Resume | Resume from where you left off |
| End Session | Stop the session and view your summary |
| 🧪 Test Popup | Fire a test popup without needing your phone |
| Quit | Stop everything and quit |

### Hotkey

`⌘⇧L` toggles between Start → Pause → Resume depending on current state.

### Session summary

When you end a session you get a breakdown:
- Total duration
- Pomodoros completed
- Phone pickups
- A rating ("BEAST MODE" to "Rough one")
- Option to open the `selfies/` folder

---

## Popup types

The app alternates between two popup types on each detection:

### Image popup (odd detections)
- Fills the top of the window with a random photo from Pexels
- Shame quotes and type-to-dismiss below

### Quote popup (even detections)
- Animated GIF sticker at the top (rotates through 8 cute angry characters: angry cat, anime pout, mad pikachu, molang, pusheen, hamster, grumpy bunny, chibi maruko)
- Large red shame headline
- Subtext
- Type-to-dismiss entry field

**To dismiss any popup:** type `I WILL LOCK IN` exactly (case-insensitive). Or wait 30 seconds for auto-close.

---

## Tuning detection

Edit `detector.py` to adjust sensitivity:

```python
CONFIDENCE_THRESHOLD = 0.45   # lower = more sensitive, more false positives
FPS = 2                        # frames per second to analyze
COOLDOWN_SECS = 30             # seconds between detections (prevents spam)
```

---

## Project structure

```
app.py              — menubar app, Pomodoro logic, event loop
detector.py         — webcam phone detection (background thread)
hotkey.py           — global ⌘⇧L hotkey listener
popup.py            — fullscreen popup window (AppKit, launched as subprocess)
pexels_client.py    — fetches random images from Pexels API
sticker_client.py   — fetches cute angry GIF stickers (Giphy CDN, no key needed)
quotes.py           — shame quotes and voice lines
assets/
  frozen_inference_graph.pb    — SSD MobileNetV2 COCO weights
  ssd_mobilenet_v2_coco.pbtxt  — model config
  stickers/                    — cached GIF stickers
selfies/            — shame selfies saved here (timestamped JPEGs)
logs/               — stdout.log and stderr.log
.env                — API keys (not committed)
```

---

## Stack

| Library | Purpose |
|---|---|
| [`rumps`](https://github.com/jaredks/rumps) | macOS menubar app framework |
| OpenCV DNN | Phone detection via SSD MobileNetV2 COCO |
| `pyobjc` (AppKit, AVFoundation) | Native popups, camera permission requests |
| `pynput` | Global hotkey capture |
| `requests` + `python-dotenv` | Pexels API and env config |
| macOS `say` | Voice shaming |

---

## Troubleshooting

**App crashes immediately / blank stderr log**
- Check `logs/stderr.log` for the error
- Most common cause: missing camera or accessibility permission

**Phone not detected**
- Lower `CONFIDENCE_THRESHOLD` in `detector.py` (try `0.35`)
- Make sure the phone is visible and reasonably lit
- The detector runs at 2 fps — wave the phone slowly

**Popup appears but is blank**
- Popup uses AppKit (not tkinter). If blank, check that `pyobjc-framework-Cocoa` is installed in the venv

**3 lock icons in menubar**
- Multiple instances running. Kill extras: `pkill -f "app.py"`

**Auto-start not working after editing files**
- You must sync changes to `~/Library/Application Support/lock-in-police/` — that's what launchd runs, not `~/Desktop/lock-in-police/`
- After syncing: `launchctl unload ... && launchctl load ...` to restart

**Hotkey not working**
- Grant Accessibility permission to Terminal in System Settings
- If running via LaunchAgent, the python3 binary itself may need the permission

---

## Privacy

All processing is local. The webcam feed is never stored — only selfie snapshots at the moment of detection. No data leaves your machine except:
- Pexels API calls (fetches an image URL)
- Giphy CDN requests (downloads a cached GIF sticker)
