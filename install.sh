#!/usr/bin/env bash
set -euo pipefail

DEST="$HOME/.config/waybar"
SRC="$(cd "$(dirname "$0")" && pwd)"

GREEN="\033[0;32m"  YELLOW="\033[0;33m"  RED="\033[0;31m"
CYAN="\033[0;36m"   BOLD="\033[1m"       RESET="\033[0m"

info()  { echo -e "${CYAN}[*]${RESET} $*"; }
ok()    { echo -e "${GREEN}[+]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[!]${RESET} $*"; }
error() { echo -e "${RED}[✗]${RESET} $*"; exit 1; }

echo -e "${BOLD}${CYAN}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║     Waybar Cyberpunk — Installer     ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${RESET}"

# ── Checks ───────────────────────────────────────────────────

command -v waybar  &>/dev/null || error "waybar not found. Install it first."
command -v python3 &>/dev/null || error "python3 not found."

# ── Backup ───────────────────────────────────────────────────

if [ -d "$DEST" ]; then
    BACKUP="${DEST}.bak.$(date +%Y%m%d_%H%M%S)"
    info "Backing up existing config to: $BACKUP"
    cp -r "$DEST" "$BACKUP"
    ok "Backup created"
fi

# ── Install ──────────────────────────────────────────────────

mkdir -p "$DEST/scripts"

info "Copying config files..."
cp "$SRC/config.jsonc" "$DEST/config.jsonc"
cp "$SRC/style.css"    "$DEST/style.css"

info "Copying scripts..."
cp "$SRC/scripts/"*.py  "$DEST/scripts/"
cp "$SRC/scripts/"*.sh  "$DEST/scripts/"
chmod +x "$DEST/scripts/"*.py "$DEST/scripts/"*.sh

ok "Files installed to $DEST"

# ── Dependency hints ─────────────────────────────────────────

echo ""
info "Checking optional dependencies..."

check() {
    local cmd="$1" pkg_apt="$2" pkg_pac="$3" label="$4"
    if command -v "$cmd" &>/dev/null; then
        echo -e "  ${GREEN}✓${RESET} $label"
    else
        echo -e "  ${YELLOW}✗${RESET} $label ${YELLOW}(missing: apt: $pkg_apt | pacman: $pkg_pac)${RESET}"
    fi
}

check wpctl      pipewire      pipewire       "pipewire / wpctl (audio)"
check nvidia-smi nvidia-utils  nvidia-utils   "nvidia-smi (VRAM monitor)"
check busctl     dbus          dbus           "busctl (power profile)"
check ss         iproute2      iproute2       "ss (connections/ports)"
check clamscan   clamav        clamav         "ClamAV (antivirus)"
check nft        nftables      nftables       "nftables (firewall)"
check iw         iw            iw             "iw (wifi monitor)"
check mpc        mpc           mpc            "mpc (MPD player)"
check ffmpeg     ffmpeg        ffmpeg         "ffmpeg (album art)"
check pavucontrol pavucontrol  pavucontrol    "pavucontrol (audio GUI)"
check wofi       wofi          wofi           "wofi (app launcher)"

# ── Reload ───────────────────────────────────────────────────

echo ""
if pgrep waybar &>/dev/null; then
    read -rp "$(echo -e ${YELLOW}Restart Waybar now? [Y/n]:${RESET} )" choice
    case "${choice:-Y}" in
        [Yy]*|"")
            pkill waybar
            sleep 0.5
            waybar &>/dev/null &
            ok "Waybar restarted"
            ;;
        *) warn "Run 'pkill waybar && waybar' to apply changes" ;;
    esac
else
    info "Start Waybar with: waybar"
fi

echo ""
ok "Done! See README.md for timezone and interface configuration."
