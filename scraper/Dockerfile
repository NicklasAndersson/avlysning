FROM python:3.11-slim

WORKDIR /app

# Installera beroenden först (cachas om requirements.txt inte ändrats)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiera scraper-källkod
COPY main.py upload.py ./
COPY scrapers/ scrapers/

# Skapa datakatalog för output
RUN mkdir -p /app/data

ENTRYPOINT ["python", "main.py", "--source", "all", "--no-cache", "--output", "/app/data/skjutfalt_status.json", "--upload"]
