'use client'

import { useState, useCallback, useEffect } from 'react'
import Link from 'next/link'
import { CodeEditorWithTemplates } from '../src/components/CodeEditorWithTemplates'
import { ExecutionConfig, type ExecutionConfigData } from '../src/components/ExecutionConfig'
import { Executions } from '../src/components/RunningEvaluations'
import { useEvaluationFlow, useQueueStatus, useBatchSubmit } from '../hooks/useEvaluation'
import type { EvaluationRequest } from '../hooks/useEvaluation'
import type { BatchSubmissionResult } from '../types/api'

interface EventMessage {
  type: string
  data: Record<string, unknown>
  timestamp: string
}

export default function ResearcherUI() {
  // State
  const [code, setCode] = useState('')
  const [events, setEvents] = useState<EventMessage[]>([])
  const [batchCount, setBatchCount] = useState<number>(5)
  const [showBatchDialog, setShowBatchDialog] = useState(false)
  // Removed selectedRunningEvalId - now handled inside Executions component

  // Execution config
  const [execConfig, setExecConfig] = useState<ExecutionConfigData>({
    timeout: 30,
    memoryLimit: 512,
    pythonVersion: '3.11',
    priority: false,
  })

  // React Query hooks
  const {
    submitCode,
    isSubmitting,
    submitError,
    evalId,
    evaluation,
    isPolling,
    evaluationError: _evaluationError,
    isComplete,
  } = useEvaluationFlow()

  const { data: queueStatus } = useQueueStatus()
  const batchSubmit = useBatchSubmit()

  // Track recently submitted evaluation IDs for UI feedback
  const [recentEvalIds, setRecentEvalIds] = useState<string[]>([])

  // Event tracking
  const addEvent = useCallback((type: string, data: Record<string, unknown>) => {
    const event: EventMessage = {
      type,
      data,
      timestamp: new Date().toLocaleTimeString(),
    }
    setEvents(prev => [...prev.slice(-50), event]) // Keep last 50 events
  }, [])

  // Submit code for evaluation
  const handleSubmit = async () => {
    try {
      addEvent('submission', {
        type: 'single',
        code: code.substring(0, 50) + '...',
      })
      const newEvalId = await submitCode(code, 'python', execConfig.priority)
      // Track the new evaluation ID
      if (newEvalId) {
        setRecentEvalIds(prev => [...prev, newEvalId])
        addEvent('evaluation_submitted', { id: newEvalId })
      }
    } catch (error) {
      addEvent('error', {
        message: error instanceof Error ? error.message : 'Failed to submit evaluation',
      })
    }
  }

  // Kill execution is now handled inside Executions component

  // Submit multiple evaluations
  const handleBatchSubmit = async (count: number) => {
    if (!code.trim()) {
      addEvent('error', { message: 'No code to submit' })
      return
    }
    
    try {
      addEvent('submission', { type: 'batch', count })

      // Prepare batch evaluations - all with the same code from editor
      const evaluations: EvaluationRequest[] = Array.from({ length: count }, () => ({
        code: code,
        language: 'python',
        engine: 'docker',
        timeout: execConfig.timeout,
        priority: execConfig.priority,
      }))

      const results = (await batchSubmit.mutateAsync(evaluations)) as BatchSubmissionResult[]

      // Extract eval IDs and add to recent submissions
      const evalIds = results.filter(r => r.eval_id).map(r => r.eval_id as string)
      setRecentEvalIds(prev => [...prev, ...evalIds])

      results.forEach((result, index) => {
        if (result.error) {
          addEvent('error', { batch_index: index + 1, message: result.error })
        } else if (result.eval_id) {
          addEvent('evaluation_submitted', {
            id: result.eval_id,
            batch_index: index + 1,
          })
        }
      })
    } catch (error) {
      addEvent('error', {
        message: error instanceof Error ? error.message : 'Failed to submit batch',
      })
    }
  }

  // Track evaluation status changes
  useEffect(() => {
    if (evaluation) {
      addEvent('status_change', { id: evalId, status: evaluation.status })

      if (isComplete) {
        addEvent('evaluation_complete', {
          id: evalId,
          status: evaluation.status,
        })
      }
    }
  }, [evaluation, evalId, isComplete, addEvent])

  // Track polling activity
  useEffect(() => {
    if (isPolling && evalId) {
      addEvent('polling', {
        id: evalId,
        evaluation_status: evaluation?.status || 'unknown',
      })
    }
  }, [isPolling, evalId, evaluation?.status, addEvent])

  // Removed auto-scroll to prevent focus stealing

  const isRunning = isPolling && !isComplete

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">⚡ Crucible Research Platform</h1>
              <p className="text-sm text-gray-600 mt-1">
                Professional Python evaluation environment for AI safety research
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/docs"
                className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700"
              >
                📚 Documentation
              </Link>
              <a
                href="/slides"
                className="px-4 py-2 bg-purple-600 text-white text-sm rounded-md hover:bg-purple-700"
              >
                Platform Slides
              </a>
              <a
                href="/storage"
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
              >
                Storage Explorer
              </a>
              <a
                href="/flower/"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-orange-600 text-white text-sm rounded-md hover:bg-orange-700"
              >
                🌻 Flower Dashboard
              </a>
              <div className="text-sm text-gray-500">v2.0.0</div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Top Row - Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Queue Status */}
          {queueStatus && (
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Queue Status</h3>
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-yellow-400 rounded-full mr-2"></div>
                    <span className="text-xs text-gray-600">Pending:</span>
                    <span className="ml-1 font-semibold text-sm">{queueStatus.queued}</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-blue-400 rounded-full mr-2"></div>
                    <span className="text-xs text-gray-600">Running:</span>
                    <span className="ml-1 font-semibold text-sm">{queueStatus.processing}</span>
                  </div>
                </div>
                <div className="flex items-center pt-1 border-t border-gray-100">
                  <div className="w-2 h-2 bg-purple-400 rounded-full mr-2"></div>
                  <span className="text-xs text-gray-600">Your Active:</span>
                  <span className="ml-1 font-semibold text-sm">{isRunning ? 1 : 0}</span>
                </div>
              </div>
            </div>
          )}

          {/* Platform Status */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Platform Status</h3>
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-gray-600">Status:</span>
                <span className="font-medium text-green-600">healthy</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-600">Engine:</span>
                <span className="font-medium text-gray-900">Docker</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-600">Using:</span>
                <span className="font-medium text-gray-900">React Query</span>
              </div>
            </div>
          </div>

        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column - Code Editor Only */}
          <div className="space-y-6">
            {/* Code Editor */}
            <CodeEditorWithTemplates
              value={code}
              onChange={setCode}
              onSubmit={() => void handleSubmit()}
              loading={isSubmitting || isRunning}
            />
          </div>

          {/* Right Column - Config & Events */}
          <div className="space-y-6">
            {/* Submit Error Display */}
            {submitError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="text-sm font-medium text-red-800 mb-1">Submission Error</h3>
                <p className="text-sm text-red-700">{submitError.message}</p>
              </div>
            )}

            {/* Execution Config */}
            <ExecutionConfig
              config={execConfig}
              onChange={setExecConfig}
              disabled={isSubmitting || isRunning}
            />

            {/* Event Stream */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4 text-gray-900">Event Stream</h2>
              <div className="bg-gray-900 rounded-md p-4 h-64 overflow-y-auto font-mono text-xs text-gray-100">
                {events.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">No events yet...</div>
                ) : (
                  <div className="space-y-1">
                    {events.map((event, idx) => (
                      <div key={idx} className="flex">
                        <span className="text-gray-400 mr-2">{event.timestamp}</span>
                        <span
                          className={`font-medium ${
                            event.type === 'error'
                              ? 'text-red-400'
                              : event.type === 'submission'
                                ? 'text-blue-400'
                                : event.type === 'evaluation_complete'
                                  ? 'text-green-400'
                                  : 'text-gray-300'
                          }`}
                        >
                          [{event.type}]
                        </span>
                        <span className="ml-2 text-gray-300">{JSON.stringify(event.data)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Unified Executions View */}
        <div className="mt-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Executions</h2>
          <Executions recentEvalIds={recentEvalIds} />
        </div>
      </div>
    </div>
  )
}
