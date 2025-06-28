'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { CodeEditorWithTemplates } from '../src/components/CodeEditorWithTemplates'
import { ExecutionConfig, ExecutionConfigData } from '../src/components/ExecutionConfig'
import { ExecutionMonitor } from '../src/components/ExecutionMonitor'
import { ErrorDisplay } from '../src/components/ErrorDisplay'
import { useEvaluationFlow, useQueueStatus, useBatchSubmit, useMultipleEvaluations } from '../hooks/useEvaluation'
import type { EvaluationRequest, EvaluationStatusResponse } from '../hooks/useEvaluation'

interface EventMessage {
  type: string
  data: any
  timestamp: string
}

// Use the generated type from OpenAPI
type EvaluationResultDisplay = EvaluationStatusResponse

export default function ResearcherUI() {
  // State
  const [code, setCode] = useState('')
  const [events, setEvents] = useState<EventMessage[]>([])
  const eventsEndRef = useRef<HTMLDivElement>(null)
  
  // Execution config
  const [execConfig, setExecConfig] = useState<ExecutionConfigData>({
    timeout: 30,
    memoryLimit: 512,
    pythonVersion: '3.11',
  })

  // React Query hooks
  const {
    submitCode,
    reset,
    isSubmitting,
    submitError,
    evalId,
    evaluation,
    isPolling,
    evaluationError: _evaluationError,
    isComplete
  } = useEvaluationFlow()

  const { data: queueStatus } = useQueueStatus()
  const batchSubmit = useBatchSubmit()
  const [batchResults, setBatchResults] = useState<any[]>([])
  const [batchEvalIds, setBatchEvalIds] = useState<string[]>([])
  const { data: batchEvaluations } = useMultipleEvaluations(batchEvalIds)

  // Event tracking
  const addEvent = useCallback((type: string, data: any) => {
    const event: EventMessage = {
      type,
      data,
      timestamp: new Date().toLocaleTimeString()
    }
    setEvents(prev => [...prev.slice(-50), event]) // Keep last 50 events
  }, [])

  // Submit code for evaluation
  const handleSubmit = async () => {
    try {
      addEvent('submission', { type: 'single', code: code.substring(0, 50) + '...' })
      await submitCode(code, 'python')
    } catch (error) {
      addEvent('error', { message: error instanceof Error ? error.message : 'Failed to submit evaluation' })
    }
  }

  // Kill execution
  const handleKillExecution = async () => {
    if (!evalId) return
    
    try {
      // TODO: Implement kill endpoint
      console.log('Kill execution:', evalId)
      reset()
    } catch (error) {
      console.error('Failed to kill execution:', error)
    }
  }

  // Jump to line in editor
  const handleLineClick = (lineNumber: number) => {
    // TODO: Implement line jumping in Monaco editor
    console.log('Jump to line:', lineNumber)
  }

  // Submit multiple evaluations
  const handleBatchSubmit = async () => {
    try {
      addEvent('submission', { type: 'batch', count: 5 })
      
      // Prepare batch evaluations
      const evaluations: EvaluationRequest[] = Array.from({ length: 5 }, (_, i) => ({
        code: `# Evaluation ${i + 1}\nprint(f"This is evaluation ${i + 1}")\nimport time\ntime.sleep(${Math.random() * 2})`,
        language: 'python',
        engine: 'docker',
        timeout: 30,
      }))
      
      const results = await batchSubmit.mutateAsync(evaluations)
      setBatchResults(results)
      
      // Extract eval IDs for polling
      const evalIds = results
        .filter((r: any) => r.eval_id)
        .map((r: any) => r.eval_id)
      setBatchEvalIds(evalIds)
      
      results.forEach((result: any, index: number) => {
        if (result.error) {
          addEvent('error', { batch_index: index + 1, message: result.error })
        } else {
          addEvent('evaluation_submitted', { 
            id: result.eval_id, 
            batch_index: index + 1 
          })
        }
      })
    } catch (error) {
      addEvent('error', { message: error instanceof Error ? error.message : 'Failed to submit batch' })
    }
  }

  // Track evaluation status changes
  useEffect(() => {
    if (evaluation) {
      addEvent('status_change', { id: evalId, status: evaluation.status })
      
      if (isComplete) {
        addEvent('evaluation_complete', { id: evalId, status: evaluation.status })
      }
    }
  }, [evaluation?.status, evalId, isComplete, addEvent])

  // Track polling activity
  useEffect(() => {
    if (isPolling && evalId) {
      addEvent('polling', { id: evalId, evaluation_status: evaluation?.status || 'unknown' })
    }
  }, [isPolling, evalId, evaluation?.status, addEvent])

  // Auto-scroll events
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  // Use evaluation directly since it matches our display type
  const result: EvaluationResultDisplay | null = evaluation || null

  const isRunning = isPolling && !isComplete

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                ⚡ Crucible Research Platform
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Professional Python evaluation environment for AI safety research
              </p>
            </div>
            <div className="flex items-center gap-4">
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
              <div className="text-sm text-gray-500">
                v2.0.0
              </div>
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

          {/* Batch Testing */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Batch Testing</h3>
            <button
              onClick={handleBatchSubmit}
              disabled={batchSubmit.isPending}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm font-medium"
            >
              {batchSubmit.isPending ? 'Submitting...' : 'Submit 5 Test Evaluations'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column - Code Editor & Config */}
          <div className="space-y-6">
            {/* Code Editor */}
            <CodeEditorWithTemplates
              value={code}
              onChange={setCode}
              onSubmit={handleSubmit}
              loading={isSubmitting || isRunning}
            />

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
                        <span className={`font-medium ${
                          event.type === 'error' ? 'text-red-400' :
                          event.type === 'submission' ? 'text-blue-400' :
                          event.type === 'evaluation_complete' ? 'text-green-400' :
                          'text-gray-300'
                        }`}>
                          [{event.type}]
                        </span>
                        <span className="ml-2 text-gray-300">
                          {JSON.stringify(event.data)}
                        </span>
                      </div>
                    ))}
                    <div ref={eventsEndRef} />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column - Monitoring & Results */}
          <div className="space-y-6">
            {/* Execution Monitor */}
            <ExecutionMonitor
              evalId={evalId}
              isRunning={isRunning}
              onKill={handleKillExecution}
            />

            {/* Submit Error Display */}
            {submitError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="text-sm font-medium text-red-800 mb-1">Submission Error</h3>
                <p className="text-sm text-red-700">{submitError.message}</p>
              </div>
            )}

            {/* Results / Error Display */}
            {result && (
              <>
                {result.status === 'completed' && result.output && (
                  <div className="bg-white rounded-lg shadow-sm p-6">
                    <h2 className="text-lg font-semibold mb-4 text-gray-900">
                      Execution Results
                    </h2>
                    <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-sm overflow-auto">
                      {result.output}
                    </pre>
                  </div>
                )}

                {result.status === 'failed' && result.error && (
                  <ErrorDisplay
                    error={result.error}
                    code={code}
                    onLineClick={handleLineClick}
                  />
                )}
              </>
            )}

            {/* Batch Results */}
            {batchResults.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold mb-4 text-gray-900">
                  Batch Results ({batchResults.length})
                </h2>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {batchResults.map((result, index) => {
                    // Find the current status from polling data
                    const currentEval = batchEvaluations?.find(e => e.eval_id === result.eval_id)
                    const status = currentEval?.status || 'queued'
                    
                    return (
                      <div key={index} className="p-3 border border-gray-200 rounded-md">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-sm">Evaluation {index + 1}</span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            status === 'completed' ? 'bg-green-100 text-green-800' :
                            status === 'failed' ? 'bg-red-100 text-red-800' :
                            status === 'running' ? 'bg-blue-100 text-blue-800' :
                            status === 'queued' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {status.toUpperCase()}
                          </span>
                        </div>
                        {result.error ? (
                          <p className="text-sm text-red-600">{result.error}</p>
                        ) : (
                          <>
                            <p className="text-sm text-gray-600 font-mono">ID: {result.eval_id}</p>
                            {currentEval?.status === 'completed' && currentEval.output && (
                              <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-x-auto font-mono">
                                {currentEval.output}
                              </pre>
                            )}
                            {currentEval?.status === 'failed' && currentEval.error && (
                              <pre className="mt-2 p-2 bg-red-50 text-red-700 rounded text-xs overflow-x-auto font-mono">
                                {currentEval.error}
                              </pre>
                            )}
                          </>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}