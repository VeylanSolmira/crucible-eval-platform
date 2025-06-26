'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface EvaluationComplete {
  evaluation: {
    id: string
    code: string
    language: string
    status: string
    created_at?: string
    completed_at?: string
    output?: string
    error?: string
    runtime_ms?: number
  }
  events: Array<{
    type: string
    timestamp: string
    message: string
  }>
  storage_locations: Record<string, string>
  timeline: Array<{
    timestamp?: string
    event: string
    details: string
  }>
  metadata: {
    total_events: number
    execution_time_ms?: number
    output_size: number
    error_size: number
  }
}

function formatTimestamp(timestamp?: string): string {
  if (!timestamp) return 'N/A'
  return new Date(timestamp).toLocaleString()
}

function formatDuration(ms?: number): string {
  if (!ms) return 'N/A'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

export default function EvaluationDetailPage({ params }: { params: { id: string } }) {
  const [evaluation, setEvaluation] = useState<EvaluationComplete | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'code' | 'output' | 'events' | 'storage'>('code')
  const router = useRouter()

  useEffect(() => {
    fetchEvaluationDetails()
  }, [params.id])

  const fetchEvaluationDetails = async () => {
    try {
      const response = await fetch(`http://localhost:8082/evaluations/${params.id}/complete`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setEvaluation(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch evaluation details')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-lg">Loading evaluation details...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-red-600">Error: {error}</div>
      </div>
    )
  }

  if (!evaluation) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-600">Evaluation not found</div>
      </div>
    )
  }

  const { evaluation: eval, events, storage_locations, timeline, metadata } = evaluation

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Evaluation Details</h1>
              <p className="text-sm text-gray-600 mt-1 font-mono">{eval.id}</p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => router.push('/storage')}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                Storage Explorer
              </button>
              <button
                onClick={() => router.push('/')}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                Back to Platform
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Status and Metadata */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-600">Status</div>
              <div className="mt-1">
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                    eval.status === 'completed'
                      ? 'bg-green-100 text-green-800'
                      : eval.status === 'failed'
                      ? 'bg-red-100 text-red-800'
                      : eval.status === 'running'
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}
                >
                  {eval.status.toUpperCase()}
                </span>
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Execution Time</div>
              <div className="text-lg font-medium mt-1">
                {formatDuration(metadata.execution_time_ms)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Created</div>
              <div className="text-sm font-medium mt-1">{formatTimestamp(eval.created_at)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Completed</div>
              <div className="text-sm font-medium mt-1">{formatTimestamp(eval.completed_at)}</div>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="bg-white rounded-lg shadow-sm mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex">
              <button
                onClick={() => setActiveTab('code')}
                className={`py-3 px-6 text-sm font-medium border-b-2 ${
                  activeTab === 'code'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Code
              </button>
              <button
                onClick={() => setActiveTab('output')}
                className={`py-3 px-6 text-sm font-medium border-b-2 ${
                  activeTab === 'output'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Output ({formatBytes(metadata.output_size)})
              </button>
              <button
                onClick={() => setActiveTab('events')}
                className={`py-3 px-6 text-sm font-medium border-b-2 ${
                  activeTab === 'events'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Events ({metadata.total_events})
              </button>
              <button
                onClick={() => setActiveTab('storage')}
                className={`py-3 px-6 text-sm font-medium border-b-2 ${
                  activeTab === 'storage'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Storage Locations
              </button>
            </nav>
          </div>

          <div className="p-6">
            {/* Code Tab */}
            {activeTab === 'code' && (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-medium text-gray-900">Source Code</h3>
                  <span className="text-sm text-gray-600">Language: {eval.language}</span>
                </div>
                <pre className="p-4 bg-gray-50 rounded-md text-sm overflow-x-auto font-mono">
                  {eval.code}
                </pre>
              </div>
            )}

            {/* Output Tab */}
            {activeTab === 'output' && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Execution Output</h3>
                {eval.output ? (
                  <pre className="p-4 bg-gray-50 rounded-md text-sm overflow-x-auto font-mono">
                    {eval.output}
                  </pre>
                ) : eval.error ? (
                  <pre className="p-4 bg-red-50 text-red-700 rounded-md text-sm overflow-x-auto font-mono">
                    {eval.error}
                  </pre>
                ) : (
                  <p className="text-gray-500">No output available</p>
                )}
              </div>
            )}

            {/* Events Tab */}
            {activeTab === 'events' && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Execution Timeline</h3>
                <div className="space-y-3">
                  {timeline.map((item, index) => (
                    <div key={index} className="flex items-start">
                      <div className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                      <div className="ml-4 flex-1">
                        <div className="flex justify-between">
                          <div>
                            <span className="font-medium text-gray-900">{item.event}</span>
                            <p className="text-sm text-gray-600 mt-1">{item.details}</p>
                          </div>
                          <span className="text-sm text-gray-500">
                            {formatTimestamp(item.timestamp)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Storage Tab */}
            {activeTab === 'storage' && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Storage Locations</h3>
                <div className="space-y-4">
                  {Object.entries(storage_locations).map(([type, location]) => (
                    <div key={type} className="flex items-center justify-between p-4 bg-gray-50 rounded-md">
                      <div>
                        <span className="font-medium text-gray-900 capitalize">{type}</span>
                        <p className="text-sm text-gray-600 mt-1 font-mono">{location}</p>
                      </div>
                      <button
                        onClick={() => {
                          if (location.startsWith('database')) {
                            router.push('/storage/database')
                          } else if (location.startsWith('file://')) {
                            router.push('/storage/file')
                          } else if (location.startsWith('redis://')) {
                            router.push('/storage/redis')
                          }
                        }}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
                      >
                        View in Storage →
                      </button>
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