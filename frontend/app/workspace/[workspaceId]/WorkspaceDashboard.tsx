'use client'

import dynamic from 'next/dynamic'
import { useState } from 'react'
import { Workspace, Document } from '@/lib/types'
import DocumentList from './components/DocumentList'
import DocumentUpload from './components/DocumentUpload'
import ChatInterfaceLoadingShell from './components/ChatInterfaceLoadingShell'

const ChatInterface = dynamic(
  () => import('./components/ChatInterface'),
  {
    ssr: false,
    loading: () => <ChatInterfaceLoadingShell />,
  },
)

interface WorkspaceDashboardProps {
  workspace: Workspace
  documents: Document[]
  workspaceId: string
}

export default function WorkspaceDashboard({ 
  workspace, 
  documents: initialDocuments, 
  workspaceId 
}: WorkspaceDashboardProps) {
  const [documents, setDocuments] = useState<Document[]>(initialDocuments)
  const [refreshKey, setRefreshKey] = useState(0)

  const handleUploadComplete = () => {
    refreshDocuments()
  }

  const handleDelete = (documentId: string) => {
    setDocuments(prev => prev.filter(doc => doc.id !== documentId))
  }

  const refreshDocuments = async () => {
    try {
      const { getDocuments } = await import('@/lib/api')
      const updatedDocs = await getDocuments(workspaceId)
      setDocuments(updatedDocs)
    } catch (error) {
      console.error('Failed to refresh documents:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Workspace
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            ID: {workspace.id.substring(0, 8)}...
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-8">
            <DocumentUpload 
              workspaceId={workspaceId}
              onUploadComplete={handleUploadComplete}
            />
            
            <DocumentList 
              documents={documents}
              workspaceId={workspaceId}
              onDelete={handleDelete}
              onRefresh={refreshDocuments}
              key={refreshKey}
            />
          </div>
          
          <div>
            <ChatInterface workspaceId={workspaceId} />
          </div>
        </div>
      </main>
    </div>
  )
}
