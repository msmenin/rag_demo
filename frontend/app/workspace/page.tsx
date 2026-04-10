import { redirect } from 'next/navigation'
import { createWorkspace } from '@/lib/api'

export default async function WorkspaceRoot() {
  try {
    const workspace = await createWorkspace()
    redirect(`/workspace/${workspace.id}`)
  } catch (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Error Creating Workspace</h1>
          <p className="text-gray-600 mb-4">Unable to create a new workspace. Please try again.</p>
          <a 
            href="/workspace" 
            className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Try Again
          </a>
        </div>
      </div>
    )
  }
}
