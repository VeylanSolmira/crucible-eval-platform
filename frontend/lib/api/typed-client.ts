/**
 * Type-safe API client for Crucible Platform
 * 
 * This provides compile-time type safety for all API calls.
 * If the API structure changes, TypeScript will catch it at build time.
 */

import type {
  EvaluationRequest,
  EvaluationResponse,
  EvaluationStatus,
  QueueStatus,
  PlatformStatus,
  HealthStatus,
  ApiError
} from './types'

// Use environment variable or default to empty string for relative URLs
const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

/**
 * Type-safe fetch wrapper
 */
async function typedFetch<T>(
  url: string,
  options?: RequestInit
): Promise<{ data?: T; error?: ApiError }> {
  try {
    const response = await fetch(url, options)
    const data = await response.json()

    if (!response.ok) {
      return { error: data as ApiError }
    }

    return { data: data as T }
  } catch (error) {
    return {
      error: {
        error: 'NetworkError',
        detail: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }
}

/**
 * Crucible API client with full type safety
 */
export const crucibleApi = {
  /**
   * Submit code for evaluation
   */
  async submitEvaluation(request: EvaluationRequest) {
    return typedFetch<EvaluationResponse>(`${API_BASE}/api/eval`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
  },

  /**
   * Get evaluation status
   */
  async getEvaluationStatus(evalId: string) {
    return typedFetch<EvaluationStatus>(`${API_BASE}/api/eval-status/${evalId}`)
  },

  /**
   * Get queue status
   */
  async getQueueStatus() {
    return typedFetch<QueueStatus>(`${API_BASE}/api/queue-status`)
  },

  /**
   * Get platform status
   */
  async getPlatformStatus() {
    return typedFetch<PlatformStatus>(`${API_BASE}/api/status`)
  },

  /**
   * Health check
   */
  async getHealth() {
    return typedFetch<HealthStatus>(`${API_BASE}/api/health`)
  }
}

// Export for use in components
export type { 
  EvaluationRequest,
  EvaluationResponse,
  EvaluationStatus,
  QueueStatus,
  PlatformStatus,
  HealthStatus,
  ApiError
}