'use client'

import React, { useState } from 'react'

interface StatusChangeDialogProps {
  isOpen: boolean
  currentStatus: string
  onConfirm: (status: string, reason: string) => void
  onCancel: () => void
}

const statusOptions = [
  { value: 'failed', label: 'Failed', description: 'Mark as failed due to error or timeout' },
  { value: 'completed', label: 'Completed', description: 'Mark as successfully completed' },
  { value: 'cancelled', label: 'Cancelled', description: 'Mark as cancelled by user or admin' }
]

export function StatusChangeDialog({
  isOpen,
  currentStatus,
  onConfirm,
  onCancel
}: StatusChangeDialogProps) {
  const [selectedStatus, setSelectedStatus] = useState('failed')
  const [reason, setReason] = useState('')

  if (!isOpen) return null

  const handleConfirm = () => {
    onConfirm(selectedStatus, reason)
    // Reset form
    setSelectedStatus('failed')
    setReason('')
  }

  const handleCancel = () => {
    // Reset form
    setSelectedStatus('failed')
    setReason('')
    onCancel()
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center px-4 py-6 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={handleCancel}
        />

        {/* This element is to trick the browser into centering the modal contents. */}
        <span className="hidden sm:inline-block sm:h-screen sm:align-middle">&#8203;</span>

        {/* Modal panel */}
        <div className="inline-block transform overflow-hidden rounded-lg bg-white text-left align-bottom shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:align-middle max-h-[90vh] flex flex-col">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4 overflow-y-auto flex-1">
            <div className="sm:flex sm:items-start">
              <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
                <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left flex-1">
                <h3 className="text-lg font-medium leading-6 text-gray-900">
                  Change Evaluation Status
                </h3>
                <div className="mt-2">
                  <p className="text-sm text-gray-500 mb-4">
                    Current status: <span className="font-medium">{currentStatus}</span>
                  </p>

                  {/* Status Selection */}
                  <div className="space-y-3">
                    <label className="block text-sm font-medium text-gray-700">
                      New Status
                    </label>
                    <div className="space-y-2">
                      {statusOptions.map((option) => (
                        <label
                          key={option.value}
                          className={`relative flex cursor-pointer rounded-lg border p-4 shadow-sm focus:outline-none ${
                            selectedStatus === option.value
                              ? 'border-blue-500 ring-2 ring-blue-500'
                              : 'border-gray-300'
                          }`}
                        >
                          <input
                            type="radio"
                            name="status"
                            value={option.value}
                            checked={selectedStatus === option.value}
                            onChange={(e) => setSelectedStatus(e.target.value)}
                            className="sr-only"
                          />
                          <div className="flex flex-1">
                            <div className="flex flex-col">
                              <span className="block text-sm font-medium text-gray-900">
                                {option.label}
                              </span>
                              <span className="mt-1 flex items-center text-sm text-gray-500">
                                {option.description}
                              </span>
                            </div>
                          </div>
                          {selectedStatus === option.value && (
                            <svg
                              className="h-5 w-5 text-blue-600"
                              viewBox="0 0 20 20"
                              fill="currentColor"
                            >
                              <path
                                fillRule="evenodd"
                                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                                clipRule="evenodd"
                              />
                            </svg>
                          )}
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Reason Input */}
                  <div className="mt-4">
                    <label htmlFor="reason" className="block text-sm font-medium text-gray-700">
                      Reason (optional)
                    </label>
                    <textarea
                      id="reason"
                      rows={3}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      placeholder="Provide additional context for this status change..."
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
            <button
              type="button"
              className="inline-flex w-full justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 sm:ml-3 sm:w-auto sm:text-sm"
              onClick={handleConfirm}
            >
              Update Status
            </button>
            <button
              type="button"
              className="mt-3 inline-flex w-full justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-base font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
              onClick={handleCancel}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}