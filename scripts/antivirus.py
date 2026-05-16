#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time

CLAMD_LOG      = "/var/log/clamav/clamd.log"
FRESHCLAM_LOG  = "/var/log/clamav/freshclam.log"
DB_DIR         = "/var/lib/clamav"


# ──────────────────────────────────────────────────────────────
# SERVICES
# ──────────────────────────────────────────────────────────────

def service_active(name):
    try:
        out = subprocess.check_output(
            ["systemctl", "is-active", name],
            stderr=subprocess.DEVNULL).decode().strip()
        return out == "active"
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────
# DATABASE INFO
# ──────────────────────────────────────────────────────────────

def get_db_info():
    """Returns (age_hours, total_sigs, daily_version, last_update_str)."""
    age_hours    = 999.0
    total_sigs   = 0
    daily_ver    = "?"
    last_update  = "Unknown"

    # Age from file mtime (daily.cld preferred, fallback daily.cvd)
    for fname in ("daily.cld", "daily.cvd"):
        fpath = os.path.join(DB_DIR, fname)
        if os.path.exists(fpath):
            age_hours = (time.time() - os.path.getmtime(fpath)) / 3600
            break

    # Parse freshclam.log for sig counts and last run time
    if os.path.exists(FRESHCLAM_LOG):
        try:
            content = open(FRESHCLAM_LOG).read()

            m = re.search(r'ClamAV update process started at (.+)', content)
            if m:
                last_update = m.group(1).strip()

            for pattern, key in [
                (r'daily\.\w+.*?version:\s*(\d+),\s*sigs:\s*(\d+)', "daily"),
                (r'main\.\w+.*?version:\s*\d+,\s*sigs:\s*(\d+)',    "main"),
                (r'bytecode\.\w+.*?sigs:\s*(\d+)',                   "byte"),
            ]:
                hit = re.search(pattern, content)
                if hit:
                    if key == "daily":
                        daily_ver   = hit.group(1)
                        total_sigs += int(hit.group(2))
                    else:
                        total_sigs += int(hit.group(1))
        except Exception:
            pass

    return age_hours, total_sigs, daily_ver, last_update


# ──────────────────────────────────────────────────────────────
# THREATS
# ──────────────────────────────────────────────────────────────

def get_threats():
    """Return list of FOUND lines from clamd.log (readable without root)."""
    threats = []
    if os.path.exists(CLAMD_LOG):
        try:
            for line in open(CLAMD_LOG):
                if "FOUND" in line:
                    threats.append(line.strip())
        except Exception:
            pass
    return threats


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

def main():
    daemon_ok      = service_active("clamav-daemon")
    freshclam_ok   = service_active("clamav-freshclam")
    age_h, sigs, ver, last_upd = get_db_info()
    threats        = get_threats()

    n_threats   = len(threats)
    db_stale    = age_h > 48   # > 2 days
    db_warn     = age_h > 24   # > 1 day

    # ── Palette ─────────────────────────────────────────────
    C_TITLE = "#bd93f9"
    C_SEC   = "#8be9fd"
    C_VAL   = "#f8f8f2"
    C_ALERT = "#ff5555"
    C_SAFE  = "#50fa7b"
    C_WARN  = "#ffb86c"
    C_DIM   = "#44475a"

    # ── Bar state ───────────────────────────────────────────
    if not daemon_ok:
        state, bar_c, label = "av-down",    C_ALERT, "DOWN"
    elif n_threats > 0:
        state, bar_c, label = "av-threat",  C_ALERT, f"{n_threats}!"
    elif db_stale:
        state, bar_c, label = "av-stale",   C_WARN,  "OLD"
    else:
        state, bar_c, label = "av-clean",   C_SAFE,  ""

    # ── Format helpers ──────────────────────────────────────
    def fmt_sigs(n):
        if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
        if n >= 1_000:     return f"{n/1_000:.0f}K"
        return str(n)

    def fmt_age(h):
        if h < 1:    return f"{int(h*60)}min"
        if h < 24:   return f"{h:.1f}h"
        return f"{h/24:.1f}d"

    def ok_str(v):
        return (f"<span color='{C_SAFE}'>active ●</span>" if v
                else f"<span color='{C_ALERT}'>down ⚠️</span>")

    sigs_str  = fmt_sigs(sigs) if sigs else "N/A"
    age_str   = fmt_age(age_h)
    age_c     = C_ALERT if db_stale else (C_WARN if db_warn else C_SAFE)
    upd_short = last_upd[:22] if last_upd != "Unknown" else "Unknown"

    # ── Tooltip ─────────────────────────────────────────────
    t  = f"<span font_desc='JetBrains Mono, Fira Code, Monospace 9'>"
    t += f"<b><span color='{C_TITLE}'>󰒃  CLAMAV</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"

    t += f"<b><span color='{C_SEC}'>  SERVICES</span></b>\n"
    t += f" ├─ <span color='{C_SEC}'>clamd    :</span> {ok_str(daemon_ok)}\n"
    t += f" └─ <span color='{C_SEC}'>freshclam:</span> {ok_str(freshclam_ok)}\n"

    t += f"<b><span color='{C_SEC}'>󰆧  DATABASE</span></b>\n"
    t += f" ├─ <span color='{C_SEC}'>Version :</span> <span color='{C_VAL}'>daily.{ver}</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Sigs    :</span> <span color='{C_VAL}'>{sigs_str}</span>\n"
    t += f" ├─ <span color='{C_SEC}'>Age     :</span> <span color='{age_c}'>{age_str}</span>\n"
    t += f" └─ <span color='{C_SEC}'>Updated :</span> <span color='{C_VAL}'>{upd_short}</span>\n"

    t += f"<b><span color='{C_SEC}'>󱣡  THREATS</span></b>\n"
    if threats:
        for line in threats[-3:]:
            # extract just the path + virus name
            snippet = re.sub(r'^\S+\s+', '', line)[:38]
            t += f" ├─ <span color='{C_ALERT}'>{snippet}</span>\n"
        t += f" └─ <span color='{C_ALERT}'><b>{n_threats} FOUND — check log!</b></span>\n"
    else:
        t += f" └─ <span color='{C_SAFE}'>Clean — no threats in log</span>\n"

    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += (f"<span color='{C_WARN}'>L</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>clamd log</span>  "
          f"<span color='{C_WARN}'>R</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>update DB</span>  "
          f"<span color='{C_WARN}'>M</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>scan ~</span></span>")

    # ── Bar text (minimal) ───────────────────────────────────
    if label:
        text = f"<span color='{bar_c}'>󰒃  {label}</span>"
    else:
        text = f"<span color='{bar_c}'>󰒃</span>"

    print(json.dumps({
        "text":    text,
        "alt":     state,
        "tooltip": t,
        "class":   [state],
    }), flush=True)


if __name__ == "__main__":
    main()
