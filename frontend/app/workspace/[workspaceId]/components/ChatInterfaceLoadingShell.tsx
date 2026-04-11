'use client'

import { FormEvent } from 'react'

/**
 * Lightweight shell shown while the lazy ChatInterface chunk loads.
 * Matches ChatInterface layout; Send shows spinner only (no centered panel spinner).
 */
export default function ChatInterfaceLoadingShell() {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
  }

  return (
    <div className="bg-white rounded-lg shadow-lg h-[600px] flex flex-col">
      <div className="border-b border-gray-200 px-4 py-3">
        <h2 className="text-lg font-semibold text-gray-900">Ask Questions</h2>
        <p className="text-sm text-gray-500">Query your documents</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="text-center text-gray-400 mt-20">
          <p className="text-sm">No messages yet</p>
          <p className="text-xs mt-2">Ask a question about your documents</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="border-t border-gray-200 p-4">
        <div className="flex space-x-2">
          <input
            type="text"
            readOnly
            placeholder="Ask a question about your documents..."
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled
          />
          <button
            type="submit"
            disabled
            className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
            aria-label="Loading chat"
          >
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
          </button>
        </div>
      </form>
    </div>
  )
}
