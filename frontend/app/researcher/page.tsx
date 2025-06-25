'use client'

import { useState, useCallback } from 'react'
import { CodeEditorWithTemplates } from '../../src/components/CodeEditorWithTemplates'
import { ExecutionConfig, ExecutionConfigData } from '../../src/components/ExecutionConfig'
import { ExecutionMonitor } from '../../src/components/ExecutionMonitor'
import { ErrorDisplay } from '../../src/components/ErrorDisplay'
import type { components } from '@/types/generated/api'

// Type definitions
type EvaluationRequest = components['schemas']['EvaluationRequest']
type EvaluationResponse = components['schemas']['EvaluationResponse']
type EvaluationStatusResponse = components['schemas']['EvaluationStatusResponse']

interface EvaluationResult {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'error'
  output?: string
  error?: string
  startTime?: number
  endTime?: number
}

export default function ResearcherUI() {
  // State
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentEvalId, setCurrentEvalId] = useState<string | null>(null)
  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  
  // Execution config
  const [execConfig, setExecConfig] = useState<ExecutionConfigData>({
    timeout: 30,
    memoryLimit: 512,
    pythonVersion: '3.11',
  })

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || ''

  // Submit code for evaluation
  const submitCode = async () => {
    setLoading(true)
    setResult(null)
    setIsRunning(true)
    
    try {
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
      
      // Start polling for results
      pollEvaluationStatus(data.eval_id)
      
    } catch (error) {
      setResult({
        id: 'error',
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to evaluate code'
      })
      setIsRunning(false)
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
        
        // Continue polling if still running
        if (data.status === 'queued' || data.status === 'running') {
          setTimeout(poll, 1000)
        } else {
          setIsRunning(false)
        }
      } catch (error) {
        console.error('Polling error:', error)
        setResult({
          id: evalId,
          status: 'error',
          error: 'Failed to fetch evaluation status'
        })
        setIsRunning(false)
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
          </div>
        </div>
      </div>
    </div>
  )
}