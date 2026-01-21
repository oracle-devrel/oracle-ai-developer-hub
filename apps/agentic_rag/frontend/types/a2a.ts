export type AgentType = "planner" | "researcher" | "reasoner" | "synthesizer"
export type AgentStatus = "available" | "busy" | "offline"

export interface Agent {
  id: string
  name: string
  type: AgentType
  version: string
  status: AgentStatus
  capabilities: string[]
  description: string
}

export interface AgentCard {
  name: string
  version: string
  description: string
  capabilities: string[]
  endpoint: string
}

export interface OrchestrationStep {
  id: string
  agentType: AgentType
  agentName: string
  status: "pending" | "running" | "completed" | "failed"
  startTime?: number
  endTime?: number
  output?: string
}

export interface OrchestrationLog {
  timestamp: number
  type: "info" | "success" | "error" | "warning"
  message: string
  agentType?: AgentType
  fade?: "in" | "out" | "visible"
}

export interface A2ATask {
  id: string
  type: string
  params: Record<string, unknown>
  status: "pending" | "running" | "completed" | "failed"
  createdAt: string
  result?: unknown
}

export interface A2ARequest {
  jsonrpc: "2.0"
  method: string
  params: Record<string, unknown>
  id: string
}

export interface A2AResponse {
  jsonrpc: "2.0"
  result?: unknown
  error?: {
    code: number
    message: string
    details?: string
  }
  id: string
}

export const AGENT_TYPES: Record<
  AgentType,
  { name: string; icon: string; color: string }
> = {
  planner: { name: "Planner", icon: "📋", color: "blue" },
  researcher: { name: "Researcher", icon: "🔬", color: "green" },
  reasoner: { name: "Reasoner", icon: "🧠", color: "purple" },
  synthesizer: { name: "Synthesizer", icon: "✍️", color: "orange" },
}
