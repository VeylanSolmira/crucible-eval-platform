'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { CodeEditorWithTemplates } from '../../src/components/CodeEditorWithTemplates'
import { ExecutionConfig, ExecutionConfigData } from '../../src/components/ExecutionConfig'
import { ExecutionMonitor } from '../../src/components/ExecutionMonitor'
import { ErrorDisplay } from '../../src/components/ErrorDisplay'
import { smartApi } from '../../src/utils/smartApiClient'
import type { components } from '@/types/generated/api'

// Type definitions
type EvaluationRequest = components['schemas']['EvaluationRequest']
type EvaluationResponse = components['schemas']['EvaluationResponse']
type EvaluationStatusResponse = components['schemas']['EvaluationStatusResponse']
type QueueStatusResponse = components['schemas']['QueueStatusResponse']

interface EvaluationResult {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'error'
  output?: string
  error?: string
  startTime?: number
  endTime?: number
}

interface QueueStatus {
  pending: number
  running: number
  completed: number
  failed: number
}

interface PlatformStatus {
  platform: string
  status: string
  engine: string
  version: string
  uptime: number
}

interface EventMessage {
  type: string
  data: any
  timestamp: string
}

export default function ResearcherUI() {
  // State
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentEvalId, setCurrentEvalId] = useState<string | null>(null)
  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  
  // Additional state from original UI
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null)
  const [platformStatus, setPlatformStatus] = useState<PlatformStatus | null>(null)
  const [events, setEvents] = useState<EventMessage[]>([])
  const [multipleResults, setMultipleResults] = useState<Map<string, EvaluationResult>>(new Map())
  const [activeEvaluations, setActiveEvaluations] = useState<Set<string>>(new Set())
  const eventsEndRef = useRef<HTMLDivElement>(null)
  
  // Execution config
  const [execConfig, setExecConfig] = useState<ExecutionConfigData>({
    timeout: 30,
    memoryLimit: 512,
    pythonVersion: '3.11',
  })

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || ''

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
  const submitCode = async () => {
    setLoading(true)
    setResult(null)
    setIsRunning(true)
    setMultipleResults(new Map()) // Clear batch results
    
    try {
      addEvent('submission', { type: 'single', code: code.substring(0, 50) + '...' })
      await fetchQueueStatus()
      
      const request: EvaluationRequest = {
        code,
        language: 'python',
        engine: 'docker',
        timeout: execConfig.timeout,
      }
      
      const response = await fetch(`${apiUrl}/api/eval`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`)
      }

      const data: EvaluationResponse = await response.json()
      setCurrentEvalId(data.eval_id)
      
      addEvent('evaluation_submitted', { id: data.eval_id, status: data.status })
      
      // Start polling for results
      pollEvaluationStatus(data.eval_id)
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to evaluate code'
      setResult({
        id: 'error',
        status: 'error',
        error: errorMessage
      })
      setIsRunning(false)
      addEvent('error', { message: errorMessage })
    } finally {
      setLoading(false)
    }
  }

  // Poll for evaluation status
  const pollEvaluationStatus = useCallback(async (evalId: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/eval-status/${evalId}`)
        if (!response.ok) {
          throw new Error('Failed to fetch status')
        }
        
        const data: EvaluationStatusResponse = await response.json()
        
        const evalResult: EvaluationResult = {
          id: data.eval_id || evalId,
          status: data.status as EvaluationResult['status'],
          output: data.output || '',
          error: data.error || ''
        }
        
        setResult(evalResult)
        
        // Add status change event
        if (evalResult.status !== result?.status) {
          addEvent('status_change', { id: evalId, status: evalResult.status })
        }
        
        // Continue polling if still running
        if (data.status === 'queued' || data.status === 'running') {
          setActiveEvaluations(prev => new Set(prev).add(evalId))
          setTimeout(poll, 1000)
        } else {
          setIsRunning(false)
          setActiveEvaluations(prev => {
            const next = new Set(prev)
            next.delete(evalId)
            return next
          })
          addEvent('evaluation_complete', { id: evalId, status: evalResult.status })
          await fetchQueueStatus()
        }
      } catch (error) {
        console.error('Polling error:', error)
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch evaluation status'
        setResult({
          id: evalId,
          status: 'error',
          error: `Polling failed: ${errorMessage}. Is the API running?`
        })
        setIsRunning(false)
        setActiveEvaluations(prev => {
          const next = new Set(prev)
          next.delete(evalId)
          return next
        })
        addEvent('error', { id: evalId, message: 'Polling failed' })
      }
    }
    
    // Start polling
    poll()
  }, [apiUrl])

  // Kill execution
  const handleKillExecution = async () => {
    if (!currentEvalId) return
    
    try {
      // TODO: Implement kill endpoint
      console.log('Kill execution:', currentEvalId)
      setIsRunning(false)
    } catch (error) {
      console.error('Failed to kill execution:', error)
    }
  }

  // Jump to line in editor
  const handleLineClick = (lineNumber: number) => {
    // TODO: Implement line jumping in Monaco editor
    console.log('Jump to line:', lineNumber)
  }

  // Fetch queue status
  const fetchQueueStatus = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/queue-status`)
      if (response.ok) {
        const data: QueueStatusResponse = await response.json()
        setQueueStatus({
          pending: data.queued || 0,
          running: data.processing || 0,
          completed: 0, // Not provided by API
          failed: 0 // Not provided by API
        })
      }
    } catch (error) {
      console.error('Failed to fetch queue status:', error)
    }
  }

  // Fetch platform status
  const fetchPlatformStatus = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/status`)
      if (response.ok) {
        const data = await response.json()
        setPlatformStatus({
          platform: 'Crucible Research Platform',
          status: data.platform === 'healthy' ? 'healthy' : 'unhealthy',
          engine: data.engine || 'Docker (Containerized - Network isolated)',
          version: data.version || '2.0.0',
          uptime: data.uptime || 0
        })
      }
    } catch (error) {
      console.error('Failed to fetch platform status:', error)
    }
  }

  // Submit multiple evaluations for testing
  const submitMultiple = async () => {
    setLoading(true)
    setResult(null)
    setMultipleResults(new Map())
    
    try {
      addEvent('submission', { type: 'batch', count: 5 })
      await fetchQueueStatus()
      
      // Prepare batch evaluations
      const evaluations = Array.from({ length: 5 }, (_, i) => ({
        code: `# Evaluation ${i + 1}\nprint(f"This is evaluation ${i + 1}")\nimport time\ntime.sleep(${Math.random() * 2})`,
        options: { timeout: execConfig.timeout }
      }))
      
      // Submit using smart API client (handles rate limiting automatically)
      const results = await smartApi.submitBatch(evaluations)
      
      // Process results
      const resultsMap = new Map<string, EvaluationResult>()
      results.forEach((result, index) => {
        if (result.error) {
          const errorId = `error-${index}`
          resultsMap.set(errorId, {
            id: errorId,
            status: 'error',
            error: result.error
          })
          addEvent('error', { batch_index: index + 1, message: result.error })
        } else {
          const evalId = result.eval_id
          const evalResult: EvaluationResult = {
            id: evalId,
            status: 'queued',
            output: ''
          }
          resultsMap.set(evalId, evalResult)
          
          // Poll for each result (also rate-limited)
          pollBatchEvaluationStatus(evalId, resultsMap)
          
          addEvent('evaluation_submitted', { 
            id: evalId, 
            batch_index: index + 1 
          })
        }
      })
      
      setMultipleResults(resultsMap)
      
      // Show API stats in event log
      const stats = smartApi.getStats()
      addEvent('api_stats', stats)
      
      await fetchQueueStatus()
    } catch (error) {
      addEvent('error', { message: error instanceof Error ? error.message : 'Failed to submit evaluations' })
    } finally {
      setLoading(false)
    }
  }

  // Poll batch evaluation status
  const pollBatchEvaluationStatus = useCallback(async (evalId: string, resultsMap: Map<string, EvaluationResult>) => {
    const poll = async () => {
      try {
        const data: EvaluationStatusResponse = await smartApi.checkStatus(evalId)
        
        const evalResult: EvaluationResult = {
          id: data.eval_id || evalId,
          status: data.status as EvaluationResult['status'],
          output: data.output || '',
          error: data.error || ''
        }
        
        resultsMap.set(evalId, evalResult)
        setMultipleResults(new Map(resultsMap))
        
        // Track active evaluations
        if (data.status === 'queued' || data.status === 'running') {
          setActiveEvaluations(prev => new Set(prev).add(evalId))
          setTimeout(poll, 1000)
        } else {
          setActiveEvaluations(prev => {
            const next = new Set(prev)
            next.delete(evalId)
            return next
          })
          await fetchQueueStatus()
        }
      } catch (error) {
        console.error('Batch polling error:', error)
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch evaluation status'
        resultsMap.set(evalId, {
          id: evalId,
          status: 'error',
          error: `Polling failed: ${errorMessage}. Is the API running?`
        })
        setMultipleResults(new Map(resultsMap))
        // Stop polling on error
        setActiveEvaluations(prev => {
          const next = new Set(prev)
          next.delete(evalId)
          return next
        })
      }
    }
    
    poll()
  }, [apiUrl])

  // Effects
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  useEffect(() => {
    fetchPlatformStatus()
    fetchQueueStatus()
    const interval = setInterval(fetchQueueStatus, 2000)
    return () => clearInterval(interval)
  }, [])

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
                href="/"
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                Classic View
              </a>
              <div className="text-sm text-gray-500">
                v2.0.0
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* API Connection Warning */}
        {!platformStatus && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-yellow-800">
                  API Connection Issue
                </h3>
                <div className="mt-2 text-sm text-yellow-700">
                  <p>Unable to connect to the API. Make sure the backend is running:</p>
                  <pre className="mt-2 bg-yellow-100 p-2 rounded text-xs">
                    cd .. && docker-compose up -d
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Top Row - Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Queue Status */}
          {queueStatus && (
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Queue Status</h3>
              <div className="grid grid-cols-2 gap-2">
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-yellow-400 rounded-full mr-2"></div>
                  <span className="text-xs text-gray-600">Pending:</span>
                  <span className="ml-1 font-semibold text-sm">{queueStatus.pending}</span>
                </div>
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-blue-400 rounded-full mr-2"></div>
                  <span className="text-xs text-gray-600">Running:</span>
                  <span className="ml-1 font-semibold text-sm">{queueStatus.running}</span>
                </div>
              </div>
            </div>
          )}

          {/* Platform Status */}
          {platformStatus && (
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Platform Status</h3>
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-600">Status:</span>
                  <span className={`font-medium ${platformStatus.status === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
                    {platformStatus.status}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-600">Engine:</span>
                  <span className="font-medium text-gray-900">Docker</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-600">Uptime:</span>
                  <span className="font-medium text-gray-900">{Math.floor(platformStatus.uptime / 60)}m</span>
                </div>
              </div>
            </div>
          )}

          {/* Batch Testing */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Batch Testing</h3>
            <button
              onClick={submitMultiple}
              disabled={loading}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm font-medium"
            >
              Submit 5 Test Evaluations
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
              onSubmit={submitCode}
              loading={loading || isRunning}
            />

            {/* Execution Config */}
            <ExecutionConfig
              config={execConfig}
              onChange={setExecConfig}
              disabled={loading || isRunning}
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
              evalId={currentEvalId}
              isRunning={isRunning}
              onKill={handleKillExecution}
            />

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

                {(result.status === 'failed' || result.status === 'error') && result.error && (
                  <ErrorDisplay
                    error={result.error}
                    code={code}
                    onLineClick={handleLineClick}
                  />
                )}
              </>
            )}

            {/* Multiple Results */}
            {multipleResults.size > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold mb-4 text-gray-900">
                  Batch Results ({multipleResults.size})
                </h2>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {Array.from(multipleResults.entries()).map(([id, evalResult]) => (
                    <div key={id} className="p-3 border border-gray-200 rounded-md">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-xs text-gray-600">{id}</span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          evalResult.status === 'completed' ? 'bg-green-100 text-green-800' :
                          evalResult.status === 'failed' || evalResult.status === 'error' ? 'bg-red-100 text-red-800' :
                          evalResult.status === 'running' ? 'bg-blue-100 text-blue-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {evalResult.status.toUpperCase()}
                        </span>
                      </div>
                      {evalResult.output && (
                        <pre className="p-2 bg-gray-50 rounded text-xs overflow-x-auto font-mono">
                          {evalResult.output}
                        </pre>
                      )}
                      {evalResult.error && (
                        <pre className="p-2 bg-red-50 text-red-700 rounded text-xs overflow-x-auto font-mono">
                          {evalResult.error}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}