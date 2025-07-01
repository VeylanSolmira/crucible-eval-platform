'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import type { RedisDetails } from '@/types/storage'

export default function RedisPage() {
  const [details, setDetails] = useState<RedisDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    void fetchRedisDetails()
  }, [])

  const fetchRedisDetails = async () => {
    try {
      const response = await fetch('http://localhost:8082/storage/redis/details')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json() as RedisDetails
      setDetails(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch Redis details')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-lg">Loading Redis details...</div>
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
        <div className="text-gray-600">No Redis data available</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Redis Cache</h1>
              <p className="text-sm text-gray-600 mt-1">Distributed cache and pub/sub</p>
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
        {/* Status Card */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Connection Status</h2>
          <div className="flex items-center space-x-2">
            <div
              className={`w-3 h-3 rounded-full ${
                details.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
              }`}
            ></div>
            <span className="font-medium capitalize">{details.status}</span>
          </div>
        </div>

        {/* Key Patterns */}
        {details.info.keys && details.info.keys.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4 text-gray-900">Cached Keys</h2>
            <div className="space-y-2">
              {details.info.keys.map(key => (
                <div key={key} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                  <span className="font-mono text-sm">{key}</span>
                  <button className="text-blue-600 hover:text-blue-800 text-sm">
                    View Value →
                  </button>
                </div>
              ))}
            </div>
            {details.info.keys.length === 0 && (
              <p className="text-gray-500 text-sm">No keys found in cache</p>
            )}
          </div>
        )}

        {/* Redis Info */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Redis Information</h2>
          <div className="bg-gray-50 rounded-md p-4">
            <p className="text-sm text-gray-600 mb-4">
              Redis provides high-performance caching for frequently accessed data and pub/sub messaging for real-time updates.
            </p>
            <div className="space-y-2">
              <div>
                <span className="font-medium text-gray-700">Use Cases:</span>
                <ul className="mt-1 ml-5 list-disc text-sm text-gray-600">
                  <li>Caching evaluation results</li>
                  <li>Storing pending evaluation status</li>
                  <li>Pub/sub for real-time updates</li>
                  <li>Session management</li>
                </ul>
              </div>
              <div className="mt-4">
                <span className="font-medium text-gray-700">Key Patterns:</span>
                <ul className="mt-1 ml-5 list-disc text-sm text-gray-600">
                  <li><code className="bg-gray-200 px-1">pending:eval_*</code> - Pending evaluations</li>
                  <li><code className="bg-gray-200 px-1">cache:result:*</code> - Cached results</li>
                  <li><code className="bg-gray-200 px-1">session:*</code> - User sessions</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Future Enhancement */}
        <div className="bg-blue-50 rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-2 text-blue-900">Coming Soon</h2>
          <p className="text-sm text-blue-700">
            Future enhancements will include real-time key monitoring, memory usage graphs, and TTL management.
          </p>
        </div>
      </div>
    </div>
  )
}