import api from '@/lib/axios'
import type {
  GeneratedPipeline, GeneratedSQL, ColumnSuggestion, JoinSuggestion,
  ChatMessage, ChatResponse, AIUsage, ColumnSchema,
} from '@/types'

export interface AgentResult {
  description: string
  generated_sql: string
  explanation: string
  model: string
  validation: { safe: boolean; issues: string[] }
  status: string
  sample?: {
    rows_in: number
    rows_out: number
    columns_before: string[]
    columns_after: string[]
    preview_before: Array<Record<string, unknown>>
    preview_after: Array<Record<string, unknown>>
    quality_before?: { score: number }
    quality_after?: { score: number }
    note?: string
  }
}

export interface PlanAction {
  type: 'reply' | 'action'
  message: string
  action?: string
  params?: Record<string, unknown>
  warning?: string | null
  requires_confirmation?: boolean
  model?: string
}

export const aiService = {
  // Chat "action mode": turns a message into a proposed action (or a reply).
  // Nothing is executed server-side — the UI confirms, then executes.
  agentPlan: async (message: string, context?: Record<string, unknown>) => {
    const res = await api.post<PlanAction>('/api/v1/ai/agent/plan', { message, context })
    return res.data
  },

  // Controlled AI agent: generates SQL, dry-runs it on a real sample, returns
  // before/after preview + validation for human approval before applying.
  agentTransform: async (description: string, fileId?: string) => {
    const res = await api.post<AgentResult>('/api/v1/ai/agent/transform', {
      description, file_id: fileId,
    })
    return res.data
  },

  generatePipeline: async (prompt: string, schema?: ColumnSchema[], context?: Record<string, unknown>) => {
    const res = await api.post<GeneratedPipeline>('/api/v1/ai/generate/pipeline', { prompt, schema, context })
    return res.data
  },

  generateSQL: async (prompt: string, schema: ColumnSchema[], dialect: 'duckdb' | 'postgresql' = 'duckdb') => {
    const res = await api.post<GeneratedSQL>('/api/v1/ai/generate/sql', { prompt, schema, dialect })
    return res.data
  },

  generateFilter: async (prompt: string, columns: ColumnSchema[]) => {
    const res = await api.post('/api/v1/ai/generate/filter', { prompt, columns })
    return res.data as { expression: string; columns_used: string[] }
  },

  suggestColumns: async (nodeType: string, schema: ColumnSchema[]) => {
    const res = await api.post<{ suggestions: ColumnSuggestion[] }>('/api/v1/ai/suggest/columns', {
      node_type: nodeType,
      schema,
    })
    return res.data.suggestions
  },

  suggestJoins: async (schemaLeft: ColumnSchema[], schemaRight: ColumnSchema[]) => {
    const res = await api.post<{ suggestions: JoinSuggestion[] }>('/api/v1/ai/suggest/joins', {
      schema_left: schemaLeft,
      schema_right: schemaRight,
    })
    return res.data.suggestions
  },

  suggestPipeline: async (goal: string, availableFiles: Array<{ id: string; schema: ColumnSchema[] }>) => {
    const res = await api.post('/api/v1/ai/suggest/pipeline', { goal, available_files: availableFiles })
    return res.data as { suggestion: string; reasoning: string; generate_now: boolean }
  },

  explainSQL: async (sql: string) => {
    const res = await api.post('/api/v1/ai/explain/sql', { sql })
    return res.data as { explanation: string; level: string }
  },

  explainError: async (errorMessage: string, context?: Record<string, unknown>) => {
    const res = await api.post('/api/v1/ai/explain/error', { error_message: errorMessage, context })
    return res.data as { plain_explanation: string; suggested_fix: string; severity: string }
  },

  chat: async (messages: ChatMessage[], pipelineContext?: Record<string, unknown>) => {
    const res = await api.post<ChatResponse>('/api/v1/ai/chat', {
      messages,
      pipeline_context: pipelineContext,
    })
    return res.data
  },

  getHistory: async () => {
    const res = await api.get('/api/v1/ai/history')
    return res.data
  },

  deleteHistory: async (sessionId: string) => {
    await api.delete(`/api/v1/ai/history/${sessionId}`)
  },

  getUsage: async () => {
    const res = await api.get<AIUsage>('/api/v1/ai/usage')
    return res.data
  },

  generateCode: async (prompt: string, options?: { model?: string; schema?: ColumnSchema[] }) => {
    const res = await api.post<{ code: string; language: string; tokens_used: number }>(
      '/api/v1/ai/generate/code',
      { prompt, ...options }
    )
    return res.data
  },
}
