'use client'

import { useState, useMemo, useEffect, useRef } from 'react'
import { useKillEvaluation, useEvaluationHistory } from '@/hooks/useEvaluation'
import { useRunningEvaluations } from '@/hooks/useRunningEvaluations'
import { ExecutionMonitor } from './ExecutionMonitor'
import { log } from '@/src/utils/logger'
import { formatDistanceToNow } from 'date-fns'
import { EvaluationStatus } from '@/shared/generated/typescript/evaluation-status'
import { getExitCodeInfo, getExitCodeBadge, getExitCodeColorClasses } from '../utils/exit-codes'

type StatusFilter = 'all' | EvaluationStatus

interface Execution {
  eval_id: string
  status: EvaluationStatus | string
  created_at: string
  started_at?: string
  completed_at?: string
  output?: string
  error?: string
  executor_id?: string
  exit_code?: number
}

interface ExecutionsProps {
  // Recently submitted evaluation IDs to highlight
  recentEvalIds?: string[]
}

export function Executions({ recentEvalIds = [] }: ExecutionsProps) {
  const [selectedExecId, setSelectedExecId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [currentPage, setCurrentPage] = useState(0)
  const [showDropdown, setShowDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const pageSize = 100

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Fetch data from various sources
  const { data: runningData } = useRunningEvaluations()
  const { data: historyData, refetch: refetchHistory } = useEvaluationHistory(
    currentPage, 
    pageSize,
    statusFilter === 'all' ? undefined : statusFilter
  )
  const killMutation = useKillEvaluation()

  // Refetch history when new evaluations are submitted
  useEffect(() => {
    if (recentEvalIds.length > 0) {
      // Refetch history after a short delay to catch new evaluations
      const timer = setTimeout(() => void refetchHistory(), 1000)
      return () => clearTimeout(timer)
    }
    return undefined
  }, [recentEvalIds, refetchHistory])

  // Combine all executions
  const allExecutions: Execution[] = useMemo(() => {
    const running = runningData?.evaluations || []
    const historical = historyData?.evaluations || []

    // Transform running evaluations to common format
    const runningExecs: Execution[] = running.map(e => ({
      eval_id: e.eval_id,
      status: EvaluationStatus.RUNNING, // Running endpoint only returns currently running evaluations
      created_at: e.started_at || new Date().toISOString(),
      started_at: e.started_at,
      executor_id: e.executor_id,
    }))

    // Transform historical evaluations
    const historicalExecs: Execution[] = historical.map(e => {
      const exec: Execution = {
        eval_id: e.eval_id,
        // Validate status is one of our known values, default to 'queued' if unknown
        status: Object.values(EvaluationStatus).includes(e.status as EvaluationStatus)
          ? (e.status as EvaluationStatus)
          : EvaluationStatus.QUEUED,
        created_at: e.created_at || new Date().toISOString(),
      }

      // Only add optional properties if they have values
      if (e.started_at) exec.started_at = e.started_at
      if (e.completed_at) exec.completed_at = e.completed_at
      if (e.output) exec.output = e.output
      if (e.error) exec.error = e.error
      if (e.exit_code !== undefined) exec.exit_code = e.exit_code

      return exec
    })

    // Combine both sources
    const combined = [...runningExecs, ...historicalExecs]

    // Remove duplicates (keeping the most recent/complete version)
    const uniqueMap = new Map<string, Execution>()
    combined.forEach(exec => {
      const existing = uniqueMap.get(exec.eval_id)
      // Keep running status over historical, or more complete data
      if (
        !existing ||
        (exec.status === 'running' && existing.status !== 'running') ||
        (exec.completed_at && !existing.completed_at)
      ) {
        uniqueMap.set(exec.eval_id, exec)
      }
    })

    // Sort by status (running first) then by time
    return Array.from(uniqueMap.values()).sort((a, b) => {
      if (a.status === EvaluationStatus.RUNNING && b.status !== EvaluationStatus.RUNNING) return -1
      if (a.status !== EvaluationStatus.RUNNING && b.status === EvaluationStatus.RUNNING) return 1
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  }, [runningData, historyData])

  // Filter executions
  const filteredExecutions = useMemo(() => {
    if (statusFilter === 'all') return allExecutions
    return allExecutions.filter(e => e.status === statusFilter)
  }, [allExecutions, statusFilter])

  // Reset selection when page changes
  useEffect(() => {
    // Check if selected execution is still in the current page
    if (selectedExecId && !allExecutions.some(e => e.eval_id === selectedExecId)) {
      setSelectedExecId(null)
    }
  }, [currentPage, selectedExecId, allExecutions])

  // Get selected execution
  const selectedExecution = selectedExecId
    ? allExecutions.find(e => e.eval_id === selectedExecId)
    : null

  const handleKill = async () => {
    if (!selectedExecId) return

    // Check if the evaluation is actually running
    const execution = allExecutions.find(e => e.eval_id === selectedExecId)
    if (!execution || execution.status !== EvaluationStatus.RUNNING) {
      alert('This evaluation is not currently running')
      return
    }

    if (!confirm(`Are you sure you want to kill evaluation ${selectedExecId}?`)) {
      return
    }

    try {
      await killMutation.mutateAsync(selectedExecId)
      // Don't clear selection, let the status update
    } catch (err) {
      log.error(`Failed to kill evaluation ${selectedExecId}:`, err)
      // Check if it's a 404 (not running)
      const errorMessage = err instanceof Error ? err.message : String(err)
      if (errorMessage.includes('not running') || errorMessage.includes('404')) {
        alert('This evaluation is no longer running')
      } else {
        alert('Failed to kill evaluation: ' + errorMessage)
      }
    }
  }

  // Debug log to verify selection is working
  useEffect(() => {
    if (selectedExecId) {
      log.info(`Selected execution: ${selectedExecId}`, {
        selectedExecution,
        hasExecution: !!selectedExecution,
        allExecutionsCount: allExecutions.length,
        allExecutionIds: allExecutions.map(e => e.eval_id),
      })
    }
  }, [selectedExecId, selectedExecution, allExecutions])

  const getStatusBadge = (status: string) => {
    const configs = {
      [EvaluationStatus.SUBMITTED]: { bg: 'bg-gray-100', text: 'text-gray-700', dot: 'bg-gray-500', label: 'Submitted' },
      [EvaluationStatus.QUEUED]: { bg: 'bg-yellow-100', text: 'text-yellow-700', dot: 'bg-yellow-500', label: 'Queued' },
      [EvaluationStatus.PROVISIONING]: { bg: 'bg-purple-100', text: 'text-purple-700', dot: 'bg-purple-500', label: 'Provisioning' },
      [EvaluationStatus.RUNNING]: { bg: 'bg-blue-100', text: 'text-blue-700', dot: 'bg-blue-500', label: 'Running' },
      [EvaluationStatus.COMPLETED]: { bg: 'bg-green-100', text: 'text-green-700', dot: 'bg-green-500', label: 'Completed' },
      [EvaluationStatus.FAILED]: { bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500', label: 'Failed' },
      [EvaluationStatus.CANCELLED]: { bg: 'bg-orange-100', text: 'text-orange-700', dot: 'bg-orange-500', label: 'Cancelled' },
    }
    return configs[status as keyof typeof configs] || configs[EvaluationStatus.QUEUED]
  }

  return (
    <div className="bg-white rounded-lg shadow-sm h-[600px]">
      <div className="flex h-full">
        {/* Left Panel - Execution List */}
        <div className="w-1/3 min-w-0 max-w-md border-r border-gray-200 flex flex-col overflow-hidden">
          {/* Header with Filters */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-gray-900">Recent Executions</h2>
              <span className="text-sm text-gray-500">
                Page {currentPage + 1} ({allExecutions.length} loaded)
              </span>
            </div>

            {/* Status Filter - Primary buttons + Dropdown */}
            <div className="flex items-center gap-2">
              {/* Primary status filters */}
              <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
                {(['all', EvaluationStatus.RUNNING, EvaluationStatus.FAILED, EvaluationStatus.COMPLETED] as StatusFilter[]).map(filter => {
                  const count =
                    filter === 'all'
                      ? allExecutions.length
                      : allExecutions.filter(e => e.status === filter).length

                  const label = filter === 'all' ? 'All' : getStatusBadge(filter).label

                  return (
                    <button
                      key={filter}
                      onClick={() => setStatusFilter(filter)}
                      className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                        statusFilter === filter
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      {label}
                      {count > 0 && <span className="ml-1 text-xs">({count})</span>}
                    </button>
                  )
                })}
              </div>

              {/* Dropdown for other statuses */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setShowDropdown(!showDropdown)}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {!['all', EvaluationStatus.RUNNING, EvaluationStatus.FAILED, EvaluationStatus.COMPLETED].includes(statusFilter) && (
                    <span className="text-blue-600">{getStatusBadge(statusFilter).label}</span>
                  )}
                  {['all', EvaluationStatus.RUNNING, EvaluationStatus.FAILED, EvaluationStatus.COMPLETED].includes(statusFilter) && (
                    <span>More</span>
                  )}
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {showDropdown && (
                  <div className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5">
                    <div className="py-1">
                      {Object.values(EvaluationStatus)
                        .filter(status => ![EvaluationStatus.RUNNING, EvaluationStatus.FAILED, EvaluationStatus.COMPLETED].includes(status))
                        .map(status => {
                          const count = allExecutions.filter(e => e.status === status).length
                          const badge = getStatusBadge(status)
                          
                          return (
                            <button
                              key={status}
                              onClick={() => {
                                setStatusFilter(status)
                                setShowDropdown(false)
                              }}
                              className="flex w-full items-center justify-between px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                            >
                              <span className="flex items-center gap-2">
                                <span className={`inline-flex h-2 w-2 rounded-full ${badge.dot}`} />
                                {badge.label}
                              </span>
                              {count > 0 && (
                                <span className="text-xs text-gray-500">({count})</span>
                              )}
                            </button>
                          )
                        })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Execution List */}
          <div className="flex-1 overflow-y-auto">
            {filteredExecutions.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <p className="text-sm">No executions found</p>
                {statusFilter !== 'all' && (
                  <button
                    onClick={() => setStatusFilter('all')}
                    className="mt-2 text-sm text-blue-600 hover:text-blue-700"
                  >
                    Clear filter
                  </button>
                )}
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredExecutions.map(execution => {
                  const status = getStatusBadge(execution.status)
                  const isSelected = execution.eval_id === selectedExecId

                  return (
                    <button
                      key={execution.eval_id}
                      onClick={() => setSelectedExecId(execution.eval_id)}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors min-w-0 ${
                        isSelected ? 'bg-blue-50 hover:bg-blue-50' : ''
                      }`}
                      type="button"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono text-sm text-gray-900 truncate block max-w-[200px]">
                              {execution.eval_id}
                            </span>
                            <span
                              className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${status.bg} ${status.text}`}
                            >
                              {execution.status === EvaluationStatus.RUNNING && (
                                <span
                                  className={`w-1.5 h-1.5 ${status.dot} rounded-full animate-pulse mr-1`}
                                />
                              )}
                              {status.label}
                            </span>
                          </div>

                          <div className="flex items-center gap-3 text-xs text-gray-500">
                            <span>
                              {formatDistanceToNow(new Date(execution.created_at), {
                                addSuffix: true,
                              })}
                            </span>
                            {execution.executor_id && <span>• {execution.executor_id}</span>}
                            {execution.exit_code !== undefined && (
                              <span
                                className={`flex items-center gap-1 ${getExitCodeColorClasses(execution.exit_code).text}`}
                                title={getExitCodeInfo(execution.exit_code).description}
                              >
                                • {getExitCodeBadge(execution.exit_code)}
                                {execution.exit_code !== 0 && execution.exit_code !== 137 && execution.exit_code !== 124 && (
                                  <span className="text-xs">({execution.exit_code})</span>
                                )}
                              </span>
                            )}
                          </div>
                        </div>

                        {isSelected && (
                          <div className="ml-2">
                            <svg
                              className="w-4 h-4 text-blue-600"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path
                                fillRule="evenodd"
                                d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                                clipRule="evenodd"
                              />
                            </svg>
                          </div>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Pagination Controls */}
          <div className="p-3 border-t border-gray-200 flex items-center justify-between">
            <button
              onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
              disabled={currentPage === 0}
              className="flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
              Previous
            </button>

            <span className="text-sm text-gray-700">
              {allExecutions.length === 0
                ? 'No results'
                : statusFilter === 'all'
                  ? `${currentPage * pageSize + 1}-${currentPage * pageSize + allExecutions.length} of ${historyData?.total || 0}`
                  : `Showing ${filteredExecutions.length} ${statusFilter} (page ${currentPage + 1})`}
            </span>

            <button
              onClick={() => setCurrentPage(prev => prev + 1)}
              disabled={!historyData?.hasMore}
              className="flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
              <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Right Panel - Execution Details */}
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
          {selectedExecution ? (
            <ExecutionMonitor
              evalId={selectedExecution.eval_id}
              isRunning={selectedExecution.status === EvaluationStatus.RUNNING}
              onKill={() => void handleKill()}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
                <p className="mt-2 text-sm">Select an execution to view details</p>
                {selectedExecId && (
                  <p className="mt-1 text-xs text-red-500">Selected: {selectedExecId}</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Keep the old components for backward compatibility
interface RunningEvaluationsProps {
  onSelectEvaluation?: (evalId: string) => void
  selectedEvalId?: string
}

export function RunningEvaluations(_props: RunningEvaluationsProps) {
  // Just delegate to the new Executions component
  return <Executions />
}

export function LogStream(_props: { evalId: string }) {
  // This is now handled by ExecutionMonitor
  return null
}
