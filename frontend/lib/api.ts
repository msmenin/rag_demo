import { Workspace, Document, DocumentStatus } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function createWorkspace(): Promise<{ id: string; created_at: string }> {
  const res = await fetch(`${API_BASE}/workspace/`, { method: 'POST' })
  if (!res.ok) {
    throw new Error(`Failed to create workspace: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function getWorkspace(id: string): Promise<Workspace> {
  const res = await fetch(`${API_BASE}/workspace/${id}`)
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error('Workspace not found')
    }
    throw new Error(`Failed to get workspace: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function getDocuments(workspaceId: string): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/workspace/${workspaceId}/documents/`)
  if (!res.ok) {
    throw new Error(`Failed to fetch documents: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function uploadDocument(workspaceId: string, file: File): Promise<Document> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE}/workspace/${workspaceId}/documents/`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    
    // Handle specific error cases
    if (res.status === 400) {
      throw new Error(errorData.detail || 'Invalid file. Only PDF files are allowed.')
    }
    if (res.status === 404) {
      throw new Error('Workspace not found')
    }
    if (res.status === 413) {
      throw new Error('File too large. Maximum size is 50MB.')
    }
    
    throw new Error(errorData.detail || `Failed to upload document: ${res.status} ${res.statusText}`)
  }

  return res.json()
}

export async function deleteDocument(workspaceId: string, documentId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/workspace/${workspaceId}/documents/${documentId}`, {
    method: 'DELETE',
  })

  if (!res.ok) {
    throw new Error(`Failed to delete document: ${res.status} ${res.statusText}`)
  }
}

export async function getDocumentStatus(
  workspaceId: string,
  documentId: string
): Promise<DocumentStatus> {
  const res = await fetch(`${API_BASE}/workspace/${workspaceId}/documents/${documentId}/status`)

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error('Document not found')
    }
    throw new Error('Failed to get document status')
  }

  return res.json()
}
