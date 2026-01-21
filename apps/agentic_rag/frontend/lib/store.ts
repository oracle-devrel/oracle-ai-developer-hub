import { create } from "zustand"
import { persist } from "zustand/middleware"
import type {
  Document,
  Collection,
  ReasoningStrategy,
  ReasoningConfig,
  Agent,
  AgentStatus,
  OrchestrationLog,
  OrchestrationStep,
} from "@/types"

interface AppState {
  // Model selection
  selectedModel: string
  setSelectedModel: (model: string) => void

  // Collection selection
  selectedCollection: Collection
  setSelectedCollection: (collection: Collection) => void

  // Documents
  documents: Document[]
  addDocument: (doc: Document) => void
  removeDocument: (id: string) => void
  updateDocument: (id: string, updates: Partial<Document>) => void

  // Reasoning mode
  reasoningEnabled: boolean
  setReasoningEnabled: (enabled: boolean) => void
  reasoningConfig: ReasoningConfig
  setReasoningConfig: (config: Partial<ReasoningConfig>) => void

  // Demo mode
  demoMode: boolean
  setDemoMode: (enabled: boolean) => void

  // Agent states for demo mode
  agents: Record<string, Agent>
  updateAgentStatus: (agentId: string, status: AgentStatus) => void
  setAgentBusy: (agentId: string) => void
  setAgentAvailable: (agentId: string) => void

  // Orchestration state
  orchestrationSteps: OrchestrationStep[]
  orchestrationLogs: OrchestrationLog[]
  addOrchestrationStep: (step: OrchestrationStep) => void
  updateOrchestrationStep: (id: string, updates: Partial<OrchestrationStep>) => void
  addOrchestrationLog: (log: OrchestrationLog) => void
  clearOrchestration: () => void
  fadeOutOldLogs: () => void

  // Command palette
  commandPaletteOpen: boolean
  setCommandPaletteOpen: (open: boolean) => void

  // Settings drawer
  settingsOpen: boolean
  setSettingsOpen: (open: boolean) => void

  // Dev tools drawer
  devToolsOpen: boolean
  setDevToolsOpen: (open: boolean) => void
}

const defaultAgents: Record<string, Agent> = {
  planner_a: {
    id: "planner_a",
    name: "Planner A",
    type: "planner",
    version: "v1.0",
    status: "available",
    capabilities: ["task_decomposition", "planning"],
    description: "Primary planner agent for task decomposition",
  },
  planner_b: {
    id: "planner_b",
    name: "Planner B",
    type: "planner",
    version: "v1.1",
    status: "available",
    capabilities: ["task_decomposition", "planning", "fast_planning"],
    description: "Fast backup planner agent",
  },
  researcher_a: {
    id: "researcher_a",
    name: "Researcher A",
    type: "researcher",
    version: "v1.0",
    status: "available",
    capabilities: ["web_search", "information_retrieval"],
    description: "Web-focused researcher agent",
  },
  researcher_b: {
    id: "researcher_b",
    name: "Researcher B",
    type: "researcher",
    version: "v1.0",
    status: "available",
    capabilities: ["vector_search", "document_retrieval"],
    description: "PDF/Vector-focused researcher agent",
  },
  reasoner_a: {
    id: "reasoner_a",
    name: "Reasoner A",
    type: "reasoner",
    version: "v1.0",
    status: "available",
    capabilities: ["deep_analysis", "chain_of_thought"],
    description: "DeepThink reasoner for complex analysis",
  },
  reasoner_b: {
    id: "reasoner_b",
    name: "Reasoner B",
    type: "reasoner",
    version: "v1.0",
    status: "available",
    capabilities: ["quick_analysis", "pattern_matching"],
    description: "QuickLogic reasoner for fast analysis",
  },
  synthesizer_a: {
    id: "synthesizer_a",
    name: "Synthesizer A",
    type: "synthesizer",
    version: "v1.0",
    status: "available",
    capabilities: ["creative_writing", "comprehensive_response"],
    description: "Creative synthesizer for detailed responses",
  },
  synthesizer_b: {
    id: "synthesizer_b",
    name: "Synthesizer B",
    type: "synthesizer",
    version: "v1.0",
    status: "available",
    capabilities: ["concise_writing", "summary"],
    description: "Concise synthesizer for brief responses",
  },
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Model selection
      selectedModel: "gemma3:4b",
      setSelectedModel: (model) => set({ selectedModel: model }),

      // Collection selection
      selectedCollection: "General",
      setSelectedCollection: (collection) => set({ selectedCollection: collection }),

      // Documents
      documents: [],
      addDocument: (doc) =>
        set((state) => ({ documents: [...state.documents, doc] })),
      removeDocument: (id) =>
        set((state) => ({
          documents: state.documents.filter((d) => d.id !== id),
        })),
      updateDocument: (id, updates) =>
        set((state) => ({
          documents: state.documents.map((d) =>
            d.id === id ? { ...d, ...updates } : d
          ),
        })),

      // Reasoning mode
      reasoningEnabled: false,
      setReasoningEnabled: (enabled) => set({ reasoningEnabled: enabled }),
      reasoningConfig: {
        strategies: ["cot"],
        totDepth: 3,
        consistencySamples: 3,
        reflectionTurns: 3,
      },
      setReasoningConfig: (config) =>
        set((state) => ({
          reasoningConfig: { ...state.reasoningConfig, ...config },
        })),

      // Demo mode
      demoMode: false,
      setDemoMode: (enabled) => set({ demoMode: enabled }),

      // Agent states
      agents: defaultAgents,
      updateAgentStatus: (agentId, status) =>
        set((state) => ({
          agents: {
            ...state.agents,
            [agentId]: { ...state.agents[agentId], status },
          },
        })),
      setAgentBusy: (agentId) => {
        const { updateAgentStatus } = get()
        updateAgentStatus(agentId, "busy")
      },
      setAgentAvailable: (agentId) => {
        const { updateAgentStatus } = get()
        updateAgentStatus(agentId, "available")
      },

      // Orchestration state
      orchestrationSteps: [],
      orchestrationLogs: [],
      addOrchestrationStep: (step) =>
        set((state) => ({
          orchestrationSteps: [...state.orchestrationSteps, step],
        })),
      updateOrchestrationStep: (id, updates) =>
        set((state) => ({
          orchestrationSteps: state.orchestrationSteps.map((s) =>
            s.id === id ? { ...s, ...updates } : s
          ),
        })),
      addOrchestrationLog: (log) =>
        set((state) => ({
          orchestrationLogs: [...state.orchestrationLogs, { ...log, fade: "in" }],
        })),
      clearOrchestration: () =>
        set({ orchestrationSteps: [], orchestrationLogs: [] }),
      fadeOutOldLogs: () =>
        set((state) => {
          const now = Date.now()
          return {
            orchestrationLogs: state.orchestrationLogs.map((log) => ({
              ...log,
              fade: now - log.timestamp > 3000 ? "out" : log.fade,
            })),
          }
        }),

      // Command palette
      commandPaletteOpen: false,
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

      // Settings drawer
      settingsOpen: false,
      setSettingsOpen: (open) => set({ settingsOpen: open }),

      // Dev tools drawer
      devToolsOpen: false,
      setDevToolsOpen: (open) => set({ devToolsOpen: open }),
    }),
    {
      name: "agentic-rag-storage",
      partialize: (state) => ({
        selectedModel: state.selectedModel,
        selectedCollection: state.selectedCollection,
        reasoningEnabled: state.reasoningEnabled,
        reasoningConfig: state.reasoningConfig,
      }),
    }
  )
)
