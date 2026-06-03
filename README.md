# DataPipe

**ETL visuel pour pipelines bancaires**  
Projet réalisé dans le cadre du **Hackathon J.U.I.N 2026 - Thème 9**.

DataPipe est une API backend Flask permettant de concevoir, exécuter et superviser des pipelines de transformation de données bancaires. La plateforme s'inspire des outils visuels de type n8n : elle permet d'assembler des noeuds, de connecter des sources de données, d'appliquer des transformations SQL ou IA, puis d'exporter les résultats.

## Objectifs

- Simplifier la création de pipelines ETL pour des cas d'usage bancaires.
- Centraliser l'ingestion, la transformation, l'exécution et le suivi des traitements.
- Fournir une API REST complète, documentée et testée.
- Intégrer des fonctionnalités d'intelligence artificielle pour assister l'analyse et la transformation des données.

## Fonctionnalités principales

- Authentification JWT avec gestion des sessions.
- Gestion des organisations, workspaces, membres et rôles.
- Création, versioning, publication, duplication et archivage de pipelines.
- Modélisation visuelle par noeuds et connexions.
- Exécution de pipelines avec logs et suivi en temps réel via SSE.
- Import de fichiers CSV/JSON et gestion des datasources.
- Transformations SQL, génération de requêtes et détection d'anomalies par IA.
- Exports de résultats en CSV/JSON.
- Scheduling, webhooks, notifications, alertes et analytics.
- Documentation Swagger UI intégrée.
- Suite de tests unitaires et d'intégration.

## Stack technique

- **Backend** : Flask 3
- **Base de données** : SQLite avec SQLAlchemy
- **Authentification** : Flask-JWT-Extended
- **Sécurité** : Flask-Bcrypt, gestion des tokens
- **API & CORS** : Flask-CORS, flasgger
- **Tests** : pytest, pytest-flask, pytest-cov
- **Déploiement** : Docker Compose, Gunicorn

## Prérequis

- Python 3.10 ou supérieur
- pip
- Docker et Docker Compose, optionnels pour l'exécution conteneurisée

## Installation locale

```bash
git clone https://github.com/Delmat237/DataPipe---ETL-Visuel-pour-Pipelines-Bancaires.git
cd DataPipe---ETL-Visuel-pour-Pipelines-Bancaires

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuration

Créer un fichier `.env` à la racine du projet :

```bash
cp .env.example .env
```

Variables utiles :

```env
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me
OPENAI_API_KEY=sk-...
```

`OPENAI_API_KEY` est optionnelle. Sans clé, les endpoints IA restent utilisables avec un fallback contextuel intégré.

## Lancement

### En local

```bash
python run.py
```

L'API est disponible sur :

```text
http://localhost:5000
```

### Avec Docker Compose

```bash
docker compose up --build
```

Le service expose l'API sur :

```text
http://localhost:5005
```

## Documentation API

Swagger UI :

```text
http://localhost:5000/api/docs
```

Spécification OpenAPI :

```text
GET http://localhost:5000/api/v1/openapi.json
```

Pour tester les endpoints protégés, utiliser l'en-tête suivant :

```http
Authorization: Bearer <access_token>
```

## Aperçu des modules API

- **Auth** : inscription, connexion, refresh token, logout, vérification email, mot de passe oublié.
- **Organisations & Workspaces** : gestion collaborative des espaces de travail.
- **Pipelines** : CRUD, templates, import/export, versioning et publication.
- **Nodes & Edges** : création des noeuds, connexions, validation des cycles et catalogue de types.
- **Runs** : exécution, annulation, relance, logs et streaming SSE.
- **Files & Datasources** : upload, preview, analyse et synchronisation.
- **Transform SQL** : validation, exécution, historique et templates.
- **IA** : génération SQL, suggestion de pipeline, détection d'anomalies, nettoyage et classification.
- **Results** : consultation et export des résultats.
- **Scheduling, Webhooks & Notifications** : automatisation, intégrations et alertes.
- **Analytics & API Keys** : statistiques, audit logs et intégrations externes.
- **Health & Ops** : health checks, métriques et informations de version.

## Structure du projet

```text
.
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models.py
│   ├── utils.py
│   ├── swagger_spec.py
│   └── routes/
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
├── config.py
├── run.py
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## Tests

Lancer toute la suite :

```bash
pytest tests/
```

Lancer les tests sans rapport de couverture :

```bash
pytest tests/ --no-cov
```

Générer un rapport HTML :

```bash
pytest tests/ --cov=app --cov-report=html
```

## Exemple rapide

Créer un compte :

```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@banque.ci",
    "name": "John Kouassi",
    "password": "Secure2026!",
    "org_name": "Banque CI"
  }'
```

Se connecter :

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@banque.ci",
    "password": "Secure2026!"
  }'
```

## Cas d'usage bancaires

- Détection d'anomalies dans des transactions.
- Rapprochement bancaire.
- Agrégation mensuelle des flux.
- Nettoyage et normalisation de fichiers CSV/JSON.
- Préparation de données pour reporting ou audit.
- Automatisation de traitements périodiques.

## Documentation complémentaire

- [Modélisation mathématique](docs/MODELISATION_MATHEMATIQUE.md)
- [État de l'art](docs/ETAT_DE_L_ART.md)

## Collaborateurs

- azangueleonel9@gmail.com
- saviojtsafackfotso@gmail.com
- balaandeguefrancoislionnel@gmail.com
- jeffbelekotan@gmail.com
- piodjiele@gmail.com

## Licence

Projet académique réalisé pour le Hackathon J.U.I.N 2026.
