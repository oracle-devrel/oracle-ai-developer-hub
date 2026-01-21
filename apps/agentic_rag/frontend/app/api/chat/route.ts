import { streamText, convertToModelMessages, UIMessage } from "ai"
import { ollama } from "@/lib/ollama"

// Allow streaming responses up to 60 seconds
export const maxDuration = 60

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const { messages, model = "gemma3:4b" } = body as {
      messages: UIMessage[]
      model?: string
    }

    const result = streamText({
      model: ollama(model),
      messages: await convertToModelMessages(messages),
    })

    return result.toUIMessageStreamResponse()
  } catch (error) {
    console.error("Chat API error:", error)
    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : "Failed to process chat request",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    )
  }
}
