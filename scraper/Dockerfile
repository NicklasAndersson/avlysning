FROM python:3.11-slim

WORKDIR /app

# Installera beroenden först (cachas om requirements.txt inte ändrats)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiera scraper-källkod
COPY main.py upload.py ./
COPY scrapers/ scrapers/

# Kopiera konfiguration till /data/ (fm.py resolves Path(__file__).parent.parent.parent / "data")
RUN mkdir -p /data
COPY field_config.json /data/field_config.json

ENTRYPOINT ["python", "main.py"]
CMD ["--source", "all", "--no-cache", "--output", "/app/data/skjutfalt_status.json", "--upload"]
