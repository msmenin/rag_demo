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

  // Transform SSE stream to AI SDK Data Stream Protocol format
  const encoder = new TextEncoder()
  const reader = response.body?.getReader()
  
  if (!reader) {
    return new Response('No stream', { status: 500 })
  }
  
  // Helper to enqueue SSE event with proper formatting
  const sendEvent = (controller: WritableStreamDefaultController, event: object) => {
    controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`))
  }
  
  const stream = new ReadableStream({
    async start(controller) {
      const decoder = new TextDecoder()
      let buffer = ''
      const messageId = crypto.randomUUID()
      const textBlockId = crypto.randomUUID()
      let messageStarted = false
      let accumulatedContent = '' // Track cumulative content to calculate deltas
      
      try {
        while (true) {
          const { done, value } = await reader.read()
          
          if (done) {
            // Send text-end if message was started
            if (messageStarted) {
              sendEvent(controller, { type: 'text-end', id: textBlockId })
            }
            // Send finish message and stream termination
            sendEvent(controller, { type: 'finish' })
            controller.enqueue(encoder.encode('data: [DONE]\n\n'))
            controller.close()
            break
          }
          
          buffer += decoder.decode(value, { stream: true })
          // Split on double newline to get complete events
          const events = buffer.split('\n\n')
          buffer = events.pop() || ''
          
          for (const event of events) {
            // Each event may have multiple data: lines
            const lines = event.split('\n')
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const jsonStr = line.slice(6).trim()
                  if (!jsonStr) continue
                  
                  const dataObj = JSON.parse(jsonStr)
                  
                  if (dataObj.type === 'chunk') {
                    // LLM sends cumulative content, extract only the new portion
                    const newContent = dataObj.content || ''
                    const delta = newContent.slice(accumulatedContent.length)
                    accumulatedContent = newContent
                    
                    // Send message start if not yet sent
                    if (!messageStarted) {
                      sendEvent(controller, { type: 'start', messageId })
                      sendEvent(controller, { type: 'text-start', id: textBlockId })
                      messageStarted = true
                    }
                    
                    // Send only the incremental delta
                    if (delta) {
                      sendEvent(controller, { type: 'text-delta', id: textBlockId, delta })
                    }
                  } else if (dataObj.type === 'error') {
                    sendEvent(controller, { type: 'error', errorText: dataObj.message || 'Unknown error' })
                  }
                  // 'done' type will be handled after the loop completes
                } catch (e) {
                  console.error('[Query API] Failed to parse SSE data:', e, 'Line:', line)
                }
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
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'x-vercel-ai-ui-message-stream': 'v1',
    },
  })
}