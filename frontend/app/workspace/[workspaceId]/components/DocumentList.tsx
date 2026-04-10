'use client'

import { useState } from 'react'
import { Document } from '@/lib/types'
import { deleteDocument } from '@/lib/api'

interface DocumentListProps {
  documents: Document[]
  workspaceId: string
  onDelete: (documentId: string) => void
  onRefresh: () => void
}

function formatFileSize(bytes: number | undefined): string {
  if (!bytes) return 'Unknown size'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function DocumentList({ 
  documents, 
  workspaceId, 
  onDelete,
  onRefresh 
}: DocumentListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleDelete = async (documentId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return
    }

    setDeletingId(documentId)
    try {
      await deleteDocument(workspaceId, documentId)
      onDelete(documentId)
    } catch (error) {
      console.error('Failed to delete document:', error)
      alert('Failed to delete document. Please try again.')
      onRefresh()
    } finally {
      setDeletingId(null)
    }
  }

  if (documents.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
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
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <h3 className="mt-4 text-lg font-medium text-gray-900">No documents yet</h3>
        <p className="mt-2 text-sm text-gray-500">
          Upload a PDF document to get started
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">Documents</h2>
      <div className="grid gap-4">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-4 flex items-center justify-between"
          >
            <div className="flex items-center space-x-4">
              <div className="flex-shrink-0">
                <svg
                  className="h-10 w-10 text-red-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-900">{doc.filename}</h3>
                <p className="text-xs text-gray-500">
                  {formatFileSize(doc.file_size)} • {formatDate(doc.created_at)}
                </p>
              </div>
            </div>
            <button
              onClick={() => handleDelete(doc.id, doc.filename)}
              disabled={deletingId === doc.id}
              className="ml-4 px-3 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {deletingId === doc.id ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
