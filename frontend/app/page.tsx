'use client'

import { useState } from 'react'
import { appConfig } from '@/lib/config'
import type { EvaluationResult, EvaluationRequest } from '@/types/api'

export default function Home() {
  const [code, setCode] = useState<string>(`print('Hello, ${appConfig.name}!')`)
  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [loading, setLoading] = useState<boolean>(false)

  const submitEvaluation = async (): Promise<void> => {
    setLoading(true)
    setResult(null)

    try {
      const request: EvaluationRequest = { code }
      
      const response = await fetch('/api/eval', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })

      const data: EvaluationResult = await response.json()
      setResult(data)
    } catch (error) {
      setResult({
        id: 'error',
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="max-w-4xl mx-auto p-8">
      <h1 className="text-4xl font-bold mb-8">{appConfig.theme.logo} {appConfig.title}</h1>
      
      {appConfig.features.showSafetyWarning && (
        <div className="bg-amber-100 border-l-4 border-amber-500 text-amber-700 p-4 mb-6">
          <h2 className="font-bold">⚠️ SAFETY WARNING</h2>
          <p>This platform executes Python code. Use with caution.</p>
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label htmlFor="code" className="block text-sm font-medium mb-2">
            Submit Python code for evaluation:
          </label>
          <textarea
            id="code"
            value={code}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCode(e.target.value)}
            className="w-full h-40 p-4 font-mono text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter Python code..."
          />
        </div>

        <button
          onClick={submitEvaluation}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Running...' : 'Run Evaluation'}
        </button>

        {result && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold mb-2">Result:</h3>
            <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto">
              {result.output || result.error || JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </main>
  )
}