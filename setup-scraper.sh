#!/usr/bin/env bash
set -euo pipefail

# FM Avlysning — Scraper setup för målmaskin
# Kör direkt:
#   curl -fsSL https://raw.githubusercontent.com/NicklasAndersson/avlysning/main/setup-scraper.sh | bash
# Eller lokalt:
#   bash setup-scraper.sh

IMAGE="ghcr.io/nicklasandersson/avlysning-scraper:latest"
ENV_FILE="$HOME/.fm-avlysning.env"
CRON_SCHEDULE="0 */6 * * *"
LOG_DIR="$HOME/.fm-avlysning-logs"

echo "=== FM Avlysning — Scraper Setup ==="
echo ""

# 1. Kontrollera Docker
if ! command -v docker &>/dev/null; then
    echo "FELMEDDELANDE: Docker saknas. Installera Docker först."
    exit 1
fi
echo "✓ Docker hittad: $(docker --version)"

# 2. Samla in S3-uppgifter
echo ""
echo "Ange Cloudflare R2-uppgifter (S3-kompatibelt API):"
echo "  Skapa API-token: Cloudflare Dashboard → R2 → Manage R2 API Tokens"
echo ""

if [[ -f "$ENV_FILE" ]]; then
    echo "Befintlig konfiguration hittad i $ENV_FILE"
    read -rp "Vill du skriva över den? (j/N) " overwrite
    if [[ "$overwrite" != "j" && "$overwrite" != "J" ]]; then
        echo "Behåller befintlig konfiguration."
    else
        rm -f "$ENV_FILE"
    fi
fi

if [[ ! -f "$ENV_FILE" ]]; then
    read -rp "S3_ENDPOINT_URL (https://<account-id>.r2.cloudflarestorage.com): " endpoint
    read -rp "S3_ACCESS_KEY_ID: " access_key
    read -rsp "S3_SECRET_ACCESS_KEY: " secret_key
    echo ""
    read -rp "S3_BUCKET_NAME [fm-avlysning]: " bucket
    bucket="${bucket:-fm-avlysning}"

    # Validera att inget är tomt
    if [[ -z "$endpoint" || -z "$access_key" || -z "$secret_key" ]]; then
        echo "FELMEDDELANDE: Alla fält måste fyllas i."
        exit 1
    fi

    cat > "$ENV_FILE" <<EOF
S3_ENDPOINT_URL=$endpoint
S3_ACCESS_KEY_ID=$access_key
S3_SECRET_ACCESS_KEY=$secret_key
S3_BUCKET_NAME=$bucket
EOF
    chmod 600 "$ENV_FILE"
    echo "✓ Konfiguration sparad i $ENV_FILE (chmod 600)"
fi

# 3. Skapa loggkatalog
mkdir -p "$LOG_DIR"
echo "✓ Loggkatalog: $LOG_DIR"

# 4. Dra ner senaste imagen
echo ""
echo "Laddar ner senaste scraper-image..."
docker pull "$IMAGE"
echo "✓ Image nedladdad: $IMAGE"

# 5. Testkör (dry run utan upload)
echo ""
echo "Testkör container (--help)..."
docker run --rm "$IMAGE" --help
echo "✓ Container fungerar"

# 6. Konfigurera cron
CRON_CMD="$CRON_SCHEDULE docker run --rm --env-file $ENV_FILE $IMAGE >> $LOG_DIR/scraper.log 2>&1"

# Kontrollera om cron redan finns
if crontab -l 2>/dev/null | grep -qF "avlysning-scraper"; then
    echo ""
    echo "Befintligt cron-jobb hittades:"
    crontab -l | grep "avlysning-scraper"
    read -rp "Vill du ersätta det? (j/N) " replace_cron
    if [[ "$replace_cron" == "j" || "$replace_cron" == "J" ]]; then
        crontab -l 2>/dev/null | grep -vF "avlysning-scraper" | crontab -
    else
        echo "Behåller befintligt cron-jobb."
        echo ""
        echo "=== Setup klar ==="
        exit 0
    fi
fi

# Lägg till cron
(crontab -l 2>/dev/null; echo "# FM Avlysning — scrapa var 6:e timme (avlysning-scraper)"; echo "$CRON_CMD") | crontab -
echo "✓ Cron-jobb installerat: $CRON_SCHEDULE"

# 7. Sammanfattning
echo ""
echo "=== Setup klar ==="
echo ""
echo "  Image:    $IMAGE"
echo "  Env-fil:  $ENV_FILE"
echo "  Loggar:   $LOG_DIR/scraper.log"
echo "  Schema:   Var 6:e timme ($CRON_SCHEDULE)"
echo ""
echo "Manuella kommandon:"
echo "  Kör nu:     docker run --rm --env-file $ENV_FILE $IMAGE"
echo "  Se loggar:  tail -f $LOG_DIR/scraper.log"
echo "  Uppdatera:  docker pull $IMAGE"
echo "  Ta bort:    crontab -l | grep -v avlysning-scraper | crontab -"
