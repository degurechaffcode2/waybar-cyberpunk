#!/usr/bin/env python3
import json
import re
import subprocess

# Portas conhecidas para identificar o serviço remoto
KNOWN_PORTS = {
    22: "SSH", 25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
    143: "IMAP", 443: "HTTPS", 465: "SMTPS", 587: "SMTP",
    993: "IMAPS", 995: "POP3S", 1194: "OpenVPN", 1723: "PPTP",
    3306: "MySQL", 3389: "RDP", 4444: "Meterp", 5432: "PgSQL",
    5900: "VNC", 6379: "Redis", 8080: "HTTP-alt", 8443: "HTTPS-alt",
    27017: "Mongo", 51820: "WireGuard",
}

RISKY_REMOTE = {4444, 5900, 3389, 445, 6379, 27017}


# ── Parser ────────────────────────────────────────────────────

def get_connections():
    conns = []
    try:
        out = subprocess.check_output(
            ["ss", "-tpn", "state", "established"],
            stderr=subprocess.DEVNULL).decode()

        for line in out.splitlines()[1:]:   # pula header
            parts = line.split()
            if len(parts) < 5:
                continue

            local  = parts[3]
            remote = parts[4]
            proc_field = parts[5] if len(parts) > 5 else ""

            # Parse IP:port do remoto (suporta IPv4 e IPv6)
            m = re.match(r'^(.+):(\d+)$', remote)
            if not m:
                continue
            rip   = m.group(1).strip('[]')
            rport = int(m.group(2))

            # Ignora loopback e link-local
            if rip.startswith("127.") or rip in ("::1", "0.0.0.0"):
                continue

            # Parse porta local
            lm = re.match(r'^(.+):(\d+)$', local)
            lport = int(lm.group(2)) if lm else 0

            # Nome do processo
            pm = re.search(r'"([^"]+)"', proc_field)
            proc = pm.group(1) if pm else "?"

            conns.append({
                "rip":   rip,
                "rport": rport,
                "lport": lport,
                "proc":  proc,
                "risky": rport in RISKY_REMOTE,
            })
    except Exception:
        pass
    return conns


# ── Main ─────────────────────────────────────────────────────

def main():
    conns   = get_connections()
    n_total = len(conns)
    n_risky = sum(1 for c in conns if c["risky"])

    # Agrupa por IP remoto
    by_ip = {}
    for c in conns:
        by_ip.setdefault(c["rip"], []).append(c)

    n_ips = len(by_ip)

    # ── Palette ──────────────────────────────────────────────
    C_TITLE = "#bd93f9"
    C_SEC   = "#8be9fd"
    C_VAL   = "#f8f8f2"
    C_ALERT = "#ff5555"
    C_SAFE  = "#50fa7b"
    C_WARN  = "#ffb86c"
    C_DIM   = "#44475a"

    # ── Estado ───────────────────────────────────────────────
    if n_risky:
        state, bar_c = "conn-risky", C_ALERT
    elif n_total == 0:
        state, bar_c = "conn-idle",  C_VAL
    elif n_total <= 8:
        state, bar_c = "conn-few",   C_SAFE
    elif n_total <= 20:
        state, bar_c = "conn-many",  C_WARN
    else:
        state, bar_c = "conn-high",  C_ALERT

    # ── Tooltip ──────────────────────────────────────────────
    t  = f"<span font_desc='JetBrains Mono, Fira Code, Monospace 9'>"
    t += f"<b><span color='{C_TITLE}'>󰒍  CONEXÕES EXTERNAS</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"

    total_c = C_ALERT if n_risky else (C_WARN if n_total > 8 else C_SAFE if n_total else C_DIM)
    t += (f"<b><span color='{C_SEC}'>Total:</span></b> <span color='{total_c}'><b>{n_total}</b></span>"
          f"  <span color='{C_SEC}'>IPs:</span> <span color='{C_VAL}'>{n_ips}</span>"
          f"  <span color='{C_SEC}'>Risco:</span> <span color='{C_ALERT if n_risky else C_SAFE}'><b>{n_risky}</b></span>\n")
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"

    if by_ip:
        # Ordena: risky primeiro, depois por IP
        sorted_ips = sorted(by_ip.items(),
                            key=lambda x: (not any(c["risky"] for c in x[1]), x[0]))
        for ip, ip_conns in sorted_ips[:12]:
            ports = sorted(set(c["rport"] for c in ip_conns))
            procs = sorted(set(c["proc"] for c in ip_conns))
            is_risky = any(c["risky"] for c in ip_conns)

            ip_c  = C_ALERT if is_risky else C_VAL
            svc   = KNOWN_PORTS.get(ports[0], "") if ports else ""
            ports_str = ", ".join(
                f":{p}" + (f"({KNOWN_PORTS[p]})" if p in KNOWN_PORTS else "")
                for p in ports[:3]
            )
            if len(ports) > 3:
                ports_str += f" +{len(ports)-3}"

            t += (f" ├─ <span color='{ip_c}'>{ip:<16}</span>"
                  f" <span color='{C_DIM}'>{ports_str}</span>"
                  f" <span color='{C_SEC}'>{procs[0]}</span>\n")

        if len(by_ip) > 12:
            t += f" └─ <span color='{C_DIM}'>... +{len(by_ip)-12} IPs</span>\n"

        if n_risky:
            t += f"\n<span color='{C_ALERT}'><b>⚠️  Conexão em porta de risco!</b></span>\n"
    else:
        t += f" <span color='{C_DIM}'>Nenhuma conexão externa</span>\n"

    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += (f"<span color='{C_WARN}'>L</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>ss -tp</span>  "
          f"<span color='{C_WARN}'>R</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>ss -tn</span></span>")

    # ── Barra ────────────────────────────────────────────────
    if n_risky:
        text = f"<span color='{bar_c}'>󰒍!</span>"
    elif n_total:
        text = f"<span color='{bar_c}'>󰒍</span>"
    else:
        text = f"<span color='{C_VAL}'>󰒍</span>"

    print(json.dumps({
        "text":    text,
        "alt":     state,
        "tooltip": t,
        "class":   [state],
    }), flush=True)


if __name__ == "__main__":
    main()
