#!/usr/bin/env python3
"""Waybar widget — Rogue AP monitor."""
import json
import os
import re
import subprocess

HOME        = os.path.expanduser("~")
SESSION     = f"{HOME}/rogue-ap/tmp/rogue-ap.pid"
LEASES      = "/var/lib/misc/dnsmasq.leases"
LOG_HOSTAPD = f"{HOME}/rogue-ap/logs/hostapd.log"
LOG_DNSMASQ = f"{HOME}/rogue-ap/logs/dnsmasq.log"

C_TITLE = "#00e5ff"
C_SEC   = "#a855f7"
C_VAL   = "#ffffff"
C_OK    = "#00ff9f"
C_WARN  = "#ffcc00"
C_ALERT = "#ff2055"
C_DIM   = "#556080"


def read_session():
    if not os.path.exists(SESSION):
        return None
    data = {}
    with open(SESSION) as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
    return data


def proc_running(name):
    try:
        subprocess.check_output(["pgrep", "-x", name], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def get_clients():
    clients = []
    if not os.path.exists(LEASES):
        return clients
    try:
        with open(LEASES) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    clients.append({
                        "mac":  parts[1],
                        "ip":   parts[2],
                        "name": parts[3] if parts[3] != "*" else "unknown",
                    })
    except Exception:
        pass
    return clients


def get_ap_ip(iface):
    try:
        out = subprocess.check_output(
            ["ip", "-4", "addr", "show", iface],
            stderr=subprocess.DEVNULL).decode()
        m = re.search(r"inet\s+([\d.]+)", out)
        return m.group(1) if m else "N/A"
    except Exception:
        return "N/A"


def get_nat_rules(uplink):
    try:
        out = subprocess.check_output(
            ["iptables", "-t", "nat", "-L", "POSTROUTING", "-n"],
            stderr=subprocess.DEVNULL).decode()
        return out.count("MASQUERADE")
    except Exception:
        return 0


def build_tooltip(session, clients, hostapd_ok, dnsmasq_ok):
    ap_iface = session.get("AP_IFACE", "wlan0")
    ul_iface = session.get("UPLINK_IFACE", "enp64s0")
    ap_ip    = get_ap_ip(ap_iface)
    nat      = get_nat_rules(ul_iface)
    start    = session.get("START", "?")

    hst_c = C_OK    if hostapd_ok else C_ALERT
    dns_c = C_OK    if dnsmasq_ok else C_ALERT
    nat_c = C_OK    if nat > 0    else C_ALERT

    t  = f"<span font_desc='MesloLGS Nerd Font 9'>"
    t += f"<b><span color='{C_TITLE}'>󰑩  ROGUE AP</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"

    t += f"<b><span color='{C_SEC}'>  Config</span></b>\n"
    t += f" ├─ <span color='{C_DIM}'>SSID   :</span> <span color='{C_VAL}'>{session.get('AP_SSID','?')}</span>\n"
    t += f" ├─ <span color='{C_DIM}'>Canal  :</span> <span color='{C_VAL}'>{session.get('AP_CHANNEL','?')}</span>\n"
    t += f" ├─ <span color='{C_DIM}'>Gateway:</span> <span color='{C_VAL}'>{ap_ip}</span>\n"
    t += f" └─ <span color='{C_DIM}'>Início :</span> <span color='{C_VAL}'>{start}</span>\n"

    t += f"<b><span color='{C_SEC}'>  Serviços</span></b>\n"
    t += f" ├─ <span color='{C_DIM}'>hostapd:</span> <span color='{hst_c}'>{'● ativo' if hostapd_ok else '✗ parado'}</span>\n"
    t += f" ├─ <span color='{C_DIM}'>dnsmasq:</span> <span color='{dns_c}'>{'● ativo' if dnsmasq_ok else '✗ parado'}</span>\n"
    t += f" └─ <span color='{C_DIM}'>NAT    :</span> <span color='{nat_c}'>{'● ativo' if nat > 0 else '✗ sem regra'}</span>\n"

    t += f"<b><span color='{C_SEC}'>󰀂  Clientes ({len(clients)})</span></b>\n"
    if clients:
        for i, c in enumerate(clients):
            prefix = " └─" if i == len(clients) - 1 else " ├─"
            t += f"{prefix} <span color='{C_OK}'>{c['ip']}</span>  <span color='{C_DIM}'>{c['mac']}</span>  <span color='{C_VAL}'>{c['name']}</span>\n"
    else:
        t += f" └─ <span color='{C_DIM}'>Nenhum cliente conectado</span>\n"

    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += f"<span color='{C_WARN}'>L</span><span color='{C_DIM}'>:</span><span color='{C_VAL}'>status</span>  "
    t += f"<span color='{C_WARN}'>R</span><span color='{C_DIM}'>:</span><span color='{C_VAL}'>captura</span>  "
    t += f"<span color='{C_WARN}'>M</span><span color='{C_DIM}'>:</span><span color='{C_VAL}'>parar AP</span></span>"

    return t


def main():
    session = read_session()

    # AP inativo
    if not session:
        print(json.dumps({
            "text":    f"<span color='{C_DIM}'>󰑩</span>",
            "alt":     "ap-off",
            "tooltip": f"<span font_desc='MesloLGS Nerd Font 9'><span color='{C_DIM}'>Rogue AP inativo</span></span>",
            "class":   ["ap-off"],
        }), flush=True)
        return

    hostapd_ok = proc_running("hostapd")
    dnsmasq_ok = proc_running("dnsmasq")
    clients    = get_clients()
    n          = len(clients)
    tooltip    = build_tooltip(session, clients, hostapd_ok, dnsmasq_ok)

    # Estado da barra
    if not hostapd_ok or not dnsmasq_ok:
        text  = f"<span color='{C_ALERT}'>󰑩!</span>"
        state = "ap-error"
    elif n == 0:
        text  = f"<span color='{C_WARN}'>󰑩</span>"
        state = "ap-on"
    else:
        text  = f"<span color='{C_OK}'>󰑩</span> <span color='{C_VAL}'>{n}</span>"
        state = "ap-clients"

    print(json.dumps({
        "text":    text,
        "alt":     state,
        "tooltip": tooltip,
        "class":   [state],
    }), flush=True)


if __name__ == "__main__":
    main()
