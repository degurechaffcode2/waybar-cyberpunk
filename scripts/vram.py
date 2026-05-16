#!/usr/bin/env python3
import json
import subprocess

C_TITLE = "#bd93f9"
C_SEC   = "#8be9fd"
C_VAL   = "#f8f8f2"
C_ALERT = "#ff5555"
C_SAFE  = "#50fa7b"
C_WARN  = "#ffb86c"
C_DIM   = "#44475a"


def query():
    out = subprocess.check_output([
        "nvidia-smi",
        "--query-gpu=memory.used,memory.total,temperature.gpu,utilization.gpu,name",
        "--format=csv,noheader,nounits",
    ], stderr=subprocess.DEVNULL).decode().strip()
    parts = [p.strip() for p in out.split(",")]
    return {
        "mem_used": int(parts[0]),
        "mem_total": int(parts[1]),
        "temp":     int(parts[2]),
        "util":     int(parts[3]),
        "name":     parts[4],
    }


def mem_bar(used, total, width=14):
    filled = round(used / total * width)
    return "█" * filled + "░" * (width - filled)


def main():
    try:
        g = query()
    except Exception:
        print(json.dumps({"text": "<span color='#ff5555'>󰢮 ERR</span>", "class": "nvidia-error"}))
        return

    pct = g["mem_used"] * 100 // g["mem_total"]

    if pct >= 80:
        bar_c = C_ALERT
        state = "vram-high"
    elif pct >= 50:
        bar_c = C_WARN
        state = "vram-mid"
    else:
        bar_c = C_SAFE
        state = "vram-ok"

    temp_c = C_ALERT if g["temp"] >= 85 else C_WARN if g["temp"] >= 70 else C_SAFE
    util_c = C_ALERT if g["util"] >= 90 else C_WARN if g["util"] >= 60 else C_VAL

    bar = mem_bar(g["mem_used"], g["mem_total"])

    t  = f"<span font_desc='JetBrains Mono, Fira Code, Monospace 9'>"
    t += f"<b><span color='{C_TITLE}'>󰢮  GPU</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += f"<b><span color='{C_SEC}'>  {g['name']}</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += f" ├─ <span color='{C_SEC}'>VRAM :</span> <span color='{bar_c}'><b>{g['mem_used']} / {g['mem_total']} MiB</b> ({pct}%)</span>\n"
    t += f" ├─ <span color='{C_SEC}'>     </span> <span color='{bar_c}'>{bar}</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Temp :</span> <span color='{temp_c}'><b>{g['temp']}°C</b></span>\n"
    t += f" └─ <span color='{C_SEC}'>GPU  :</span> <span color='{util_c}'><b>{g['util']}%</b></span>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span></span>"

    text = f"<span color='{bar_c}'>󰢮 {g['mem_used']}M</span>"

    print(json.dumps({
        "text":    text,
        "alt":     state,
        "tooltip": t,
        "class":   [state],
    }), flush=True)


if __name__ == "__main__":
    main()
