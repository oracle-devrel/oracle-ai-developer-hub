"use client"

import { X, FileText, Globe, FolderGit, Loader2 } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import type { Document } from "@/types"

const typeIcons = {
  pdf: FileText,
  url: Globe,
  repo: FolderGit,
}

const typeColors = {
  pdf: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100",
  url: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
  repo: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100",
}

export function DocumentChips() {
  const { documents, removeDocument } = useAppStore()

  if (documents.length === 0) return null

  return (
    <div className="border-t bg-muted/50 px-4 py-2">
      <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">Active sources:</span>
        <AnimatePresence mode="popLayout">
          {documents.map((doc) => (
            <DocumentChip
              key={doc.id}
              document={doc}
              onRemove={() => removeDocument(doc.id)}
            />
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}

interface DocumentChipProps {
  document: Document
  onRemove: () => void
}

function DocumentChip({ document, onRemove }: DocumentChipProps) {
  const Icon = typeIcons[document.type]

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ duration: 0.15 }}
    >
      <Badge
        variant="outline"
        className={cn(
          "gap-1.5 pr-1",
          typeColors[document.type],
          document.status === "error" && "border-destructive bg-destructive/10"
        )}
      >
        {document.status === "processing" ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Icon className="h-3 w-3" />
        )}
        <span className="max-w-[150px] truncate">{document.name}</span>
        {document.chunks && (
          <span className="text-[10px] opacity-70">({document.chunks})</span>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="ml-1 h-4 w-4 p-0 hover:bg-transparent"
          onClick={onRemove}
        >
          <X className="h-3 w-3" />
          <span className="sr-only">Remove</span>
        </Button>
      </Badge>
    </motion.div>
  )
}
