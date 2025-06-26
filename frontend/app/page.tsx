'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import type { components } from '@/types/generated/api'

// Use generated types from OpenAPI
type EvaluationRequest = components['schemas']['EvaluationRequest']
type EvaluationResponse = components['schemas']['EvaluationResponse']
type EvaluationStatusResponse = components['schemas']['EvaluationStatusResponse']
type QueueStatusResponse = components['schemas']['QueueStatusResponse']

// Map to local interface names for minimal code changes
interface EvaluationResult {
  id: string
  status: string
  output?: string
  error?: string
  timestamp?: string
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

export default function Home() {
  const [code, setCode] = useState('print("Hello from Crucible Platform!")')
  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null)
  const [multipleResults, setMultipleResults] = useState<Map<string, EvaluationResult>>(new Map())
  const [platformStatus, setPlatformStatus] = useState<PlatformStatus | null>(null)
  const [events, setEvents] = useState<EventMessage[]>([])
  const [activeEvaluations, setActiveEvaluations] = useState<Set<string>>(new Set())
  const eventsEndRef = useRef<HTMLDivElement>(null)

  // Use relative URLs when deployed behind proxy, localhost for development
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || ''

  const addEvent = useCallback((type: string, data: any) => {
    const event: EventMessage = {
      type,
      data,
      timestamp: new Date().toLocaleTimeString()
    }
    setEvents(prev => [...prev.slice(-50), event]) // Keep last 50 events
  }, [])

  // We'll define processEvaluationResponse after pollEvaluationStatus is declared

  const fetchQueueStatus = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/queue-status`)
      if (response.ok) {
        const data: QueueStatusResponse = await response.json()
        // Map the response to our local interface
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

  const fetchPlatformStatus = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/status`)
      if (response.ok) {
        const data = await response.json()
        setPlatformStatus({
          platform: 'QueuedEvaluationPlatform',
          status: data.platform === 'healthy' ? 'healthy' : 'unhealthy',
          engine: data.engine || 'Docker (Containerized - Network isolated)',
          version: data.version || '1.0.0',
          uptime: data.uptime || 0
        })
      }
    } catch (error) {
      console.error('Failed to fetch platform status:', error)
    }
  }

  // Scroll to bottom of events when new events are added
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  // Fetch initial status
  useEffect(() => {
    fetchPlatformStatus()
    fetchQueueStatus()
    // Set up polling for queue status
    const interval = setInterval(fetchQueueStatus, 2000)
    return () => clearInterval(interval)
  }, [])

  const submitCode = async (): Promise<void> => {
    setLoading(true)
    setResult(null)
    setMultipleResults(new Map())
    
    try {
      addEvent('submission', { type: 'single', code: code.substring(0, 50) + '...' })
      await fetchQueueStatus()
      
      const request: EvaluationRequest = { 
        code,
        language: 'python',
        engine: 'docker',
        timeout: 30
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
      
      // Process the response using our helper
      const result = processEvaluationResponse(data)
      setResult(result)
      
      // Fetch queue status after submission
      await fetchQueueStatus()
    } catch (error) {
      const errorResult = {
        id: 'error',
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to evaluate code'
      }
      setResult(errorResult)
      addEvent('error', { message: errorResult.error })
    } finally {
      setLoading(false)
    }
  }

  const submitMultiple = async (): Promise<void> => {
    setLoading(true)
    setResult(null)
    setMultipleResults(new Map())
    
    try {
      addEvent('submission', { type: 'batch', count: 5 })
      await fetchQueueStatus()
      
      // Submit 5 evaluations in parallel
      const promises = Array.from({ length: 5 }, async (_, i) => {
        const evalCode = `# Evaluation ${i + 1}\nprint(f"This is evaluation ${i + 1}")\nimport time\ntime.sleep(${Math.random() * 2})`
        
        const response = await fetch(`${apiUrl}/api/eval`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ code: evalCode }),
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.error || `HTTP error! status: ${response.status}`)
        }

        return response.json()
      })
      
      const results = await Promise.allSettled(promises)
      
      // Process results
      const resultsMap = new Map<string, EvaluationResult>()
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          // Process the response using our helper
          const evalResult = processEvaluationResponse(result.value, resultsMap, index + 1)
          resultsMap.set(evalResult.id, evalResult)
        } else {
          const errorId = `error-${index}`
          resultsMap.set(errorId, {
            id: errorId,
            status: 'error',
            error: result.reason?.message || 'Failed to submit evaluation'
          })
          addEvent('error', { batch_index: index + 1, message: result.reason?.message })
        }
      })
      
      setMultipleResults(resultsMap)
      
      // Fetch queue status after submission
      await fetchQueueStatus()
    } catch (error) {
      const errorResult = {
        id: 'error',
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to submit evaluations'
      }
      setResult(errorResult)
      addEvent('error', { message: errorResult.error })
    } finally {
      setLoading(false)
    }
  }

  const pollEvaluationStatus = useCallback(async (evalId: string, resultsMap?: Map<string, EvaluationResult>) => {
    const targetMap = resultsMap || multipleResults
    
    const poll = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/eval-status/${evalId}`)
        if (!response.ok && response.status !== 202) {
          throw new Error('Failed to fetch status')
        }
        
        const data: EvaluationStatusResponse = await response.json()
        
        // Extract the result from the API response
        const evalResult: EvaluationResult = {
          id: data.eval_id || evalId,
          status: data.status || 'unknown',
          output: data.output || '',
          error: data.error || ''
        }
        
        // Update the result
        if (resultsMap) {
          resultsMap.set(evalId, evalResult)
          setMultipleResults(new Map(resultsMap))
        } else {
          setResult(evalResult)
        }
        
        // Add status change event
        const previousStatus = targetMap.get(evalId)?.status
        if (evalResult.status !== previousStatus) {
          addEvent('status_change', { id: evalId, from: previousStatus, to: evalResult.status })
        }
        
        // Continue polling if still running (check outer status, not result status)
        if (data.status === 'queued' || data.status === 'running') {
          setTimeout(() => poll(), 1000)
        } else {
          // Remove from active evaluations
          setActiveEvaluations(prev => {
            const next = new Set(prev)
            next.delete(evalId)
            return next
          })
          // Final fetch of queue status
          await fetchQueueStatus()
        }
      } catch (error) {
        console.error('Polling error:', error)
        // Update with error status
        const errorResult = {
          id: evalId,
          status: 'error',
          error: 'Failed to fetch evaluation status'
        }
        if (resultsMap) {
          resultsMap.set(evalId, errorResult)
          setMultipleResults(new Map(resultsMap))
        } else {
          setResult(errorResult)
        }
        // Remove from active evaluations
        setActiveEvaluations(prev => {
          const next = new Set(prev)
          next.delete(evalId)
          return next
        })
        addEvent('error', { id: evalId, message: 'Polling failed' })
      }
    }
    
    // Start polling after a short delay
    setTimeout(poll, 1000)
  }, [multipleResults, addEvent, fetchQueueStatus])

  const processEvaluationResponse = useCallback((
    apiResponse: any,
    resultsMap?: Map<string, EvaluationResult>,
    batchIndex?: number
  ): EvaluationResult => {
    const evalId = apiResponse.eval_id
    const initialResult: EvaluationResult = {
      id: evalId,
      status: apiResponse.status || 'queued',
      output: apiResponse.message || ''
    }
    
    // Add event
    const eventData: any = { id: evalId, status: initialResult.status }
    if (batchIndex !== undefined) eventData.batch_index = batchIndex
    addEvent('evaluation_submitted', eventData)
    
    // Track active evaluations
    if (initialResult.status === 'queued' || initialResult.status === 'running') {
      setActiveEvaluations(prev => new Set(prev).add(evalId))
      pollEvaluationStatus(evalId, resultsMap)
    }
    
    return initialResult
  }, [addEvent, pollEvaluationStatus])

  const getStatusBgColor = (status: string): string => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'failed':
      case 'error': return 'bg-red-100 text-red-800'
      case 'running': return 'bg-blue-100 text-blue-800'
      case 'queued': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">⚡ Crucible Evaluation Platform</h1>
            {platformStatus && (
              <div className="text-sm text-gray-600">
                <span className="font-medium">Engine:</span> {platformStatus.engine}
                <span className="ml-4 font-medium">Status:</span>
                <span className={`ml-1 ${platformStatus.status === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
                  {platformStatus.status}
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left Panel - Code Submission */}
          <div className="flex-1 space-y-6">
            {/* Queue Status Card */}
            {queueStatus && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold mb-4 text-gray-900">Queue Status</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center">
                    <div className="w-3 h-3 bg-yellow-400 rounded-full mr-2"></div>
                    <span className="text-gray-600">Pending:</span>
                    <span className="ml-2 font-semibold text-gray-900">{queueStatus.pending}</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-3 h-3 bg-blue-400 rounded-full mr-2"></div>
                    <span className="text-gray-600">Running:</span>
                    <span className="ml-2 font-semibold text-gray-900">{queueStatus.running}</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-3 h-3 bg-green-400 rounded-full mr-2"></div>
                    <span className="text-gray-600">Completed:</span>
                    <span className="ml-2 font-semibold text-gray-900">{queueStatus.completed}</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-3 h-3 bg-red-400 rounded-full mr-2"></div>
                    <span className="text-gray-600">Failed:</span>
                    <span className="ml-2 font-semibold text-gray-900">{queueStatus.failed}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Code Editor */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4 text-gray-900">Code Editor</h2>
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full h-64 p-4 border border-gray-300 rounded-md font-mono text-sm bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                placeholder="Enter your Python code here..."
                spellCheck={false}
              />
              <div className="mt-4 flex gap-3">
                <button
                  onClick={submitCode}
                  disabled={loading}
                  className="px-6 py-2.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {loading ? 'Evaluating...' : 'Run Evaluation'}
                </button>
                <button
                  onClick={submitMultiple}
                  disabled={loading}
                  className="px-6 py-2.5 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {loading ? 'Submitting...' : 'Submit 5 Evaluations'}
                </button>
              </div>
            </div>

            {/* Results Panel */}
            {(result || multipleResults.size > 0) && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold mb-4 text-gray-900">
                  {multipleResults.size > 0 ? `Batch Results (${multipleResults.size})` : 'Evaluation Result'}
                </h2>
                
                {/* Single Result */}
                {result && !multipleResults.size && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-sm text-gray-600">{result.id}</span>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBgColor(result.status)}`}>
                        {result.status.toUpperCase()}
                      </span>
                    </div>
                    {result.output && (
                      <pre className="p-4 bg-gray-50 rounded-md text-sm overflow-x-auto font-mono">
                        {result.output}
                      </pre>
                    )}
                    {result.error && (
                      <pre className="p-4 bg-red-50 text-red-700 rounded-md text-sm overflow-x-auto font-mono">
                        {result.error}
                      </pre>
                    )}
                  </div>
                )}

                {/* Multiple Results */}
                {multipleResults.size > 0 && (
                  <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar">
                    {Array.from(multipleResults.entries()).map(([id, evalResult]) => (
                      <div key={id} className="p-4 border border-gray-200 rounded-md hover:bg-gray-50 transition-colors">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-mono text-sm text-gray-600">{id}</span>
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBgColor(evalResult.status)}`}>
                            {evalResult.status.toUpperCase()}
                          </span>
                        </div>
                        {evalResult.output && (
                          <pre className="p-3 bg-gray-50 rounded text-xs overflow-x-auto font-mono">
                            {evalResult.output}
                          </pre>
                        )}
                        {evalResult.error && (
                          <pre className="p-3 bg-red-50 text-red-700 rounded text-xs overflow-x-auto font-mono">
                            {evalResult.error}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Panel - Monitoring */}
          <div className="flex-1 space-y-6">
            {/* Active Evaluations */}
            {activeEvaluations.size > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold mb-4 text-gray-900">Active Evaluations</h2>
                <div className="space-y-2">
                  {Array.from(activeEvaluations).map(id => (
                    <div key={id} className="flex items-center justify-between p-3 bg-blue-50 rounded-md">
                      <span className="font-mono text-sm">{id}</span>
                      <div className="flex items-center">
                        <div className="animate-pulse w-2 h-2 bg-blue-400 rounded-full mr-2"></div>
                        <span className="text-sm text-blue-700">Processing</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Event Stream */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4 text-gray-900">Event Stream</h2>
              <div className="bg-gray-50 rounded-md p-4 h-96 overflow-y-auto font-mono text-xs custom-scrollbar">
                {events.length === 0 ? (
                  <div className="text-gray-400 text-center py-8">No events yet...</div>
                ) : (
                  <div className="space-y-1">
                    {events.map((event, idx) => (
                      <div key={idx} className="flex">
                        <span className="text-gray-500 mr-2">{event.timestamp}</span>
                        <span className={`font-medium ${
                          event.type === 'error' ? 'text-red-600' :
                          event.type === 'submission' ? 'text-blue-600' :
                          event.type === 'evaluation_complete' ? 'text-green-600' :
                          'text-gray-700'
                        }`}>
                          [{event.type}]
                        </span>
                        <span className="ml-2 text-gray-600">
                          {JSON.stringify(event.data)}
                        </span>
                      </div>
                    ))}
                    <div ref={eventsEndRef} />
                  </div>
                )}
              </div>
            </div>

            {/* Platform Info */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4 text-gray-900">Platform Information</h2>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">API Endpoint:</span>
                  <span className="font-mono">{apiUrl}</span>
                </div>
                {platformStatus && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Platform:</span>
                      <span>{platformStatus.platform}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Version:</span>
                      <span>{platformStatus.version}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Uptime:</span>
                      <span>{Math.floor(platformStatus.uptime / 60)}m</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}