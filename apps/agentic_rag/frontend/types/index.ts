export * from "./chat"
export * from "./a2a"

export interface Document {
  id: string
  name: string
  type: "pdf" | "url" | "repo"
  status: "processing" | "ready" | "error"
  chunks?: number
  error?: string
  uploadedAt: Date
}

export interface Model {
  id: string
  name: string
  description: string
  size?: string
}

export const AVAILABLE_MODELS: Model[] = [
  { id: "gemma3:4b", name: "Gemma 3 4B", description: "Fast, efficient model", size: "4B" },
  { id: "gemma3:12b", name: "Gemma 3 12B", description: "Balanced performance", size: "12B" },
  { id: "gemma3:27b", name: "Gemma 3 27B", description: "High quality responses", size: "27B" },
  { id: "llama3.2:3b", name: "Llama 3.2 3B", description: "Meta's efficient model", size: "3B" },
  { id: "llama3.2:7b", name: "Llama 3.2 7B", description: "Meta's balanced model", size: "7B" },
  { id: "mistral:7b", name: "Mistral 7B", description: "Mistral AI's base model", size: "7B" },
  { id: "deepseek-r1:7b", name: "DeepSeek R1 7B", description: "Reasoning model", size: "7B" },
  { id: "qwen2.5:7b", name: "Qwen 2.5 7B", description: "Alibaba's model", size: "7B" },
]
