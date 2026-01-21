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
