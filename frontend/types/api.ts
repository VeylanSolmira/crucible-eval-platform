// API Request Types
export interface EvaluationRequest {
  code: string
  engine?: 'direct' | 'docker' | 'gvisor'
  timeout?: number
}

// API Response Types
export interface ApiResponse<T> {
  data?: T
  error?: string
  status: 'success' | 'error'
}

export interface EvaluationResult {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'timeout'
  output?: string
  error?: string
  executionTime?: number
  queueTime?: number
}

export interface QueueStatus {
  pending: number
  running: number
  completed: number
  workers: number
}

export interface PlatformStatus {
  status: 'healthy' | 'degraded' | 'down'
  version: string
  engines: string[]
  features: Record<string, boolean>
}

// WebSocket Event Types
export interface EvaluationEvent {
  type: 'status_update' | 'output_chunk' | 'completed' | 'error'
  evaluationId: string
  data: {
    status?: EvaluationResult['status']
    output?: string
    error?: string
  }
}