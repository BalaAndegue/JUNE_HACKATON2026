# État de l'art

## 1. Introduction

La transformation numérique du secteur bancaire impose une gestion rapide, fiable et traçable des données. Les banques manipulent quotidiennement des volumes importants d'informations : transactions, comptes clients, journaux d'audit, fichiers de rapprochement, opérations interbancaires, données de conformité et indicateurs de risque.

Dans ce contexte, les pipelines ETL jouent un rôle central. Ils permettent d'extraire les données depuis plusieurs sources, de les transformer selon des règles métier, puis de les charger vers des systèmes d'analyse, de reporting ou de supervision.

DataPipe s'inscrit dans cette évolution en proposant une approche visuelle, modulaire et orientée API pour construire des pipelines bancaires, avec une intégration de traitements SQL, de validation, de monitoring et d'intelligence artificielle.

## 2. Les systèmes ETL traditionnels

Les solutions ETL classiques reposent sur trois étapes fondamentales :

- **Extraction** : récupération des données depuis des fichiers, bases de données, API ou systèmes métiers.
- **Transformation** : nettoyage, filtrage, agrégation, normalisation, enrichissement et validation.
- **Chargement** : écriture des données vers un entrepôt, un data mart, un fichier ou une application cible.

Des outils comme Talend, Informatica PowerCenter, Microsoft SSIS ou Pentaho ont longtemps dominé ce domaine. Ils offrent des interfaces graphiques, des connecteurs variés et des mécanismes d'orchestration avancés.

Cependant, ces solutions peuvent être coûteuses, lourdes à déployer et difficiles à adapter rapidement dans un contexte de hackathon, de preuve de concept ou de développement agile.

## 3. Les outils modernes d'orchestration de données

Les plateformes modernes ont introduit une séparation plus claire entre l'orchestration, la transformation et l'observabilité.

Parmi les outils de référence :

- **Apache Airflow** : orchestration de workflows sous forme de DAG, très utilisé dans les architectures data modernes.
- **Dagster** : orchestration orientée assets, avec une forte attention à la qualité et à la traçabilité.
- **Prefect** : orchestration Python flexible, adaptée aux environnements cloud et hybrides.
- **dbt** : transformation SQL déclarative, versionnée et testable, principalement utilisée dans les entrepôts de données.

Ces outils sont puissants, mais ils demandent souvent des compétences techniques avancées. Leur usage est généralement plus proche du data engineering que d'une interface accessible à des analystes métiers.

## 4. Les plateformes visuelles de workflows

Les plateformes visuelles, comme n8n, Node-RED, Zapier ou Make, ont popularisé une approche par blocs connectés. L'utilisateur construit un workflow en assemblant des noeuds représentant des actions.

Cette approche présente plusieurs avantages :

- compréhension visuelle du flux de données ;
- modularité des traitements ;
- réduction du temps de prototypage ;
- meilleure collaboration entre profils techniques et non techniques ;
- facilité de démonstration et de maintenance.

DataPipe reprend cette logique de modélisation par noeuds, mais l'adapte spécifiquement aux pipelines ETL bancaires : ingestion de fichiers, transformations SQL, validation de données, détection d'anomalies, export et alerting.

## 5. Les enjeux spécifiques du domaine bancaire

Le secteur bancaire impose des exigences plus fortes que beaucoup d'autres domaines applicatifs.

Les principales contraintes sont :

- **Fiabilité** : les données financières doivent être exactes et cohérentes.
- **Traçabilité** : chaque transformation doit pouvoir être expliquée et auditée.
- **Sécurité** : les accès, tokens, clés API et données sensibles doivent être protégés.
- **Conformité** : les traitements doivent respecter les règles internes, réglementaires et de gouvernance.
- **Disponibilité** : les traitements critiques doivent être surveillés et relancés en cas d'échec.
- **Qualité des données** : les doublons, valeurs manquantes, incohérences et anomalies doivent être détectés.

Un outil ETL bancaire ne doit donc pas seulement transformer les données. Il doit aussi produire des preuves d'exécution, des logs, des métriques et des alertes.

## 6. Qualité et validation des données

La qualité des données est un sujet central dans les architectures ETL. Les erreurs de données peuvent conduire à de mauvaises décisions, à des rapports incorrects ou à des risques opérationnels.

Les pratiques courantes incluent :

- vérification des champs obligatoires ;
- contrôle des types de données ;
- détection des doublons ;
- validation de formats ;
- contrôle des bornes numériques ;
- détection de valeurs aberrantes ;
- comparaison entre sources.

Des outils comme Great Expectations, Soda Core ou Deequ permettent de formaliser des règles de qualité. DataPipe adopte une approche plus légère et intégrée, en proposant des noeuds de validation directement dans le pipeline.

## 7. Détection d'anomalies dans les transactions

La détection d'anomalies est particulièrement importante dans les systèmes bancaires. Elle permet d'identifier des transactions atypiques, des erreurs de saisie, des comportements suspects ou des écarts de rapprochement.

Les méthodes classiques incluent :

- les seuils fixes ;
- le z-score ;
- l'écart interquartile ;
- la médiane absolue des écarts ;
- les modèles de clustering ;
- les forêts d'isolation ;
- les modèles supervisés de détection de fraude.

DataPipe utilise actuellement une approche explicable basée sur le z-score pour identifier les montants fortement éloignés de la moyenne. Cette méthode est simple, rapide et compréhensible par les utilisateurs métier. Elle constitue une base solide pour une première version, avec une possibilité d'évolution vers des modèles plus avancés.

## 8. Intelligence artificielle appliquée aux pipelines ETL

L'intelligence artificielle transforme progressivement la manière de concevoir les pipelines data.

Les usages courants sont :

- génération de requêtes SQL à partir du langage naturel ;
- suggestion automatique de pipelines ;
- nettoyage assisté des données ;
- classification automatique de lignes ;
- extraction d'entités ;
- analyse de qualité ;
- assistance conversationnelle pour les utilisateurs.

DataPipe intègre cette logique en permettant à l'utilisateur de décrire une transformation en langage naturel. Le système peut générer une requête SQL applicable au dataset d'entrée. Cette approche réduit la barrière technique pour les utilisateurs non experts en SQL.

L'IA ne remplace cependant pas les contrôles métier. Elle doit être encadrée par des validations, des logs et des mécanismes de fallback pour garantir la robustesse de l'exécution.

## 9. Observabilité et monitoring

Un pipeline professionnel doit être observable. Cela signifie qu'il doit fournir des informations sur son état, ses performances et ses erreurs.

Les éléments essentiels sont :

- statut d'exécution ;
- durée par noeud ;
- nombre de lignes traitées ;
- nombre de lignes produites ;
- logs horodatés ;
- erreurs détaillées ;
- alertes en cas d'échec ;
- métriques globales du système.

DataPipe répond à cet enjeu avec des runs, des logs, des résultats par noeud, des endpoints de health check, des métriques et un système d'alertes.

## 10. Notifications et alerting

Les systèmes modernes doivent prévenir les équipes lorsqu'un traitement échoue ou lorsqu'une condition critique est détectée.

Les canaux fréquents sont :

- email ;
- Slack ou Microsoft Teams ;
- SMS ;
- webhooks ;
- tableaux de bord internes.

Dans DataPipe, les alertes peuvent être configurées sur des conditions et des canaux. L'envoi email repose sur une configuration SMTP, ce qui permet de l'intégrer à des serveurs mail internes ou à des fournisseurs externes.

## 11. Sécurité et gestion des accès

La sécurité est indispensable dans un contexte bancaire. Un système ETL manipule souvent des données confidentielles ou réglementées.

Les bonnes pratiques incluent :

- authentification robuste ;
- gestion des sessions ;
- séparation des rôles ;
- révocation des tokens ;
- hachage des mots de passe ;
- limitation des opérations SQL dangereuses ;
- masquage des secrets ;
- audit des actions utilisateurs.

DataPipe applique plusieurs de ces principes : authentification JWT, bcrypt pour les mots de passe, gestion des organisations, rôles, sessions, clés API et blocage des requêtes SQL destructives.

## 12. Comparaison synthétique

| Catégorie | Exemples | Forces | Limites |
|---|---|---|---|
| ETL traditionnels | Talend, Informatica, SSIS | Maturité, connecteurs, gouvernance | Coût, complexité, lourdeur |
| Orchestrateurs data | Airflow, Dagster, Prefect | DAG, scheduling, robustesse | Moins accessibles aux profils métier |
| Transformation SQL | dbt | Versioning, tests, SQL propre | Centré entrepôt de données |
| Workflows visuels | n8n, Node-RED, Make | Simplicité, rapidité, visuel | Moins spécialisés pour l'ETL bancaire |
| Qualité data | Great Expectations, Soda | Règles fortes, contrôle qualité | Intégration parfois complexe |
| DataPipe | Projet actuel | API complète, graphe visuel, IA, contexte bancaire | Prototype évolutif, dépend de l'enrichissement des connecteurs |

## 13. Positionnement de DataPipe

DataPipe se positionne comme une solution légère, spécialisée et pédagogique pour concevoir des pipelines bancaires visuels.

Son positionnement repose sur quatre axes :

- **Accessibilité** : construction par noeuds et API REST documentée.
- **Spécialisation bancaire** : cas d'usage orientés transactions, rapprochement, anomalies et reporting.
- **Extensibilité** : architecture modulaire avec types de noeuds, templates et marketplace.
- **Intelligence assistée** : génération SQL, détection d'anomalies et assistance IA.

Cette combinaison permet de rapprocher les besoins métier des capacités techniques d'un backend data moderne.

## 14. Limites des solutions existantes et opportunité

Les solutions existantes sont puissantes, mais elles ne répondent pas toujours simultanément aux besoins suivants :

- être simple à utiliser ;
- être visuelle ;
- être orientée métier bancaire ;
- exposer une API complète ;
- intégrer l'IA ;
- rester légère à déployer ;
- fournir des tests et une documentation claire.

DataPipe exploite cette opportunité en proposant une solution intermédiaire : plus spécialisée qu'un outil de workflow généraliste, plus simple qu'une plateforme ETL industrielle, et plus accessible qu'un orchestrateur purement technique.

## 15. Perspectives d'évolution

Pour se rapprocher des standards industriels, DataPipe pourrait évoluer vers :

- des connecteurs PostgreSQL, MySQL, Oracle, S3 et Kafka ;
- une exécution distribuée ou parallèle des branches indépendantes ;
- un moteur de règles de qualité plus complet ;
- une gestion avancée des schémas ;
- un catalogue de données ;
- une interface visuelle complète ;
- des modèles avancés de détection d'anomalies ;
- une journalisation d'audit renforcée ;
- une intégration avec Slack, Teams et outils de ticketing ;
- un système de permissions plus granulaire.

## 16. Conclusion

L'état de l'art montre que les pipelines ETL modernes doivent combiner orchestration, qualité, observabilité, sécurité et automatisation. Dans le domaine bancaire, ces exigences sont renforcées par la criticité des données et les contraintes de conformité.

DataPipe répond à ces enjeux en proposant une architecture visuelle, modulaire et orientée API. Le projet s'appuie sur les principes des graphes de workflows, des transformations relationnelles, de l'observabilité et de l'intelligence artificielle pour offrir une base solide de pipeline ETL bancaire.

Son intérêt principal réside dans son équilibre entre simplicité, spécialisation métier et capacité d'évolution.
