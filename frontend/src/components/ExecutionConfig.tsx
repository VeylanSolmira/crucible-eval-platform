'use client'

import React from 'react'

export interface ExecutionConfigData {
  timeout: number
  memoryLimit: number
  pythonVersion: string
  priority: boolean
}

interface ExecutionConfigProps {
  config: ExecutionConfigData
  onChange: (config: ExecutionConfigData) => void
  disabled?: boolean
}

const TIMEOUT_OPTIONS = [
  { label: '30 seconds', value: 30 },
  { label: '1 minute', value: 60 },
  { label: '2 minutes', value: 120 },
  { label: '5 minutes', value: 300 },
]

const MEMORY_OPTIONS = [
  { label: '256 MB', value: 256 },
  { label: '512 MB', value: 512 },
  { label: '1 GB', value: 1024 },
  { label: '2 GB', value: 2048 },
]

const PYTHON_VERSIONS = [
  { label: 'Python 3.11 (Latest)', value: '3.11' },
  { label: 'Python 3.10', value: '3.10' },
  { label: 'Python 3.9', value: '3.9' },
  { label: 'Python 3.8', value: '3.8' },
]

export const ExecutionConfig: React.FC<ExecutionConfigProps> = ({
  config,
  onChange,
  disabled = false,
}) => {
  const handleChange = (field: keyof ExecutionConfigData, value: string | number | boolean) => {
    onChange({
      ...config,
      [field]: value,
    })
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h2 className="text-lg font-semibold mb-4 text-gray-900">Execution Configuration</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Timeout Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Timeout</label>
          <select
            value={config.timeout}
            onChange={e => handleChange('timeout', Number(e.target.value))}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            {TIMEOUT_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-500">Maximum execution time</p>
        </div>

        {/* Memory Limit Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Memory Limit</label>
          <select
            value={config.memoryLimit}
            onChange={e => handleChange('memoryLimit', Number(e.target.value))}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            {MEMORY_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-500">Container memory allocation</p>
        </div>

        {/* Python Version Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Python Version</label>
          <select
            value={config.pythonVersion}
            onChange={e => handleChange('pythonVersion', e.target.value)}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            {PYTHON_VERSIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-500">Runtime environment</p>
        </div>
      </div>

      {/* Resource Usage Warning */}
      {config.memoryLimit >= 1024 && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-sm text-yellow-800">
            <span className="font-medium">Note:</span> High memory limits may affect queue wait
            times during peak usage.
          </p>
        </div>
      )}

      {/* Priority Queue Toggle */}
      <div className="mt-4 p-4 bg-blue-50 rounded-md">
        <div className="flex items-center justify-between">
          <div>
            <label htmlFor="priority" className="text-sm font-medium text-gray-900">
              High Priority Queue
            </label>
            <p className="text-xs text-gray-600 mt-1">
              Skip ahead of normal evaluations (limited availability)
            </p>
          </div>
          <button
            type="button"
            onClick={() => handleChange('priority', !config.priority)}
            disabled={disabled}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
              config.priority ? 'bg-blue-600' : 'bg-gray-200'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            role="switch"
            aria-checked={config.priority}
            aria-labelledby="priority"
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                config.priority ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
        {config.priority && (
          <div className="mt-2 text-xs text-blue-700">
            ⚡ This evaluation will be processed with high priority
          </div>
        )}
      </div>

      {/* Configuration Summary */}
      <div className="mt-4 p-3 bg-gray-50 rounded-md">
        <p className="text-sm text-gray-600">
          Your code will run for up to <span className="font-medium">{config.timeout}s</span> with{' '}
          <span className="font-medium">{config.memoryLimit}MB</span> of memory using{' '}
          <span className="font-medium">Python {config.pythonVersion}</span>
          {config.priority && (
            <span className="text-blue-600 font-medium"> with high priority</span>
          )}
        </p>
      </div>
    </div>
  )
}
