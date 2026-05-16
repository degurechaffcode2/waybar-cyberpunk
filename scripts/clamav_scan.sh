#!/usr/bin/env bash
echo "╔══════════════════════════════════════╗"
echo "║        ClamAV — Scan do Home         ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "[*] Alvo: $HOME"
echo "[*] Iniciado: $(date '+%H:%M:%S %d/%m/%Y')"
echo "───────────────────────────────────────"
echo ""

clamscan --recursive --infected --bell "$HOME" 2>&1 | tee /tmp/clamav_scan.txt

echo ""
echo "───────────────────────────────────────"
echo "[*] Resultado salvo em: /tmp/clamav_scan.txt"
echo ""
read -rp "Pressione Enter para fechar..."
