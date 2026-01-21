# Ollama Provider Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all AI SDK integrations with direct Ollama provider (`ollama-ai-provider-v2`) for optimized local LLM experience.

**Architecture:** The frontend will communicate directly with Ollama via the `ollama-ai-provider-v2` package for chat completions and streaming. The existing FastAPI backend will only be used for RAG-specific operations (document retrieval, vector search, A2A protocol). Chat requests will stream directly from Ollama to the browser.

**Tech Stack:** Next.js 16, React 19, Vercel AI SDK v6, ollama-ai-provider-v2, TypeScript

---

## Task 1: Update Dependencies

**Files:**
- Modify: `package.json`

**Step 1: Remove @ai-sdk/openai dependency**

Edit `package.json` to remove `@ai-sdk/openai` from dependencies.

**Step 2: Add ollama-ai-provider-v2**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/frontend && npm install ollama-ai-provider-v2
```

**Step 3: Verify installation**

Run: `cat package.json | grep ollama`
Expected: `"ollama-ai-provider-v2": "^x.x.x"`

**Step 4: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: replace @ai-sdk/openai with ollama-ai-provider-v2"
```

---

## Task 2: Create Ollama Provider Configuration

**Files:**
- Create: `lib/ollama.ts`

**Step 1: Create the Ollama provider configuration file**

```typescript
import { createOllama } from "ollama-ai-provider-v2"

// Create Ollama provider instance
// Default: http://localhost:11434/api
// Can be overridden via NEXT_PUBLIC_OLLAMA_URL environment variable
export const ollama = createOllama({
  baseURL: process.env.NEXT_PUBLIC_OLLAMA_URL || "http://localhost:11434/api",
})

// Export model factory for convenience
export const getOllamaModel = (modelId: string) => ollama(modelId)

// Default model configuration
export const DEFAULT_MODEL = "gemma3:4b"

// Available models (can be extended based on what's pulled in Ollama)
export const AVAILABLE_MODELS = [
  { id: "gemma3:4b", name: "Gemma 3 4B", description: "Fast, efficient model" },
  { id: "gemma3:12b", name: "Gemma 3 12B", description: "Balanced performance" },
  { id: "gemma3:27b", name: "Gemma 3 27B", description: "High quality responses" },
  { id: "llama3.2:3b", name: "Llama 3.2 3B", description: "Meta's efficient model" },
  { id: "llama3.2:7b", name: "Llama 3.2 7B", description: "Meta's balanced model" },
  { id: "mistral:7b", name: "Mistral 7B", description: "Mistral AI's base model" },
  { id: "deepseek-r1:7b", name: "DeepSeek R1 7B", description: "Reasoning model" },
  { id: "qwen2.5:7b", name: "Qwen 2.5 7B", description: "Alibaba's model" },
] as const

export type OllamaModelId = (typeof AVAILABLE_MODELS)[number]["id"] | string
```

**Step 2: Verify file creation**

Run: `cat lib/ollama.ts`
Expected: File contents as above

**Step 3: Commit**

```bash
git add lib/ollama.ts
git commit -m "feat: add Ollama provider configuration"
```

---

## Task 3: Rewrite Chat API Route for Direct Ollama Streaming

**Files:**
- Modify: `app/api/chat/route.ts`

**Step 1: Rewrite the chat route to use Ollama provider with streamText**

Replace entire contents of `app/api/chat/route.ts` with:

```typescript
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
```

**Step 2: Verify the changes**

Run: `cat app/api/chat/route.ts`
Expected: New streamText-based implementation

**Step 3: Commit**

```bash
git add app/api/chat/route.ts
git commit -m "feat: rewrite chat route with direct Ollama streaming"
```

---

## Task 4: Create RAG-Enhanced Chat Route

**Files:**
- Create: `app/api/chat-rag/route.ts`

**Step 1: Create a dedicated RAG endpoint that combines retrieval with Ollama**

```typescript
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
        createdAt: new Date(),
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
```

**Step 2: Verify file creation**

Run: `cat app/api/chat-rag/route.ts`
Expected: File contents as above

**Step 3: Commit**

```bash
git add app/api/chat-rag/route.ts
git commit -m "feat: add RAG-enhanced chat route with Ollama streaming"
```

---

## Task 5: Update Chat Container to Use AI SDK useChat Hook

**Files:**
- Modify: `components/chat/chat-container.tsx`

**Step 1: Rewrite chat container to use the useChat hook**

Replace entire contents of `components/chat/chat-container.tsx` with:

```typescript
"use client"

import { useRef, useEffect, useState, useCallback } from "react"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import { AnimatePresence, motion } from "framer-motion"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ChatMessage } from "./chat-message"
import { ChatInput } from "./chat-input"
import { DocumentChips } from "./document-chips"
import { OrchestrationPanel } from "@/components/demo-mode/orchestration-panel"
import { useAppStore } from "@/lib/store"

export function ChatContainer() {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [input, setInput] = useState("")

  const {
    demoMode,
    selectedCollection,
    reasoningEnabled,
    reasoningConfig,
    selectedModel,
    documents,
    addOrchestrationLog,
    addOrchestrationStep,
    updateOrchestrationStep,
    clearOrchestration,
    setAgentBusy,
    setAgentAvailable,
  } = useAppStore()

  // Determine which endpoint to use based on mode
  const apiEndpoint = reasoningEnabled || documents.length > 0 ? "/api/chat-rag" : "/api/chat"

  const { messages, sendMessage, status, error } = useChat({
    transport: new DefaultChatTransport({
      api: apiEndpoint,
      body: {
        model: selectedModel,
        collection: selectedCollection,
        useReasoning: reasoningEnabled,
        reasoningConfig: reasoningEnabled ? reasoningConfig : undefined,
      },
    }),
  })

  const isLoading = status === "streaming" || status === "submitted"

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
  }, [])

  const simulateDemoOrchestration = useCallback(async () => {
    clearOrchestration()

    const steps = ["planner", "researcher", "reasoner", "synthesizer"] as const

    for (const agentType of steps) {
      addOrchestrationStep({
        id: `${agentType}-${Date.now()}`,
        agentType,
        agentName: `${agentType.charAt(0).toUpperCase() + agentType.slice(1)} A`,
        status: "running",
        startTime: Date.now(),
      })

      setAgentBusy(`${agentType}_a`)

      addOrchestrationLog({
        timestamp: Date.now(),
        type: "info",
        message: `${agentType.charAt(0).toUpperCase() + agentType.slice(1)} agent starting...`,
        agentType,
      })

      await new Promise((resolve) => setTimeout(resolve, 800 + Math.random() * 400))

      updateOrchestrationStep(`${agentType}-${Date.now()}`, {
        status: "completed",
        endTime: Date.now(),
      })

      setAgentAvailable(`${agentType}_a`)

      addOrchestrationLog({
        timestamp: Date.now(),
        type: "success",
        message: `${agentType.charAt(0).toUpperCase() + agentType.slice(1)} completed successfully`,
        agentType,
      })
    }
  }, [
    clearOrchestration,
    addOrchestrationStep,
    addOrchestrationLog,
    updateOrchestrationStep,
    setAgentBusy,
    setAgentAvailable,
  ])

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (!input.trim() || isLoading) return

      // Simulate demo orchestration if demo mode is on
      if (demoMode) {
        simulateDemoOrchestration()
      }

      sendMessage({ text: input })
      setInput("")
    },
    [input, isLoading, demoMode, simulateDemoOrchestration, sendMessage]
  )

  const setInputValue = useCallback((value: string) => {
    setInput(value)
  }, [])

  return (
    <div className="flex h-full flex-col">
      {/* Demo Mode Orchestration Panel */}
      <AnimatePresence>
        {demoMode && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          >
            <OrchestrationPanel />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat Messages */}
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {messages.length === 0 ? (
            <div className="flex h-[50vh] flex-col items-center justify-center text-center">
              <div className="mb-4 text-6xl">🤖</div>
              <h2 className="mb-2 text-2xl font-semibold">Welcome to Agentic RAG</h2>
              <p className="max-w-md text-muted-foreground">
                Upload documents, add URLs, or ask questions. I can help you find
                information from your knowledge base using advanced reasoning.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                <SuggestionChip onClick={() => setInputValue("What documents have been uploaded?")}>
                  📚 What documents are available?
                </SuggestionChip>
                <SuggestionChip onClick={() => setInputValue("Explain how GANs work")}>
                  🧠 Explain GANs
                </SuggestionChip>
                <SuggestionChip onClick={() => setInputValue("Summarize the main concepts in my documents")}>
                  📝 Summarize my docs
                </SuggestionChip>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <ChatMessage
                key={message.id}
                role={message.role as "user" | "assistant"}
                content={
                  message.parts
                    ?.filter((p): p is { type: "text"; text: string } => p.type === "text")
                    .map((p) => p.text)
                    .join("") || ""
                }
                isLoading={false}
              />
            ))
          )}

          {isLoading && messages[messages.length - 1]?.role === "user" && (
            <ChatMessage role="assistant" content="" isLoading={true} />
          )}

          {error && (
            <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
              <p className="font-medium">Error</p>
              <p className="text-sm">{error.message}</p>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Document Chips */}
      {documents.length > 0 && <DocumentChips />}

      {/* Chat Input */}
      <ChatInput
        value={input}
        onChange={handleInputChange}
        onSubmit={handleSubmit}
        isLoading={isLoading}
        onClear={messages.length > 0 ? () => window.location.reload() : undefined}
      />
    </div>
  )
}

function SuggestionChip({
  children,
  onClick,
}: {
  children: React.ReactNode
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="rounded-full border bg-background px-4 py-2 text-sm transition-colors hover:bg-accent"
    >
      {children}
    </button>
  )
}
```

**Step 2: Verify the changes**

Run: `head -50 components/chat/chat-container.tsx`
Expected: New useChat-based implementation

**Step 3: Commit**

```bash
git add components/chat/chat-container.tsx
git commit -m "feat: update chat container to use AI SDK useChat hook"
```

---

## Task 6: Update Store with Ollama Models

**Files:**
- Modify: `lib/store.ts`

**Step 1: Update the default model in store to use Ollama model ID**

In `lib/store.ts`, change line 146:
```typescript
selectedModel: "gemma3:270m",
```
to:
```typescript
selectedModel: "gemma3:4b",
```

**Step 2: Verify the change**

Run: `grep -n "selectedModel:" lib/store.ts`
Expected: Line showing `selectedModel: "gemma3:4b"`

**Step 3: Commit**

```bash
git add lib/store.ts
git commit -m "fix: update default model to valid Ollama model ID"
```

---

## Task 7: Update Environment Configuration

**Files:**
- Modify: `.env.example`
- Modify: `.env.local`

**Step 1: Update .env.example with Ollama configuration**

Replace contents of `.env.example`:

```bash
# Ollama API URL (default: http://localhost:11434/api)
NEXT_PUBLIC_OLLAMA_URL=http://localhost:11434/api

# Backend API URL for RAG operations (FastAPI server)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Step 2: Update .env.local with Ollama configuration**

Replace contents of `.env.local`:

```bash
# Ollama API URL
NEXT_PUBLIC_OLLAMA_URL=http://localhost:11434/api

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Step 3: Verify the changes**

Run: `cat .env.example && echo "---" && cat .env.local`
Expected: Both files showing Ollama URL configuration

**Step 4: Commit**

```bash
git add .env.example .env.local
git commit -m "chore: add Ollama URL to environment configuration"
```

---

## Task 8: Update Settings Drawer with Ollama Models

**Files:**
- Modify: `components/layout/settings-drawer.tsx`

**Step 1: Read current settings drawer implementation**

First, read the file to understand its structure.

**Step 2: Update the model selection to use AVAILABLE_MODELS from lib/ollama.ts**

Import AVAILABLE_MODELS and update the model selector to use the predefined Ollama models instead of hardcoded values.

**Step 3: Verify the changes**

Run: `grep -A5 "AVAILABLE_MODELS" components/layout/settings-drawer.tsx`
Expected: Import and usage of AVAILABLE_MODELS

**Step 4: Commit**

```bash
git add components/layout/settings-drawer.tsx
git commit -m "feat: update settings drawer with Ollama model selection"
```

---

## Task 9: Remove Unused Reasoning Route

**Files:**
- Delete: `app/api/reasoning/route.ts`

**Step 1: Delete the unused reasoning route**

The reasoning functionality is now integrated into the chat-rag route.

```bash
rm app/api/reasoning/route.ts
```

**Step 2: Verify deletion**

Run: `ls app/api/`
Expected: Only `chat/` and `chat-rag/` directories

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove unused reasoning route (merged into chat-rag)"
```

---

## Task 10: Clean Up Package.json

**Files:**
- Modify: `package.json`

**Step 1: Remove @ai-sdk/openai from package.json if still present**

Edit package.json to ensure @ai-sdk/openai is removed from dependencies.

**Step 2: Run npm install to clean up**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/frontend && npm install
```

**Step 3: Verify dependencies**

Run: `cat package.json | grep -E "ollama|openai"`
Expected: Only `ollama-ai-provider-v2` should appear

**Step 4: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: clean up dependencies, remove @ai-sdk/openai"
```

---

## Task 11: Test the Integration

**Files:**
- None (testing only)

**Step 1: Ensure Ollama is running**

```bash
curl http://localhost:11434/api/tags
```
Expected: JSON response with available models

**Step 2: Start the development server**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/frontend && npm run dev
```

**Step 3: Test basic chat**

Open browser to http://localhost:3000 and send a test message.
Expected: Streaming response from Ollama model

**Step 4: Test model switching**

Open settings, change model, send another message.
Expected: Response from different model

---

## Task 12: Final Commit and Summary

**Step 1: Create final summary commit if any uncommitted changes remain**

```bash
git status
```

If changes exist:
```bash
git add -A
git commit -m "feat: complete Ollama provider integration for agentic RAG frontend"
```

---

## Summary of Changes

1. **Dependencies**: Replaced `@ai-sdk/openai` with `ollama-ai-provider-v2`
2. **New Files**:
   - `lib/ollama.ts` - Ollama provider configuration
   - `app/api/chat-rag/route.ts` - RAG-enhanced chat endpoint
3. **Modified Files**:
   - `app/api/chat/route.ts` - Direct Ollama streaming
   - `components/chat/chat-container.tsx` - useChat hook integration
   - `components/layout/settings-drawer.tsx` - Ollama model selection
   - `lib/store.ts` - Updated default model
   - `.env.example`, `.env.local` - Ollama URL configuration
4. **Deleted Files**:
   - `app/api/reasoning/route.ts` - Merged into chat-rag

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
├─────────────────────────────────────────────────────────────────┤
│  ChatContainer (useChat hook)                                    │
│       │                                                          │
│       ├── /api/chat ────────────► Ollama (direct streaming)     │
│       │                                                          │
│       └── /api/chat-rag ────┬──► FastAPI /retrieve (RAG)        │
│                             └──► Ollama (augmented streaming)    │
│                                                                  │
│                             ┌──► FastAPI /a2a (reasoning mode)   │
└─────────────────────────────────────────────────────────────────┘
```
