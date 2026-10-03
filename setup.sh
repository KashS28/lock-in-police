#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python3"
ASSETS_DIR="$SCRIPT_DIR/assets"
PLIST_SRC="$SCRIPT_DIR/com.lockInPolice.agent.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.lockInPolice.agent.plist"

MODEL_PB="$ASSETS_DIR/frozen_inference_graph.pb"
MODEL_PBTXT="$ASSETS_DIR/ssd_mobilenet_v2_coco.pbtxt"

echo ""
echo "🔒 Lock-In Police — Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Step 1: Virtual environment ──────────────────────────────────────────────
echo "[1/5] Creating virtual environment..."
mkdir -p "$ASSETS_DIR" "$SCRIPT_DIR/selfies" "$SCRIPT_DIR/logs"

if [ ! -d "$VENV_DIR" ]; then
    /usr/bin/python3 -m venv "$VENV_DIR"
fi

echo "[2/5] Installing dependencies (~80MB, please wait)..."
"$PYTHON_BIN" -m pip install --upgrade pip --quiet
"$PYTHON_BIN" -m pip install \
    "rumps==0.4.0" \
    "opencv-python>=4.8.0" \
    "Pillow>=10.0.0" \
    "requests>=2.28.0" \
    "python-dotenv>=1.0.0" \
    "pynput>=1.7.6" \
    --quiet

# ── Step 2: Download detection model ─────────────────────────────────────────
echo "[3/5] Downloading detection model (~25MB)..."

if [ ! -f "$MODEL_PB" ]; then
    TMP_TAR="$(mktemp /tmp/ssd_model.XXXXXX.tar.gz)"
    echo "    Downloading SSD MobileNetV2 COCO weights..."
    curl -fsSL \
        "http://download.tensorflow.org/models/object_detection/ssd_mobilenet_v2_coco_2018_03_29.tar.gz" \
        -o "$TMP_TAR"
    tar -xzf "$TMP_TAR" \
        -C "$ASSETS_DIR" \
        --strip-components=1 \
        "ssd_mobilenet_v2_coco_2018_03_29/frozen_inference_graph.pb" \
        2>/dev/null || true
    rm -f "$TMP_TAR"
    echo "    ✓ frozen_inference_graph.pb"
else
    echo "    ✓ Model weights already present, skipping."
fi

if [ ! -f "$MODEL_PBTXT" ]; then
    echo "    Downloading OpenCV DNN config..."
    curl -fsSL \
        "https://raw.githubusercontent.com/opencv/opencv_extra/master/testdata/dnn/ssd_mobilenet_v2_coco_2018_03_29.pbtxt" \
        -o "$MODEL_PBTXT"
    echo "    ✓ ssd_mobilenet_v2_coco.pbtxt"
else
    echo "    ✓ Config already present, skipping."
fi

# ── Step 3: .env file ─────────────────────────────────────────────────────────
echo "[4/5] Setting up config..."
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "    ✓ Created .env — edit it to add your PEXELS_API_KEY"
    echo "      (optional — app works without it, will show quotes instead of images)"
else
    echo "    ✓ .env already exists"
fi

# ── Step 4: LaunchAgent ───────────────────────────────────────────────────────
echo "[5/5] Installing LaunchAgent (auto-start at login)..."
mkdir -p "$HOME/Library/LaunchAgents"
sed \
    "s|__PYTHON__|$PYTHON_BIN|g; s|__APPDIR__|$SCRIPT_DIR|g" \
    "$PLIST_SRC" > "$PLIST_DST"

launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load -w "$PLIST_DST"
echo "    ✓ LaunchAgent installed and started"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅  Lock-In Police is running!"
echo ""
echo "Look for 🔒 in your menubar."
echo ""
echo "NEXT STEPS:"
echo ""
echo "  1. Add your Pexels API key (optional, for angry images):"
echo "     open \"$SCRIPT_DIR/.env\""
echo "     Get a free key at: https://www.pexels.com/api/"
echo ""
echo "  2. Grant Accessibility permission for the ⌘⇧L hotkey:"
echo "     System Settings → Privacy & Security → Accessibility"
echo "     → add this app or Terminal to the list"
echo ""
echo "  3. Allow camera when prompted on first session start."
echo ""
echo "  4. Click 🔒 in the menubar → 'Start Session'"
echo "     or press ⌘⇧L from anywhere."
echo ""
echo "Logs: $SCRIPT_DIR/logs/"
echo "Shame selfies: $SCRIPT_DIR/selfies/"
echo ""
