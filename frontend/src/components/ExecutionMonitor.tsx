'use client'

import React, { useEffect, useState, useRef } from 'react';

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

  useEffect(() => {
    if (isRunning && evalId) {
      startTimeRef.current = Date.now();
      
      // Update elapsed time every 100ms
      metricsIntervalRef.current = setInterval(() => {
        if (startTimeRef.current) {
          setMetrics(prev => ({
            ...prev,
            elapsedTime: Math.floor((Date.now() - startTimeRef.current!) / 1000),
          }));
        }
      }, 100);

      // TODO: Connect to WebSocket for real-time metrics
      // For now, simulate some data
      const simulateMetrics = () => {
        setMetrics(prev => ({
          ...prev,
          cpuUsage: Math.min(100, prev.cpuUsage + Math.random() * 10),
          memoryUsage: Math.min(prev.memoryLimit, prev.memoryUsage + Math.random() * 20),
          stdout: prev.stdout + `Processing... (${new Date().toLocaleTimeString()})\n`,
        }));
      };

      const simulationInterval = setInterval(simulateMetrics, 1000);

      return () => {
        if (metricsIntervalRef.current) {
          clearInterval(metricsIntervalRef.current);
        }
        clearInterval(simulationInterval);
      };
    } else {
      // Reset when not running
      startTimeRef.current = null;
      if (metricsIntervalRef.current) {
        clearInterval(metricsIntervalRef.current);
      }
    }
  }, [isRunning, evalId]);

  useEffect(() => {
    if (autoScroll && outputEndRef.current) {
      outputEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [metrics.stdout, metrics.stderr, autoScroll]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const cpuPercentage = Math.round(metrics.cpuUsage);
  const memoryPercentage = Math.round((metrics.memoryUsage / metrics.memoryLimit) * 100);

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Execution Monitor</h2>
        {isRunning && (
          <button
            onClick={onKill}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-sm font-medium"
          >
            🛑 Kill Execution
          </button>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-3 gap-4 mb-6">
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
      <div className="space-y-4">
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
      <div className="mt-4 flex items-center text-sm">
        {isRunning ? (
          <>
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2" />
            <span className="text-green-700">Execution in progress...</span>
          </>
        ) : (
          <>
            <div className="w-2 h-2 bg-gray-400 rounded-full mr-2" />
            <span className="text-gray-600">Not running</span>
          </>
        )}
      </div>
    </div>
  );
};