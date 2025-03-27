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

# Mettre à jour pip
RUN pip install --upgrade pip setuptools wheel

# Copier le fichier requirements
COPY requirements.txt .

# Installer les dépendances une par une pour identifier le problème
RUN pip install --no-cache-dir python-dotenv && \
    pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir pydantic==1.10.8 && \
    pip install --no-cache-dir websockets==10.4 && \
    pip install --no-cache-dir httpx==0.24.1 && \
    pip install --no-cache-dir protobuf==4.23.4 && \
    pip install --no-cache-dir aiohttp==3.8.5 && \
    pip install --no-cache-dir python-jose==3.3.0
    echo "Dépendances de base installées avec succès"

# Installer les plugins LiveKit séparément
RUN pip install --no-cache-dir livekit-agents==1.0.0 || echo "Erreur avec livekit-agents"
RUN pip install --no-cache-dir livekit-plugins-openai==0.3.0 || echo "Erreur avec livekit-plugins-openai"
RUN pip install --no-cache-dir livekit-plugins-deepgram==0.1.0 || echo "Erreur avec livekit-plugins-deepgram"
RUN pip install --no-cache-dir git+https://github.com/livekit/livekit-plugins-silero.git || echo "Erreur avec livekit-plugins-silero"

# Assurez-vous que cette ligne est présente dans votre Dockerfile après l'installation des autres dépendances
RUN pip install --no-cache-dir uvicorn==0.23.2 fastapi==0.103.1
# Copier le reste du code
COPY . .

# Exposer le port pour l'application
EXPOSE 8000


# Commande pour démarrer l'application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
