'use client'

import React, { useState } from 'react';

interface ParsedError {
  type: string;
  message: string;
  traceback?: Array<{
    file: string;
    line: number;
    function: string;
    code?: string;
  }>;
  lineNumber?: number;
  columnNumber?: number;
}

interface ErrorDisplayProps {
  error: string;
  code?: string;
  onLineClick?: (lineNumber: number) => void;
}

const COMMON_ERRORS = {
  'SyntaxError': {
    explanation: 'Your code contains invalid Python syntax.',
    tips: [
      'Check for missing colons after if/for/while statements',
      'Ensure proper indentation (use 4 spaces)',
      'Look for unclosed brackets, quotes, or parentheses',
    ],
  },
  'IndentationError': {
    explanation: 'Python uses indentation to define code blocks.',
    tips: [
      'Use consistent indentation (4 spaces recommended)',
      'Don\'t mix tabs and spaces',
      'Ensure all code in a block has the same indentation',
    ],
  },
  'NameError': {
    explanation: 'You\'re trying to use a variable or function that doesn\'t exist.',
    tips: [
      'Check spelling of variable/function names',
      'Ensure variables are defined before use',
      'Import required modules',
    ],
  },
  'TypeError': {
    explanation: 'You\'re using an operation on the wrong type of data.',
    tips: [
      'Check data types match expected operations',
      'Convert types if needed (e.g., str() or int())',
      'Verify function arguments',
    ],
  },
  'ImportError': {
    explanation: 'The module you\'re trying to import cannot be found.',
    tips: [
      'Standard library modules are available',
      'External packages may not be installed',
      'Check module name spelling',
    ],
  },
  'ZeroDivisionError': {
    explanation: 'You\'re trying to divide by zero.',
    tips: [
      'Add checks before division operations',
      'Use try/except blocks for safe division',
      'Consider edge cases in your logic',
    ],
  },
  'IndexError': {
    explanation: 'You\'re trying to access an index that doesn\'t exist.',
    tips: [
      'Check list/string length before accessing',
      'Remember indices start at 0',
      'Use negative indices carefully',
    ],
  },
};

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  code,
  onLineClick,
}) => {
  const [showDetails, setShowDetails] = useState(true);
  const [showEnvironment, setShowEnvironment] = useState(false);

  const parseError = (errorText: string): ParsedError => {
    const lines = errorText.split('\n');
    const parsed: ParsedError = {
      type: 'Unknown Error',
      message: errorText,
      traceback: [],
    };

    // Extract error type and message
    const errorMatch = errorText.match(/(\w+Error): (.+)/);
    if (errorMatch) {
      parsed.type = errorMatch[1];
      parsed.message = errorMatch[2];
    }

    // Parse traceback
    let inTraceback = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      if (line.includes('Traceback (most recent call last)')) {
        inTraceback = true;
        continue;
      }

      if (inTraceback && line.match(/^\s*File "(.+)", line (\d+), in (.+)$/)) {
        const match = line.match(/^\s*File "(.+)", line (\d+), in (.+)$/);
        if (match) {
          const frame = {
            file: match[1],
            line: parseInt(match[2]),
            function: match[3],
            code: '',
          };

          // Get the code line if available
          if (i + 1 < lines.length && lines[i + 1].match(/^\s{4}/)) {
            frame.code = lines[i + 1].trim();
          }

          parsed.traceback?.push(frame);
        }
      }

      // Extract line number from syntax errors
      if (parsed.type === 'SyntaxError') {
        const lineMatch = errorText.match(/line (\d+)/);
        if (lineMatch) {
          parsed.lineNumber = parseInt(lineMatch[1]);
        }
      }
    }

    return parsed;
  };

  const parsedError = parseError(error);
  const errorInfo = COMMON_ERRORS[parsedError.type as keyof typeof COMMON_ERRORS];

  const getCodeLines = () => {
    if (!code) return [];
    return code.split('\n');
  };

  const handleLineClick = (lineNumber: number) => {
    if (onLineClick) {
      onLineClick(lineNumber);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center">
          <span className="text-2xl mr-3">⚠️</span>
          <div>
            <h2 className="text-lg font-semibold text-red-700">{parsedError.type}</h2>
            <p className="text-gray-700">{parsedError.message}</p>
          </div>
        </div>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-gray-600 hover:text-gray-900"
        >
          {showDetails ? 'Hide Details' : 'Show Details'}
        </button>
      </div>

      {showDetails && (
        <>
          {/* Error Explanation */}
          {errorInfo && (
            <div className="mb-6 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-medium text-blue-900 mb-2">What this means:</h3>
              <p className="text-blue-800 mb-3">{errorInfo.explanation}</p>
              <h4 className="font-medium text-blue-900 mb-1">Common fixes:</h4>
              <ul className="list-disc list-inside space-y-1">
                {errorInfo.tips.map((tip, idx) => (
                  <li key={idx} className="text-blue-800">{tip}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Traceback */}
          {parsedError.traceback && parsedError.traceback.length > 0 && (
            <div className="mb-6">
              <h3 className="font-medium text-gray-900 mb-3">Stack Trace:</h3>
              <div className="space-y-2">
                {parsedError.traceback.map((frame, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="font-mono text-sm">
                          <span className="text-gray-600">in</span>{' '}
                          <span className="font-medium">{frame.function}</span>
                        </div>
                        {frame.code && (
                          <div className="mt-1 font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                            {frame.code}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => handleLineClick(frame.line)}
                        className="ml-4 text-sm text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Line {frame.line} →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Code Context */}
          {code && parsedError.lineNumber && (
            <div className="mb-6">
              <h3 className="font-medium text-gray-900 mb-3">Code Context:</h3>
              <div className="bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-sm overflow-auto">
                {getCodeLines().map((line, idx) => {
                  const lineNumber = idx + 1;
                  const isErrorLine = lineNumber === parsedError.lineNumber;
                  return (
                    <div
                      key={idx}
                      className={`flex ${isErrorLine ? 'bg-red-900 bg-opacity-30' : ''}`}
                    >
                      <span className="select-none text-gray-500 mr-4 text-right" style={{ width: '3em' }}>
                        {lineNumber}
                      </span>
                      <span className={isErrorLine ? 'text-red-300' : ''}>
                        {line || ' '}
                      </span>
                    </div>
                  );
                }).slice(Math.max(0, (parsedError.lineNumber || 1) - 4), (parsedError.lineNumber || 1) + 3)}
              </div>
            </div>
          )}

          {/* Raw Error */}
          <details className="mb-6">
            <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-900 font-medium">
              Show Raw Error
            </summary>
            <pre className="mt-2 p-4 bg-gray-100 rounded-lg text-xs overflow-auto font-mono">
              {error}
            </pre>
          </details>

          {/* Environment Info */}
          <div className="border-t pt-4">
            <button
              onClick={() => setShowEnvironment(!showEnvironment)}
              className="text-sm text-gray-600 hover:text-gray-900 font-medium"
            >
              {showEnvironment ? 'Hide' : 'Show'} Environment Info
            </button>
            {showEnvironment && (
              <div className="mt-3 p-4 bg-gray-50 rounded-lg text-sm">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="font-medium">Python Version:</span> 3.11.5
                  </div>
                  <div>
                    <span className="font-medium">Container:</span> Docker
                  </div>
                  <div>
                    <span className="font-medium">Memory Limit:</span> 512MB
                  </div>
                  <div>
                    <span className="font-medium">Timeout:</span> 30s
                  </div>
                  <div>
                    <span className="font-medium">Network:</span> Isolated
                  </div>
                  <div>
                    <span className="font-medium">File System:</span> Read-only
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};