"use client"

import { useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { AgentFlow } from "./agent-flow"
import { LiveLogs } from "./live-logs"
import { AgentAvailability } from "./agent-availability"
import { useAppStore } from "@/lib/store"

export function OrchestrationPanel() {
  const { fadeOutOldLogs } = useAppStore()

  // Auto-fade old logs
  useEffect(() => {
    const interval = setInterval(() => {
      fadeOutOldLogs()
    }, 1000)

    return () => clearInterval(interval)
  }, [fadeOutOldLogs])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="border-b bg-muted/30"
    >
      <div className="mx-auto max-w-5xl p-4">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-muted-foreground">
            Agent Orchestration (Demo Mode)
          </h3>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
            <span className="text-xs text-muted-foreground">Live</span>
          </div>
        </div>

        {/* Agent Flow Visualization */}
        <AgentFlow />

        {/* Live Logs */}
        <div className="mt-4">
          <LiveLogs />
        </div>

        {/* Agent Availability */}
        <div className="mt-4">
          <AgentAvailability />
        </div>
      </div>
    </motion.div>
  )
}
