import type { Pipeline, NodeData } from '@/types'
import type { Edge } from '@xyflow/react'
import { NODE_REGISTRY } from './nodeRegistry'

type DemoNode = { id: string; type: string; position: { x: number; y: number }; data: NodeData }

function makeNodeTypes() {
  return NODE_REGISTRY.map((n) => ({ slug: n.slug, label: n.label, category: n.category, description: n.description }))
}

function pipe(id: string, name: string, desc: string): Pipeline {
  return { id, name, description: desc, workspace_id: 'demo', nodes_count: 0, created_at: '', updated_at: '' }
}

// ── Pipeline 1 — Analyse des ventes ──────────────────────────────────────
const salesNodes: DemoNode[] = [
  { id: 'n1', type: 'csv_import',   position: { x: 60,  y: 160 }, data: { label: 'CSV Import',   config: { file_id: 'ventes_2024.csv', separator: ',', has_header: true } } },
  { id: 'n2', type: 'filter',       position: { x: 320, y: 160 }, data: { label: 'Filtre',        config: { column: 'montant', operator: '>', value: '500' } } },
  { id: 'n3', type: 'aggregate',    position: { x: 580, y: 160 }, data: { label: 'Agrégation',    config: { group_by: ['région'], aggregations: [{ column: 'montant', function: 'SUM', alias: 'CA' }] } } },
  { id: 'n4', type: 'chart',        position: { x: 840, y: 160 }, data: { label: 'Chart',         config: { chart_type: 'bar', x_column: 'région', y_column: 'CA', title: 'CA par région' } } },
]
const salesEdges: Edge[] = [
  { id: 'e1-2', source: 'n1', target: 'n2' },
  { id: 'e2-3', source: 'n2', target: 'n3' },
  { id: 'e3-4', source: 'n3', target: 'n4' },
]

// ── Pipeline 2 — CRM Nettoyage ────────────────────────────────────────────
const crmNodes: DemoNode[] = [
  { id: 'n1', type: 'json_loader',  position: { x: 60,  y: 160 }, data: { label: 'JSON Loader',  config: { source: 'file', file_id: 'clients.json', root_path: '' } } },
  { id: 'n2', type: 'clean',        position: { x: 320, y: 160 }, data: { label: 'Nettoyage',    config: { remove_duplicates: true, remove_null_rows: true, trim_strings: true } } },
  { id: 'n3', type: 'rename',       position: { x: 580, y: 160 }, data: { label: 'Rename',       config: { operations: [{ from: 'client_id', to: 'id' }, { from: 'full_name', to: 'nom' }] } } },
  { id: 'n4', type: 'export',       position: { x: 840, y: 160 }, data: { label: 'Export',       config: { format: 'csv', filename: 'crm_clean.csv' } } },
]
const crmEdges: Edge[] = [
  { id: 'e1-2', source: 'n1', target: 'n2' },
  { id: 'e2-3', source: 'n2', target: 'n3' },
  { id: 'e3-4', source: 'n3', target: 'n4' },
]

// ── Pipeline 3 — IA Transform ─────────────────────────────────────────────
const aiNodes: DemoNode[] = [
  { id: 'n1', type: 'csv_import',    position: { x: 60,  y: 160 }, data: { label: 'CSV Import',    config: { file_id: 'revenus_q4.csv', separator: ';', has_header: true } } },
  { id: 'n2', type: 'ai_transform',  position: { x: 380, y: 160 }, data: { label: 'IA Transform',  config: { model: 'claude-sonnet-4-6', prompt: 'Crée une colonne tranche_âge à partir de la colonne age (0-18, 19-35, 36-60, 60+)' } } },
  { id: 'n3', type: 'table_preview', position: { x: 700, y: 160 }, data: { label: 'Table Preview', config: { page_size: 50 } } },
]
const aiEdges: Edge[] = [
  { id: 'e1-2', source: 'n1', target: 'n2' },
  { id: 'e2-3', source: 'n2', target: 'n3' },
]

export const DEMO_PIPELINES_DATA: Record<string, {
  pipeline: Pipeline
  nodeTypes: ReturnType<typeof makeNodeTypes>
  nodes: DemoNode[]
  edges: Edge[]
}> = {
  'demo-sales': { pipeline: pipe('demo-sales', 'Analyse des ventes 2024', ''), nodeTypes: makeNodeTypes(), nodes: salesNodes, edges: salesEdges },
  'demo-crm':   { pipeline: pipe('demo-crm',   'Nettoyage CRM clients',  ''), nodeTypes: makeNodeTypes(), nodes: crmNodes,   edges: crmEdges   },
  'demo-ai':    { pipeline: pipe('demo-ai',    'IA Transform — revenus', ''), nodeTypes: makeNodeTypes(), nodes: aiNodes,    edges: aiEdges    },
}
