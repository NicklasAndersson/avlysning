#!/usr/bin/env bash
set -euo pipefail

# FM Avlysning — Efemär scraper-körning
#
# Skapar en Hetzner-server, kör scrapern med R2-upload, raderar servern.
# Kräver: hcloud CLI, lokal .env-fil med R2-uppgifter
#
# Användning:
#   bash run-scraper.sh                          # Använder ~/.fm-avlysning.env
#   bash run-scraper.sh /path/to/.env            # Använder angiven env-fil

ENV_FILE="${1:-$HOME/.fm-avlysning.env}"
SERVER_NAME="fm-scraper-$(date +%s)"
SERVER_TYPE="ccx13"
IMAGE="ubuntu-24.04"
LOCATION="fsn1"
SSH_KEY="nicklas.andersson@leanon.se"
DOCKER_IMAGE="ghcr.io/nicklasandersson/avlysning-scraper:latest"
SSH_OPTS="-o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"

# Kontrollera env-fil
if [[ ! -f "$ENV_FILE" ]]; then
    echo "Saknar env-fil: $ENV_FILE"
    echo "Skapa den med:"
    echo "  S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com"
    echo "  S3_ACCESS_KEY_ID=..."
    echo "  S3_SECRET_ACCESS_KEY=..."
    echo "  S3_BUCKET_NAME=fm-avlysning"
    exit 1
fi

# Cleanup-funktion — raderar servern oavsett hur scriptet avslutas
cleanup() {
    echo ""
    echo "Raderar server $SERVER_NAME..."
    hcloud server delete "$SERVER_NAME" 2>/dev/null && echo "Server raderad." || echo "Kunde inte radera server (kanske redan borta)."
}
trap cleanup EXIT

echo "=== FM Avlysning — Efemär scraper-körning ==="
echo ""
echo "  Server:  $SERVER_TYPE @ $LOCATION"
echo "  Image:   $DOCKER_IMAGE"
echo "  Env:     $ENV_FILE"
echo ""

# Skapa server med Docker förinstallerat
CLOUD_INIT=$(cat <<'YAML'
#cloud-config
package_update: true
packages:
  - docker.io
runcmd:
  - systemctl enable --now docker
YAML
)

echo "1/5 Skapar server..."
CLOUD_INIT_FILE=$(mktemp)
echo "$CLOUD_INIT" > "$CLOUD_INIT_FILE"
hcloud server create \
    --name "$SERVER_NAME" \
    --type "$SERVER_TYPE" \
    --image "$IMAGE" \
    --location "$LOCATION" \
    --ssh-key "$SSH_KEY" \
    --user-data-from-file "$CLOUD_INIT_FILE" \
    > /dev/null
rm -f "$CLOUD_INIT_FILE"

IP=$(hcloud server ip "$SERVER_NAME")
echo "   Server: $IP"

# Vänta på SSH
echo "2/5 Väntar på SSH..."
for i in {1..30}; do
    if ssh $SSH_OPTS root@"$IP" true 2>/dev/null; then
        break
    fi
    sleep 5
done

# Vänta på cloud-init (Docker)
echo "3/5 Väntar på Docker-installation..."
ssh $SSH_OPTS root@"$IP" "cloud-init status --wait" 2>/dev/null || true

# Kopiera env-fil till servern
echo "4/5 Konfigurerar..."
scp $SSH_OPTS "$ENV_FILE" root@"$IP":/tmp/.env > /dev/null

# Kör scrapern
echo "5/5 Kör scraper..."
echo ""
ssh $SSH_OPTS root@"$IP" "docker pull $DOCKER_IMAGE" 2>/dev/null | tail -1
echo ""
ssh $SSH_OPTS root@"$IP" "docker run --rm --env-file /tmp/.env $DOCKER_IMAGE"
EXIT_CODE=$?

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "=== Scraping klar ==="
else
    echo "=== Scraping misslyckades (exit $EXIT_CODE) ==="
fi

# cleanup körs automatiskt via trap
