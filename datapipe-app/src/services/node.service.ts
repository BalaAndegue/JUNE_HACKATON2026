import api from '@/lib/axios'
import type { FlowNode, FlowEdge, NodeType, NodeTypeSchema } from '@/types'

export const nodeService = {
  // Nodes
  listNodes: async (pipelineId: string) => {
    const res = await api.get<{ nodes: FlowNode[] }>(`/api/v1/pipelines/${pipelineId}/nodes`)
    return res.data.nodes
  },

  addNode: async (pipelineId: string, data: {
    type: string
    position: { x: number; y: number }
    data?: { config: Record<string, unknown> }
    label?: string
  }) => {
    const res = await api.post<FlowNode>(`/api/v1/pipelines/${pipelineId}/nodes`, data)
    return res.data
  },

  getNode: async (pipelineId: string, nodeId: string) => {
    const res = await api.get<FlowNode>(`/api/v1/pipelines/${pipelineId}/nodes/${nodeId}`)
    return res.data
  },

  replaceNode: async (pipelineId: string, nodeId: string, data: { position?: { x: number; y: number }; data: FlowNode['data'] }) => {
    const res = await api.put<FlowNode>(`/api/v1/pipelines/${pipelineId}/nodes/${nodeId}`, data)
    return res.data
  },

  updateNode: async (pipelineId: string, nodeId: string, data: {
    position?: { x: number; y: number }
    'data.config'?: Record<string, unknown>
    'data.label'?: string
  }) => {
    const res = await api.patch<FlowNode>(`/api/v1/pipelines/${pipelineId}/nodes/${nodeId}`, data)
    return res.data
  },

  deleteNode: async (pipelineId: string, nodeId: string) => {
    const res = await api.delete(`/api/v1/pipelines/${pipelineId}/nodes/${nodeId}`)
    return res.data as { deleted_node_id: string; deleted_edges: string[] }
  },

  bulkCreateNodes: async (pipelineId: string, nodes: FlowNode[]) => {
    const res = await api.post(`/api/v1/pipelines/${pipelineId}/nodes/bulk`, { nodes })
    return res.data.created as FlowNode[]
  },

  getTestData: async (pipelineId: string, nodeId: string) => {
    const res = await api.get(`/api/v1/pipelines/${pipelineId}/nodes/${nodeId}/test-data`)
    return res.data
  },

  pinData: async (pipelineId: string, nodeId: string, runId: string) => {
    const res = await api.post(`/api/v1/pipelines/${pipelineId}/nodes/${nodeId}/pin-data`, { run_id: runId })
    return res.data
  },

  getPinnedData: async (pipelineId: string, nodeId: string) => {
    const res = await api.get(`/api/v1/pipelines/${pipelineId}/nodes/${nodeId}/pinned-data`)
    return res.data
  },

  deletePinnedData: async (pipelineId: string, nodeId: string) => {
    await api.delete(`/api/v1/pipelines/${pipelineId}/nodes/${nodeId}/pinned-data`)
  },

  // Edges
  listEdges: async (pipelineId: string) => {
    const res = await api.get<{ edges: FlowEdge[] }>(`/api/v1/pipelines/${pipelineId}/edges`)
    return res.data.edges
  },

  createEdge: async (pipelineId: string, data: {
    source: string
    target: string
    source_handle?: string
    target_handle?: string
  }) => {
    const res = await api.post<FlowEdge & { valid: boolean }>(`/api/v1/pipelines/${pipelineId}/edges`, data)
    return res.data
  },

  deleteEdge: async (pipelineId: string, edgeId: string) => {
    const res = await api.delete(`/api/v1/pipelines/${pipelineId}/edges/${edgeId}`)
    return res.data as { deleted_edge_id: string }
  },

  validateEdge: async (pipelineId: string, data: { source: string; target: string }) => {
    const res = await api.post(`/api/v1/pipelines/${pipelineId}/edges/validate`, data)
    return res.data as { valid: boolean; reason?: string }
  },

  // Node type catalog
  getNodeTypes: async () => {
    const res = await api.get<{ node_types: NodeType[] }>('/api/v1/node-types')
    return res.data.node_types
  },

  getNodeType: async (typeSlug: string) => {
    const res = await api.get<NodeType>(`/api/v1/node-types/${typeSlug}`)
    return res.data
  },

  getNodeSchema: async (typeSlug: string) => {
    const res = await api.get<{ schema: NodeTypeSchema }>(`/api/v1/node-types/${typeSlug}/schema`)
    return res.data.schema
  },
}
