# DataPipe — Backend API

**Hackathon J.U.I.N 2026 · Thème 9 · ETL Visuel pour Pipelines Bancaires**

API REST Flask complète pour concevoir, exécuter et monitorer des pipelines de transformation de données bancaires. Interface nodale (style n8n) permettant d'ingérer des fichiers CSV/JSON, d'exécuter des requêtes SQL, d'appliquer des transformations IA et d'exporter les résultats.

---

## Stack technique

| Composant | Technologie |
|---|---|
| Framework | Flask 3.0 |
| Base de données | SQLite (SQLAlchemy) |
| Authentification | JWT (Flask-JWT-Extended) |
| Hachage | bcrypt (Flask-Bcrypt) |
| CORS | Flask-CORS |
| Documentation | Swagger UI (flasgger) |
| Tests | pytest + pytest-flask + pytest-cov |

---

## Démarrage rapide

### Prérequis

- Python 3.10+

### Installation

```bash
git clone https://github.com/BalaAndegue/JUNE_HACKATON2026.git
cd JUNE_HACKATON2026/datapipe_backend

pip install -r requirements.txt
```

### Configuration (optionnel)

```bash
cp .env.example .env
# Éditer .env si besoin :
# OPENAI_API_KEY=sk-...   → active l'IA réelle sur /ai/*
# SECRET_KEY=...
# JWT_SECRET_KEY=...
```

### Lancer le serveur

```bash
python run.py
# → http://localhost:5000
```

### Swagger UI

```
http://localhost:5000/api/docs
```

Cliquer sur **Authorize**, saisir `Bearer <access_token>` pour tester tous les endpoints directement dans le navigateur.

Spec OpenAPI téléchargeable :
```
GET http://localhost:5000/api/v1/openapi.json
```

---

## Structure du projet

```
datapipe_backend/
├── app/
│   ├── __init__.py          # App factory Flask
│   ├── extensions.py        # db, jwt, bcrypt, blacklist tokens
│   ├── models.py            # 25 modèles SQLAlchemy + seed data
│   ├── utils.py             # Helpers (validate, paginate, slugify, audit)
│   ├── swagger_spec.py      # Spec OpenAPI 2.0 complète (138 paths)
│   └── routes/
│       ├── auth.py          # Auth & Sessions
│       ├── orgs.py          # Organisations & Workspaces
│       ├── pipelines.py     # Pipelines CRUD + versioning + templates
│       ├── nodes.py         # Nodes, Edges, Pin-data, Node-types
│       ├── runs.py          # Exécution + SSE logs
│       ├── files.py         # Upload fichiers + Datasources
│       ├── transform.py     # SQL transforms + mock data
│       ├── ai.py            # Intelligence artificielle
│       ├── results.py       # Résultats & Exports
│       ├── scheduling.py    # Scheduling cron
│       ├── webhooks.py      # Webhooks entrants/sortants
│       ├── notifications.py # Notifications & Alertes
│       ├── analytics.py     # Analytics & Audit
│       ├── api_keys.py      # API Keys & Intégrations
│       └── health.py        # Health, Ops, Marketplace
├── tests/
│   ├── conftest.py          # Fixtures partagées (app, client, auth)
│   ├── unit/
│   │   ├── test_models.py   # Tests unitaires des modèles
│   │   └── test_utils.py    # Tests unitaires des utilitaires
│   └── integration/
│       ├── test_auth.py
│       ├── test_orgs.py
│       ├── test_pipelines.py
│       ├── test_nodes.py
│       ├── test_runs.py
│       └── test_transform_ai_health.py
├── config.py
├── run.py
├── pytest.ini
└── requirements.txt
```

---

## Endpoints — Vue d'ensemble

**Base URL :** `http://localhost:5000/api/v1`

**Auth :** Toutes les routes (sauf `/health`, `/auth/login`, `/auth/register`) exigent :
```
Authorization: Bearer <access_token>
```

| # | Section | Endpoints | Description |
|---|---|---|---|
| 01 | **Auth** | 14 | Register, login, refresh, logout, verify-email, forgot/reset password, sessions |
| 02 | **Organisations** | 9 | CRUD orgs, membres, invitations, rôles |
| 03 | **Workspaces** | 5 | CRUD workspaces par org |
| 04 | **Pipelines** | 19 | CRUD, duplicate, archive, publish, versioning, templates, import/export, diff, merge |
| 05 | **Nodes & Edges** | 14 | CRUD nœuds, arêtes, pin-data, validation cycles, catalogue |
| 06 | **Exécution** | 9 | Trigger, cancel, retry, logs, SSE stream, output par nœud |
| 07 | **Fichiers** | 6 | Upload CSV/JSON, preview, analyze |
| 08 | **Datasources** | 10 | CRUD, test connexion, schéma, sync |
| 09 | **Transform SQL** | 9 | Validate, execute, history, fonctions, templates, mock data |
| 10 | **IA** | 13 | Generate-transform, suggest-pipeline, detect-anomalies, chat, classify, embed |
| 11 | **Résultats** | 10 | Résultats runs, exports CSV/JSON, download |
| 12 | **Scheduling** | 9 | Cron, pause/resume, trigger manuel |
| 13 | **Webhooks** | 9 | CRUD webhooks, test, inbound, events |
| 14 | **Notifications** | 10 | Notifications, alertes, mark-read |
| 15 | **Analytics** | 6 | Overview, stats pipeline, timeline, audit logs |
| 16 | **API Keys** | 8 | Clés API, intégrations (Slack, email, PagerDuty…) |
| 17 | **Health & Ops** | 7 | Health, ready, live, metrics, version, marketplace |

---

## Exemples d'utilisation

### 1. Créer un compte et se connecter

```bash
# Inscription
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"john@banque.ci","name":"John Kouassi","password":"Secure2026!","org_name":"Banque CI"}'

# Connexion
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"john@banque.ci","password":"Secure2026!"}'
# → {"access_token": "eyJ...", "refresh_token": "eyJ...", "expires_in": 900}
```

### 2. Créer un pipeline depuis un template

```bash
TOKEN="eyJ..."

# Lister les templates disponibles
curl http://localhost:5000/api/v1/pipelines/templates \
  -H "Authorization: Bearer $TOKEN"

# Instancier le template "Détection d'anomalies bancaires"
curl -X POST http://localhost:5000/api/v1/pipelines/templates/<template_id>/instantiate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"workspace_id":"ws_xxx","name":"Détection Fraudes Juin 2026"}'
```

### 3. Ajouter des nœuds et les connecter

```bash
PIPELINE_ID="pip_xxx"

# Créer un nœud CSV Reader
curl -X POST http://localhost:5000/api/v1/pipelines/$PIPELINE_ID/nodes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "csv_reader",
    "label": "Charger transactions",
    "position": {"x": 100, "y": 200},
    "config": {"delimiter": ",", "has_header": true}
  }'

# Créer un nœud AI Transform
curl -X POST http://localhost:5000/api/v1/pipelines/$PIPELINE_ID/nodes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "ai_transform",
    "label": "Détecter anomalies",
    "position": {"x": 400, "y": 200},
    "config": {"instruction": "Identifier les transactions dont le montant est anormalement élevé"}
  }'

# Connecter les nœuds
curl -X POST http://localhost:5000/api/v1/pipelines/$PIPELINE_ID/edges \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source": "nod_xxx", "target": "nod_yyy"}'
```

### 4. Exécuter le pipeline

```bash
curl -X POST http://localhost:5000/api/v1/pipelines/$PIPELINE_ID/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"trigger": "manual"}'

# Streamer les logs en temps réel (SSE)
curl http://localhost:5000/api/v1/runs/<run_id>/logs/stream \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Générer une requête SQL avec l'IA

```bash
curl -X POST http://localhost:5000/api/v1/ai/generate-transform \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Somme des transactions par mois et par type de paiement",
    "context": {"columns": ["id","montant","type","date_transaction","statut"]}
  }'
# → {"query": "SELECT STRFTIME('%Y-%m', date_transaction) as mois, type, SUM(montant)..."}
```

### 6. Détecter les anomalies dans un dataset

```bash
curl -X POST http://localhost:5000/api/v1/ai/detect-anomalies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"id":1,"montant":1500},{"id":2,"montant":1800},
      {"id":3,"montant":9999999}
    ],
    "amount_field": "montant"
  }'
# → {"anomalies": [{"row_index": 2, "z_score": 5.73, "severity": "high"}], ...}
```

---

## Types de nœuds disponibles

| Catégorie | Nœuds |
|---|---|
| **Input** | `csv_reader`, `json_reader`, `sql_query`, `http_request` |
| **Transform** | `filter`, `map`, `aggregate`, `join`, `sort`, `dedup`, `sql_transform`, `validate` |
| **AI** | `ai_transform` |
| **Output** | `sql_write`, `file_export`, `webhook_send`, `notification_send` |
| **Control** | `merge`, `split` |
| **Trigger** | `schedule_trigger` |

---

## Intelligence Artificielle

Les endpoints `/api/v1/ai/*` fonctionnent en deux modes :

- **Avec `OPENAI_API_KEY`** : appels réels à GPT-4o-mini (résultats optimaux)
- **Sans clé** : fallback contextuel bancaire intégré (fonctionnel sans configuration)

| Endpoint | Fonction |
|---|---|
| `POST /ai/generate-transform` | SQL depuis une description naturelle |
| `POST /ai/suggest-pipeline` | Suggère une structure de pipeline |
| `POST /ai/detect-anomalies` | Z-score sur les montants |
| `POST /ai/clean-data` | Nettoyage automatique |
| `POST /ai/generate-schema` | Inférence de schéma JSON |
| `POST /ai/chat` | Assistant DataPipe (contexte bancaire) |
| `POST /ai/classify` | Classification de lignes |
| `POST /ai/extract-entities` | Extraction montants, dates, noms |

---

## Données pré-chargées au démarrage

- **20 types de nœuds** bancaires avec leurs JSON Schema de configuration
- **4 templates de pipelines** :
  - CSV vers SQL
  - Détection d'anomalies bancaires
  - Rapprochement bancaire
  - ETL Agrégation mensuelle
- **8 nœuds marketplace** (Stripe Reader, CinetPay, Anomaly Detector, PostgreSQL Writer…)

---

## Tests

```bash
# Lancer tous les tests
pytest tests/

# Sans rapport de couverture (plus rapide)
pytest tests/ --no-cov

# Un seul fichier
pytest tests/integration/test_auth.py -v

# Avec rapport HTML (ouvre htmlcov/index.html)
pytest tests/ --cov=app --cov-report=html
```

**Résultats :** 218 tests · 100 % passent · ~5 secondes

| Suite | Tests |
|---|---|
| `unit/test_models.py` | 18 |
| `unit/test_utils.py` | 14 |
| `integration/test_auth.py` | 31 |
| `integration/test_orgs.py` | 20 |
| `integration/test_pipelines.py` | 28 |
| `integration/test_nodes.py` | 35 |
| `integration/test_runs.py` | 15 |
| `integration/test_transform_ai_health.py` | 57 |

---

## Modèles de données

```
User ──── Session
  │
  └── OrgMember ──── Org ──── Workspace ──── Pipeline ──── Node
                                                  │              └── Edge
                                                  ├── PipelineVersion
                                                  ├── Run ──── RunLog
                                                  ├── Schedule
                                                  ├── Webhook ──── WebhookEvent
                                                  └── Alert
```

---

## Contributeur

**Bala Andegue François Lionnel**
Hackathon J.U.I.N 2026 — Édition Cursor
