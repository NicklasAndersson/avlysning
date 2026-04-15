# FM Avlysning

Visar aktiva avlysningar för svenska skjut- och övningsfält på en interaktiv karta.

> **OBS:** Detta är INTE en officiell tjänst från Försvarsmakten. Fysisk skyltning vid fältet gäller alltid.

## Scraper — Setup på server

Kör på målmaskinen (kräver Docker):

```bash
curl -fsSL https://raw.githubusercontent.com/NicklasAndersson/avlysning/main/setup-scraper.sh | bash
```

Scriptet frågar efter Cloudflare R2-uppgifter, drar ner Docker-imagen och installerar ett cron-jobb (var 6:e timme).

### Manuella kommandon

```bash
# Kör scraper nu
docker run --rm --env-file ~/.fm-avlysning.env ghcr.io/nicklasandersson/avlysning-scraper:latest

# Uppdatera image
docker pull ghcr.io/nicklasandersson/avlysning-scraper:latest

# Se loggar
tail -f ~/.fm-avlysning-logs/scraper.log

# Ta bort cron-jobb
crontab -l | grep -v avlysning-scraper | crontab -
```

## Utveckling

```bash
# Frontend
cd frontend && npm install && npm run dev

# Scraper (lokalt)
cd scraper && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py --source all
```
