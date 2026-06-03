# DataPipe — ETL Visuel Bancaire (Thème 9) · Guide de démo

> Plateforme DataOps bancaire : construire visuellement des pipelines
> d'ingestion/transformation, avec un **moteur d'exécution réel** (DuckDB/Pandas),
> de l'**anonymisation RGPD**, de la **détection d'anomalies**, un **score qualité**
> et un **agent IA contrôlé** qui génère du SQL et le **teste sur un échantillon réel**
> avant exécution.

## Ce qui nous distingue (au-delà du sujet)

| Attendu (sujet) | Ce qu'on livre en plus |
|---|---|
| Interface nodale CSV/JSON/SQL | ✅ + nœuds **bancaires** : masquage PII, anomalies, score qualité |
| Transformations à la volée | ✅ **vrai moteur** DuckDB/Pandas (pas de simulation) |
| IA qui génère du SQL | ✅ **agent contrôlé** : génère → explique → **dry-run sur échantillon** → validation humaine |
| — | ✅ **audit trail** réel à chaque exécution (conformité bancaire) |
| — | ✅ **score qualité** réel par étape (nulls, doublons) |

Le bonus IA du règlement (+3 pts) cible une *implémentation concrète* d'un **Agent IA** :
c'est exactement `/api/v1/ai/agent/transform`.

## Lancer (2 terminaux)

**Backend** (port 5000) :
```bash
cd datapipe_backend
python -m venv .venv && . .venv/bin/activate     # (fish: . .venv/bin/activate.fish)
pip install -r requirements.txt
python run.py        # http://localhost:5000  — Swagger: /apidocs
```

**Frontend** (port 3000) :
```bash
cd datapipe-app
npm install
npm run dev          # http://localhost:3000
```
> `.env.local` pointe déjà le frontend vers `http://localhost:5000`.

## Compte de démo (déjà semé)

```
Email : demo@bank.cm
Mot de passe : Hackaton2026!
```
Un pipeline **« Nettoyage & conformité transactions »** est déjà prêt, avec le
fichier `transactions_demo.csv` (données volontairement sales) attaché.

## Parcours jury (≈ 3 min)

1. **Login** avec le compte démo → Dashboard.
2. Ouvrir le pipeline **Nettoyage & conformité transactions** dans l'éditeur.
   - Graphe : `Transactions CSV → Masquage RGPD → Détection anomalies → Agrégation par type`.
3. Cliquer **Exécuter**. Le run est réel et synchrone.
4. Onglet **Données**, cliquer chaque nœud :
   - **Transactions CSV** : 15 lignes, score qualité réel.
   - **Masquage RGPD** : `client_name`, `account_number`, `phone` anonymisés
     (`T*** A*** W***`, `*******5001`, `699***456`).
   - **Détection anomalies** : 4 transactions suspectes (négatives + > 5 000 000).
   - **Agrégation par type** : totaux réels crédit/débit.
5. Ouvrir le **panneau IA** : demander « total des montants par type » →
   l'agent génère le SQL, l'explique, et on peut le tester avant exécution.

## Preuves techniques

- **240 tests backend** verts : `cd datapipe_backend && .venv/bin/python -m pytest`
- **Smoke moteur** (e2e, données réelles) : `python scripts/smoke_engine.py`
- **Parcours démo** (mime le frontend) : `python scripts/verify_demo_flow.py`

## Architecture

```
Frontend  Next.js 16 + React Flow (@xyflow) + Zustand + axios
Backend   Flask + SQLAlchemy + JWT (175+ endpoints, Swagger)
Moteur    app/engine/ — tri topologique + exécution DuckDB/Pandas
IA        API Claude (Anthropic) + agent contrôlé + fallback heuristique
Compat    app/routes/compat.py — couche d'adaptation front↔back (testée)
```
