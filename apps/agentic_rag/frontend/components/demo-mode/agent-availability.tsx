"use client"

import { motion } from "framer-motion"
import { useAppStore } from "@/lib/store"
import { AGENT_TYPES, type AgentType, type AgentStatus } from "@/types"
import { cn } from "@/lib/utils"

const statusColors: Record<AgentStatus, string> = {
  available: "bg-green-500",
  busy: "bg-yellow-500",
  offline: "bg-gray-400",
}

const statusLabels: Record<AgentStatus, string> = {
  available: "Available",
  busy: "Busy",
  offline: "Offline",
}

export function AgentAvailability() {
  const { agents } = useAppStore()

  // Group agents by type
  const agentsByType = Object.values(agents).reduce(
    (acc, agent) => {
      if (!acc[agent.type]) {
        acc[agent.type] = []
      }
      acc[agent.type].push(agent)
      return acc
    },
    {} as Record<AgentType, typeof agents[string][]>
  )

  return (
    <div className="rounded-lg border bg-background/50 p-3">
      <h4 className="mb-2 text-xs font-medium text-muted-foreground">
        Agent Availability
      </h4>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(Object.keys(AGENT_TYPES) as AgentType[]).map((type) => (
          <div key={type} className="space-y-1">
            <div className="flex items-center gap-1 text-xs font-medium">
              <span>{AGENT_TYPES[type].icon}</span>
              <span>{AGENT_TYPES[type].name}s</span>
            </div>

            <div className="space-y-1">
              {agentsByType[type]?.map((agent) => (
                <motion.div
                  key={agent.id}
                  layout
                  className="flex items-center gap-2 rounded bg-muted/50 px-2 py-1"
                >
                  <motion.div
                    animate={{
                      scale: agent.status === "busy" ? [1, 1.2, 1] : 1,
                    }}
                    transition={{
                      repeat: agent.status === "busy" ? Infinity : 0,
                      duration: 1,
                    }}
                    className={cn(
                      "h-2 w-2 rounded-full",
                      statusColors[agent.status]
                    )}
                  />
                  <span className="flex-1 truncate text-[10px]">
                    {agent.name}
                  </span>
                  <span className="text-[9px] text-muted-foreground">
                    {agent.version}
                  </span>
                </motion.div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-3 flex items-center justify-center gap-4 border-t pt-2">
        {(Object.keys(statusColors) as AgentStatus[]).map((status) => (
          <div key={status} className="flex items-center gap-1">
            <span className={cn("h-2 w-2 rounded-full", statusColors[status])} />
            <span className="text-[10px] text-muted-foreground">
              {statusLabels[status]}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
