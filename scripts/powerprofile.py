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

PROFILES = {
    "performance": {"icon": "󱐋", "label": "Performance",  "color": C_ALERT},
    "balanced":    {"icon": "󰾅", "label": "Balanceado",   "color": C_SAFE},
    "power-saver": {"icon": "󰌪", "label": "Economia",     "color": C_WARN},
}


def busctl_get(prop):
    out = subprocess.check_output(
        ["busctl", "get-property",
         "net.hadess.PowerProfiles",
         "/net/hadess/PowerProfiles",
         "net.hadess.PowerProfiles", prop],
        stderr=subprocess.DEVNULL,
    ).decode().strip()
    # format: s "value"
    m = re.search(r'"([^"]+)"', out)
    return m.group(1) if m else None


def get_active():
    return busctl_get("ActiveProfile")


def get_available():
    try:
        out = subprocess.check_output(
            ["busctl", "get-property",
             "net.hadess.PowerProfiles",
             "/net/hadess/PowerProfiles",
             "net.hadess.PowerProfiles", "Profiles"],
            stderr=subprocess.DEVNULL,
        ).decode()
        return re.findall(r'"Profile"\s+s\s+"([^"]+)"', out)
    except Exception:
        return list(PROFILES.keys())


def main():
    try:
        active    = get_active() or "balanced"
        available = get_available()
    except Exception:
        print(json.dumps({"text": "<span color='#ff5555'>󰾅 ERR</span>", "class": "profile-error"}))
        return

    profile = PROFILES.get(active, {"icon": "󰾅", "label": active, "color": C_VAL})

    # ── Tooltip ─────────────────────────────────────────────
    t  = f"<span font_desc='JetBrains Mono, Fira Code, Monospace 9'>"
    t += f"<b><span color='{C_TITLE}'>{profile['icon']}  DESEMPENHO</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Perfil  :</span> <span color='{profile['color']}'><b>{profile['label']}</b></span>\n"
    t += f" └─ <span color='{C_SEC}'>Driver  :</span> <span color='{C_VAL}'>intel_pstate</span>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += f"<b><span color='{C_SEC}'>  Perfis disponíveis</span></b>\n"
    for p in available:
        info = PROFILES.get(p, {"icon": "󰾅", "label": p, "color": C_VAL})
        marker = f"<span color='{C_SAFE}'>●</span>" if p == active else f"<span color='{C_DIM}'>○</span>"
        t += f" {marker} <span color='{info['color']}'>{info['icon']}  {info['label']}</span>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span></span>"

    text = f"<span color='{profile['color']}'>{profile['icon']}</span>"

    print(json.dumps({
        "text":    text,
        "alt":     active,
        "tooltip": t,
        "class":   [f"profile-{active}"],
    }), flush=True)


if __name__ == "__main__":
    main()
