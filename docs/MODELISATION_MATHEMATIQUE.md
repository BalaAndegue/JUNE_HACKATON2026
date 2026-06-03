# Modélisation mathématique de DataPipe

## 1. Introduction

DataPipe modélise un pipeline ETL bancaire comme un système de transformation de données structuré autour d'un graphe orienté acyclique. Chaque pipeline reçoit une ou plusieurs sources de données, applique une suite ordonnée de transformations, puis produit des sorties exploitables pour l'analyse, le reporting, l'audit ou l'automatisation bancaire.

L'objectif de cette modélisation est de formaliser le comportement du système afin de garantir :

- la cohérence de l'exécution des pipelines ;
- la traçabilité des transformations ;
- la fiabilité des résultats produits ;
- la détection d'anomalies dans les flux transactionnels ;
- l'évaluation de la performance d'exécution.

## 2. Notations générales

On note :

- \( P \) : un pipeline DataPipe ;
- \( G = (V, E) \) : le graphe associé au pipeline ;
- \( V = \{v_1, v_2, ..., v_n\} \) : l'ensemble des noeuds du pipeline ;
- \( E \subseteq V \times V \) : l'ensemble des connexions entre noeuds ;
- \( D_i \) : le dataset produit par le noeud \( v_i \) ;
- \( T_i \) : la transformation appliquée par le noeud \( v_i \) ;
- \( C_i \) : la configuration du noeud \( v_i \) ;
- \( R \) : l'ensemble des lignes d'un dataset ;
- \( A = \{a_1, a_2, ..., a_m\} \) : l'ensemble des attributs ou colonnes.

Un dataset est représenté comme une relation tabulaire :

\[
D = \{r_1, r_2, ..., r_k\}
\]

où chaque ligne \( r_j \) est un vecteur de valeurs :

\[
r_j = (x_{j1}, x_{j2}, ..., x_{jm})
\]

## 3. Modélisation du pipeline comme graphe orienté acyclique

Un pipeline DataPipe est représenté par un graphe orienté :

\[
G = (V, E)
\]

Un noeud \( v_i \in V \) correspond à une opération élémentaire : lecture de fichier, filtrage, agrégation, jointure, transformation SQL, validation, export ou transformation assistée par IA.

Une arête \( e = (v_i, v_j) \in E \) signifie que la sortie du noeud \( v_i \) devient une entrée du noeud \( v_j \).

Pour qu'un pipeline soit exécutable, le graphe doit être acyclique :

\[
\nexists (v_1, v_2, ..., v_k) \text{ tel que } v_1 \rightarrow v_2 \rightarrow ... \rightarrow v_k \rightarrow v_1
\]

Cette contrainte garantit qu'il existe un ordre d'exécution valide. DataPipe applique un tri topologique pour déterminer cet ordre :

\[
\operatorname{order}(G) = (v_{\pi(1)}, v_{\pi(2)}, ..., v_{\pi(n)})
\]

tel que pour toute arête \( (v_i, v_j) \), le noeud \( v_i \) est exécuté avant \( v_j \).

## 4. Fonction de transformation d'un noeud

Chaque noeud est modélisé comme une fonction :

\[
T_i : \mathcal{D}^{p_i} \times C_i \rightarrow \mathcal{D}
\]

où :

- \( \mathcal{D} \) est l'espace des datasets ;
- \( p_i \) est le nombre d'entrées du noeud ;
- \( C_i \) est la configuration du noeud ;
- \( T_i \) produit un dataset de sortie.

La sortie d'un noeud est donc :

\[
D_i = T_i(D_{parent_1}, D_{parent_2}, ..., D_{parent_p}, C_i)
\]

Pour les noeuds sources, comme `csv_reader` ou `json_reader`, la transformation ne dépend pas d'un parent :

\[
D_i = T_i(C_i)
\]

## 5. Opérateurs de transformation

### 5.1 Filtrage

Le filtrage conserve uniquement les lignes qui satisfont une condition logique \( \varphi \).

\[
T_{filter}(D, \varphi) = \{r \in D \mid \varphi(r) = vrai\}
\]

Si plusieurs conditions sont définies, elles sont combinées par :

\[
\varphi(r) = \varphi_1(r) \land \varphi_2(r) \land ... \land \varphi_k(r)
\]

ou :

\[
\varphi(r) = \varphi_1(r) \lor \varphi_2(r) \lor ... \lor \varphi_k(r)
\]

selon la logique `AND` ou `OR`.

### 5.2 Projection et mapping

Le mapping sélectionne, renomme ou réorganise les attributs d'un dataset.

Pour un ensemble de colonnes \( B \subseteq A \), la projection est :

\[
T_{map}(D, B) = \pi_B(D)
\]

Chaque ligne de sortie contient uniquement les attributs sélectionnés ou renommés.

### 5.3 Agrégation

L'agrégation regroupe les lignes selon un ensemble de clés \( K \), puis applique des fonctions statistiques.

\[
T_{agg}(D, K, F) = \gamma_{K, F}(D)
\]

Les fonctions prises en charge incluent :

- comptage : \( COUNT(D_g) = |D_g| \) ;
- somme : \( SUM(x) = \sum_{i=1}^{n} x_i \) ;
- moyenne : \( AVG(x) = \frac{1}{n}\sum_{i=1}^{n} x_i \) ;
- minimum : \( MIN(x) \) ;
- maximum : \( MAX(x) \) ;
- nombre de valeurs distinctes : \( COUNT\_DISTINCT(x) \).

Pour un groupe \( g \), la sortie est :

\[
r_g = (K_g, F_1(D_g), F_2(D_g), ..., F_q(D_g))
\]

### 5.4 Tri

Le tri ordonne les lignes selon une ou plusieurs clés.

\[
T_{sort}(D, a, ordre) = \operatorname{sort}(D, a, ordre)
\]

avec \( ordre \in \{asc, desc\} \).

### 5.5 Dédoublonnage

Le dédoublonnage conserve une seule occurrence pour une clé donnée \( K \).

\[
T_{dedup}(D, K) = \{r \in D \mid key(r) \notin S\}
\]

où \( S \) est l'ensemble des clés déjà rencontrées.

Selon la configuration, DataPipe conserve la première ou la dernière occurrence.

### 5.6 Jointure

La jointure combine deux datasets \( D_L \) et \( D_R \) selon deux clés \( k_L \) et \( k_R \).

Pour une jointure interne :

\[
T_{join}(D_L, D_R) =
\{r_L \cup r_R \mid r_L \in D_L, r_R \in D_R, r_L[k_L] = r_R[k_R]\}
\]

DataPipe prend aussi en charge les variantes `left`, `right` et `full`, qui conservent respectivement les lignes non appariées du dataset gauche, droit ou des deux.

### 5.7 Transformation SQL

Une transformation SQL est modélisée comme une fonction déclarative :

\[
T_{sql}(D, q) = q(D)
\]

où \( q \) est une requête `SELECT` appliquée au dataset d'entrée représenté comme une table temporaire `input`.

Pour des raisons de sécurité, seules les transformations non destructives sont autorisées. Les opérations de modification de structure ou de données, comme `DROP`, `DELETE`, `ALTER`, `INSERT` ou `UPDATE`, sont rejetées.

### 5.8 Validation de données

La validation applique un ensemble de règles \( \mathcal{R} \) à chaque ligne.

\[
T_{validate}(D, \mathcal{R}) =
\{r \in D \mid \forall \rho \in \mathcal{R}, \rho(r) = vrai\}
\]

Une règle typique est la contrainte de présence :

\[
\rho_{required}(r, a) = vrai \iff r[a] \neq null \land r[a] \neq ""
\]

Les lignes invalides sont écartées et journalisées.

## 6. Modélisation de la détection d'anomalies

Dans le contexte bancaire, une anomalie correspond à une transaction dont le comportement s'écarte fortement du comportement statistique attendu.

Pour une variable numérique \( X \), par exemple le montant d'une transaction, on calcule :

\[
\mu = \frac{1}{n}\sum_{i=1}^{n} x_i
\]

\[
\sigma = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(x_i - \mu)^2}
\]

Le score d'anomalie utilisé est le z-score :

\[
z_i = \frac{|x_i - \mu|}{\sigma}
\]

Une ligne est considérée comme anomalie si :

\[
z_i > \tau
\]

avec \( \tau = 3 \) dans l'implémentation actuelle.

Interprétation :

- \( z_i \leq 3 \) : transaction considérée comme normale ;
- \( 3 < z_i \leq 5 \) : anomalie moyenne ;
- \( z_i > 5 \) : anomalie forte.

Cette approche est simple, explicable et adaptée à une première analyse de transactions. Elle est particulièrement utile pour détecter des montants extrêmes, mais elle peut être complétée par des méthodes plus avancées lorsque les données deviennent volumineuses ou multidimensionnelles.

## 7. Transformation assistée par IA

La transformation IA est modélisée comme une fonction de génération :

\[
G_{IA} : (d, A) \rightarrow q
\]

où :

- \( d \) est une description en langage naturel ;
- \( A \) est la liste des colonnes disponibles ;
- \( q \) est une requête SQL générée.

La transformation complète devient :

\[
T_{IA}(D, d) = T_{sql}(D, G_{IA}(d, A))
\]

Exemple :

Description utilisateur :

```text
Calculer la somme des transactions par mois.
```

Requête générée :

```sql
SELECT STRFTIME('%Y-%m', date_transaction) AS mois,
       SUM(montant) AS total
FROM input
GROUP BY mois
ORDER BY mois DESC;
```

Le rôle de l'IA est donc de convertir une intention métier en transformation formelle exécutable.

## 8. Modèle d'exécution

L'exécution d'un pipeline suit trois étapes :

1. Validation structurelle du graphe.
2. Tri topologique des noeuds.
3. Exécution séquentielle des transformations selon l'ordre obtenu.

Pour chaque noeud \( v_i \), DataPipe calcule :

\[
D_i = T_i(inputs(v_i), C_i)
\]

avec :

\[
inputs(v_i) = \{D_j \mid (v_j, v_i) \in E\}
\]

Chaque exécution produit des métriques opérationnelles :

- nombre de lignes reçues ;
- nombre de lignes produites ;
- durée d'exécution ;
- colonnes de sortie ;
- aperçu du résultat ;
- logs d'information, d'avertissement ou d'erreur.

## 9. Métriques de performance

Pour un pipeline \( P \), la durée totale d'exécution est :

\[
T(P) = \sum_{i=1}^{n} T(v_i)
\]

où \( T(v_i) \) est la durée d'exécution du noeud \( v_i \).

Le débit peut être estimé par :

\[
Q(P) = \frac{N_{out}}{T(P)}
\]

où \( N_{out} \) est le nombre de lignes produites par le pipeline.

Le taux de réduction des données est :

\[
\rho = 1 - \frac{N_{out}}{N_{in}}
\]

avec :

- \( N_{in} \) : nombre total de lignes en entrée ;
- \( N_{out} \) : nombre total de lignes en sortie.

Un taux élevé peut indiquer un filtrage important, une validation stricte ou une agrégation forte.

## 10. Qualité des données

La qualité d'un dataset peut être évaluée à l'aide de plusieurs indicateurs.

### 10.1 Complétude

\[
Completeness(D) = 1 - \frac{N_{missing}}{N_{total}}
\]

### 10.2 Unicité

\[
Uniqueness(D, K) = \frac{|distinct(K)|}{|D|}
\]

### 10.3 Taux d'anomalies

\[
AnomalyRate(D) = \frac{N_{anomalies}}{|D|}
\]

### 10.4 Taux de validité

\[
Validity(D) = \frac{N_{valid}}{|D|}
\]

Ces métriques permettent d'évaluer la fiabilité des données avant leur export ou leur exploitation métier.

## 11. Exemple bancaire : détection d'anomalies

Soit un dataset de transactions :

\[
D = \{(id, montant, type, statut, date)\}
\]

On souhaite détecter les transactions anormalement élevées.

Pipeline :

```text
CSV Reader -> Validate -> Filter -> AI/SQL Transform -> Export
```

Formalisation :

\[
D_1 = T_{csv}(fichier)
\]

\[
D_2 = T_{validate}(D_1, \mathcal{R})
\]

\[
D_3 = T_{filter}(D_2, statut = "traite")
\]

\[
D_4 = \{r \in D_3 \mid z(r.montant) > 3\}
\]

\[
D_5 = T_{export}(D_4)
\]

Le résultat final contient les transactions les plus suspectes selon leur écart statistique à la moyenne.

## 12. Limites du modèle actuel

Le modèle actuel est robuste pour des pipelines ETL explicables, mais il présente certaines limites :

- le z-score est sensible aux valeurs extrêmes lorsqu'elles influencent fortement la moyenne ;
- les transformations sont exécutées séquentiellement, sans parallélisation globale du graphe ;
- la détection d'anomalies actuelle est principalement univariée ;
- la qualité des résultats IA dépend de la précision de la description utilisateur et des colonnes disponibles ;
- SQLite en mémoire est adapté aux transformations légères à moyennes, mais pas aux volumes massifs.

## 13. Évolutions recommandées

Pour renforcer le modèle mathématique et analytique, les évolutions suivantes sont pertinentes :

- introduire des méthodes robustes comme le score MAD :

\[
MAD = median(|x_i - median(X)|)
\]

- utiliser des modèles multivariés comme Isolation Forest ou Local Outlier Factor ;
- ajouter une estimation de complexité par type de noeud ;
- paralléliser les branches indépendantes du DAG ;
- intégrer des contraintes de schéma fortes avant exécution ;
- calculer automatiquement les métriques de qualité des données après chaque transformation ;
- versionner les hypothèses statistiques utilisées par les pipelines critiques.

## 14. Conclusion

La modélisation mathématique de DataPipe repose sur une représentation claire : un pipeline est un graphe orienté acyclique dont les noeuds sont des fonctions de transformation appliquées à des relations tabulaires.

Cette approche permet de combiner les fondements des bases de données relationnelles, de l'algorithmique des graphes, de la statistique descriptive et de l'intelligence artificielle pour répondre à des besoins concrets de traitement de données bancaires.

Le modèle est explicable, extensible et aligné avec les exigences d'un environnement financier : traçabilité, contrôle, qualité des données et détection précoce des anomalies.
