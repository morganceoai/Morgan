#!/bin/bash
# Sincroniza .env do MacBook para o Mac Mini
set -e

MAC_MINI="bcvertex@100.100.15.110"
REMOTE_PATH="~/Morgan/.env"

echo "A sincronizar .env para o Mac Mini..."
scp .env "$MAC_MINI:$REMOTE_PATH"
echo "Feito."

echo "A reiniciar o servidor Morgan no Mac Mini..."
ssh "$MAC_MINI" "pkill -f desktop_server.py || true; cd ~/Morgan && source venv/bin/activate && nohup python desktop_server.py > morgan_server.log 2>&1 &"
echo "Servidor reiniciado."
