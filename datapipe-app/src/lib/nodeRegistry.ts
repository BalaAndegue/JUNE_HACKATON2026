/**
 * Static registry of all 12 node types.
 * Used by NodePanel, NodeInspector, and the canvas.
 */

import type { NodeType } from '@/types'

export const NODE_REGISTRY: NodeType[] = [
  // ── SOURCES ──────────────────────────────────────────────────────────────
  {
    slug: 'csv_import',
    label: 'CSV Import',
    category: 'source',
    color: '#00e5a0',
    icon: '',
    description: 'Importe un fichier .csv uploadé',
    inputs: 0,
    outputs: 1,
  },
  {
    slug: 'json_loader',
    label: 'JSON Loader',
    category: 'source',
    color: '#00e5a0',
    icon: '',
    description: 'Charge un fichier .json ou une URL d\'API',
    inputs: 0,
    outputs: 1,
  },
  {
    slug: 'sql_query',
    label: 'SQL Query',
    category: 'source',
    color: '#00e5a0',
    icon: '',
    description: 'Exécute une requête SQL sur une base de données',
    inputs: 0,
    outputs: 1,
  },

  // ── TRANSFORMATIONS ───────────────────────────────────────────────────────
  {
    slug: 'filter',
    label: 'Filtre',
    category: 'transform',
    color: '#3b82f6',
    icon: '',
    description: 'Filtre les lignes selon une condition',
    inputs: 1,
    outputs: 1,
  },
  {
    slug: 'join',
    label: 'Join',
    category: 'transform',
    color: '#3b82f6',
    icon: '',
    description: 'Fusionne deux DataFrames',
    inputs: 2,
    outputs: 1,
  },
  {
    slug: 'aggregate',
    label: 'Agrégation',
    category: 'transform',
    color: '#3b82f6',
    icon: '',
    description: 'GROUP BY + fonctions d\'agrégation',
    inputs: 1,
    outputs: 1,
  },
  {
    slug: 'rename',
    label: 'Rename / Select',
    category: 'transform',
    color: '#3b82f6',
    icon: '',
    description: 'Renomme, supprime ou réordonne les colonnes',
    inputs: 1,
    outputs: 1,
  },
  {
    slug: 'clean',
    label: 'Nettoyage',
    category: 'transform',
    color: '#3b82f6',
    icon: '',
    description: 'Supprime doublons, gère les nulls, trim strings',
    inputs: 1,
    outputs: 1,
  },

  // ── AI ───────────────────────────────────────────────────────────────────
  {
    slug: 'ai_transform',
    label: 'IA Transform',
    category: 'ai',
    color: '#a855f7',
    icon: '',
    description: 'Transformation guidée par un prompt en langage naturel',
    inputs: 1,
    outputs: 1,
  },

  // ── OUTPUTS ───────────────────────────────────────────────────────────────
  {
    slug: 'table_preview',
    label: 'Table Preview',
    category: 'output',
    color: '#f59e0b',
    icon: '',
    description: 'Affiche un tableau interactif dans la console',
    inputs: 1,
    outputs: 0,
  },
  {
    slug: 'chart',
    label: 'Chart',
    category: 'output',
    color: '#f59e0b',
    icon: '',
    description: 'Génère un graphique Bar/Line/Pie avec Recharts',
    inputs: 1,
    outputs: 0,
  },
  {
    slug: 'export',
    label: 'Export',
    category: 'output',
    color: '#f59e0b',
    icon: '',
    description: 'Télécharge le DataFrame en CSV ou JSON',
    inputs: 1,
    outputs: 0,
  },
]

export const NODE_REGISTRY_MAP = Object.fromEntries(
  NODE_REGISTRY.map((n) => [n.slug, n])
)
