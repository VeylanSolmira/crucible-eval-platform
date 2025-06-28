/**
 * React hooks for interacting with the Crucible API
 * These hooks provide type-safe API interactions with built-in state management
 */

import { useState, useEffect, useCallback } from 'react'
import { apiClient, type EvaluationRequest, type EvaluationStatusResponse, type QueueStatusResponse } from './client'

/**
 * Hook for submitting and tracking evaluations
 */
export function useEvaluation() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submitEvaluation = useCallback(async (request: EvaluationRequest) => {
    setIsSubmitting(true)
    setError(null)

    const { data, error } = await apiClient.submitEvaluation(request)

    if (error) {
      setError(error.message)
      setIsSubmitting(false)
      return null
    }

    setIsSubmitting(false)
    return data
  }, [])

  return {
    submitEvaluation,
    isSubmitting,
    error,
  }
}

/**
 * Hook for tracking evaluation status with polling
 */
export function useEvaluationStatus(evalId: string | null, pollInterval = 1000) {
  const [status, setStatus] = useState<EvaluationStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!evalId) return

    let intervalId: NodeJS.Timeout

    const fetchStatus = async () => {
      setIsLoading(true)
      const { data, error } = await apiClient.getEvaluationStatus(evalId)

      if (error) {
        setError(error.message)
        setIsLoading(false)
        return
      }

      setStatus(data || null)
      setIsLoading(false)

      // Stop polling if evaluation is complete
      if (data?.status === 'completed' || data?.status === 'failed') {
        clearInterval(intervalId)
      }
    }

    // Initial fetch
    fetchStatus()

    // Set up polling
    intervalId = setInterval(fetchStatus, pollInterval)

    return () => clearInterval(intervalId)
  }, [evalId, pollInterval])

  return {
    status,
    isLoading,
    error,
  }
}

/**
 * Hook for monitoring queue status
 */
export function useQueueStatus(pollInterval = 5000) {
  const [queueStatus, setQueueStatus] = useState<QueueStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchQueueStatus = async () => {
      setIsLoading(true)
      const { data, error } = await apiClient.getQueueStatus()

      if (error) {
        setError(error.message)
        setIsLoading(false)
        return
      }

      setQueueStatus(data || null)
      setIsLoading(false)
    }

    // Initial fetch
    fetchQueueStatus()

    // Set up polling
    const intervalId = setInterval(fetchQueueStatus, pollInterval)

    return () => clearInterval(intervalId)
  }, [pollInterval])

  return {
    queueStatus,
    isLoading,
    error,
  }
}

/**
 * Hook for streaming evaluation events
 */
export function useEvaluationStream(evalId: string | null) {
  const [events, setEvents] = useState<Array<{ timestamp: Date; data: any }>>([])
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    if (!evalId) return

    const eventSource = apiClient.streamEvents(evalId)

    eventSource.onopen = () => {
      setIsConnected(true)
    }

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setEvents((prev) => [...prev, { timestamp: new Date(), data }])
    }

    eventSource.onerror = () => {
      setIsConnected(false)
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [evalId])

  return {
    events,
    isConnected,
  }
}