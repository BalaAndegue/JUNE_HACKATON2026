# Rapport d'Intégration du Module IA — DataPipe (Hackathon 2026)

Ce rapport présente l'architecture, les fonctionnalités implémentées, la documentation des endpoints et les résultats des tests d'intégration pour le module d'Intelligence Artificielle de **DataPipe**, migré avec succès dans le backend Flask central.

---

## 1. Objectifs & Architecture

L'objectif principal du module IA est de fournir des capacités intelligentes d'assistance à la création de requêtes SQL (ETL) et de pipelines de données (visualisables sous React Flow), tout en garantissant une haute résilience (fallback) pour les démonstrations du Hackathon.

L'architecture repose sur un mécanisme à trois niveaux de priorité (Multi-Provider & Fallback) :
1. **Anthropic Claude (Prioritaire)** : Appels directs à Claude 3.5 Haiku pour une précision maximale dans l'interprétation des intentions utilisateur.
2. **OpenAI GPT (Fallback 1)** : Bascule vers `gpt-4o-mini` si Claude n'est pas disponible ou si la clé Anthropic est absente.
3. **Mock Intelligent NLP (Fallback 2)** : Moteur d'analyse sémantique local (regex + détection de mots-clés) qui génère des structures cohérentes sans appel API externe (idéal en mode hors-ligne ou démo sans crédits).

---

## 2. Configuration & Clés API

Les variables d'environnement suivantes ont été configurées et intégrées au système de configuration de Bala :

- **`config.py`** :
  - `ANTHROPIC_API_KEY` : Clé API Anthropic (récupérée de `.env`).
  - `CLAUDE_MODEL` : Modèle utilisé (par défaut `claude-3-5-haiku-20241022`).
- **`.env.example`** : Ajout des variables d'exemple correspondantes.

---

## 3. Endpoints Implémentés / Mis à Jour

### 3.1. `POST /api/v1/ai/generate-pipeline` [NOUVEAU]
Génère une structure de pipeline complète directement compatible avec **React Flow** à partir d'une description textuelle.

* **Requête** :
  ```json
  {
    "prompt": "Importer les transactions bancaires depuis un CSV, filtrer celles supérieures à 50000, et exporter au format CSV."
  }
  ```

* **Réponse (Format React Flow)** :
  ```json
  {
    "nodes": [
      {
        "id": "node_0",
        "type": "csvImport",
        "data": { "label": "Import CSV" },
        "position": { "x": 100, "y": 150 }
      },
      {
        "id": "node_1",
        "type": "filter",
        "data": { "label": "Filtrage des données" },
        "position": { "x": 380, "y": 150 }
      },
      {
        "id": "node_2",
        "type": "csvExport",
        "data": { "label": "Export CSV" },
        "position": { "x": 660, "y": 150 }
      }
    ],
    "edges": [
      {
        "id": "edge_0_to_1",
        "source": "node_0",
        "target": "node_1",
        "sourceHandle": "output",
        "targetHandle": "input"
      },
      {
        "id": "edge_1_to_2",
        "source": "node_1",
        "target": "node_2",
        "sourceHandle": "output",
        "targetHandle": "input"
      }
    ],
    "explanation": "Pipeline généré (3 nœuds) : import CSV → filtrage des données → export CSV. Cliquez sur 'Exécuter' pour lancer le pipeline."
  }
  ```

### 3.2. `POST /api/v1/ai/suggest-pipeline` [MIS À JOUR]
Suggère une liste logique de nœuds conceptuels sous forme de JSON structuré pour guider l'utilisateur.
* Intègre la priorité Claude + fallback OpenAI et mock NLP.

### 3.3. `POST /api/v1/ai/generate-transform` [MIS À JOUR]
Génère une requête SQL d'agrégation, de filtrage ou de jointure à partir de descriptions en langage naturel et du schéma des colonnes fourni.
* Intègre le fallback intelligent vers des templates SQL si aucune clé API n'est active.

### 3.4. `POST /api/v1/ai/chat` [MIS À JOUR]
Assistant conversationnel DataPipe pour répondre aux questions ETL des utilisateurs en français.
* Utilise l'historique de session (mémoire des 10 derniers messages) avec Claude ou OpenAI.

---

## 4. Intégration Swagger & Documentation

L'endpoint `/ai/generate-pipeline` a été officiellement déclaré dans le fichier de spécification OpenAPI de l'application (`app/swagger_spec.py`) pour permettre son test immédiat dans l'interface interactive Swagger UI du backend.

---

## 5. Tests et Validation

Des tests d'intégration robustes ont été ajoutés dans `tests/integration/test_transform_ai_health.py` pour valider :
- La génération correcte du graphe React Flow (`nodes` contenant des positions géométriques valides, `edges` reliant les nœuds).
- La gestion des erreurs et de la validation des requêtes (ex: prompt ou description manquants -> renvoi d'une erreur 400).

### Résultat de la suite de tests (`pytest`) :
```bash
====================== 267 passed, 187 warnings in 13.43s ======================
```
Les 267 tests du projet (incluant l'authentification, les workspaces, les runs, le module IA, le **moteur d'exécution ETL réel** et la **suite Fichiers/Datasources**) passent à **100% avec succès**.

> Couverture renforcée : `app/routes/files.py` est passé de **40 % à 92 %** grâce à la
> nouvelle suite `tests/integration/test_files.py` (upload CSV/JSON, preview, analyze,
> suppression, CRUD datasources) — le chemin d'upload, critique pour la démo, est
> désormais largement sécurisé.

---

## 6. Moteur d'Exécution ETL Réel [NOUVEAU]

Le module IA génère des graphes de pipeline (`nodes` + `edges`). Pour que ces
pipelines produisent de **vrais résultats** — et non plus des données simulées —, un
moteur d'exécution ETL a été ajouté dans **`app/engine.py`**. C'est ce qui répond
concrètement au problème du thème 9 : consolider et transformer réellement des
fichiers de données.

### 6.1. Principe
- **Tri topologique** du graphe (DAG) avec détection de cycle (`CycleError`).
- Exécution nœud par nœud : chaque nœud reçoit les sorties de ses parents et produit
  un dataset réel (liste de lignes) transmis à ses enfants.
- Coercition automatique des valeurs CSV en nombres pour que les filtres numériques
  et les agrégations fonctionnent.

### 6.2. Nœuds réellement exécutés
| Catégorie | Nœuds | Statut |
|---|---|---|
| Input | `csv_reader`, `json_reader` | ✅ lecture fichier disque |
| Transform | `filter`, `map`, `aggregate`, `join`, `sort`, `dedup`, `sql_transform`, `validate` | ✅ |
| Control | `merge`, `split` | ✅ |
| AI | `ai_transform` | ✅ génère du SQL (IA) puis l'exécute sur l'entrée |
| Input externe | `sql_query`, `http_request` | ⚠️ datasource/réseau non branché |
| Output | `file_export`, `sql_write`, `webhook_send`, `notification_send` | ⚠️ passe-through journalisé |

`sql_transform` / `sql_query` exécutent du vrai SQL via **SQLite en mémoire** sur la
table `{input}` (mots-clés destructeurs bloqués).

### 6.2 bis. Nœud IA branché sur la génération SQL (bonus démo +3 pts)

Le nœud `ai_transform` n'est plus un simple passe-through. Lors de l'exécution :
1. Il récupère l'instruction en langage naturel (`config.instruction`) et les colonnes
   du dataset d'entrée.
2. Il appelle la fonction `generate_sql()` (factorisée depuis `/ai/generate-transform`,
   même chaîne OpenRouter → Claude → OpenAI → mock).
3. La requête SQL générée est **exécutée réellement** sur les données via SQLite.

Le générateur est injecté dans le moteur (`execute_pipeline(..., sql_generator=...)`),
ce qui garde `engine.py` découplé de Flask/IA et testable hors-ligne. Si l'IA est
indisponible, le nœud se rabat proprement sur un passe-through (le run ne plante jamais).

### 6.3. Persistance des résultats
- L'ancien `_simulate_run` (qui fabriquait `100 + i*37` lignes fictives) est remplacé
  par `_execute_run`, qui lance le moteur, persiste les logs par nœud et les
  `node_results`.
- Le **dataset complet** du nœud terminal est écrit sur disque
  (`uploads/results/<run_id>.json`) afin que `GET /results/<run_id>/download` renvoie
  **toutes** les lignes (et non l'aperçu limité à 10).
- Les endpoints `POST /transform/sql/execute` et `POST /transform/preview` exécutent
  désormais réellement le SQL sur les données fournies.

### 6.4. Validation
- `tests/unit/test_engine.py` : tests unitaires des transformations (filter,
  aggregate, join, sort, dedup, SQL, merge, détection de cycle).
- `tests/integration/test_runs.py` : test bout-en-bout
  (upload CSV → filter → aggregate → export complet).

Voir le détail complet du parcours dans **`docs/WORKFLOW.md`**.

---

## 7. Prochaines Étapes pour la Démo Hackathon

1. **Configuration Staging/Prod** : Renseigner les variables `ANTHROPIC_API_KEY` dans le fichier `.env` sur le serveur de démonstration si les appels réels à Claude sont requis.
2. **Interface Graphique** : L'équipe Frontend (Jeff) peut consommer directement `POST /api/v1/ai/generate-pipeline` et passer le tableau `nodes` et `edges` directement à l'état React Flow pour un affichage immédiat à l'écran.
3. **Démo complète** : enchaîner IA → graphe React Flow → `POST /pipelines/<id>/run` (moteur ETL réel) → `GET /results/<run_id>/download` pour montrer le cycle complet « prompt en français → résultat téléchargeable ».
