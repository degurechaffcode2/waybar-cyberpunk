#!/usr/bin/env bash
# fw-ops — Regras temporárias de pentest para nftables
# Uso: fw-ops <add|del|list|flush|status|panel> [args]

CHAIN_PATH="inet filter input"
TAG="pentest"
STATE_FILE="/tmp/fw-ops-state.json"

R="\033[0;31m"  G="\033[0;32m"  Y="\033[0;33m"
C="\033[0;36m"  D="\033[0;90m"  B="\033[1m"  N="\033[0m"
LINE="${D}──────────────────────────────────────────${N}"

# ── State file ───────────────────────────────────────────────

state_load() {
    [[ -f "$STATE_FILE" ]] && cat "$STATE_FILE" || echo '{"rules":[]}'
}

state_add() {
    local proto="$1" port="$2" desc="$3"
    local tmp; tmp=$(state_load | python3 -c "
import json,sys
d=json.load(sys.stdin)
d['rules'] = [r for r in d['rules'] if not (r['proto']=='$proto' and r['port']==$port)]
d['rules'].append({'proto':'$proto','port':$port,'desc':'$desc'})
print(json.dumps(d))")
    echo "$tmp" > "$STATE_FILE"
}

state_del() {
    local proto="$1" port="$2"
    local tmp; tmp=$(state_load | python3 -c "
import json,sys
d=json.load(sys.stdin)
d['rules'] = [r for r in d['rules'] if not (r['proto']=='$proto' and r['port']==$port)]
print(json.dumps(d))")
    echo "$tmp" > "$STATE_FILE"
}

state_clear() {
    echo '{"rules":[]}' > "$STATE_FILE"
}

waybar_refresh() {
    pkill -SIGUSR2 waybar 2>/dev/null || true
}

# ── ADD ──────────────────────────────────────────────────────

cmd_add() {
    local proto="${1,,}" port="$2" desc="${3:-op}"

    [[ -z "$proto" || -z "$port" ]] && {
        echo -e "${R}[!]${N} Uso: fw-ops add <tcp|udp> <porta> [descrição]"; exit 1; }
    [[ "$proto" != "tcp" && "$proto" != "udp" ]] && {
        echo -e "${R}[!]${N} Protocolo inválido: $proto"; exit 1; }
    [[ ! "$port" =~ ^[0-9]+$ || $port -lt 1 || $port -gt 65535 ]] && {
        echo -e "${R}[!]${N} Porta inválida: $port"; exit 1; }

    if sudo nft -a list chain $CHAIN_PATH 2>/dev/null | grep -qE "${proto} dport ${port} "; then
        echo -e "${Y}[!]${N} Regra ${C}${proto}/${port}${N} já existe"
        exit 0
    fi

    echo -e "${G}[+]${N} Abrindo ${B}${C}${proto}/${port}${N} — ${D}${desc}${N}"
    sudo nft add rule $CHAIN_PATH "$proto" dport "$port" accept \
        comment "\"${TAG}: ${desc}\""

    if [[ $? -eq 0 ]]; then
        state_add "$proto" "$port" "$desc"
        echo -e "${G}[+]${N} Regra adicionada"
        waybar_refresh
    else
        echo -e "${R}[!]${N} Falha ao adicionar regra"
        exit 1
    fi
}

# ── DEL ──────────────────────────────────────────────────────

cmd_del() {
    local proto="${1,,}" port="$2"

    [[ -z "$proto" || -z "$port" ]] && {
        echo -e "${R}[!]${N} Uso: fw-ops del <tcp|udp> <porta>"; exit 1; }

    local handle
    handle=$(sudo nft -a list chain $CHAIN_PATH 2>/dev/null \
             | grep -E "${proto} dport ${port} " \
             | grep -oP 'handle \K\d+')

    if [[ -z "$handle" ]]; then
        echo -e "${Y}[!]${N} Regra não encontrada: ${C}${proto}/${port}${N}"
        state_del "$proto" "$port"
        exit 1
    fi

    echo -e "${R}[-]${N} Removendo ${B}${C}${proto}/${port}${N} (handle $handle)"
    sudo nft delete rule $CHAIN_PATH handle "$handle"

    if [[ $? -eq 0 ]]; then
        state_del "$proto" "$port"
        echo -e "${G}[+]${N} Regra removida"
        waybar_refresh
    else
        echo -e "${R}[!]${N} Falha ao remover"
        exit 1
    fi
}

# ── LIST ─────────────────────────────────────────────────────

cmd_list() {
    local rules
    rules=$(sudo nft -a list chain $CHAIN_PATH 2>/dev/null | grep "${TAG}:")

    echo -e "${B}${C}[*] Regras temporárias ativas:${N}\n"

    if [[ -z "$rules" ]]; then
        echo -e "  ${D}Nenhuma regra temporária ativa${N}\n"
    else
        printf "  ${B}%-5s %-7s %-26s %s${N}\n" "PROTO" "PORTA" "DESCRIÇÃO" "HANDLE"
        echo -e "  ${D}─────────────────────────────────────────${N}"
        while IFS= read -r line; do
            local proto port desc handle
            proto=$(echo "$line"  | grep -oP '(tcp|udp)')
            port=$(echo "$line"   | grep -oP 'dport \K\d+')
            desc=$(echo "$line"   | grep -oP "${TAG}: \K[^\"]+")
            handle=$(echo "$line" | grep -oP 'handle \K\d+')
            printf "  ${G}%-5s${N} ${C}%-7s${N} ${Y}%-26s${N} ${D}%s${N}\n" \
                   "${proto:-?}" "${port:-?}" "${desc:-?}" "${handle:-?}"
        done <<< "$rules"
        echo ""
    fi
}

# ── FLUSH ────────────────────────────────────────────────────

cmd_flush() {
    local handles
    handles=$(sudo nft -a list chain $CHAIN_PATH 2>/dev/null \
              | grep "${TAG}:" | grep -oP 'handle \K\d+')

    if [[ -z "$handles" ]]; then
        echo -e "${D}[*] Nenhuma regra temporária para remover${N}"
        return
    fi

    local count=0
    while IFS= read -r handle; do
        sudo nft delete rule $CHAIN_PATH handle "$handle" 2>/dev/null && ((count++))
    done <<< "$handles"

    state_clear
    echo -e "${G}[+]${N} ${B}$count${N} regra(s) removida(s)"
    waybar_refresh
}

# ── STATUS ───────────────────────────────────────────────────

cmd_status() {
    clear
    echo -e "${B}${C}╔══════════════════════════════════════════╗${N}"
    echo -e "${B}${C}║        FIREWALL — MANUAL COMPLETO        ║${N}"
    echo -e "${B}${C}╚══════════════════════════════════════════╝${N}"

    # ── Estado atual ─────────────────────────────────────────
    echo -e "\n${B}${C}  1. ESTADO ATUAL${N}\n"

    local svc_result
    svc_result=$(systemctl show nftables --property=Result 2>/dev/null | cut -d= -f2)
    local enabled
    enabled=$(systemctl is-enabled nftables 2>/dev/null)

    if [[ "$enabled" == "enabled" && "$svc_result" == "success" ]]; then
        echo -e "  ${G}●${N} Engine : ${G}${B}nftables ativo${N}"
    else
        echo -e "  ${R}●${N} Engine : ${R}${B}INATIVO${N}  — execute: sudo systemctl enable --now nftables"
    fi

    # Políticas atuais do arquivo de config
    local in_pol out_pol
    in_pol=$(awk '/chain input/,/^[[:space:]]*}/' /etc/nftables.conf \
             | grep -oP 'policy \K(drop|accept)' | head -1 | tr '[:lower:]' '[:upper:]')
    out_pol=$(awk '/chain output/,/^[[:space:]]*}/' /etc/nftables.conf \
              | grep -oP 'policy \K(drop|accept)' | head -1 | tr '[:lower:]' '[:upper:]')

    local in_c="${G}"; [[ "$in_pol"  != "DROP"   ]] && in_c="${Y}"
    local out_c="${G}"; [[ "$out_pol" != "ACCEPT" ]] && out_c="${R}"

    echo -e "  ${G}●${N} INPUT  : ${in_c}${B}${in_pol:-UNKNOWN}${N}"
    echo -e "  ${G}●${N} OUTPUT : ${out_c}${B}${out_pol:-UNKNOWN}${N}"

    echo -e "\n  ${B}Regras base (INPUT chain):${N}"
    echo -e "  ${D}✗  pacotes inválidos       → drop${N}"
    echo -e "  ${G}✓  conexões estabelecidas  → accept${N}  ${D}(retorno do seu tráfego)${N}"
    echo -e "  ${G}✓  loopback (127.x)        → accept${N}  ${D}(serviços locais)${N}"
    echo -e "  ${G}✓  ICMP / ICMPv6           → accept${N}  ${D}(ping, diagnóstico)${N}"

    # Regras pentest ativas
    local pentest_rules
    pentest_rules=$(sudo nft -a list chain inet filter input 2>/dev/null | grep "pentest:")
    if [[ -n "$pentest_rules" ]]; then
        echo -e "\n  ${B}Portas temporárias abertas (pentest):${N}"
        while IFS= read -r line; do
            local proto port desc handle
            proto=$(echo "$line"  | grep -oP '(tcp|udp)')
            port=$(echo "$line"   | grep -oP 'dport \K\d+')
            desc=$(echo "$line"   | grep -oP 'pentest: \K[^"]+')
            handle=$(echo "$line" | grep -oP 'handle \K\d+')
            echo -e "  ${R}▲  ${proto^^}/:${port}${N}  ${Y}${desc}${N}  ${D}[handle $handle]${N}"
        done <<< "$pentest_rules"
    fi

    # ── O que é o firewall ───────────────────────────────────
    echo -e "\n$LINE"
    echo -e "${B}${C}  2. O QUE É O FIREWALL (nftables)${N}\n"
    echo -e "  O nftables é o filtro de pacotes do kernel Linux. Ele decide o que"
    echo -e "  entra, sai e é encaminhado pela sua máquina com base em regras.\n"
    echo -e "  ${B}Chains (cadeias):${N}"
    echo -e "  ${C}INPUT  ${N}  pacotes destinados à sua própria máquina"
    echo -e "  ${C}OUTPUT ${N}  pacotes gerados pela sua máquina"
    echo -e "  ${C}FORWARD${N}  pacotes em trânsito (roteamento) — não somos roteador\n"
    echo -e "  ${B}As regras são avaliadas em ordem. A primeira que casar, vence.${N}"
    echo -e "  ${D}Se nenhuma casar, a política padrão da chain é aplicada.${N}"

    # ── Políticas ────────────────────────────────────────────
    echo -e "\n$LINE"
    echo -e "${B}${C}  3. POLÍTICAS — DROP vs ACCEPT${N}\n"
    echo -e "  ${G}${B}DROP  ${N}  Tudo bloqueado por padrão."
    echo -e "          Só passa o que tiver regra explícita de accept."
    echo -e "          ${D}→ Correto para pentest, campo, redes não confiáveis.${N}\n"
    echo -e "  ${Y}${B}ACCEPT${N}  Tudo permitido por padrão."
    echo -e "          Regras só servem para bloquear exceções."
    echo -e "          ${D}→ Evite. Expõe todos os seus serviços à rede.${N}\n"
    echo -e "  ${B}Combinação ideal em pentest:${N}\n"
    echo -e "  ${G}INPUT  DROP  ${N}  você não é servidor — outros hosts não te alcançam"
    echo -e "  ${G}OUTPUT ACCEPT${N}  suas ferramentas saem sem restrição"
    echo -e "  ${G}established  ${N}  retorno das suas conexões volta automaticamente\n"
    echo -e "  ${D}Com essa config: nmap, masscan, burp, sqlmap, hydra, metasploit"
    echo -e "  (exploits ativos) funcionam sem abrir nenhuma porta.${N}"

    # ── Quando abrir portas ──────────────────────────────────
    echo -e "\n$LINE"
    echo -e "${B}${C}  4. QUANDO VOCÊ PRECISA ABRIR PORTA (fw-ops add)${N}\n"
    echo -e "  Apenas quando o ${B}alvo conecta de volta em você${N}:\n"
    echo -e "  ${Y}Reverse shell / Meterpreter ${D}— alvo recebe exploit, chama seu listener${N}"
    echo -e "  ${Y}Beacon C2                   ${D}— implante chama o servidor de C2 (você)${N}"
    echo -e "  ${Y}Pivot / SOCKS proxy         ${D}— tráfego da rede interna passa por você${N}\n"
    echo -e "  ${R}Nunca deixe ACCEPT global em campo.${N}"
    echo -e "  ${D}Você expõe sua máquina para todos os alvos que está atacando —"
    echo -e "  alguns podem tentar contra-atacar ou enumerá-la.${N}"

    # ── Como mudar a política ────────────────────────────────
    echo -e "\n$LINE"
    echo -e "${B}${C}  5. COMO MUDAR A POLÍTICA${N}\n"
    echo -e "  ${B}INPUT:${N}\n"
    echo -e "  ${D}# Bloquear (recomendado em campo):${N}"
    echo -e "  sudo nft chain inet filter input '{ policy drop; }'\n"
    echo -e "  ${D}# Liberar (evite em campo):${N}"
    echo -e "  sudo nft chain inet filter input '{ policy accept; }'\n"
    echo -e "  ${B}OUTPUT:${N}\n"
    echo -e "  ${D}# Liberar (padrão — ferramentas saem livres):${N}"
    echo -e "  sudo nft chain inet filter output '{ policy accept; }'\n"
    echo -e "  ${D}# Bloquear saída (raramente necessário):${N}"
    echo -e "  sudo nft chain inet filter output '{ policy drop; }'\n"
    echo -e "  ${B}Para tornar permanente:${N}"
    echo -e "  ${D}1. Edite /etc/nftables.conf (altere a linha 'policy' da chain)${N}"
    echo -e "  ${D}2. sudo systemctl restart nftables${N}"

    # ── fw-ops cheatsheet ────────────────────────────────────
    echo -e "\n$LINE"
    echo -e "${B}${C}  6. fw-ops — CHEATSHEET${N}\n"
    printf "  ${G}%-35s${N} ${D}%s${N}\n" "fw-ops add tcp 4444 revshell"  "abre porta para listener"
    printf "  ${G}%-35s${N} ${D}%s${N}\n" "fw-ops add tcp 8080 burp"      "proxy Burp Suite"
    printf "  ${G}%-35s${N} ${D}%s${N}\n" "fw-ops add tcp 443  c2-https"  "beacon C2 HTTPS"
    printf "  ${G}%-35s${N} ${D}%s${N}\n" "fw-ops add udp 53   dns-spoof" "spoofing DNS"
    printf "  ${R}%-35s${N} ${D}%s${N}\n" "fw-ops del tcp 4444"           "fecha porta específica"
    printf "  ${R}%-35s${N} ${D}%s${N}\n" "fw-ops flush"                  "remove TODAS as temporárias"
    printf "  ${C}%-35s${N} ${D}%s${N}\n" "fw-ops list"                   "lista portas abertas"
    printf "  ${C}%-35s${N} ${D}%s${N}\n" "fw-ops panel"                  "painel de status"
    echo ""
    echo -e "  ${Y}Boas práticas:${N}"
    echo -e "  ${D}→ Sempre use fw-ops flush ao terminar o engagement${N}"
    echo -e "  ${D}→ Regras temporárias somem no reboot (proposital)${N}"
    echo -e "  ${D}→ Use descrições claras: revshell, c2, burp, pivot${N}\n"

    echo -e "$LINE"
    read -rp "  Pressione Enter para fechar..."
}

# ── PANEL (clique waybar) ────────────────────────────────────

cmd_panel() {
    clear
    echo -e "${B}${C}╔══════════════════════════════════════════╗${N}"
    echo -e "${B}${C}║         FIREWALL — PENTEST PANEL         ║${N}"
    echo -e "${B}${C}╚══════════════════════════════════════════╝${N}\n"

    # Status do serviço
    local svc_state enabled result
    svc_state=$(systemctl is-active nftables 2>/dev/null)
    enabled=$(systemctl is-enabled nftables 2>/dev/null)
    result=$(systemctl show nftables --property=Result 2>/dev/null | cut -d= -f2)

    if [[ "$enabled" == "enabled" && "$result" == "success" ]]; then
        echo -e "  ${G}●${N} nftables ${G}ativo${N}  |  Boot: ${G}habilitado${N}"
    else
        echo -e "  ${R}●${N} nftables ${R}INATIVO${N}  |  Boot: ${enabled}"
    fi

    # Política INPUT do arquivo de config
    local policy
    policy=$(awk '/chain input/,/^[[:space:]]*}/' /etc/nftables.conf \
             | grep -oP 'policy \K(drop|accept)' | head -1 | tr '[:lower:]' '[:upper:]')
    [[ "$policy" == "DROP" ]] \
        && echo -e "  ${G}●${N} INPUT policy: ${G}${B}DROP${N} (bloqueado por padrão)" \
        || echo -e "  ${Y}●${N} INPUT policy: ${Y}${B}${policy:-UNKNOWN}${N}"

    echo ""
    echo -e "$LINE"

    # Regras temporárias ativas
    cmd_list

    echo -e "$LINE"

    # Mini manual
    echo -e "${B}${C}  MANUAL RÁPIDO — fw-ops${N}\n"

    echo -e "  ${G}ABRIR PORTA${N}"
    echo -e "  ${D}fw-ops add tcp 4444 revshell${N}       listener meterpreter/nc"
    echo -e "  ${D}fw-ops add tcp 8080 burp-proxy${N}     proxy Burp Suite"
    echo -e "  ${D}fw-ops add tcp 443  c2-https${N}       C2 HTTPS"
    echo -e "  ${D}fw-ops add udp 53   dns-spoof${N}      spoofing DNS\n"

    echo -e "  ${R}FECHAR PORTA${N}"
    echo -e "  ${D}fw-ops del tcp 4444${N}                remove uma regra específica"
    echo -e "  ${D}fw-ops flush${N}                       remove TODAS temporárias\n"

    echo -e "  ${C}INSPECIONAR${N}"
    echo -e "  ${D}fw-ops list${N}                        lista regras temporárias"
    echo -e "  ${D}fw-ops status${N}                      ruleset completo (sudo)\n"

    echo -e "  ${Y}BOAS PRÁTICAS${N}"
    echo -e "  ${D}→ Sempre feche portas após o engagement (fw-ops del / flush)${N}"
    echo -e "  ${D}→ Use descrições claras: revshell, burp, c2, pivot${N}"
    echo -e "  ${D}→ Regras temporárias são perdidas no reboot (proposital)${N}\n"

    echo -e "$LINE"
    read -rp "  Pressione Enter para fechar..."
}

# ── Main ─────────────────────────────────────────────────────

case "${1:-}" in
    add)    cmd_add    "$2" "$3" "$4" ;;
    del)    cmd_del    "$2" "$3"      ;;
    list)   cmd_list                  ;;
    flush)  cmd_flush                 ;;
    status) cmd_status                ;;
    panel)  cmd_panel                 ;;
    *)      usage 2>/dev/null || true
            echo -e "${B}${C}fw-ops${N} — gerenciador de regras temporárias nftables\n"
            echo -e "  ${G}add${N}   <tcp|udp> <porta> [desc]   Abre porta"
            echo -e "  ${R}del${N}   <tcp|udp> <porta>           Fecha porta"
            echo -e "  ${C}list${N}                              Lista ativas"
            echo -e "  ${Y}flush${N}                             Remove todas"
            echo -e "  ${D}status${N}                            Ruleset completo"
            echo -e "  ${D}panel${N}                             Painel interativo\n"
            ;;
esac
