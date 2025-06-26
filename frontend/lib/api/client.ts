/**
 * API Client for Crucible Evaluation Platform
 * 
 * This client uses the auto-generated types from the OpenAPI specification
 * to ensure type safety and catch API contract mismatches at build time.
 */

// Import generated types from OpenAPI spec
// These types will be generated when running `npm run generate-types`
import type { paths, components } from '@/types/generated/api'

// Re-export commonly used types for convenience
export type EvaluationRequest = components['schemas']['EvaluationRequest']
export type EvaluationResponse = components['schemas']['EvaluationResponse']
export type EvaluationStatusResponse = components['schemas']['EvaluationStatusResponse']
export type QueueStatusResponse = components['schemas']['QueueStatusResponse']
export type ValidationError = components['schemas']['ValidationError']
export type HTTPValidationError = components['schemas']['HTTPValidationError']

// Create type aliases for clarity
export type EvaluationAccepted = EvaluationResponse  // Same structure
export type ApiError = HTTPValidationError

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

/**
 * Type-safe fetch wrapper that handles JSON responses
 */
async function typedFetch<T>(
  url: string,
  options?: RequestInit
): Promise<{ data?: T; error?: Error }> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    const data = await response.json()

    if (!response.ok) {
      return { error: data as Error }
    }

    return { data: data as T }
  } catch (error) {
    return {
      error: new Error(
        error instanceof Error ? error.message : 'Unknown error'
      ),
    }
  }
}

/**
 * API Client class with type-safe methods
 */
export class CrucibleAPIClient {
  private baseUrl: string

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || API_BASE_URL
  }

  /**
   * Submit an evaluation
   * Uses type-safe paths from OpenAPI spec
   */
  async submitEvaluation(
    request: paths['/api/eval']['post']['requestBody']['content']['application/json']
  ): Promise<{ 
    data?: paths['/api/eval']['post']['responses']['200']['content']['application/json']; 
    error?: Error 
  }> {
    type ResponseType = paths['/api/eval']['post']['responses']['200']['content']['application/json']
    return typedFetch<ResponseType>(
      `${this.baseUrl}/api/eval`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      }
    )
  }

  /**
   * Get evaluation status
   * Uses type-safe paths from OpenAPI spec
   */
  async getEvaluationStatus(
    evalId: string
  ): Promise<{ 
    data?: paths['/api/eval-status/{eval_id}']['get']['responses']['200']['content']['application/json']; 
    error?: Error 
  }> {
    type ResponseType = paths['/api/eval-status/{eval_id}']['get']['responses']['200']['content']['application/json']
    return typedFetch<ResponseType>(
      `${this.baseUrl}/api/eval-status/${evalId}`
    )
  }

  /**
   * Get queue status
   */
  async getQueueStatus(): Promise<{ data?: QueueStatusResponse; error?: Error }> {
    return typedFetch<QueueStatusResponse>(`${this.baseUrl}/api/queue-status`)
  }

  /**
   * Get platform health (untyped endpoint)
   */
  async getHealth(): Promise<{ data?: components['schemas']['HealthResponse']; error?: Error }> {
    return typedFetch<components['schemas']['HealthResponse']>(`${this.baseUrl}/api/health`)
  }

  /**
   * Get platform status (untyped endpoint)
   */
  async getStatus(): Promise<{ data?: components['schemas']['StatusResponse']; error?: Error }> {
    return typedFetch<components['schemas']['StatusResponse']>(`${this.baseUrl}/api/status`)
  }

  /**
   * Stream evaluation events via Server-Sent Events
   */
  streamEvents(evalId?: string): EventSource {
    const url = new URL(`${this.baseUrl}/api/events`)
    if (evalId) {
      url.searchParams.append('evalId', evalId)
    }
    return new EventSource(url.toString())
  }
}

// Create a default client instance
export const apiClient = new CrucibleAPIClient()