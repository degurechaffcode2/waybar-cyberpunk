#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time

STATE_FILE = "/tmp/fw-ops-state.json"

# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def run(cmd, timeout=2):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL,
                                       timeout=timeout).decode().strip()
    except Exception:
        return ""

def service_active(name):
    active  = run(["systemctl", "is-active",  name]) == "active"
    enabled = run(["systemctl", "is-enabled", name]) in ("enabled", "static")
    result  = run(["systemctl", "show", name, "--property=Result"])
    # oneshot services ficam 'inactive' após completar — checar pelo resultado
    last_ok = "Result=success" in result
    return active or (enabled and last_ok)


# ──────────────────────────────────────────────────────────────
# NFTABLES
# ──────────────────────────────────────────────────────────────

def get_nft_info():
    """Returns (tables_list, input_policy, output_policy) without root when possible."""
    tables = []
    input_policy  = "UNKNOWN"
    output_policy = "UNKNOWN"

    raw = run(["nft", "list", "tables"])
    if raw:
        tables = [l.split()[-1] for l in raw.splitlines() if l.strip()]

    for chain, var in [("input", "input_policy"), ("output", "output_policy")]:
        chain_raw = run(["nft", "list", "chain", "inet", "filter", chain])
        if not chain_raw:
            chain_raw = run(["nft", "list", "chain", "ip", "filter", chain])
        if chain_raw:
            m = re.search(r'policy\s+(\w+)', chain_raw)
            if m:
                if chain == "input":
                    input_policy = m.group(1).upper()
                else:
                    output_policy = m.group(1).upper()

    # Fallback: parse /etc/nftables.conf directly (readable without root)
    if "UNKNOWN" in (input_policy, output_policy) or not tables:
        try:
            content = open("/etc/nftables.conf").read()
            if not tables:
                tables = re.findall(r'table\s+\w+\s+(\w+)\s*\{', content)

            current_chain = None
            for line in content.splitlines():
                if re.search(r'chain\s+input', line):
                    current_chain = "input"
                elif re.search(r'chain\s+output', line):
                    current_chain = "output"
                elif re.search(r'chain\s+forward', line):
                    current_chain = "forward"
                elif line.strip() == "}":
                    current_chain = None

                if current_chain:
                    m = re.search(r'policy\s+(drop|accept)', line, re.IGNORECASE)
                    if m:
                        val = m.group(1).upper()
                        if current_chain == "input"  and input_policy  == "UNKNOWN":
                            input_policy  = val
                        if current_chain == "output" and output_policy == "UNKNOWN":
                            output_policy = val
        except Exception:
            pass

    return tables, input_policy, output_policy


# ──────────────────────────────────────────────────────────────
# IPTABLES (fallback / parallel)
# ──────────────────────────────────────────────────────────────

def get_ipt_tables():
    """Read loaded iptables tables from /proc (no root needed)."""
    try:
        return open("/proc/net/ip_tables_names").read().strip().splitlines()
    except Exception:
        return []

def get_ipt_policy():
    """Try to read INPUT policy without root (works on some configs)."""
    raw = run(["iptables", "-L", "INPUT", "-n"])
    if raw:
        m = re.search(r'Chain INPUT \(policy (\w+)\)', raw)
        if m:
            return m.group(1).upper()
    return "UNKNOWN"


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

def get_pentest_rules():
    """Read active pentest rules from fw-ops state file."""
    try:
        if os.path.exists(STATE_FILE):
            data = json.load(open(STATE_FILE))
            return data.get("rules", [])
    except Exception:
        pass
    return []

def main():
    nft_active  = service_active("nftables")
    ipt_active  = service_active("iptables")
    firewalld   = service_active("firewalld")

    pentest_rules           = get_pentest_rules()
    nft_tables, nft_policy, nft_out_policy = get_nft_info()
    ipt_tables              = get_ipt_tables()
    ipt_policy              = get_ipt_policy() if (ipt_tables and not nft_active) else "N/A"

    # Active engine + policy
    if nft_active or nft_tables:
        engine        = "nftables"
        policy        = nft_policy
        output_policy = nft_out_policy
        tables        = nft_tables
    elif ipt_tables:
        engine        = "iptables"
        policy        = ipt_policy
        output_policy = "ACCEPT"   # iptables default when no output chain
        tables        = ipt_tables
    elif firewalld:
        engine        = "firewalld"
        policy        = "UNKNOWN"
        output_policy = "UNKNOWN"
        tables        = []
    else:
        engine        = "none"
        policy        = "NONE"
        output_policy = "NONE"
        tables        = []

    fw_on = engine != "none"

    # ── State ───────────────────────────────────────────────
    if not fw_on:
        state, bar_c = "fw-off",     "#ff5555"
    elif policy in ("ACCEPT", "UNKNOWN", "NONE"):
        state, bar_c = "fw-open",    "#ffb86c"
    else:
        state, bar_c = "fw-drop",    "#50fa7b"

    # ── Palette ─────────────────────────────────────────────
    C_TITLE = "#bd93f9"
    C_SEC   = "#8be9fd"
    C_VAL   = "#f8f8f2"
    C_ALERT = "#ff5555"
    C_SAFE  = "#50fa7b"
    C_WARN  = "#ffb86c"
    C_DIM   = "#44475a"

    def svc(v):
        return f"<span color='{C_SAFE}'>active ●</span>" if v else f"<span color='{C_DIM}'>inactive</span>"

    pol_c = C_SAFE if policy == "DROP" else (C_ALERT if policy in ("ACCEPT","NONE") else C_WARN)
    tables_str = ", ".join(tables) if tables else "N/A"

    # ── Tooltip ─────────────────────────────────────────────
    t  = f"<span font_desc='JetBrains Mono, Fira Code, Monospace 9'>"
    t += f"<b><span color='{C_TITLE}'>󰒏  FIREWALL</span></b>\n"
    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"

    t += f"<b><span color='{C_SEC}'>  SERVICES</span></b>\n"
    t += f" ├─ <span color='{C_SEC}'>nftables :</span> {svc(nft_active)}\n"
    t += f" ├─ <span color='{C_SEC}'>iptables :</span> {svc(ipt_active)}\n"
    t += f" └─ <span color='{C_SEC}'>firewalld:</span> {svc(firewalld)}\n"

    t += f"<b><span color='{C_SEC}'>󰖟  ACTIVE ENGINE</span></b>\n"
    eng_c = C_SAFE if fw_on else C_ALERT
    out_c = C_SAFE if output_policy == "ACCEPT" else (C_ALERT if output_policy == "DROP" else C_WARN)

    t += f" ├─ <span color='{C_SEC}'>Engine  :</span> <span color='{eng_c}'><b>{engine}</b></span>\n"
    t += f" ├─ <span color='{C_SEC}'>Tables  :</span> <span color='{C_VAL}'>{tables_str}</span>\n"
    t += f" ├─ <span color='{C_SEC}'>INPUT   :</span> <span color='{pol_c}'><b>{policy}</b></span>\n"
    t += f" └─ <span color='{C_SEC}'>OUTPUT  :</span> <span color='{out_c}'><b>{output_policy}</b></span>\n"

    if not fw_on:
        t += f"\n<span color='{C_ALERT}'><b>⚠️  SEM FIREWALL ATIVO!</b></span>\n"
    elif policy == "ACCEPT":
        t += f"\n<span color='{C_WARN}'>⚠️  Política ACCEPT — tráfego não bloqueado</span>\n"

    # ── Pentest rules ────────────────────────────────────────
    if pentest_rules:
        t += f"<b><span color='{C_SEC}'>󱗆  PENTEST RULES ({len(pentest_rules)} ativas)</span></b>\n"
        for r in pentest_rules:
            t += (f" ├─ <span color='{C_WARN}'>{r['proto'].upper()}</span>"
                  f" <span color='{C_ALERT}'>:{r['port']}</span>"
                  f" <span color='{C_DIM}'>{r['desc']}</span>\n")
        t  = t.rstrip(" ├─\n") + "\n"  # fix last branch
    else:
        t += f"<b><span color='{C_SEC}'>󱗆  PENTEST RULES</span></b>\n"
        t += f" └─ <span color='{C_DIM}'>Nenhuma porta temporária aberta</span>\n"

    t += f"<span color='{C_DIM}'>──────────────────────────</span>\n"
    t += (f"<span color='{C_WARN}'>L</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>painel</span>  "
          f"<span color='{C_WARN}'>R</span><span color='{C_DIM}'>:</span>"
          f"<span color='{C_VAL}'>ruleset</span></span>")

    # ── Bar text ─────────────────────────────────────────────
    if not fw_on:
        label = " OFF"
    elif pentest_rules:
        label = f" {len(pentest_rules)}▲"   # sinaliza portas abertas
    elif policy != "DROP":
        label = " !"
    else:
        label = ""
    text = f"<span color='{bar_c}'>󰒏{label}</span>"

    print(json.dumps({
        "text":    text,
        "alt":     state,
        "tooltip": t,
        "class":   [state],
    }), flush=True)


if __name__ == "__main__":
    main()
