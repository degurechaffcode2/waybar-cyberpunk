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


def get_sink_name():
    try:
        out = subprocess.check_output(
            ["wpctl", "inspect", "@DEFAULT_AUDIO_SINK@"], stderr=subprocess.DEVNULL
        ).decode()
        m = re.search(r'node\.description\s*=\s*"([^"]+)"', out)
        return m.group(1) if m else "Speaker"
    except Exception:
        return "Speaker"


def vol_bar(pct, width=14):
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def main():
    try:
        volume, muted = get_volume("@DEFAULT_AUDIO_SINK@")
        sink_name     = get_sink_name()
    except Exception:
        print(json.dumps({"text": "<span color='#ff5555'>󰝟 ERR</span>", "class": "audio-error"}))
        return

    # ── Estado ──────────────────────────────────────────────
    if muted:
        state  = "audio-muted"
        bar_c  = C_DIM
        icon   = "󰝟"
    elif volume == 0:
        state  = "audio-off"
        bar_c  = C_DIM
        icon   = "󰕿"
    elif volume > 100:
        state  = "audio-loud"
        bar_c  = C_ALERT
        icon   = "󰕾"
    elif volume >= 60:
        state  = "audio-high"
        bar_c  = C_WARN
        icon   = "󰕾"
    elif volume >= 30:
        state  = "audio-mid"
        bar_c  = C_VAL
        icon   = "󰖀"
    else:
        state  = "audio-low"
        bar_c  = C_VAL
        icon   = "󰕿"

    mute_str = f"<span color='{C_ALERT}'><b>MUDO</b></span>" if muted \
               else f"<span color='{C_SAFE}'>ativo</span>"

    bar = vol_bar(min(volume, 100))

    # ── Tooltip ─────────────────────────────────────────────
    t  = f"<span font_desc='JetBrains Mono, Fira Code, Monospace 9'>"
    t += f"<b><span color='{C_TITLE}'>󰕾  ÁUDIO</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Saída  :</span> <span color='{C_VAL}'>{sink_name[:26]}</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Volume :</span> <span color='{bar_c}'><b>{volume}%</b></span>\n"
    t += f" ├─ <span color='{C_SEC}'>        </span> <span color='{bar_c}'>{bar}</span>\n"
    t += f" └─ <span color='{C_SEC}'>Mudo   :</span> {mute_str}\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += (f"<span color='{C_WARN}'>L</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>pavucontrol</span></span>")

    text = f"<span color='{bar_c}'>{icon} {volume}%</span>"

    print(json.dumps({
        "text":    text,
        "alt":     state,
        "tooltip": t,
        "class":   [state],
    }), flush=True)


if __name__ == "__main__":
    main()
