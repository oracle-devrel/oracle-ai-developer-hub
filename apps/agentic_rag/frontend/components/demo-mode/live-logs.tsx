"use client"

import { useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle, XCircle, Info, AlertTriangle } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useAppStore } from "@/lib/store"
import { AGENT_TYPES, type OrchestrationLog } from "@/types"
import { cn } from "@/lib/utils"

const typeIcons = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
  warning: AlertTriangle,
}

const typeColors = {
  success: "text-green-500",
  error: "text-red-500",
  info: "text-blue-500",
  warning: "text-yellow-500",
}

export function LiveLogs() {
  const { orchestrationLogs } = useAppStore()
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [orchestrationLogs])

  if (orchestrationLogs.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
        Waiting for orchestration activity...
      </div>
    )
  }

  return (
    <ScrollArea className="h-32 rounded-lg border bg-background/50">
      <div ref={scrollRef} className="space-y-1 p-2">
        <AnimatePresence mode="popLayout">
          {orchestrationLogs.map((log, index) => (
            <LogEntry key={`${log.timestamp}-${index}`} log={log} />
          ))}
        </AnimatePresence>
      </div>
    </ScrollArea>
  )
}

function LogEntry({ log }: { log: OrchestrationLog }) {
  const Icon = typeIcons[log.type]
  const colorClass = typeColors[log.type]
  const agentInfo = log.agentType ? AGENT_TYPES[log.agentType] : null

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{
        opacity: log.fade === "out" ? 0.3 : 1,
        x: 0,
      }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.15 }}
      className={cn(
        "flex items-start gap-2 rounded px-2 py-1 text-xs transition-opacity",
        log.fade === "out" && "opacity-30"
      )}
    >
      <Icon className={cn("mt-0.5 h-3 w-3 shrink-0", colorClass)} />

      <span className="shrink-0 font-mono text-muted-foreground">
        {new Date(log.timestamp).toLocaleTimeString()}
      </span>

      {agentInfo && (
        <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px]">
          {agentInfo.icon} {agentInfo.name}
        </span>
      )}

      <span className="flex-1">{log.message}</span>
    </motion.div>
  )
}
