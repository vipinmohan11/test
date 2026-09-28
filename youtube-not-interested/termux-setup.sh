#!/data/data/com.termux/files/usr/bin/bash
# One-time setup inside Termux. Run: bash termux-setup.sh
set -e

pkg update -y
# Pillow and lxml fail to build with plain pip on Termux; use the prebuilt packages.
pkg install -y python android-tools python-pillow python-lxml
pip install uiautomator2

echo
echo "Done. Next: pair with wireless debugging (see README, step 3), then run ./yt.sh dump"
