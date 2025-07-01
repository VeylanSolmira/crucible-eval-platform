'use client'

import React, { useEffect, useState, useRef } from 'react';
import { useEvaluationLogs, useUpdateEvaluationStatus, useKillEvaluation } from '@/hooks/useEvaluation';
import { Toast } from './Toast';

interface ExecutionMetrics {
  cpuUsage: number;
  memoryUsage: number;
  memoryLimit: number;
  elapsedTime: number;
  stdout: string;
  stderr: string;
}

interface ExecutionMonitorProps {
  evalId: string | null;
  isRunning: boolean;
  onKill?: () => void;
}

export const ExecutionMonitor: React.FC<ExecutionMonitorProps> = ({
  evalId,
  isRunning,
  onKill,
}) => {
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [showKillConfirm, setShowKillConfirm] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [showStatusDialog, setShowStatusDialog] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [metrics, setMetrics] = useState<ExecutionMetrics>({
    cpuUsage: 0,
    memoryUsage: 0,
    memoryLimit: 512,
    elapsedTime: 0,
    stdout: '',
    stderr: '',
  });
  
  const [autoScroll, setAutoScroll] = useState(true);
  const outputEndRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef<number | null>(null);
  const metricsIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Fetch real logs from the API
  const { data: logs } = useEvaluationLogs(evalId);
  const updateStatusMutation = useUpdateEvaluationStatus();
  const killMutation = useKillEvaluation();

  // Calculate elapsed time based on evaluation data
  useEffect(() => {
    if (!evalId || !logs) return undefined;
    
    // Calculate elapsed time immediately on mount
    const calculateElapsedTime = () => {
      if (logs.runtime_ms) {
        // If we have runtime_ms, use it (most accurate)
        return Math.floor(logs.runtime_ms / 1000);
      } else if (logs.completed_at && logs.started_at) {
        // If completed, calculate duration
        const duration = new Date(logs.completed_at).getTime() - new Date(logs.started_at).getTime();
        return Math.floor(duration / 1000);
      } else if (logs.started_at) {
        // If still running or incomplete, calculate from start time
        const duration = Date.now() - new Date(logs.started_at).getTime();
        return Math.floor(duration / 1000);
      } else if (logs.created_at) {
        // Fallback to created_at if no started_at
        const duration = Date.now() - new Date(logs.created_at).getTime();
        return Math.floor(duration / 1000);
      }
      return 0; // Only return 0 if we have no timing info at all
    };

    // Set initial elapsed time
    setMetrics(prev => ({
      ...prev,
      elapsedTime: calculateElapsedTime(),
    }));
    
    if (isRunning && logs.started_at) {
      // For running evaluations with a start time, update continuously
      const startTime = new Date(logs.started_at).getTime();
      startTimeRef.current = startTime;
      
      // Update elapsed time every 100ms
      metricsIntervalRef.current = setInterval(() => {
        setMetrics(prev => ({
          ...prev,
          elapsedTime: Math.floor((Date.now() - startTime) / 1000),
        }));
      }, 100);

      return () => {
        if (metricsIntervalRef.current) {
          clearInterval(metricsIntervalRef.current);
        }
      };
    } else {
      // For non-running evaluations, just clear any interval
      // The elapsed time was already set above
      if (metricsIntervalRef.current) {
        clearInterval(metricsIntervalRef.current);
      }
    }
    
    return undefined;
  }, [isRunning, evalId, logs]);

  // Update metrics when logs data changes
  useEffect(() => {
    if (logs) {
      setMetrics(prev => ({
        ...prev,
        stdout: logs.output || '',
        stderr: logs.error || '',
      }));
    }
  }, [logs]);

  useEffect(() => {
    // Only auto-scroll when there's an active evaluation running
    // This prevents scrolling on initial page load
    if (autoScroll && outputEndRef.current && isRunning && evalId) {
      // Scroll only within the container, not the entire page
      const container = outputEndRef.current.parentElement;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }, [metrics.stdout, metrics.stderr, autoScroll, isRunning, evalId]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const cpuPercentage = Math.round(metrics.cpuUsage);
  const memoryPercentage = Math.round((metrics.memoryUsage / metrics.memoryLimit) * 100);

  // Get status display info
  const getStatusBadge = () => {
    const status = logs?.status || 'unknown';
    const statusConfig = {
      running: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Running' },
      completed: { bg: 'bg-green-100', text: 'text-green-700', label: 'Completed' },
      failed: { bg: 'bg-red-100', text: 'text-red-700', label: 'Failed' },
      queued: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Queued' },
      unknown: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Unknown' }
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.unknown;
    return config;
  };
  
  const statusBadge = getStatusBadge();
  
  // Calculate if this evaluation might be stuck
  const isStuck = React.useMemo(() => {
    if (!logs || logs.status !== 'running') return false;
    
    // If running for more than 5 minutes with no recent logs
    const lastLogTime = logs.last_update || logs.started_at;
    if (lastLogTime) {
      const timeSinceLastUpdate = Date.now() - new Date(lastLogTime).getTime();
      return timeSinceLastUpdate > 5 * 60 * 1000; // 5 minutes
    }
    return false;
  }, [logs]);

  // Handle kill action
  const handleKill = async () => {
    if (!evalId || !onKill) return;

    try {
      await killMutation.mutateAsync(evalId);
      setToast({ message: 'Evaluation killed successfully', type: 'success' });
      setShowKillConfirm(false);
      onKill();
    } catch (error) {
      // If the evaluation is not running, update its status instead
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (errorMessage.includes('not running') || errorMessage.includes('404')) {
        console.info(`[INFO] Evaluation ${evalId} not running on any executor, updating status instead`);
        try {
          await updateStatusMutation.mutateAsync({
            evalId,
            status: 'failed',
            reason: 'Evaluation was not running but marked as running'
          });
          setToast({ message: 'Status updated to failed', type: 'success' });
        } catch (updateError) {
          setToast({ message: `Failed to update status: ${updateError}`, type: 'error' });
        }
      } else {
        setToast({ message: `Failed to kill evaluation: ${errorMessage}`, type: 'error' });
      }
      setShowKillConfirm(false);
    }
  };
  
  // Show helpful message if no evaluation selected
  if (!evalId) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="text-center py-12">
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Evaluation Selected</h3>
          <p className="text-gray-500">Submit an evaluation or select one from the running list to view logs</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col h-full p-6 bg-white overflow-y-auto min-w-0">
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-gray-900">Execution Monitor</h2>
          {evalId && (
            <span className={`px-3 py-1 text-sm font-medium rounded-full ${statusBadge.bg} ${statusBadge.text}`}>
              {statusBadge.label}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isRunning && onKill && (
            <button
              onClick={() => setShowKillConfirm(true)}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-sm font-medium"
            >
              🛑 Kill Execution
            </button>
          )}
          {!isRunning && logs?.status && logs.status !== 'completed' && logs.status !== 'failed' && (
            <span className="text-xs text-gray-500 italic">
              Use admin controls to update status
            </span>
          )}
        </div>
      </div>

      {/* Kill Confirmation Inline */}
      {showKillConfirm && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-gray-700 mb-3">
            Are you sure you want to kill evaluation {evalId}? This will terminate the execution immediately.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleKill}
              className="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
              disabled={killMutation.isPending}
            >
              {killMutation.isPending ? 'Killing...' : 'Yes, Kill Execution'}
            </button>
            <button
              onClick={() => setShowKillConfirm(false)}
              className="px-3 py-1 bg-gray-300 text-gray-700 text-xs rounded hover:bg-gray-400"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-3 gap-4 mb-6 flex-shrink-0">
        {/* Elapsed Time */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600 mb-1">Elapsed Time</div>
          <div className="text-2xl font-mono font-semibold text-gray-900">
            {formatTime(metrics.elapsedTime)}
          </div>
        </div>

        {/* CPU Usage */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600 mb-1">CPU Usage</div>
          <div className="flex items-end gap-2">
            <div className="text-2xl font-mono font-semibold text-gray-900">
              {cpuPercentage}%
            </div>
            <div className="flex-1 mb-1">
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-300 ${
                    cpuPercentage > 80 ? 'bg-red-500' : 
                    cpuPercentage > 60 ? 'bg-yellow-500' : 
                    'bg-green-500'
                  }`}
                  style={{ width: `${cpuPercentage}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Memory Usage */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600 mb-1">Memory Usage</div>
          <div className="flex items-end gap-2">
            <div className="text-lg font-mono font-semibold text-gray-900">
              {metrics.memoryUsage}/{metrics.memoryLimit}MB
            </div>
            <div className="flex-1 mb-1">
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-300 ${
                    memoryPercentage > 90 ? 'bg-red-500' : 
                    memoryPercentage > 75 ? 'bg-yellow-500' : 
                    'bg-blue-500'
                  }`}
                  style={{ width: `${memoryPercentage}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Output Display */}
      <div className="space-y-4 flex-1 overflow-y-auto min-h-0">
        {/* Stdout */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-sm font-medium text-gray-700">Standard Output</h3>
            <label className="flex items-center text-sm text-gray-600">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="mr-2"
              />
              Auto-scroll
            </label>
          </div>
          <div className="bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-sm h-48 overflow-auto">
            {metrics.stdout || (
              <span className="text-gray-500">
                {isRunning ? 'Waiting for output...' : 'No output yet'}
              </span>
            )}
            <div ref={outputEndRef} />
          </div>
        </div>

        {/* Stderr */}
        {metrics.stderr && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Standard Error</h3>
            <div className="bg-red-50 text-red-800 rounded-lg p-4 font-mono text-sm h-32 overflow-auto">
              {metrics.stderr}
            </div>
          </div>
        )}
      </div>

      {/* Status Indicator */}
      <div className="mt-4 flex items-center justify-between text-sm">
        <div className="flex items-center">
          {isRunning ? (
            <>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2" />
              <span className="text-green-700">Execution in progress...</span>
              {isStuck && (
                <span className="ml-2 px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded-full">
                  Possibly stuck
                </span>
              )}
            </>
          ) : (
            <>
              <div className="w-2 h-2 bg-gray-400 rounded-full mr-2" />
              <span className="text-gray-600">Not running</span>
            </>
          )}
        </div>
        
        {/* Debug Toggle */}
        <button
          onClick={() => setShowDebugPanel(!showDebugPanel)}
          className="text-sm font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-50 px-3 py-1.5 rounded-md flex items-center gap-2 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          {showDebugPanel ? 'Hide' : 'Show'} Admin Controls
        </button>
      </div>
      
      {/* Debug Panel */}
      {showDebugPanel && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Debug Information & Admin Controls</h4>
          
          <div className="space-y-2 text-xs text-gray-700 mb-4">
            <div><strong>Eval ID:</strong> {evalId}</div>
            <div><strong>Status:</strong> {logs?.status || 'unknown'}</div>
            <div><strong>Started:</strong> {logs?.started_at || 'N/A'}</div>
            <div><strong>Last Update:</strong> {logs?.last_update || 'N/A'}</div>
            <div><strong>Container ID:</strong> {logs?.container_id || 'N/A'}</div>
            <div><strong>Executor:</strong> {logs?.executor_id || 'N/A'}</div>
            {isStuck && (
              <div className="text-orange-600">
                <strong>⚠️ Warning:</strong> No updates for over 5 minutes
              </div>
            )}
          </div>
          
          {/* Admin Actions */}
          <div className="border-t border-gray-200 pt-3">
            <h5 className="text-xs font-medium text-gray-700 mb-2">Admin Actions</h5>
            
            {/* Admin controls layout */}
            <div className="flex gap-4 items-start">
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={() => {
                    setShowConfirmDialog(true);
                    setShowStatusDialog(false);
                  }}
                  className="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:opacity-50"
                  disabled={updateStatusMutation.isPending || showConfirmDialog || showStatusDialog}
                >
                  Mark as Failed
                </button>
                
                <button
                  onClick={() => {
                    setShowStatusDialog(true);
                    setShowConfirmDialog(false);
                  }}
                  className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50"
                  disabled={updateStatusMutation.isPending || showConfirmDialog || showStatusDialog}
                >
                  Change Status
                </button>
                
                <button
                  onClick={() => {
                    // TODO: Refresh data
                    window.location.reload();
                  }}
                  className="px-3 py-1 bg-gray-600 text-white text-xs rounded hover:bg-gray-700"
                >
                  Refresh
                </button>
              </div>
              
              {/* Show forms to the right of buttons */}
              {showConfirmDialog && (
                <div className="flex-1 p-3 bg-white rounded border border-red-200">
                  <p className="text-sm text-gray-700 mb-3">
                    Are you sure you want to mark this evaluation as failed? This action cannot be undone.
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={async () => {
                        try {
                          await updateStatusMutation.mutateAsync({
                            evalId: evalId!,
                            status: 'failed',
                            reason: 'Manually marked as failed due to stuck/unresponsive state'
                          });
                          setToast({ message: 'Evaluation marked as failed', type: 'success' });
                        } catch (error) {
                          setToast({ message: `Failed to update status: ${error}`, type: 'error' });
                        }
                        setShowConfirmDialog(false);
                      }}
                      className="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                      disabled={updateStatusMutation.isPending}
                    >
                      {updateStatusMutation.isPending ? 'Updating...' : 'Confirm - Mark as Failed'}
                    </button>
                    <button
                      onClick={() => setShowConfirmDialog(false)}
                      className="px-3 py-1 bg-gray-300 text-gray-700 text-xs rounded hover:bg-gray-400"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
              
              {showStatusDialog && (
                <div className="flex-1 p-3 bg-white rounded border border-blue-200">
                  <p className="text-sm text-gray-700 mb-3">Change evaluation status to:</p>
                  <div className="space-y-2 mb-3">
                    {['completed', 'failed', 'cancelled'].map((status) => (
                      <label key={status} className="flex items-center text-xs">
                        <input
                          type="radio"
                          name="status"
                          value={status}
                          onChange={(e) => setSelectedStatus(e.target.value)}
                          className="mr-2"
                        />
                        <span className="capitalize">{status}</span>
                      </label>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={async () => {
                        if (selectedStatus) {
                          try {
                            await updateStatusMutation.mutateAsync({
                              evalId: evalId!,
                              status: selectedStatus,
                              reason: `Manually changed to ${selectedStatus}`
                            });
                            setToast({ message: `Evaluation marked as ${selectedStatus}`, type: 'success' });
                          } catch (error) {
                            setToast({ message: `Failed to update status: ${error}`, type: 'error' });
                          }
                        }
                        setShowStatusDialog(false);
                        setSelectedStatus('');
                      }}
                      className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                      disabled={updateStatusMutation.isPending}
                    >
                      {updateStatusMutation.isPending ? 'Updating...' : 'Confirm Change'}
                    </button>
                    <button
                      onClick={() => {
                        setShowStatusDialog(false);
                        setSelectedStatus('');
                      }}
                      className="px-3 py-1 bg-gray-300 text-gray-700 text-xs rounded hover:bg-gray-400"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      
      </div>
      
      {/* Toast Notifications */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </>
  );
};