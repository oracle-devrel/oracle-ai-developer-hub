import { useId } from 'react'
import {
  fetchServerSentEvents,
  useChat,
  createChatClientOptions,
} from '@tanstack/ai-react'
import type { InferChatMessages } from '@tanstack/ai-react'

const chatOptions = createChatClientOptions({
  connection: fetchServerSentEvents('/api/ai/chat'),
})

export type ChatMessages = InferChatMessages<typeof chatOptions>

export const useAIChat = () => {
  const threadId = useId()
  return useChat({ ...chatOptions, threadId })
}
