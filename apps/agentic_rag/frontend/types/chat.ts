export interface Message {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  createdAt?: Date
  metadata?: MessageMetadata
}

export interface MessageMetadata {
  sources?: Source[]
  reasoningSteps?: string[]
  strategyResults?: StrategyResult[]
  executionTrace?: TraceEvent[]
}

export interface Source {
  id: string
  type: "pdf" | "web" | "repo"
  name: string
  page?: number
  url?: string
  relevance?: number
}

export interface StrategyResult {
  strategy: ReasoningStrategy
  response: string
  duration: number
  isWinner: boolean
  voteCount?: number
}

export interface TraceEvent {
  timestamp: string
  message: string
  type: "info" | "success" | "error" | "warning"
}

export type ReasoningStrategy =
  | "cot"
  | "tot"
  | "react"
  | "self_reflection"
  | "consistency"
  | "decomposed"
  | "least_to_most"
  | "recursive"
  | "standard"

export interface ReasoningConfig {
  strategies: ReasoningStrategy[]
  totDepth: number
  consistencySamples: number
  reflectionTurns: number
}

export const STRATEGY_INFO: Record<
  ReasoningStrategy,
  { name: string; icon: string; description: string }
> = {
  cot: {
    name: "Chain-of-Thought",
    icon: "🔗",
    description: "Step-by-step reasoning through the problem",
  },
  tot: {
    name: "Tree of Thoughts",
    icon: "🌳",
    description: "Explore multiple reasoning paths in parallel",
  },
  react: {
    name: "ReAct",
    icon: "🛠️",
    description: "Reason and act iteratively with tool use",
  },
  self_reflection: {
    name: "Self-Reflection",
    icon: "🪞",
    description: "Critique and refine responses iteratively",
  },
  consistency: {
    name: "Self-Consistency",
    icon: "🔄",
    description: "Sample multiple answers and vote for consensus",
  },
  decomposed: {
    name: "Decomposed",
    icon: "🧩",
    description: "Break complex problems into sub-problems",
  },
  least_to_most: {
    name: "Least-to-Most",
    icon: "📈",
    description: "Solve simpler sub-problems first, building up",
  },
  recursive: {
    name: "Recursive",
    icon: "🔁",
    description: "Apply reasoning recursively to sub-problems",
  },
  standard: {
    name: "Standard",
    icon: "📝",
    description: "Direct response without special reasoning",
  },
}

export type Collection = "PDF" | "Repository" | "Web" | "General"

export const COLLECTION_INFO: Record<
  Collection,
  { name: string; icon: string }
> = {
  PDF: { name: "PDF Collection", icon: "📄" },
  Repository: { name: "Repository Collection", icon: "📁" },
  Web: { name: "Web Knowledge Base", icon: "🌐" },
  General: { name: "General Knowledge", icon: "🧠" },
}
