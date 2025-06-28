import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { appConfig } from '@/lib/config'
import type { components } from '@/types/generated/api'

// Use OpenAPI generated types
export type EvaluationRequest = components['schemas']['EvaluationRequest']
export type EvaluationResponse = components['schemas']['EvaluationResponse']
export type EvaluationStatusResponse = components['schemas']['EvaluationStatusResponse']
export type QueueStatusResponse = components['schemas']['QueueStatusResponse']
export type EvaluationStatus = components['schemas']['EvaluationStatus']

// For backwards compatibility
export type EvaluationResult = EvaluationStatusResponse

// API functions
async function submitEvaluation(request: EvaluationRequest): Promise<{ eval_id: string }> {
  console.log('[API] Submitting evaluation:', new Date().toISOString())
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
  console.log('[API] Evaluation submitted:', result.eval_id, new Date().toISOString())
  return result
}

async function fetchEvaluation(evalId: string): Promise<EvaluationStatusResponse> {
  console.log('[API] Fetching evaluation status:', evalId, new Date().toISOString())
  const response = await fetch(`${appConfig.api.baseUrl}/api/eval-status/${evalId}`)
  
  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || 'Failed to fetch evaluation')
  }

  const result = await response.json()
  console.log('[API] Evaluation status:', evalId, result.status, new Date().toISOString())
  return result
}

// React Query hooks
export function useSubmitEvaluation() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: submitEvaluation,
    onSuccess: (data) => {
      // Prefetch the evaluation data
      queryClient.prefetchQuery({
        queryKey: ['evaluation', data.eval_id],
        queryFn: () => fetchEvaluation(data.eval_id),
      })
    },
  })
}

export function useEvaluation(evalId: string | null) {
  return useQuery({
    queryKey: ['evaluation', evalId],
    queryFn: () => fetchEvaluation(evalId!),
    enabled: !!evalId,
    // Poll while evaluation is running
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 1000 // Poll every second initially
      if (data.status === 'queued' || data.status === 'running') {
        return 1000 // Continue polling every second
      }
      return false // Stop polling when completed or failed
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

// Hook for managing the full evaluation flow
export function useEvaluationFlow() {
  const submitMutation = useSubmitEvaluation()
  const [currentEvalId, setCurrentEvalId] = useState<string | null>(null)
  const evaluationQuery = useEvaluation(currentEvalId)

  const submitCode = async (code: string, language: string = 'python') => {
    try {
      const result = await submitMutation.mutateAsync({ 
        code, 
        language,
        engine: 'docker',
        timeout: 30
      })
      setCurrentEvalId(result.eval_id)
      return result.eval_id
    } catch (error) {
      console.error('Failed to submit evaluation:', error)
      throw error
    }
  }

  const reset = () => {
    setCurrentEvalId(null)
    submitMutation.reset()
  }

  const isComplete = evaluationQuery.data?.status === 'completed' || evaluationQuery.data?.status === 'failed'
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

// Hook for fetching evaluation history
export function useEvaluationHistory() {
  return useQuery({
    queryKey: ['evaluations', 'history'],
    queryFn: async () => {
      const response = await fetch(`${appConfig.api.baseUrl}/api/evaluations`)
      if (!response.ok) {
        throw new Error('Failed to fetch evaluation history')
      }
      return response.json()
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
        evalIds.map(async (evalId) => {
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
              success: false
            } as EvaluationStatusResponse
          }
        })
      )
      return results
    },
    enabled: evalIds.length > 0,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 1000
      
      // Continue polling if any evaluation is still in progress
      const hasActive = data.some(e => e.status === 'queued' || e.status === 'running')
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
      // Try batch endpoint first
      try {
        const response = await fetch(`${appConfig.api.baseUrl}/api/eval-batch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ evaluations })
        })
        
        if (response.ok) {
          const data = await response.json()
          return data.evaluations || []
        }
      } catch (error) {
        console.log('Batch endpoint not available, submitting individually')
      }
      
      // Fallback to individual submissions
      const results = []
      for (const evaluation of evaluations) {
        try {
          const response = await fetch(`${appConfig.api.baseUrl}/api/eval`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(evaluation)
          })
          
          if (!response.ok) {
            throw new Error(`Failed to submit evaluation`)
          }
          
          const result = await response.json()
          results.push(result)
        } catch (error) {
          results.push({ error: error instanceof Error ? error.message : 'Failed' })
        }
      }
      return results
    },
    onSuccess: (results) => {
      // Prefetch status for each successful submission
      results.forEach((result: any) => {
        if (result.eval_id) {
          queryClient.prefetchQuery({
            queryKey: ['evaluation', result.eval_id],
            queryFn: () => fetchEvaluation(result.eval_id),
          })
        }
      })
    }
  })
}