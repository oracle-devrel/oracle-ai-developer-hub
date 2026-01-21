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
