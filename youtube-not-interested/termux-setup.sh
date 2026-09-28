#!/data/data/com.termux/files/usr/bin/bash
# One-time setup inside Termux. Run: bash termux-setup.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

pkg update -y
# Pillow and lxml fail to build with plain pip on Termux; use the prebuilt packages.
pkg install -y python android-tools python-pillow python-lxml nmap termux-api
pip install uiautomator2
chmod +x "$DIR"/*.sh

# Home-screen button (Termux:Widget). tasks/ = runs in the background, no terminal.
mkdir -p ~/.shortcuts/tasks
cat > ~/.shortcuts/tasks/"YouTube Reset" <<SH
#!/data/data/com.termux/files/usr/bin/bash
exec bash "$DIR/toggle.sh"
SH
chmod 700 ~/.shortcuts ~/.shortcuts/tasks ~/.shortcuts/tasks/"YouTube Reset"

echo
echo "Done. Next steps (README steps 3-5):"
echo "  1. adb pair localhost:<pairing-port>"
echo "  2. ./yt.sh run --dry-run"
echo "  3. Add the Termux:Widget widget to your home screen and pick 'YouTube Reset'"
