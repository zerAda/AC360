# =============================================================================
# onix-actions — image du microservice applicatif (audit / génération / etc.).
# Base slim ÉPINGLÉE. Installe les binaires d'OCR LOCAL : tesseract-ocr (moteur)
# + tesseract-ocr-fra (français) + poppler-utils (rendu PDF -> image pour pdf2image).
# Aucune dépendance cloud. Tourne en utilisateur non-root.
# =============================================================================
FROM python:3.11.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ONIX_ACTIONS_DB=/data/onix_actions.db \
    ONIX_JOBS_DIR=/data/jobs \
    ONIX_REFERENCE_DIR=/data/reference

# Binaires système pour l'OCR local + healthcheck (curl).
# `apt-get upgrade` applique les correctifs de sécurité Debian disponibles sur la
# base épinglée → élimine les CVE OS « fixables » (CRITICAL/HIGH) que le scan trivy
# bloque (la base figée accumule des CVE corrigées en amont mais non appliquées).
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-fra \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Données persistées (SQLite, jobs .docx, références montées) : volume.
RUN useradd --create-home --uid 10001 onix \
    && mkdir -p /data/jobs /data/reference \
    && chown -R onix:onix /data /app
USER onix

EXPOSE 8100

# Healthcheck interne (pas de port hôte) : interroge /health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8100/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
