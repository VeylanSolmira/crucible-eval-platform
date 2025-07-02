import { useQuery } from '@tanstack/react-query'
import { appConfig } from '@/lib/config'
import { log } from '@/src/utils/logger'
import type { RunningEvaluationsResponse } from '@/types/api'

/**
 * Hook for fetching running evaluations
 * Polls the API every 2 seconds for updates
 */
export function useRunningEvaluations() {
  return useQuery<RunningEvaluationsResponse>({
    queryKey: ['evaluations', 'running'],
    queryFn: async () => {
      log.debug('Fetching running evaluations')
      const response = await fetch(`${appConfig.api.baseUrl}/api/evaluations?status=running`)
      if (!response.ok) {
        throw new Error('Failed to fetch running evaluations')
      }
      const data = await response.json()

      // Transform evaluations to match expected format
      const runningEvals =
        data.evaluations?.map((ev: any) => ({
          eval_id: ev.id || ev.eval_id,
          status: ev.status,
          created_at: ev.created_at,
          executor_id: ev.executor_id || 'unknown',
          container_id: ev.container_id || 'unknown',
          started_at: ev.started_at || ev.created_at || new Date().toISOString(),
          timeout: ev.timeout || 30,
        })) || []

      return { evaluations: runningEvals }
    },
    refetchInterval: 2000, // Poll every 2 seconds
  })
}
