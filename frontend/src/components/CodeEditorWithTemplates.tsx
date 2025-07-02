'use client'

import React, { useState, useEffect, useRef } from 'react'
import { CodeEditor } from './CodeEditor'
import { useCodeTemplates } from '@/hooks/useCodeTemplates'
import { log } from '@/src/utils/logger'

interface CodeEditorWithTemplatesProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  onBatchSubmit?: (count: number) => void
  loading?: boolean
}

export const CodeEditorWithTemplates: React.FC<CodeEditorWithTemplatesProps> = ({
  value,
  onChange,
  onSubmit,
  onBatchSubmit,
  loading = false,
}) => {
  const [showTemplates, setShowTemplates] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [showBatchDialog, setShowBatchDialog] = useState(false)
  const [batchCount, setBatchCount] = useState(5)
  const [recentCodes, setRecentCodes] = useState<Array<{ code: string; timestamp: string }>>([])
  const { templates, templatesByCategory, loading: templatesLoading } = useCodeTemplates()
  const hasLoadedInitialData = useRef(false)
  const onChangeRef = useRef(onChange)
  const initialValue = useRef(value)

  // Keep onChange ref up to date
  useEffect(() => {
    onChangeRef.current = onChange
  }, [onChange])

  useEffect(() => {
    if (hasLoadedInitialData.current) return
    hasLoadedInitialData.current = true

    // Load recent codes from localStorage
    const savedRecent = localStorage.getItem('crucible-recent-codes')
    if (savedRecent) {
      try {
        const parsed = JSON.parse(savedRecent) as Array<{ code: string; timestamp: string }>
        setRecentCodes(parsed)
      } catch (e) {
        log.error('Failed to parse recent codes:', e)
      }
    }

    // Only load draft if there's no initial value
    const draft = localStorage.getItem('crucible-draft-code')
    if (draft && !initialValue.current) {
      onChangeRef.current(draft)
    }
  }, []) // Empty dependency array - only runs once on mount

  const handleTemplateSelect = (templateId: string) => {
    const template = templates.find(t => t.id === templateId)
    if (template) {
      onChange(template.code)
      setShowTemplates(false)
    }
  }

  const handleSubmit = () => {
    // Save to recent codes
    const newRecent = [
      { code: value, timestamp: new Date().toISOString() },
      ...recentCodes.filter(r => r.code !== value).slice(0, 9), // Keep last 10 unique
    ]
    setRecentCodes(newRecent)
    localStorage.setItem('crucible-recent-codes', JSON.stringify(newRecent))

    onSubmit()
  }

  const loadRecentCode = (code: string) => {
    onChange(code)
    setShowTemplates(false)
  }

  return (
    <>
      {/* Backdrop when expanded */}
      {isExpanded && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40" onClick={() => setIsExpanded(false)} />
      )}
      
      {/* Editor container */}
      <div className={`bg-white rounded-lg shadow-sm p-6 transition-all ${
        isExpanded 
          ? 'fixed top-4 left-4 right-4 bottom-4 z-50 overflow-auto' 
          : ''
      }`}>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Code Editor</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="px-3 py-1.5 text-sm text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
            title={isExpanded ? "Collapse editor" : "Expand editor"}
          >
            {isExpanded ? (
              <>
                <svg className="w-4 h-4 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Collapse
              </>
            ) : (
              <>
                <svg className="w-4 h-4 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
                Expand
              </>
            )}
          </button>
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            {showTemplates ? 'Hide Templates' : 'Show Templates'}
          </button>
          {value && (
            <button
              onClick={() => {
                localStorage.setItem('crucible-last-code', value)
                localStorage.setItem('crucible-last-saved', new Date().toISOString())
              }}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
              title="Save (Ctrl+S)"
            >
              💾 Save
            </button>
          )}
        </div>
      </div>

      {/* Templates Panel */}
      {showTemplates && (
        <div className="mb-4 border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="font-medium text-gray-900 mb-3">Code Templates</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {templatesLoading ? (
              <div className="col-span-2 text-center py-4 text-gray-500">Loading templates...</div>
            ) : (
              Object.entries(templatesByCategory).map(([category, categoryTemplates]) => (
                <div key={category}>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">{category}</h4>
                  <div className="space-y-1">
                    {categoryTemplates.map(template => (
                      <button
                        key={template.id}
                        onClick={() => handleTemplateSelect(template.id)}
                        className="w-full text-left px-3 py-2 text-sm rounded hover:bg-white hover:shadow-sm transition-all"
                      >
                        <div className="font-medium">{template.name}</div>
                        <div className="text-xs text-gray-600">{template.description}</div>
                      </button>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Recent Submissions */}
          {recentCodes.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Recent Submissions</h4>
              <div className="space-y-1">
                {recentCodes.slice(0, 3).map((recent, idx) => (
                  <button
                    key={idx}
                    onClick={() => loadRecentCode(recent.code)}
                    className="w-full text-left px-3 py-2 text-sm rounded hover:bg-white hover:shadow-sm transition-all"
                  >
                    <div className="font-mono text-xs truncate">{recent.code.split('\n')[0]}</div>
                    <div className="text-xs text-gray-500">
                      {new Date(recent.timestamp).toLocaleString()}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Code Editor */}
      <CodeEditor 
        value={value} 
        onChange={onChange} 
        height={isExpanded ? "calc(100vh - 300px)" : "400px"} 
      />

      {/* Action Buttons */}
      <div className="mt-4 flex gap-3">
        <button
          onClick={handleSubmit}
          disabled={loading || !value.trim()}
          className="px-6 py-2.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {loading ? 'Evaluating...' : 'Run Evaluation'}
        </button>

        {onBatchSubmit && (
          <button
            onClick={() => setShowBatchDialog(true)}
            disabled={loading || !value.trim()}
            className="px-4 py-2.5 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            Run K Evaluations
          </button>
        )}

        <button
          onClick={() => onChange('')}
          disabled={loading || !value}
          className="px-4 py-2.5 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Clear
        </button>

        <div className="ml-auto text-sm text-gray-500 flex items-center">
          <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs">Ctrl</kbd>
          <span className="mx-1">+</span>
          <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs">S</kbd>
          <span className="ml-2">to save</span>
        </div>
      </div>
    </div>
    
    {/* Batch Submit Dialog */}
    {showBatchDialog && onBatchSubmit && (
      <>
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50" onClick={() => setShowBatchDialog(false)} />
        <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-xl p-6 z-50 min-w-[300px]">
          <h3 className="text-lg font-semibold mb-4">Run Multiple Evaluations</h3>
          <p className="text-sm text-gray-600 mb-4">
            Submit {batchCount} copies of the current code for evaluation.
          </p>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of evaluations:
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="10"
                value={batchCount}
                onChange={(e) => setBatchCount(Math.min(10, Math.max(1, parseInt(e.target.value) || 1)))}
                className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-500">(max: 10)</span>
            </div>
          </div>
          
          <div className="flex gap-3 justify-end">
            <button
              onClick={() => setShowBatchDialog(false)}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                onBatchSubmit(batchCount)
                setShowBatchDialog(false)
              }}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Submit {batchCount} Evaluations
            </button>
          </div>
        </div>
      </>
    )}
    </>
  )
}
