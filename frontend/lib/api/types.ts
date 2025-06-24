/**
 * Manually defined types for the Crucible API
 * 
 * These match what the API actually returns.
 * In the future, the backend should properly annotate responses
 * so these can be auto-generated.
 */

export interface EvaluationRequest {
  code: string
  language?: string
  engine?: string
  timeout?: number
}

export interface EvaluationResponse {
  eval_id: string
  status: string
  message: string
  queue_position?: number
}

export interface EvaluationStatus {
  eval_id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'timeout'
  created_at: string
  completed_at: string | null
  output: string
  error: string
  success: boolean
}

export interface QueueStatus {
  queued: number
  processing: number
  queue_length: number
  total_tasks: number
}

export interface PlatformStatus {
  platform: string
  mode: string
  services: {
    gateway: string
    queue: string
    storage: string
    executor: string
  }
  queue: QueueStatus
  storage: Record<string, any>
  version: string
}

export interface HealthStatus {
  status: string
  services: {
    gateway: boolean
    queue: boolean
    redis: boolean
    storage: boolean
    last_check: string | null
  }
  timestamp: string
}

export interface ApiError {
  error: string
  detail?: string
  path?: string
}