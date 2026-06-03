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
====================== 220 passed, 160 warnings in 18.78s ======================
```
Les 220 tests du projet (incluant l'authentification, les workspaces, les runs et le module IA) passent à **100% avec succès**.

---

## 6. Prochaines Étapes pour la Démo Hackathon

1. **Configuration Staging/Prod** : Renseigner les variables `ANTHROPIC_API_KEY` dans le fichier `.env` sur le serveur de démonstration si les appels réels à Claude sont requis.
2. **Interface Graphique** : L'équipe Frontend (Jeff) peut consommer directement `POST /api/v1/ai/generate-pipeline` et passer le tableau `nodes` et `edges` directement à l'état React Flow pour un affichage immédiat à l'écran.
