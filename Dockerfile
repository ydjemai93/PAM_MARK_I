FROM python:3.9-slim

WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copier seulement requirements.txt d'abord (meilleure utilisation du cache Docker)
COPY requirements.txt .

# Mettre à jour pip et installer les dépendances
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

# Exposer le port pour l'application
EXPOSE 8000

# Commande pour démarrer l'application
CMD ["python", "agent.py", "dev"]
