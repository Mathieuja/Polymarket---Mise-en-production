# Setup local development environment

## Installation des dépendances

Pour développer et tester localement, installer les requirements :

```bash
# Installation du package partagé
pip install -e ./shared

# Installation du backend
pip install -r app/backend/requirements.txt

# Installation du frontend
pip install -r app/frontend/requirements.txt
```

## Exécuter les tests

```bash
# Tous les tests
python -m pytest

# Tests spécifiques
python -m pytest tests/unit -v

# Avec coverage
python -m pytest --cov=app tests/
```

## Linting

```bash
# Vérifier le linting
python -m ruff check .

# Auto-fix
python -m ruff check . --fix
```

## Docker

```bash
# Build et démarrer
docker-compose up -d

# Arrêter
docker-compose down
```
