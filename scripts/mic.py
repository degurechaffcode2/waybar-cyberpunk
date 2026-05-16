#!/usr/bin/env python3
import json
import re
import subprocess

C_TITLE = "#bd93f9"
C_SEC   = "#8be9fd"
C_VAL   = "#f8f8f2"
C_ALERT = "#ff5555"
C_SAFE  = "#50fa7b"
C_WARN  = "#ffb86c"
C_DIM   = "#44475a"


def get_volume(target):
    out = subprocess.check_output(
        ["wpctl", "get-volume", target], stderr=subprocess.DEVNULL
    ).decode().strip()
    muted  = "[MUTED]" in out
    m      = re.search(r"Volume:\s+([0-9.]+)", out)
    volume = round(float(m.group(1)) * 100) if m else 0
    return volume, muted


def get_source_name():
    try:
        out = subprocess.check_output(
            ["wpctl", "inspect", "@DEFAULT_AUDIO_SOURCE@"], stderr=subprocess.DEVNULL
        ).decode()
        m = re.search(r'node\.description\s*=\s*"([^"]+)"', out)
        return m.group(1) if m else "Microphone"
    except Exception:
        return "Microphone"


def vol_bar(pct, width=14):
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def main():
    try:
        volume, muted = get_volume("@DEFAULT_AUDIO_SOURCE@")
        source_name   = get_source_name()
    except Exception:
        print(json.dumps({"text": "<span color='#ff5555'>󰍭 ERR</span>", "class": "mic-error"}))
        return

    # ── Estado ──────────────────────────────────────────────
    if muted:
        state  = "mic-muted"
        bar_c  = C_ALERT
        icon   = "󰍭"
    else:
        state  = "mic-active"
        bar_c  = C_SAFE
        icon   = "󰍬"

    mute_str = f"<span color='{C_ALERT}'><b>MUDO</b></span>" if muted \
               else f"<span color='{C_SAFE}'>ativo</span>"

    bar = vol_bar(min(volume, 100))

    # ── Tooltip ─────────────────────────────────────────────
    t  = f"<span font_desc='JetBrains Mono, Fira Code, Monospace 9'>"
    t += f"<b><span color='{C_TITLE}'>󰍬  MICROFONE</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Entrada:</span> <span color='{C_VAL}'>{source_name[:26]}</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Ganho  :</span> <span color='{bar_c}'><b>{volume}%</b></span>\n"
    t += f" ├─ <span color='{C_SEC}'>        </span> <span color='{bar_c}'>{bar}</span>\n"
    t += f" └─ <span color='{C_SEC}'>Mudo   :</span> {mute_str}\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += (f"<span color='{C_WARN}'>L</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>toggle mudo</span></span>")

    text = f"<span color='{bar_c}'>{icon}</span>"

    print(json.dumps({
        "text":    text,
        "alt":     state,
        "tooltip": t,
        "class":   [state],
    }), flush=True)


if __name__ == "__main__":
    main()
