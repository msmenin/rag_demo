export interface Workspace {
  id: string
  created_at: string
  name?: string
}

export interface Document {
  id: string
  workspace_id: string
  filename: string
  file_path?: string
  page_count?: number
  file_size?: number
  indexed_at?: string
  error_message?: string
  created_at: string
}

export interface DocumentStatus {
  id: string
  status: 'processing' | 'complete' | 'error'
  page_count?: number
  error_message?: string
}
