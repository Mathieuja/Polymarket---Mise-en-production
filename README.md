# Polymarket — Mise en production (ENSAE)

[![CI](https://github.com/Mathieuja/Polymarket---Mise-en-production/actions/workflows/ci.yml/badge.svg)](https://github.com/Mathieuja/Polymarket---Mise-en-production/actions/workflows/ci.yml)

Objectif: construire une webapp interactive (Streamlit) autour de données Polymarket, en respectant les bonnes pratiques de reproductibilité et de mise en production vues en cours.

Statut: l'app Streamlit est développée d'abord en **mode mock** (sans backend), puis basculera vers une API (FastAPI) une fois le contrat stabilisé.

## Lancer l'app (local, mode mock)

Pré-requis: Python 3.10+

1) Créer un environnement

```bash
python -m venv .venv
```

2) Activer l'environnement

- Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

3) Installer les dépendances

Frontend:

```bash
pip install -r app/frontend/requirements.txt
```

Backend API:

```bash
pip install -r app/backend/requirements.txt
```

4) Configurer les variables d'environnement

Copier `.env.example` en `.env` et ajuster si besoin.

Variables utilisées par l'app:
- `BACKEND_MODE`: `mock` (par défaut) ou `api`
- `API_URL`: base URL de l'API quand `BACKEND_MODE=api` (ex: `http://localhost:8000`)

Variables backend (MVP login en mode API):
- `JWT_SECRET`: secret pour signer les JWT (dev uniquement)
- `DEMO_EMAIL` / `DEMO_PASSWORD`: identifiants du compte démo

5) Démarrer Streamlit

```bash
streamlit run app/frontend/main.py
```

## Démarrer l'API (local)

Quand `BACKEND_MODE=api`, Streamlit appelle l'API (dont `POST /auth/login`).

```bash
uvicorn app.backend.api.main:app --reload --port 8000
```

## Structure

- `app/frontend/`: frontend Streamlit (pages, client API, fixtures mock)
- `app/backend/`: backend FastAPI (API routes, schemas, config)
- `tests/unit/`: tests unitaires (dont tests composants)
- `tests/integration/`: tests d'integration
- `ds/`: (à venir) pipeline data science / ingestion

## Docker

Docker/Compose est volontairement **différé** au début: on stabilise d'abord l'UI, le mode mock, et la qualité (lint/tests/CI).

## Contrat d'API (préparation)

Le backend (FastAPI) n'est pas implémenté ici pour l'instant, mais le contrat est défini dans:
- [docs/api/openapi.yaml](docs/api/openapi.yaml)