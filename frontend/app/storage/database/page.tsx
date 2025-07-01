'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import type { DatabaseDetails } from '@/types/storage'

function formatTimestamp(timestamp?: string): string {
  if (!timestamp) return 'N/A'
  return new Date(timestamp).toLocaleString()
}

export default function DatabasePage() {
  const [details, setDetails] = useState<DatabaseDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    void fetchDatabaseDetails()
  }, [])

  const fetchDatabaseDetails = async () => {
    try {
      const response = await fetch('http://localhost:8082/storage/database/details')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json() as DatabaseDetails
      setDetails(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch database details')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-lg">Loading database details...</div>
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

  if (!details) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-600">No database data available</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Database Storage</h1>
              <p className="text-sm text-gray-600 mt-1">PostgreSQL backend details</p>
            </div>
            <button
              onClick={() => router.push('/storage')}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              Back to Overview
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Connection Info */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Connection Information</h2>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm text-gray-600">Backend Type</dt>
              <dd className="font-medium">{details.backend}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-600">Connection</dt>
              <dd className="font-medium">{details.connection}</dd>
            </div>
          </dl>
        </div>

        {/* Table Statistics */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Table Statistics</h2>
          
          {/* Evaluations Table */}
          <div className="mb-6">
            <h3 className="font-medium text-gray-900 mb-2">Evaluations Table</h3>
            <div className="bg-gray-50 rounded-md p-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div>
                  <div className="text-2xl font-bold">{details.tables.evaluations.count}</div>
                  <div className="text-sm text-gray-600">Total Records</div>
                </div>
                {Object.entries(details.tables.evaluations.by_status).map(([status, count]) => (
                  <div key={status}>
                    <div className="text-2xl font-bold">{count}</div>
                    <div className="text-sm text-gray-600 capitalize">{status}</div>
                  </div>
                ))}
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Columns:</div>
                <div className="flex flex-wrap gap-2">
                  {details.tables.evaluations.columns.map(col => (
                    <span key={col} className="px-2 py-1 bg-white rounded text-xs font-mono">
                      {col}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Events Table */}
          <div>
            <h3 className="font-medium text-gray-900 mb-2">Events Table</h3>
            <div className="bg-gray-50 rounded-md p-4">
              <div className="mb-2">
                <span className="text-2xl font-bold">{details.tables.evaluation_events.count}</span>
                <span className="text-sm text-gray-600 ml-2">Total Events</span>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Columns:</div>
                <div className="flex flex-wrap gap-2">
                  {details.tables.evaluation_events.columns.map(col => (
                    <span key={col} className="px-2 py-1 bg-white rounded text-xs font-mono">
                      {col}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Evaluations */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Recent Evaluations</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Language
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {details.recent_evaluations.map((evaluation) => (
                  <tr key={evaluation.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                      {evaluation.id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          evaluation.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : evaluation.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : evaluation.status === 'running'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {evaluation.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {evaluation.language}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatTimestamp(evaluation.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={() => router.push(`/evaluation/${evaluation.id}`)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        View Details →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}