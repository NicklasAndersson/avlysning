#!/usr/bin/env bash
set -euo pipefail

# Skapar en Hetzner-server med Docker förinstallerat via cloud-init,
# sedan körs setup-scraper.sh för att konfigurera cron + R2-upload.
#
# Kräver: hcloud CLI med aktiv kontext och SSH-nyckel

SERVER_NAME="fm-scraper"
SERVER_TYPE="ccx13"
IMAGE="ubuntu-24.04"
LOCATION="fsn1"
SSH_KEY="nicklas.andersson@leanon.se"

CLOUD_INIT=$(cat <<'EOF'
#cloud-config
package_update: true
packages:
  - docker.io
runcmd:
  - systemctl enable --now docker
EOF
)

echo "=== FM Avlysning — Skapa Hetzner-server ==="
echo ""
echo "  Namn:     $SERVER_NAME"
echo "  Typ:      $SERVER_TYPE"
echo "  Image:    $IMAGE"
echo "  Plats:    $LOCATION"
echo "  SSH-key:  $SSH_KEY"
echo ""

# Kolla om servern redan finns
if hcloud server describe "$SERVER_NAME" &>/dev/null; then
    echo "Server '$SERVER_NAME' finns redan:"
    hcloud server describe "$SERVER_NAME" -o format='  IP: {{.PublicNet.IPv4.IP}}'
    read -rp "Ta bort och skapa ny? (j/N) " recreate
    if [[ "$recreate" == "j" || "$recreate" == "J" ]]; then
        hcloud server delete "$SERVER_NAME"
        echo "Borttagen."
    else
        IP=$(hcloud server ip "$SERVER_NAME")
        echo ""
        echo "Anslut: ssh root@$IP"
        exit 0
    fi
fi

# Skapa server
echo "Skapar server..."
CLOUD_INIT_FILE=$(mktemp)
echo "$CLOUD_INIT" > "$CLOUD_INIT_FILE"
hcloud server create \
    --name "$SERVER_NAME" \
    --type "$SERVER_TYPE" \
    --image "$IMAGE" \
    --location "$LOCATION" \
    --ssh-key "$SSH_KEY" \
    --user-data-from-file "$CLOUD_INIT_FILE"
rm -f "$CLOUD_INIT_FILE"

IP=$(hcloud server ip "$SERVER_NAME")
echo ""
echo "Server skapad: $IP"

# Rensa gammal host key (Hetzner återanvänder IP:n)
ssh-keygen -R "$IP" 2>/dev/null || true

SSH_OPTS="-o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new"

# Vänta på SSH
echo "Väntar på SSH..."
for i in {1..30}; do
    if ssh $SSH_OPTS root@"$IP" true 2>/dev/null; then
        break
    fi
    sleep 5
done

# Vänta på cloud-init
echo "Väntar på cloud-init (Docker-installation)..."
ssh $SSH_OPTS root@"$IP" "cloud-init status --wait" 2>/dev/null || true

# Kör setup-scriptet
echo ""
echo "Kör setup-scraper.sh på servern..."
ssh $SSH_OPTS root@"$IP" 'curl -fsSL https://raw.githubusercontent.com/NicklasAndersson/avlysning/main/setup-scraper.sh -o /tmp/setup-scraper.sh && chmod +x /tmp/setup-scraper.sh'
ssh $SSH_OPTS -t root@"$IP" 'bash /tmp/setup-scraper.sh'

echo ""
echo "=== Klart ==="
echo "  Server:  $SERVER_NAME ($IP)"
echo "  Anslut:  ssh root@$IP"
echo "  Loggar:  ssh root@$IP tail -f ~/.fm-avlysning-logs/scraper.log"
