/**
 * Example component demonstrating type-safe API usage
 * This component will have compile-time type checking against the OpenAPI spec
 */

import React, { useState } from 'react'
import { useEvaluation, useEvaluationStatus } from '@/lib/api/hooks'
import type { EvaluationRequest } from '@/lib/api/client'

export function EvaluationExample() {
  const [code, setCode] = useState('print("Hello, World!")')
  const [evalId, setEvalId] = useState<string | null>(null)
  
  const { submitEvaluation, isSubmitting, error: submitError } = useEvaluation()
  const { status, isLoading, error: statusError } = useEvaluationStatus(evalId)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // TypeScript will enforce the correct shape of the request
    // based on the OpenAPI schema
    const request: EvaluationRequest = {
      code,
      language: 'python',
      engine: 'docker',
      timeout: 30
    }

    const result = await submitEvaluation(request)
    if (result) {
      setEvalId(result.eval_id)
    }
  }

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Code Evaluation Example</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="code" className="block text-sm font-medium mb-2">
            Python Code
          </label>
          <textarea
            id="code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full h-32 p-2 border rounded"
            placeholder="Enter your Python code here..."
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
        >
          {isSubmitting ? 'Submitting...' : 'Evaluate Code'}
        </button>
      </form>

      {submitError && (
        <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
          Error: {submitError}
        </div>
      )}

      {evalId && isLoading && (
        <div className="mt-6 p-4 bg-gray-100 rounded">
          <div className="flex items-center">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500 mr-3"></div>
            <span>Loading evaluation status...</span>
          </div>
        </div>
      )}

      {status && (
        <div className="mt-6 p-4 bg-gray-100 rounded">
          <h3 className="font-semibold mb-2">Evaluation Status</h3>
          <dl className="space-y-1">
            <div>
              <dt className="inline font-medium">ID:</dt>
              <dd className="inline ml-2">{status.eval_id}</dd>
            </div>
            <div>
              <dt className="inline font-medium">Status:</dt>
              <dd className="inline ml-2">
                <span className={`px-2 py-1 rounded text-sm ${
                  status.status === 'completed' ? 'bg-green-200' :
                  status.status === 'failed' ? 'bg-red-200' :
                  status.status === 'running' ? 'bg-blue-200' :
                  'bg-gray-200'
                }`}>
                  {status.status}
                </span>
              </dd>
            </div>
            {status.output && (
              <div className="mt-3">
                <dt className="font-medium">Output:</dt>
                <dd className="mt-1">
                  <pre className="p-2 bg-white rounded border">{status.output}</pre>
                </dd>
              </div>
            )}
            {status.error && (
              <div className="mt-3">
                <dt className="font-medium">Error:</dt>
                <dd className="mt-1 text-red-600">{status.error}</dd>
              </div>
            )}
          </dl>
        </div>
      )}

      {statusError && (
        <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
          Status Error: {statusError}
        </div>
      )}
    </div>
  )
}