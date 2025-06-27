'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface StorageMetrics {
  evaluations?: number
  events?: number
  size_bytes?: number
  files?: number
  total_size_bytes?: number
  keys?: number
  memory_used_bytes?: number
  hit_rate?: number
  cache_hits?: number
  cache_misses?: number
  largest_file?: string
  oldest_record?: string
}

interface StorageBackend {
  type: string
  status: string
  metrics?: StorageMetrics
  error?: string
}

interface StorageOverview {
  backends: Record<string, StorageBackend>
  summary: {
    total_evaluations: number
    total_storage_bytes: number
    active_backends: number
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleString()
}

export default function StoragePage() {
  const [overview, setOverview] = useState<StorageOverview | null>(null)
  const [expandedBackends, setExpandedBackends] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    fetchStorageOverview()
  }, [])

  const fetchStorageOverview = async () => {
    try {
      const response = await fetch('http://localhost:8082/storage/overview')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setOverview(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch storage overview')
    } finally {
      setLoading(false)
    }
  }

  const toggleBackend = (backend: string) => {
    setExpandedBackends(prev => {
      const next = new Set(prev)
      if (next.has(backend)) {
        next.delete(backend)
      } else {
        next.add(backend)
      }
      return next
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-lg">Loading storage overview...</div>
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

  if (!overview) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-600">No storage data available</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                ⚡ Crucible Research Platform
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Storage Explorer - View where your evaluation data lives
              </p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/')}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Back to Platform
              </button>
              <div className="text-sm text-gray-500">
                v2.0.0
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Summary Card */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Storage Summary</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {overview.summary.total_evaluations}
              </div>
              <div className="text-sm text-gray-600">Total Evaluations</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {formatBytes(overview.summary.total_storage_bytes)}
              </div>
              <div className="text-sm text-gray-600">Total Storage Used</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {overview.summary.active_backends}
              </div>
              <div className="text-sm text-gray-600">Active Backends</div>
            </div>
          </div>
        </div>

        {/* Backend Cards */}
        <div className="space-y-4">
          {Object.entries(overview.backends).map(([name, backend]) => (
            <div key={name} className="bg-white rounded-lg shadow-sm">
              <div
                className="p-6 cursor-pointer hover:bg-gray-50"
                onClick={() => toggleBackend(name)}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 capitalize">
                      {name} Storage
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">Type: {backend.type}</p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        backend.status === 'healthy'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {backend.status.toUpperCase()}
                    </span>
                    <svg
                      className={`w-5 h-5 text-gray-400 transform transition-transform ${
                        expandedBackends.has(name) ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </div>

                {/* Summary Metrics */}
                {backend.metrics && (
                  <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                    {name === 'database' && (
                      <>
                        <div>
                          <div className="text-lg font-medium">{backend.metrics.evaluations}</div>
                          <div className="text-xs text-gray-600">Evaluations</div>
                        </div>
                        <div>
                          <div className="text-lg font-medium">{backend.metrics.events}</div>
                          <div className="text-xs text-gray-600">Events</div>
                        </div>
                      </>
                    )}
                    {name === 'file' && (
                      <>
                        <div>
                          <div className="text-lg font-medium">{backend.metrics.files}</div>
                          <div className="text-xs text-gray-600">Files</div>
                        </div>
                        <div>
                          <div className="text-lg font-medium">
                            {formatBytes(backend.metrics.total_size_bytes || 0)}
                          </div>
                          <div className="text-xs text-gray-600">Total Size</div>
                        </div>
                      </>
                    )}
                    {name === 'redis' && (
                      <>
                        <div>
                          <div className="text-lg font-medium">{backend.metrics.keys}</div>
                          <div className="text-xs text-gray-600">Keys</div>
                        </div>
                        <div>
                          <div className="text-lg font-medium">
                            {(backend.metrics.hit_rate || 0).toFixed(2)}
                          </div>
                          <div className="text-xs text-gray-600">Hit Rate</div>
                        </div>
                      </>
                    )}
                    {name === 'memory' && backend.metrics.cache_hits !== undefined && (
                      <>
                        <div>
                          <div className="text-lg font-medium">{backend.metrics.cache_hits}</div>
                          <div className="text-xs text-gray-600">Cache Hits</div>
                        </div>
                        <div>
                          <div className="text-lg font-medium">{backend.metrics.cache_misses}</div>
                          <div className="text-xs text-gray-600">Cache Misses</div>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {backend.error && (
                  <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
                    Error: {backend.error}
                  </div>
                )}
              </div>

              {/* Expanded Details */}
              {expandedBackends.has(name) && (
                <div className="border-t border-gray-200 p-6">
                  <div className="space-y-4">
                    {name === 'database' && backend.metrics && (
                      <>
                        <div>
                          <h4 className="font-medium text-gray-900 mb-2">Database Details</h4>
                          <dl className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <dt className="text-gray-600">Oldest Record</dt>
                              <dd className="font-medium">
                                {formatDate(backend.metrics.oldest_record)}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-gray-600">Storage Size</dt>
                              <dd className="font-medium">
                                {formatBytes(backend.metrics.size_bytes || 0)}
                              </dd>
                            </div>
                          </dl>
                        </div>
                        <button
                          onClick={() => router.push('/storage/database')}
                          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                        >
                          View Database Details →
                        </button>
                      </>
                    )}

                    {name === 'file' && backend.metrics && (
                      <>
                        <div>
                          <h4 className="font-medium text-gray-900 mb-2">File System Details</h4>
                          <dl className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <dt className="text-gray-600">Largest File</dt>
                              <dd className="font-medium">{backend.metrics.largest_file || 'N/A'}</dd>
                            </div>
                            <div>
                              <dt className="text-gray-600">Total Files</dt>
                              <dd className="font-medium">{backend.metrics.files}</dd>
                            </div>
                          </dl>
                        </div>
                        <button
                          onClick={() => router.push('/storage/file')}
                          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                        >
                          Browse Files →
                        </button>
                      </>
                    )}

                    {name === 'redis' && (
                      <>
                        <div>
                          <h4 className="font-medium text-gray-900 mb-2">Redis Cache Details</h4>
                          <p className="text-sm text-gray-600">
                            Distributed cache for fast data access and pub/sub messaging
                          </p>
                        </div>
                        <button
                          onClick={() => router.push('/storage/redis')}
                          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                        >
                          View Redis Details →
                        </button>
                      </>
                    )}

                    {name === 'memory' && (
                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">In-Memory Cache</h4>
                        <p className="text-sm text-gray-600">
                          Local process cache for frequently accessed data
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}