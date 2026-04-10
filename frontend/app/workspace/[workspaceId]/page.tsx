import { getWorkspace, getDocuments } from '@/lib/api'
import WorkspaceDashboard from './WorkspaceDashboard'

export default async function WorkspacePage({ 
  params 
}: { 
  params: Promise<{ workspaceId: string }> 
}) {
  const { workspaceId } = await params
  
  try {
    const workspace = await getWorkspace(workspaceId)
    const documents = await getDocuments(workspaceId)
    
    return <WorkspaceDashboard 
      workspace={workspace} 
      documents={documents} 
      workspaceId={workspaceId}
    />
  } catch (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Workspace Not Found</h1>
          <p className="text-gray-600 mb-4">The workspace you&apos;re looking for doesn&apos;t exist or has been deleted.</p>
          <a 
            href="/workspace" 
            className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Create New Workspace
          </a>
        </div>
      </div>
    )
  }
}
