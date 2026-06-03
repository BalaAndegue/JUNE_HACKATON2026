# DataPipe — Workflow complet

**Thème 9 · ETL Visuel pour Pipelines Bancaires · Hackathon J.U.I.N 2026**

Ce document décrit le parcours de bout en bout, de l'inscription jusqu'au résultat
exporté, en suivant le cas d'usage du guide : *le contrôleur de gestion qui consolide
ses fichiers CSV d'agences sans écrire une ligne de code*.

> Toutes les routes sont sous `http://localhost:5000/api/v1`.
> Sauf `/auth/*` et `/health`, chaque requête exige l'en-tête :
> `Authorization: Bearer <access_token>`.

---

## Vue d'ensemble — les 5 étapes

```
1. AUTH          2. STRUCTURE        3. CONSTRUCTION       4. EXÉCUTION         5. RÉSULTATS
   register   →    org/workspace  →    pipeline + nodes  →   run (moteur ETL) →   download CSV/JSON
   login           upload fichier      + edges (graphe)       node_results         exports
```

---

## Étape 1 — Authentification (`app/routes/auth.py`)

```
POST /auth/register   {email, name, password, org_name}
   └─→ crée User + Org + Workspace + OrgMember(owner)   [tout en un seul appel]

POST /auth/login      {email, password}
   └─→ {access_token (15 min), refresh_token (30 j), expires_in}
```

L'inscription **amorce déjà toute la hiérarchie** : l'utilisateur repart avec une
organisation et un workspace prêts à l'emploi. Le token JWT est ensuite porté par
toutes les requêtes suivantes.

Endpoints connexes : `POST /auth/refresh-token`, `POST /auth/logout`,
`GET /auth/me`, `GET /auth/sessions`.

---

## Étape 2 — Structure & données sources

### Hiérarchie des ressources (`app/models.py`)

```
User ── OrgMember ── Org ── Workspace ── Pipeline ── Node / Edge / Run
```

### Upload du fichier réel (`app/routes/files.py`)

C'est l'entrée concrète des données dans le système :

```
POST /files/upload   (multipart: workspace_id + file=transactions.csv)
   └─→ parse le CSV/JSON
       stocke le fichier sur disque (uploads/<workspace_id>/)
       calcule rows_count, columns, preview[5]
       renvoie {id: "fil_xxx"}
```

Le `file_id` renvoyé est la clé qui relie le fichier physique au nœud lecteur du
pipeline.

Endpoints connexes : `GET /files`, `GET /files/<id>/preview`,
`POST /files/<id>/analyze`, et les **datasources** (`POST /datasources`, etc.).

---

## Étape 3 — Construction du pipeline (le graphe nodal)

### 3a. Créer le pipeline (`app/routes/pipelines.py`)

Vide, ou instancié depuis un template :

```
POST /pipelines                              {name, workspace_id}
POST /pipelines/templates/<id>/instantiate   {workspace_id, name}   ← 4 templates pré-chargés
```

### 3b. Ajouter les nœuds (`app/routes/nodes.py`)

Chaque nœud a un `type`, un `config`, une `position` :

```
POST /pipelines/<pid>/nodes
   {type:"csv_reader", config:{file_id:"fil_xxx"}}                          ← source
   {type:"filter",     config:{conditions:[{field:"montant",operator:"gt",value:50000}]}}
   {type:"aggregate",  config:{group_by:["region"],
                               aggregations:[{field:"montant",function:"sum",alias:"total"}]}}
```

### 3c. Connecter les nœuds avec des arêtes

C'est ce qui définit le **sens du flux** des données :

```
POST /pipelines/<pid>/edges          {source:"nod_reader", target:"nod_filter"}
POST /pipelines/<pid>/edges          {source:"nod_filter", target:"nod_aggregate"}
POST /pipelines/<pid>/edges/validate ← détecte les cycles avant l'exécution
```

Le pipeline est maintenant un **DAG** (graphe orienté acyclique) :
`csv_reader → filter → aggregate`.

---

## Étape 4 — Exécution (le moteur ETL réel)

```
POST /pipelines/<pid>/run   {trigger:"manual"}
```

Ce qui se passe dans `app/routes/runs.py:_execute_run` + `app/engine.py` :

```
1. run.status = "running"                         (Run créé, persisté en base)
2. Charge les nodes + edges du pipeline
3. engine.execute_pipeline(nodes, edges, file_loader):
   ├─ _toposort()  → ordonne les nœuds, lève CycleError si cycle
   └─ pour chaque nœud dans l'ordre topologique :
        inputs = sorties des nœuds parents (suivant les edges)
        data   = _execute_node(...)               ← VRAI traitement des données
        node_results[id] = {rows_output, columns, output_preview, duration_ms}
4. Persiste : RunLog (1 ligne par nœud) + run.node_results + run.status
```

### Le flux de données concret

```
csv_reader   lit le fichier disque        →  5 lignes  (montants coercés en nombres)
   │                                          [{id:1,montant:1500,region:"Abidjan"}, ...]
   ▼
filter       montant > 50000               →  2 lignes
   │                                          [{id:2,montant:80000...}, {id:4,montant:120000...}]
   ▼
aggregate    GROUP BY region, SUM(montant) →  2 lignes
                                              [{region:"Abidjan",total:80000},
                                               {region:"Bouake",total:120000}]
```

Chaque nœud passe sa sortie au nœud suivant. Cas particuliers :

| Nœud | Comportement |
|---|---|
| `join` | reçoit **deux** entrées (gauche/droite selon l'ordre des edges) |
| `merge` | concatène **toutes** ses entrées |
| `sql_transform` / `sql_query` | exécute du vrai SQL via **SQLite en mémoire** sur `{input}` |
| `split` | duplique son entrée vers chaque sortie |

### Suivi en temps réel

```
GET  /runs/<run_id>/logs                  ← logs par nœud ("filter : 2 ligne(s) en sortie")
GET  /runs/<run_id>/logs/stream           ← SSE (text/event-stream)
GET  /runs/<run_id>/nodes/<nid>/output    ← inspecter la sortie d'un nœud précis
POST /pipelines/<pid>/runs/<run_id>/retry   ← relance
POST /pipelines/<pid>/runs/<run_id>/cancel  ← annule
```

---

## Étape 5 — Résultats & export (`app/routes/results.py`)

```
GET  /runs/<run_id>/results                  → lignes du nœud terminal + résumé par nœud
GET  /results/<run_id>/download?format=csv   → télécharge un vrai fichier CSV
GET  /results/<run_id>/download?format=json  → … ou JSON
POST /results/<run_id>/export                → crée un export persistant
```

`_get_run_data()` prend la sortie du **dernier nœud** du graphe et la sérialise en
CSV/JSON téléchargeable.

---

## En une phrase

> L'utilisateur **uploade un CSV**, **assemble visuellement** des nœuds reliés par des
> arêtes (un DAG), **lance un run** qui fait couler les données réelles de nœud en nœud
> via le moteur ETL, puis **télécharge le résultat** transformé — exactement les
> « 2 jours d'Excel ramenés à 15 minutes » du thème 9.

---

## Types de nœuds disponibles

| Catégorie | Nœuds | Exécution réelle ? |
|---|---|---|
| **Input** | `csv_reader`, `json_reader` | ✅ lecture fichier disque |
| **Input** | `sql_query`, `http_request` | ⚠️ datasource/réseau non branché → sortie vide + log |
| **Transform** | `filter`, `map`, `aggregate`, `join`, `sort`, `dedup`, `sql_transform`, `validate` | ✅ |
| **AI** | `ai_transform` | ⚠️ passe-through journalisé |
| **Output** | `file_export`, `sql_write`, `webhook_send`, `notification_send` | ⚠️ passe-through journalisé |
| **Control** | `merge`, `split` | ✅ |
| **Trigger** | `schedule_trigger` | n/a |

---

## Limitations connues

- **Export limité à l'aperçu** : le moteur ne stocke dans `node_results` que
  `output_preview` (les **10 premières lignes**, plafond `preview_rows`). Donc
  `GET /results/.../download` ne renvoie que ces 10 lignes, pas le dataset complet.
  → Pour une vraie consolidation, il faudrait persister le dataset complet du nœud
  terminal (sur disque ou en base) et faire pointer le download dessus.
- **Datasources externes** (`sql_query`, `http_request`) non connectées : elles
  renvoient une sortie vide avec un log d'avertissement plutôt que des données fictives.
  Le chemin **fichier → transforms → export** est, lui, 100 % réel.
- **Sorties terminales** (`sql_write`, `webhook_send`, `notification_send`) et
  `ai_transform` sont en passe-through journalisé (pas d'effet externe réel).

---

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `app/engine.py` | Moteur ETL : tri topologique + exécution des nœuds |
| `app/routes/runs.py` | Déclenche les runs, charge les fichiers, persiste logs/résultats |
| `app/routes/transform.py` | `/sql/execute` et `/transform/preview` (SQL réel sur données fournies) |
| `app/routes/files.py` | Upload et parsing des fichiers sources |
| `app/routes/results.py` | Récupération et export des résultats |
| `app/models.py` | 25 modèles SQLAlchemy (User → … → Run/RunLog) |
| `tests/unit/test_engine.py` | Tests unitaires du moteur |
| `tests/integration/test_runs.py` | Test bout-en-bout (upload CSV → filter → aggregate) |
