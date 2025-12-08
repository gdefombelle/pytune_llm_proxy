# ===============================
# Étape 1 : Build avec UV (workspace complet)
# ===============================
FROM --platform=linux/amd64 python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app

# Copier workspace root
COPY pyproject.toml uv.lock ./

# Copier tous les packages + services
COPY src ./src

# Installer toutes les dépendances dans /app/.venv
RUN uv sync --no-dev


# ===============================
# Étape 2 : Image finale
# ===============================
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ❗ IMPORTANT : on se place dans le dossier contenant app/main.py
WORKDIR /app/src/services/pytune_llm_proxy

# Copier tout le workspace + la venv
COPY --from=builder /app /app

EXPOSE 8007

# Lancement via la venv root
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]