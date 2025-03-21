# AI Phone Agent API

API pour la gestion des agents téléphoniques IA.

## Configuration de développement

### Prérequis

- Python 3.9+
- PostgreSQL
- Compte LiveKit
- Compte Supabase
- Clés API pour OpenAI, Deepgram et Cartesia

### Installation

1. Cloner le dépôt
```bash
git clone https://github.com/votre-username/ai-phone-agent.git
cd ai-phone-agent
```

2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. Installer les dépendances
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement
```bash
cp .env.example .env
# Éditer .env avec vos propres valeurs
```

5. Lancer les migrations de base de données
```bash
alembic upgrade head
```

6. Démarrer le serveur de développement
```bash
uvicorn app.main:app --reload
```

## Déploiement

Ce projet est configuré pour être déployé sur Railway.

## Documentation API

La documentation API est disponible à l'adresse `/docs` lorsque le serveur est en cours d'exécution.
