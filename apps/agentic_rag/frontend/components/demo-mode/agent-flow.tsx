"use client"

import { motion } from "framer-motion"
import { CheckCircle, Loader2, Circle, ArrowRight } from "lucide-react"
import { useAppStore } from "@/lib/store"
import { AGENT_TYPES, type AgentType } from "@/types"
import { cn } from "@/lib/utils"

const flowSteps: AgentType[] = ["planner", "researcher", "reasoner", "synthesizer"]

export function AgentFlow() {
  const { orchestrationSteps, agents } = useAppStore()

  const getStepStatus = (agentType: AgentType) => {
    const step = orchestrationSteps.find((s) => s.agentType === agentType)
    return step?.status || "pending"
  }

  const getActiveAgent = (agentType: AgentType) => {
    // Find any agent of this type that is busy
    const busyAgent = Object.values(agents).find(
      (a) => a.type === agentType && a.status === "busy"
    )
    if (busyAgent) return busyAgent

    // Otherwise return the first available agent of this type
    return Object.values(agents).find(
      (a) => a.type === agentType && a.status === "available"
    )
  }

  return (
    <div className="flex items-center justify-center gap-2 overflow-x-auto py-4">
      {flowSteps.map((agentType, index) => {
        const status = getStepStatus(agentType)
        const agent = getActiveAgent(agentType)
        const typeInfo = AGENT_TYPES[agentType]

        return (
          <div key={agentType} className="flex items-center">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: index * 0.1 }}
              className={cn(
                "relative flex flex-col items-center rounded-lg border p-3 transition-all",
                status === "running" && "border-primary bg-primary/5 shadow-md",
                status === "completed" && "border-green-500 bg-green-500/5",
                status === "failed" && "border-destructive bg-destructive/5",
                status === "pending" && "border-muted bg-muted/50"
              )}
            >
              {/* Status Icon */}
              <div className="absolute -right-1 -top-1">
                {status === "completed" && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="rounded-full bg-green-500 p-0.5"
                  >
                    <CheckCircle className="h-3 w-3 text-white" />
                  </motion.div>
                )}
                {status === "running" && (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    className="rounded-full bg-primary p-0.5"
                  >
                    <Loader2 className="h-3 w-3 text-white" />
                  </motion.div>
                )}
              </div>

              {/* Agent Icon */}
              <div
                className={cn(
                  "mb-1 text-2xl",
                  status === "running" && "animate-pulse"
                )}
              >
                {typeInfo.icon}
              </div>

              {/* Agent Type */}
              <span className="text-xs font-medium">{typeInfo.name}</span>

              {/* Active Agent Name */}
              {agent && (
                <span className="mt-0.5 text-[10px] text-muted-foreground">
                  {agent.name} {agent.version}
                </span>
              )}

              {/* Status Indicator */}
              <div className="mt-1 flex items-center gap-1">
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    status === "completed" && "bg-green-500",
                    status === "running" && "bg-primary animate-pulse-dot",
                    status === "failed" && "bg-destructive",
                    status === "pending" && "bg-muted-foreground/30"
                  )}
                />
                <span className="text-[10px] text-muted-foreground capitalize">
                  {status}
                </span>
              </div>
            </motion.div>

            {/* Arrow between steps */}
            {index < flowSteps.length - 1 && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 + 0.05 }}
                className="mx-2"
              >
                <ArrowRight
                  className={cn(
                    "h-4 w-4",
                    status === "completed"
                      ? "text-green-500"
                      : "text-muted-foreground/30"
                  )}
                />
              </motion.div>
            )}
          </div>
        )
      })}
    </div>
  )
}
