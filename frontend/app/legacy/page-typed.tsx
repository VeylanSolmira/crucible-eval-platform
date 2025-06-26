'use client'

import { useState } from 'react'
import { apiClient } from '@/lib/api/client'
import type { EvaluationStatusResponse } from '@/lib/api/client'

// Example of how to use the typed API client
export function TypedEvaluationDemo() {
  const [status, setStatus] = useState<EvaluationStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submitEvaluation = async () => {
    setLoading(true)
    setError(null)

    // TypeScript knows exactly what fields are required
    const { data, error } = await apiClient.submitEvaluation({
      code: 'print("Hello from typed API!")',
      language: 'python',
      engine: 'docker',
      timeout: 30
      // TypeScript would error if we added invalid fields here
    })

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    if (data) {
      // TypeScript knows data.eval_id exists
      pollStatus(data.eval_id)
    }
  }

  const pollStatus = async (evalId: string) => {
    const { data, error } = await apiClient.getEvaluationStatus(evalId)
    
    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    if (data) {
      setStatus(data)
      
      // TypeScript knows all the fields available
      if (data.status === 'queued' || data.status === 'running') {
        setTimeout(() => pollStatus(evalId), 1000)
      } else {
        setLoading(false)
      }
    }
  }

  return (
    <div className="p-4">
      <button 
        onClick={submitEvaluation}
        disabled={loading}
        className="bg-blue-500 text-white px-4 py-2 rounded"
      >
        Submit Typed Evaluation
      </button>

      {error && (
        <div className="text-red-500 mt-2">Error: {error}</div>
      )}

      {status && (
        <div className="mt-4 p-4 border rounded">
          <p>Status: {status.status}</p>
          <p>Output: {status.output}</p>
          {/* TypeScript knows exactly what fields exist */}
          {/* If you try status.nonExistentField, you get a compile error */}
        </div>
      )}
    </div>
  )
}