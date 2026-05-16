#!/usr/bin/env python3
import json
import re
import subprocess

# Portas que merecem atenção se expostas externamente
RISKY_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    80: "HTTP", 110: "POP3", 143: "IMAP", 389: "LDAP",
    443: "HTTPS", 445: "SMB", 512: "rexec", 513: "rlogin",
    514: "rsh", 631: "IPP", 873: "rsync", 3306: "MySQL",
    3389: "RDP", 4444: "Meterpreter", 5432: "PostgreSQL",
    5900: "VNC", 6379: "Redis", 8080: "HTTP-alt",
    8443: "HTTPS-alt", 27017: "MongoDB",
}


# ──────────────────────────────────────────────────────────────
# PARSE ss OUTPUT
# ──────────────────────────────────────────────────────────────

def parse_ss(proto):
    """Returns list of dicts: {proto, port, addr, process}."""
    flag = "-tlnpH" if proto == "tcp" else "-ulnpH"
    entries = []
    try:
        out = subprocess.check_output(["sudo", "-n", "ss", flag], stderr=subprocess.DEVNULL).decode()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            local = parts[3]        # e.g. 0.0.0.0:22 or [::]:80 or 127.0.0.1:631
            process = parts[5] if len(parts) > 5 else ""

            # Parse addr:port — handle IPv6 brackets
            m = re.match(r'^\[?([^\]]*)\]?:(\d+)$', local)
            if not m:
                continue
            addr = m.group(1)
            port = int(m.group(2))

            # Extract process name from users:(("name",pid=X,fd=Y))
            proc_m = re.search(r'"([^"]+)"', process)
            proc_name = proc_m.group(1) if proc_m else "?"

            # Qualquer 127.x.x.x ou ::1 ou %lo é loopback
            is_loopback = (
                addr.startswith("127.") or
                addr in ("::1", "lo") or
                addr.endswith("%lo")
            )
            entries.append({
                "proto":    proto.upper(),
                "port":     port,
                "addr":     addr,
                "process":  proc_name,
                "external": not is_loopback,
            })
    except Exception:
        pass
    return entries


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

def main():
    tcp = parse_ss("tcp")
    udp = parse_ss("udp")

    # Deduplica por (proto, port): prefere externa sobre loopback
    seen = {}
    for p in tcp + udp:
        key = (p["proto"], p["port"])
        if key not in seen or p["external"]:
            seen[key] = p
    all_ports = list(seen.values())

    external = [p for p in all_ports if p["external"]]
    risky    = [p for p in external if p["port"] in RISKY_PORTS]

    n_ext   = len(external)
    n_risky = len(risky)

    # ── State ───────────────────────────────────────────────
    if n_risky > 0:
        state, bar_c = "ports-risky",  "#ff5555"
    elif n_ext > 8:
        state, bar_c = "ports-many",   "#ffb86c"
    elif n_ext > 0:
        state, bar_c = "ports-some",   "#f1fa8c"
    else:
        state, bar_c = "ports-clean",  "#50fa7b"

    # ── Palette ─────────────────────────────────────────────
    C_TITLE = "#bd93f9"
    C_SEC   = "#8be9fd"
    C_VAL   = "#f8f8f2"
    C_ALERT = "#ff5555"
    C_SAFE  = "#50fa7b"
    C_WARN  = "#ffb86c"
    C_YEL   = "#f1fa8c"
    C_DIM   = "#44475a"

    def port_color(p):
        if p["port"] in RISKY_PORTS:
            return C_ALERT
        if p["external"]:
            return C_YEL
        return C_VAL

    def fmt_entry(p):
        name = RISKY_PORTS.get(p["port"], "")
        label = f"{name} " if name else ""
        binding = "0.0.0.0" if p["addr"] in ("0.0.0.0", "*", "::") else p["addr"]
        c = port_color(p)
        return (f" ├─ <span color='{C_SEC}'>{p['proto']}</span>"
                f" <span color='{c}'><b>:{p['port']}</b></span>"
                f" <span color='{C_DIM}'>{label}</span>"
                f"<span color='{C_VAL}'>{binding}</span>"
                f" <span color='{C_DIM}'>({p['process']})</span>")

    # Sort: external first, then by port
    sorted_ext = sorted(external, key=lambda p: (p["port"] not in RISKY_PORTS, p["port"]))
    loopback   = [p for p in all_ports if not p["external"]]

    # ── Tooltip ─────────────────────────────────────────────
    t  = f"<span font_desc='JetBrains Mono, Fira Code, Monospace 9'>"
    t += f"<b><span color='{C_TITLE}'>󰲝  OPEN PORTS</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"

    # Summary line
    ext_c = C_ALERT if n_risky else (C_WARN if n_ext > 8 else C_YEL if n_ext else C_SAFE)
    t += (f"<b><span color='{C_SEC}'>External:</span></b> <span color='{ext_c}'><b>{n_ext}</b></span>"
          f"  <span color='{C_SEC}'>Risky:</span> <span color='{C_ALERT if n_risky else C_SAFE}'><b>{n_risky}</b></span>"
          f"  <span color='{C_SEC}'>Loopback:</span> <span color='{C_DIM}'>{len(loopback)}</span>\n")
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"

    if sorted_ext:
        t += f"<b><span color='{C_SEC}'>󰖟  EXPOSED (all interfaces)</span></b>\n"
        for p in sorted_ext[:12]:
            t += fmt_entry(p) + "\n"
        if len(sorted_ext) > 12:
            t += f" └─ <span color='{C_DIM}'>... +{len(sorted_ext)-12} mais</span>\n"
    else:
        t += f"<span color='{C_SAFE}'>Nenhuma porta exposta externamente</span>\n"

    if loopback:
        t += f"<b><span color='{C_SEC}'>  LOOPBACK only</span></b>\n"
        for p in sorted(loopback, key=lambda p: p["port"])[:6]:
            t += fmt_entry(p) + "\n"
        if len(loopback) > 6:
            t += f" └─ <span color='{C_DIM}'>... +{len(loopback)-6} mais</span>\n"

    if risky:
        t += f"\n<span color='{C_ALERT}'><b>⚠️  Portas de risco expostas!</b></span>\n"

    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += (f"<span color='{C_WARN}'>L</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>ss -tlnp</span>  "
          f"<span color='{C_WARN}'>R</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>ss -ulnp</span></span>")

    # ── Bar text ─────────────────────────────────────────────
    if n_risky:
        text = f"<span color='{bar_c}'>󰲝!</span>"
    else:
        text = f"<span color='{bar_c}'>󰲝</span>"

    print(json.dumps({
        "text":    text,
        "alt":     state,
        "tooltip": t,
        "class":   [state],
    }), flush=True)


if __name__ == "__main__":
    main()
