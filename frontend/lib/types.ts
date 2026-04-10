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
  created_at: string
}
