import { streamText, convertToModelMessages, UIMessage } from "ai"
import { ollama } from "@/lib/ollama"

// Allow streaming responses up to 120 seconds for RAG operations
export const maxDuration = 120

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface RAGContext {
  content: string
  metadata?: {
    source?: string
    page_numbers?: number[]
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const {
      messages,
      model = "gemma3:4b",
      collection = "General",
      useReasoning = false,
      reasoningConfig,
    } = body as {
      messages: UIMessage[]
      model?: string
      collection?: string
      useReasoning?: boolean
      reasoningConfig?: {
        strategies?: string[]
        totDepth?: number
        consistencySamples?: number
        reflectionTurns?: number
      }
    }

    // Get the last user message for retrieval
    const lastMessage = messages[messages.length - 1]
    const query = lastMessage?.parts
      ?.filter((p): p is { type: "text"; text: string } => p.type === "text")
      .map((p) => p.text)
      .join(" ") || ""

    // If reasoning mode is enabled, use the A2A protocol
    if (useReasoning && reasoningConfig?.strategies?.length) {
      const a2aResponse = await fetch(`${API_BASE_URL}/a2a`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0",
          method: "agent.query",
          params: {
            agent_id: "orchestrator",
            query,
            collection,
            use_cot: true,
            reasoning_strategies: reasoningConfig.strategies,
            config: {
              tot_depth: reasoningConfig.totDepth,
              consistency_samples: reasoningConfig.consistencySamples,
              reflection_turns: reasoningConfig.reflectionTurns,
            },
          },
          id: `chat-${Date.now()}`,
        }),
      })

      const result = await a2aResponse.json()

      if (result.error) {
        throw new Error(result.error.message)
      }

      // Format and stream the reasoning response
      const answer = result.result?.answer || "No answer provided"
      const reasoningSteps = result.result?.reasoning_steps || []
      const sources = result.result?.sources || []

      let formattedResponse = ""

      if (reasoningSteps.length > 0) {
        formattedResponse += "## Reasoning Steps\n\n"
        reasoningSteps.forEach((step: string, index: number) => {
          formattedResponse += `**Step ${index + 1}:** ${step}\n\n`
        })
        formattedResponse += "---\n\n"
      }

      formattedResponse += `## Answer\n\n${answer}`

      if (sources.length > 0) {
        formattedResponse += "\n\n## Sources\n\n"
        sources.forEach((source: { name: string; page?: number }) => {
          formattedResponse += `- ${source.name}${source.page ? ` (page ${source.page})` : ""}\n`
        })
      }

      const encoder = new TextEncoder()
      const stream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(formattedResponse))
          controller.close()
        },
      })

      return new Response(stream, {
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      })
    }

    // Fetch context from the backend for RAG
    const retrievalResponse = await fetch(`${API_BASE_URL}/retrieve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        collection,
        top_k: 5,
      }),
    })

    let contextText = ""
    let sources: RAGContext[] = []

    if (retrievalResponse.ok) {
      const retrievalResult = await retrievalResponse.json()
      sources = retrievalResult.context || []

      if (sources.length > 0) {
        contextText = sources
          .map((ctx, i) => `[Source ${i + 1}]: ${ctx.content}`)
          .join("\n\n")
      }
    }

    // Build augmented messages with context
    const systemMessage = contextText
      ? `You are a helpful assistant. Use the following context to answer the user's question. If the context doesn't contain relevant information, say so and answer based on your general knowledge.\n\nContext:\n${contextText}`
      : "You are a helpful assistant."

    const augmentedMessages: UIMessage[] = [
      {
        id: "system",
        role: "system" as const,
        parts: [{ type: "text", text: systemMessage }],
      },
      ...messages,
    ]

    const result = streamText({
      model: ollama(model),
      messages: await convertToModelMessages(augmentedMessages),
    })

    return result.toUIMessageStreamResponse()
  } catch (error) {
    console.error("RAG Chat API error:", error)
    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : "Failed to process RAG request",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    )
  }
}
