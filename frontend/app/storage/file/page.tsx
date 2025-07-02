'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface FileInfo {
  path: string
  size: number
  modified: string
}

interface FileSystemDetails {
  backend: string
  path: string
  files: FileInfo[]
  total_files: number
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

export default function FilePage() {
  const [details, setDetails] = useState<FileSystemDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set())
  const router = useRouter()

  useEffect(() => {
    void fetchFileDetails()
  }, [])

  const fetchFileDetails = async () => {
    try {
      const response = await fetch('http://localhost:8082/storage/file/details')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = (await response.json()) as FileSystemDetails
      setDetails(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch file details')
    } finally {
      setLoading(false)
    }
  }

  const togglePath = (path: string) => {
    setExpandedPaths(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  // Group files by directory
  const groupFilesByDirectory = (files: FileInfo[]) => {
    const grouped: Record<string, FileInfo[]> = {}

    files.forEach(file => {
      const parts = file.path.split('/')
      const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : '/'

      if (!grouped[dir]) {
        grouped[dir] = []
      }
      grouped[dir].push(file)
    })

    return grouped
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-lg">Loading file system details...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-red-600">Error: {error}</div>
      </div>
    )
  }

  if (!details) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-600">No file system data available</div>
      </div>
    )
  }

  const groupedFiles = groupFilesByDirectory(details.files)
  const directories = Object.keys(groupedFiles).sort()

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">File System Storage</h1>
              <p className="text-sm text-gray-600 mt-1">Storage path: {details.path}</p>
            </div>
            <button
              onClick={() => router.push('/storage')}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              Back to Overview
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Summary Statistics */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Storage Summary</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-2xl font-bold text-gray-900">{details.total_files}</div>
              <div className="text-sm text-gray-600">Total Files</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {formatBytes(details.files.reduce((sum, f) => sum + f.size, 0))}
              </div>
              <div className="text-sm text-gray-600">Total Size</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{directories.length}</div>
              <div className="text-sm text-gray-600">Directories</div>
            </div>
          </div>
        </div>

        {/* Top 10 Largest Files */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Largest Files</h2>
          <div className="space-y-2">
            {details.files.slice(0, 10).map((file, index) => (
              <div
                key={file.path}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
              >
                <div className="flex-1">
                  <div className="font-mono text-sm text-gray-900">{file.path}</div>
                  <div className="text-xs text-gray-500">Modified: {formatDate(file.modified)}</div>
                </div>
                <div className="text-right">
                  <div className="font-medium">{formatBytes(file.size)}</div>
                  <div className="text-xs text-gray-500">#{index + 1}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Directory Browser */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Directory Browser</h2>
          <div className="space-y-2">
            {directories.map(dir => {
              const files = groupedFiles[dir] || []
              const isExpanded = expandedPaths.has(dir)
              const totalSize = files.reduce((sum, f) => sum + f.size, 0)

              return (
                <div key={dir} className="border border-gray-200 rounded-md">
                  <div
                    className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50"
                    onClick={() => togglePath(dir)}
                  >
                    <div className="flex items-center space-x-2">
                      <svg
                        className={`w-4 h-4 text-gray-400 transform transition-transform ${
                          isExpanded ? 'rotate-90' : ''
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                      <svg
                        className="w-5 h-5 text-blue-500"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                      </svg>
                      <span className="font-mono text-sm">{dir === '/' ? 'root' : dir}</span>
                    </div>
                    <div className="text-sm text-gray-500">
                      {files.length} files • {formatBytes(totalSize)}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="border-t border-gray-200">
                      {files.map(file => (
                        <div
                          key={file.path}
                          className="flex items-center justify-between px-6 py-2 hover:bg-gray-50"
                        >
                          <div className="flex items-center space-x-2">
                            <svg
                              className="w-4 h-4 text-gray-400"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path
                                fillRule="evenodd"
                                d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-5L9 2H4z"
                                clipRule="evenodd"
                              />
                            </svg>
                            <span className="font-mono text-sm text-gray-700">
                              {file.path.split('/').pop()}
                            </span>
                          </div>
                          <div className="text-sm text-gray-500">{formatBytes(file.size)}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
