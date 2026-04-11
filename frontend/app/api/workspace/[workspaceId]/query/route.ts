import { NextRequest } from 'next/server'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ workspaceId: string }> }
) {
  const { workspaceId } = await params
  const body = await request.json()
  
  const lastMessage = body.messages?.[body.messages.length - 1]
  const queryText = body.query || lastMessage?.parts?.[0]?.text || lastMessage?.content
  
  if (!queryText || typeof queryText !== 'string' || !queryText.trim()) {
    return new Response(
      JSON.stringify({ error: 'Invalid or missing query text' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    )
  }
  
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
  
  const response = await fetch(`${backendUrl}/workspace/${workspaceId}/query/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query: queryText, document_ids: body.document_ids })
  })

  if (!response.ok) {
    const errorText = await response.text()
    return new Response(
      JSON.stringify({ error: 'Backend request failed', details: errorText }),
      { status: response.status, headers: { 'Content-Type': 'application/json' } }
    )
  }

  // Transform SSE stream to AI SDK format
  const encoder = new TextEncoder()
  const reader = response.body?.getReader()
  
  if (!reader) {
    return new Response('No stream', { status: 500 })
  }
  
  const stream = new ReadableStream({
    async start(controller) {
      const decoder = new TextDecoder()
      let buffer = ''
      
      try {
        while (true) {
          const { done, value } = await reader.read()
          
          if (done) {
            controller.close()
            break
          }
          
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const jsonStr = line.slice(6)
                const dataObj = JSON.parse(jsonStr)
                
                if (dataObj.type === 'chunk') {
                  const text = dataObj.content || ''
                  controller.enqueue(encoder.encode(`0:${JSON.stringify(text)}\n`))
                } else if (dataObj.type === 'error') {
                  controller.enqueue(encoder.encode(`3:${JSON.stringify({ error: dataObj.message })}\n`))
                } else if (dataObj.type === 'done') {
                  controller.enqueue(encoder.encode(`e:${JSON.stringify({ finishReason: 'stop' })}\n`))
                }
              } catch (e) {
                console.error('[Query API] Failed to parse SSE data:', e)
              }
            }
          }
        }
      } catch (error) {
        console.error('[Query API] Stream error:', error)
        controller.error(error)
      }
    }
  })
  
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}