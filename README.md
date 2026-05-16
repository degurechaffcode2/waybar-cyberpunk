<div align="right">
  <a href="README.md">🇺🇸 English</a> &nbsp;|&nbsp;
  <a href="README.pt-BR.md">🇧🇷 Português</a>
</div>

# Waybar Cyberpunk Tokyo

A Waybar configuration with a dark cyberpunk aesthetic (Tokyo Night / Dracula palette) featuring a rich security monitoring cluster, hardware monitors with styled tooltips, and a dual-bar layout for Hyprland.

## Preview

![Waybar Cyberpunk Tokyo](assets/preview.png)

> **Top bar:** VRAM · Audio · Mic · Brightness · Power Profile · Battery · Security cluster  
> **Bottom bar:** Workspaces · App shortcuts · Taskbar · Tray

## Features

### Hardware
| Module | Description |
|---|---|
| `custom/vram` | NVIDIA GPU VRAM usage, temperature, GPU% — via `nvidia-smi` |
| `custom/battery` | Charge %, health, power draw, cycle count — auto-detects battery |
| `custom/audio` | Volume with bar, scroll to adjust, middle-click mute |
| `custom/mic` | Mic mute state — click to toggle |
| `custom/powerprofile` | Active power profile + all available profiles |
| `backlight` | Display brightness |

### Security
| Module | Description |
|---|---|
| `custom/connections` | Active external TCP connections |
| `custom/firewall` | nftables state + pentest rule manager (`fw-ops`) |
| `custom/ports` | Open ports (external vs loopback, risky ports highlighted) |
| `custom/antivirus` | ClamAV daemon status + threat log |
| `custom/wifi-pentest` | Wi-Fi interface state, VPN detection, monitor mode |
| `custom/rogue-ap` | Rogue AP session monitor (requires [rogue-ap](https://github.com/)) |

### Player
MPD player controls with album art, track info, and ncmpcpp integration.

## Requirements

### Core
- [Waybar](https://github.com/Alexays/Waybar) ≥ 0.10
- [Hyprland](https://hyprland.org/) (or adapt modules for your WM)
- Python 3.8+
- A [Nerd Font](https://www.nerdfonts.com/) — MesloLGS or JetBrains Mono recommended

### Per-module
| Module | Dependency |
|---|---|
| VRAM | `nvidia-smi` (NVIDIA drivers) |
| Audio / Mic | `pipewire` + `wireplumber` (`wpctl`) |
| Power Profile | `power-profiles-daemon` |
| Brightness | `brightnessctl` or `light` |
| Connections / Ports | `iproute2` (`ss`) |
| Firewall | `nftables` |
| Antivirus | `clamav` (clamd + freshclam) |
| Wi-Fi | `iw`, `iwconfig`, `macchanger` |
| Player | `mpd`, `mpc`, `ncmpcpp`, `ffmpeg` |
| Audio control UI | `pavucontrol` |
| App launcher | `wofi` |
| Power menu | `nwg-bar` |

### Ubuntu / Debian
```bash
sudo apt install waybar python3 pipewire wireplumber \
    power-profiles-daemon iproute2 nftables clamav \
    iw macchanger mpc ncmpcpp ffmpeg pavucontrol wofi
```

### Arch / CachyOS / Manjaro
```bash
sudo pacman -S waybar python pipewire wireplumber \
    power-profiles-daemon iproute2 nftables clamav \
    iw macchanger mpc ncmpcpp ffmpeg pavucontrol wofi
```

## Installation

```bash
git clone https://github.com/degurechaffcode2/waybar-cyberpunk.git
cd waybar-cyberpunk
chmod +x install.sh
./install.sh
```

The script backs up your existing config and copies all files to `~/.config/waybar/`.

## Configuration

### Timezone
Edit `config.jsonc` and change the `clock` timezone:
```jsonc
"clock": {
  "timezone": "America/New_York",   // change to your timezone
  ...
}
```

### Wi-Fi Interface
The MAC randomizer in `custom/wifi-pentest` uses `wlan0` by default.  
Check your interface name with `ip link show` and update the `on-click-right` command in `config.jsonc`.

### MPD Music Directory
`mpd-cover.sh` defaults to `~/Music`. Override with the environment variable:
```bash
export MPD_MUSIC_DIR="/path/to/your/music"
```
Or set it permanently in your shell profile.

### NVIDIA not present
Remove `custom/vram` from `modules-right` in `config.jsonc` if you don't have an NVIDIA GPU.

### Security modules not needed
The security cluster (`connections`, `firewall`, `ports`, `antivirus`, `wifi-pentest`, `rogue-ap`) can be removed from `modules-right` if not needed.

## Tooltip Style

All custom modules share a unified tooltip design:
- **Font:** JetBrains Mono / Fira Code (monospace fallback)
- **Palette:** Dracula — purple headers, cyan labels, colored states
- **Layout:** tree-style `├─ / └─` rows with color-coded values

## License

MIT
