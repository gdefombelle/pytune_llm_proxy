# Étape 1 : Utiliser une image Python optimisée
FROM python:3.12.3-slim

# Étape 2 : Définir le dossier de travail
WORKDIR /app

# Étape 3 : Installer les dépendances système requises (PostgreSQL, bcrypt, etc.)
RUN apt-get update && apt-get install -y libpq-dev gcc

# Étape 4 : Installer Poetry
RUN pip install --no-cache-dir poetry

# Étape 5 : Copier uniquement les fichiers nécessaires pour la gestion des dépendances
COPY pyproject.toml poetry.lock README.md ./

# Étape 6 : Installer les dépendances avec Poetry
RUN poetry install --without dev --no-root

# Étape 7 : Copier le code source
COPY . .

# Étape 8 : Exposer le port utilisé par FastAPI
EXPOSE 8007

# Étape 9 : Lancer Uvicorn
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]
