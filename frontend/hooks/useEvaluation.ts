import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useRef } from 'react'
import { appConfig } from '@/lib/config'
import { log } from '@/src/utils/logger'
import type { components } from '@/types/generated/api'
import type {
  RunningEvaluationsResponse,
  EvaluationLogs,
  KillEvaluationResponse,
  EvaluationsApiResponse,
} from '@/types/api'
import { isTerminalStatus, isActiveStatus } from '@/shared/generated/typescript/evaluation-status'

// Use OpenAPI generated types
export type EvaluationRequest = components['schemas']['EvaluationRequest']
export type EvaluationSubmitResponse = components['schemas']['EvaluationSubmitResponse']
export type EvaluationResponse = components['schemas']['EvaluationResponse']
export type EvaluationStatusResponse = components['schemas']['EvaluationStatusResponse']
export type QueueStatusResponse = components['schemas']['QueueStatusResponse']
export type EvaluationStatus = components['schemas']['EvaluationStatus']

// For backwards compatibility
export type EvaluationResult = EvaluationStatusResponse

// API functions
async function submitEvaluation(request: EvaluationRequest): Promise<{ eval_id: string }> {
  log.debug('Submitting evaluation')
  const response = await fetch(`${appConfig.api.baseUrl}/api/eval`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || 'Failed to submit evaluation')
  }

  const result = await response.json()
  log.debug('Evaluation submitted', result.eval_id)
  return result
}

async function fetchEvaluation(evalId: string): Promise<EvaluationResponse> {
  log.debug('Fetching evaluation details', evalId)
  const response = await fetch(`${appConfig.api.baseUrl}/api/eval/${evalId}`)

  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || 'Failed to fetch evaluation')
  }

  const result = await response.json()
  log.debug('Evaluation details', evalId, result.status)
  return result
}

// React Query hooks
export function useSubmitEvaluation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: submitEvaluation,
    onSuccess: data => {
      // Prefetch the evaluation data
      queryClient.prefetchQuery({
        queryKey: ['evaluation', data.eval_id],
        queryFn: () => fetchEvaluation(data.eval_id),
      })
    },
  })
}

export function useEvaluation(evalId: string | null) {
  const queryClient = useQueryClient()
  const previousStatusRef = useRef<string | null>(null)
  
  return useQuery({
    queryKey: ['evaluation', evalId],
    queryFn: () => fetchEvaluation(evalId!),
    enabled: !!evalId,
    // Poll while evaluation is running
    refetchInterval: query => {
      const data = query.state.data
      if (!data) return 1000 // Poll every second initially
      
      // Check for status transition
      const previousStatus = previousStatusRef.current
      if (data.status !== previousStatus) {
        // Only invalidate on transition from running -> terminal state
        if (previousStatus === 'running' && isTerminalStatus(data.status)) {
          queryClient.invalidateQueries({ queryKey: ['evaluations', 'running'] })
        }
        previousStatusRef.current = data.status
      }
      
      // Continue polling for non-terminal states
      if (isActiveStatus(data.status)) {
        return 1000 // Continue polling every second
      }
      return false // Stop polling when in terminal state
    },
    // Once complete, data never changes - keep it forever
    staleTime: Infinity,
    gcTime: Infinity,
    // Never refetch completed evaluations
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
    // Retry failed requests
    retry: (failureCount, error) => {
      // Don't retry if evaluation not found
      if (error.message.includes('404')) return false
      return failureCount < 3
    },
  })
}

// Hook for fetching running evaluations
export function useRunningEvaluations() {
  return useQuery<RunningEvaluationsResponse>({
    queryKey: ['evaluations', 'running'],
    queryFn: async () => {
      const response = await fetch(`${appConfig.api.baseUrl}/api/evaluations?status=running`)
      if (!response.ok) {
        throw new Error('Failed to fetch running evaluations')
      }
      const data: EvaluationsApiResponse = await response.json()

      // Transform evaluations to include placeholder executor info
      // TODO: Update when API returns executor info
      return {
        evaluations:
          data.evaluations?.map(ev => ({
            eval_id: ev.eval_id, // Now TypeScript will catch if this field doesn't exist!
            status: ev.status,
            created_at: ev.created_at,
            executor_id: 'unknown',
            container_id: 'unknown',
            started_at: ev.created_at || new Date().toISOString(),
            timeout: 30,
          })) || [],
      }
    },
    refetchInterval: 2000, // Poll every 2 seconds
  })
}

// Hook for updating evaluation status (admin action)
export function useUpdateEvaluationStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      evalId,
      status,
      reason,
    }: {
      evalId: string
      status: string
      reason?: string
    }) => {
      // Build URL with proper handling for relative paths
      const baseUrl = appConfig.api.baseUrl || ''
      const path = `/api/eval/${evalId}/status`
      const params = new URLSearchParams()
      params.append('status', status)
      if (reason) {
        params.append('reason', reason)
      }
      const url = `${baseUrl}${path}?${params.toString()}`

      const response = await fetch(url, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const error = await response.text()
        throw new Error(error || 'Failed to update evaluation status')
      }

      return response.json()
    },
    onSuccess: (_data, variables) => {
      // Invalidate queries to refresh the UI
      queryClient.invalidateQueries({ queryKey: ['evaluation', variables.evalId] })
      queryClient.invalidateQueries({ queryKey: ['evaluations'] })
      queryClient.invalidateQueries({ queryKey: ['evaluations', 'running'] })
    },
  })
}

// Hook for killing an evaluation
export function useKillEvaluation() {
  const queryClient = useQueryClient()

  return useMutation<KillEvaluationResponse, Error, string>({
    mutationFn: async (evalId: string) => {
      const response = await fetch(`${appConfig.api.baseUrl}/api/eval/${evalId}/kill`, {
        method: 'POST',
      })
      if (!response.ok) {
        let errorMessage = 'Failed to kill evaluation'
        try {
          const errorData = await response.json()
          errorMessage = errorData.error || errorData.detail || errorMessage
        } catch {
          // If JSON parsing fails, try to get text
          const errorText = await response.text()
          if (errorText) errorMessage = errorText
        }
        throw new Error(errorMessage)
      }
      return response.json()
    },
    onSuccess: () => {
      // Invalidate running evaluations to refresh the list
      queryClient.invalidateQueries({ queryKey: ['evaluations', 'running'] })
    },
  })
}

// Hook for streaming evaluation logs
export function useEvaluationLogs(evalId: string | null) {
  const queryClient = useQueryClient()
  const wasRunningRef = useRef<boolean | null>(null)
  
  return useQuery<EvaluationLogs | null>({
    queryKey: ['evaluation', evalId, 'logs'],
    queryFn: async () => {
      if (!evalId) return null

      const response = await fetch(`${appConfig.api.baseUrl}/api/eval/${evalId}/logs`)
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Evaluation not running')
        }
        throw new Error('Failed to fetch logs')
      }
      return response.json()
    },
    enabled: !!evalId,
    refetchInterval: query => {
      // Continue polling if evaluation is running
      const data = query.state.data
      if (!data || data.is_running) {
        wasRunningRef.current = true
        return 1000 // Poll every second
      }
      // When evaluation completes, invalidate running evaluations ONCE
      if (wasRunningRef.current === true) {
        queryClient.invalidateQueries({ queryKey: ['evaluations', 'running'] })
        queryClient.invalidateQueries({ queryKey: ['evaluations', 'history'] })
        wasRunningRef.current = false
      }
      return false // Stop polling when not running
    },
    retry: false, // Don't retry 404s
  })
}

// Hook for managing the full evaluation flow
export function useEvaluationFlow() {
  const submitMutation = useSubmitEvaluation()
  const [currentEvalId, setCurrentEvalId] = useState<string | null>(null)
  const evaluationQuery = useEvaluation(currentEvalId)

  const submitCode = async (
    code: string,
    language: string = 'python',
    priority: boolean = false
  ) => {
    try {
      const result = await submitMutation.mutateAsync({
        code,
        language,
        engine: 'docker',
        timeout: 30,
        priority,
      })
      setCurrentEvalId(result.eval_id)
      return result.eval_id
    } catch (error) {
      log.error('Failed to submit evaluation:', error)
      throw error
    }
  }

  const reset = () => {
    setCurrentEvalId(null)
    submitMutation.reset()
  }

  const isComplete = evaluationQuery.data?.status 
    ? isTerminalStatus(evaluationQuery.data.status) 
    : false
  const isPolling = evaluationQuery.isFetching && !isComplete

  return {
    submitCode,
    reset,
    isSubmitting: submitMutation.isPending,
    submitError: submitMutation.error,
    evalId: currentEvalId,
    evaluation: evaluationQuery.data,
    isPolling,
    evaluationError: evaluationQuery.error,
    isComplete,
  }
}

// Hook for fetching evaluation history with pagination
export function useEvaluationHistory(page: number = 0, limit: number = 100, status?: string) {
  return useQuery({
    queryKey: ['evaluations', 'history', page, limit, status],
    queryFn: async () => {
      const offset = page * limit
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      })
      if (status && status !== 'all') {
        params.append('status', status)
      }
      
      const response = await fetch(
        `${appConfig.api.baseUrl}/api/evaluations?${params}`
      )
      if (!response.ok) {
        throw new Error('Failed to fetch evaluation history')
      }
      const data: EvaluationsApiResponse = await response.json()
      // Return the full response to get both evaluations and metadata
      return {
        evaluations: data.evaluations || [],
        total: data.count || data.evaluations?.length || 0,
        hasMore: data.has_more || false,
      }
    },
    staleTime: 5 * 60 * 1000, // Consider data stale after 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  })
}

// Hook for fetching evaluation output with pagination
export function useEvaluationOutput(evalId: string | null, lastLine: number = 0) {
  const queryClient = useQueryClient()

  return useQuery({
    queryKey: ['evaluation', evalId, 'output', lastLine],
    queryFn: async () => {
      const response = await fetch(
        `${appConfig.api.baseUrl}/api/eval/${evalId}/output?last_line=${lastLine}`
      )
      if (!response.ok) {
        throw new Error('Failed to fetch evaluation output')
      }
      return response.json()
    },
    enabled: !!evalId,
    // Poll for new output while running
    refetchInterval: () => {
      const evaluation = queryClient.getQueryData<EvaluationResult>(['evaluation', evalId])
      if (evaluation?.status === 'running') {
        return 500 // Poll every 500ms for output
      }
      return false
    },
  })
}

// Hook for polling multiple evaluations
export function useMultipleEvaluations(evalIds: string[]) {
  return useQuery({
    queryKey: ['evaluations', 'multiple', evalIds],
    queryFn: async () => {
      if (evalIds.length === 0) return []

      const results = await Promise.all(
        evalIds.map(async evalId => {
          try {
            const evaluation = await fetchEvaluation(evalId)
            return evaluation
          } catch (error) {
            // Return a failed evaluation with error details
            return {
              eval_id: evalId,
              status: 'failed' as const,
              error: error instanceof Error ? error.message : 'Failed to fetch',
              output: '',
              success: false,
            } as EvaluationStatusResponse
          }
        })
      )
      return results
    },
    enabled: evalIds.length > 0,
    refetchInterval: query => {
      const data = query.state.data
      if (!data) return 1000

      // Continue polling if any evaluation is still in progress
      const hasActive = data.some(e => isActiveStatus(e.status))
      return hasActive ? 1000 : false
    },
  })
}

// Hook for fetching queue status
export function useQueueStatus() {
  return useQuery({
    queryKey: ['queue', 'status'],
    queryFn: async (): Promise<QueueStatusResponse> => {
      const response = await fetch(`${appConfig.api.baseUrl}/api/queue-status`)
      if (!response.ok) {
        throw new Error('Failed to fetch queue status')
      }
      return response.json()
    },
    refetchInterval: 2000, // Poll every 2 seconds
    staleTime: 1000, // Consider stale after 1 second
  })
}

// Hook for batch submission
export function useBatchSubmit() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (evaluations: EvaluationRequest[]) => {
      // Use the batch endpoint which handles rate limiting server-side
      const response = await fetch(`${appConfig.api.baseUrl}/api/eval-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          evaluations: evaluations.map(evaluation => ({
            code: evaluation.code,
            language: evaluation.language || 'python',
            engine: evaluation.engine || 'docker',
            timeout: evaluation.timeout || 30,
            priority: evaluation.priority || false,
          }))
        }),
      })
      
      // Accept both 200 (old behavior) and 202 (new async behavior)
      if (!response.ok && response.status !== 202) {
        const error = await response.text()
        throw new Error(error || `Batch submission failed with status ${response.status}`)
      }
      
      const data = await response.json()
      
      // Transform batch response to match expected format
      // The API returns { evaluations: [...], total: N, queued: N, failed: N }
      return data.evaluations || []
    },
    onSuccess: (results: EvaluationResponse[]) => {
      // Prefetch status for each successful submission
      results.forEach(result => {
        if (result.eval_id) {
          queryClient.prefetchQuery({
            queryKey: ['evaluation', result.eval_id],
            queryFn: () => fetchEvaluation(result.eval_id),
          })
        }
      })
    },
  })
}
