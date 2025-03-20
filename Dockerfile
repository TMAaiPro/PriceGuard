FROM python:3.10-slim as builder

WORKDIR /app

# Installer les dépendances de build
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Image finale
FROM python:3.10-slim

# Informations sur l'image
LABEL maintainer="PriceGuard Team <info@priceguard.io>"
LABEL version="1.0"
LABEL description="PriceGuard Scraper Service"

# Installer les dépendances système nécessaires
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    wget \
    gnupg \
    # Dépendances pour Puppeteer
    chromium \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    # Nettoyage
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd -m scraper

# Créer les répertoires nécessaires
WORKDIR /app
RUN mkdir -p /app/media/screenshots && chown -R scraper:scraper /app

# Copier les wheels et installer les dépendances
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copier le code source
COPY . .

# Configurer les variables d'environnement pour Puppeteer
ENV PYPPETEER_CHROMIUM_REVISION=1095492
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Script d'entrée
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Changer l'utilisateur
USER scraper

# Exposer le port de l'application
EXPOSE 8000

# Point d'entrée
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Commande par défaut (peut être remplacée)
CMD ["web"]
