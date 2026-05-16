#!/usr/bin/env python3
import glob
import json

# Auto-detect battery — change if you have multiple batteries
_bats = sorted(glob.glob("/sys/class/power_supply/BAT*"))
BAT = _bats[0] if _bats else "/sys/class/power_supply/BAT0"

C_TITLE = "#bd93f9"
C_SEC   = "#8be9fd"
C_VAL   = "#f8f8f2"
C_ALERT = "#ff5555"
C_SAFE  = "#50fa7b"
C_WARN  = "#ffb86c"
C_DIM   = "#44475a"

ICONS_DISCHARGE = ["󰁺", "󰁻", "󰁼", "󰁽", "󰁾", "󰁿", "󰂀", "󰂁", "󰂂", "󰁹"]


def sysfs(name):
    try:
        return open(f"{BAT}/{name}").read().strip()
    except Exception:
        return None


def capacity_bar(pct, width=14):
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def main():
    try:
        capacity    = int(sysfs("capacity") or 0)
        status      = sysfs("status") or "Unknown"
        charge_now  = int(sysfs("charge_now") or 0)
        charge_full = int(sysfs("charge_full") or 1)
        voltage_uv  = int(sysfs("voltage_now") or 0)
        current_ua  = int(sysfs("current_now") or 0)
        cycles      = sysfs("cycle_count") or "?"
    except Exception:
        print(json.dumps({"text": "<span color='#ff5555'>󰂑 ERR</span>", "class": "bat-error"}))
        return

    power_w = abs(current_ua * voltage_uv) / 1e12
    health_raw = sysfs("charge_full_design")
    health  = round(charge_full / int(health_raw) * 100) if health_raw else 100

    # ── State ───────────────────────────────────────────────
    charging = status in ("Charging", "Full")

    if status == "Full":
        state  = "bat-full"
        bar_c  = C_SAFE
        icon   = "󰚚"
    elif status == "Charging":
        state  = "bat-charging"
        bar_c  = C_SAFE
        icon   = "󱐋"
    elif capacity <= 15:
        state  = "bat-critical"
        bar_c  = C_ALERT
        icon   = ICONS_DISCHARGE[0]
    elif capacity <= 30:
        state  = "bat-warning"
        bar_c  = C_WARN
        icon   = ICONS_DISCHARGE[max(0, capacity // 10 - 1)]
    else:
        state  = "bat-ok"
        bar_c  = C_VAL
        icon   = ICONS_DISCHARGE[min(9, capacity // 10)]

    # ── Time estimate ────────────────────────────────────────
    time_str = ""
    if current_ua > 0:
        hours = (charge_full - charge_now) / current_ua if charging else charge_now / current_ua
        h, m = int(hours), int((hours % 1) * 60)
        time_str = f"{h}h{m:02d}m"

    bar = capacity_bar(capacity)
    power_str  = f"{power_w:.1f}W" if power_w > 0.1 else "–"
    time_label = f"Full in {time_str}" if charging and time_str else \
                 f"Remaining {time_str}" if time_str else "–"

    # ── Tooltip ─────────────────────────────────────────────
    t  = f"<span font_desc='JetBrains Mono, Fira Code, Monospace 9'>"
    t += f"<b><span color='{C_TITLE}'>󰁹  BATTERY</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Charge :</span> <span color='{bar_c}'><b>{capacity}%</b></span>\n"
    t += f" ├─ <span color='{C_SEC}'>       </span> <span color='{bar_c}'>{bar}</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Status :</span> <span color='{bar_c}'><b>{status}</b></span>\n"
    t += f" ├─ <span color='{C_SEC}'>Time   :</span> <span color='{C_VAL}'>{time_label}</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Power  :</span> <span color='{C_VAL}'>{power_str}</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Health :</span> <span color='{'#50fa7b' if health >= 80 else '#ffb86c' if health >= 60 else '#ff5555'}'>{health}%</span>\n"
    t += f" └─ <span color='{C_SEC}'>Cycles :</span> <span color='{C_VAL}'>{cycles}</span>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span></span>"

    print(json.dumps({
        "text":    f"<span color='{bar_c}'>{icon}</span>",
        "alt":     state,
        "tooltip": t,
        "class":   [state],
    }), flush=True)


if __name__ == "__main__":
    main()
