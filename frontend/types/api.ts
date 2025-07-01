// NOTE: EvaluationRequest is now imported from generated types
// See types/generated/api.ts

// API Response Types
export interface ApiResponse<T> {
  data?: T
  error?: string
  status: 'success' | 'error'
}

export interface AsyncEvaluationResponse {
  eval_id: string
  status: 'queued' | 'processing'
  message?: string
  error?: string
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

// Running Evaluation Types
export interface RunningEvaluation {
  eval_id: string
  executor_id: string
  container_id: string
  started_at: string
  timeout: number
}

export interface RunningEvaluationsResponse {
  evaluations: RunningEvaluation[]
}

export interface EvaluationLogs {
  eval_id: string
  output: string
  error: string
  is_running: boolean
  exit_code: number | null
  status?: string  // Added to match API response
  created_at?: string  // When the evaluation was created
  last_update?: string  // Last activity timestamp (including heartbeats)
  started_at?: string  // When the evaluation started
  completed_at?: string  // When the evaluation completed
  runtime_ms?: number  // Total runtime in milliseconds
  source?: string  // Whether from redis_cache or database
  container_id?: string  // Docker container ID
  executor_id?: string  // Which executor is running the evaluation
}

export interface KillEvaluationResponse {
  eval_id: string
  killed: boolean
  message?: string
}

// API response types for evaluation list endpoint
export interface EvaluationListItem {
  eval_id: string
  status: string  // API returns string, we'll validate/narrow at usage
  created_at: string
  code_preview?: string
  success?: boolean
  // Optional fields that might be in the response
  started_at?: string
  completed_at?: string
  output?: string
  error?: string
  exit_code?: number
}

export interface EvaluationsApiResponse {
  evaluations: EvaluationListItem[]
  count: number
  limit: number
  offset: number
  has_more: boolean
  error?: string
}

// Batch submission types
export interface BatchSubmissionResult {
  eval_id?: string
  error?: string
  batch_index?: number
}

export interface BatchSubmissionResponse {
  evaluations: BatchSubmissionResult[]
}