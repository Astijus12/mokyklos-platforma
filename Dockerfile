# Multi-stage build - mažesnis galutinis image
# Python 3.13 – ta pati versija kaip kūrimo aplinkoje ir Render (.python-version)
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================
FROM python:3.13-slim

WORKDIR /app

# fonts-dejavu-core – šriftas su lietuviškomis raidėmis PDF dokumentams (ReportLab)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r flask && useradd -r -g flask flask

COPY --from=builder /root/.local /home/flask/.local

COPY --chown=flask:flask . .

# Katalogai, į kuriuos prijungiami tomai (volumes), sukuriami iš anksto: tada nauji tomai
# perima naudotojo flask teises ir programa gali įrašyti PDF dokumentus bei laiškus
RUN mkdir -p /app/static/uploads /app/duomenys/dokumentai /app/duomenys/laiskai \
    && chown -R flask:flask /app

USER flask

ENV PATH=/home/flask/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP="app:create_app()"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# --preload: wsgi.py (migracijos ir demo duomenys) įvykdomas vieną kartą
# pagrindiniame procese, prieš sukuriant 2 darbinius procesus.
# Fono procesas (worker) naudoja tą patį atvaizdą su komanda „python worker.py“.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--preload", "wsgi:app"]
