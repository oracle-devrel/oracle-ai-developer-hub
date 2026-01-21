"use client"

import { useState, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Plus, FileText, Globe, FolderGit, Settings, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"

const menuItems = [
  { icon: FileText, label: "Upload PDF", action: "pdf" },
  { icon: Globe, label: "Add URL", action: "url" },
  { icon: FolderGit, label: "Add Repo", action: "repo" },
  { icon: Settings, label: "Settings", action: "settings" },
]

export function FABMenu() {
  const [isOpen, setIsOpen] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { setSettingsOpen, addDocument } = useAppStore()

  const handleAction = (action: string) => {
    setIsOpen(false)

    switch (action) {
      case "pdf":
        fileInputRef.current?.click()
        break
      case "url":
        const url = prompt("Enter URL to add to knowledge base:")
        if (url) {
          addDocument({
            id: `url-${Date.now()}`,
            name: new URL(url).hostname,
            type: "url",
            status: "processing",
            uploadedAt: new Date(),
          })
        }
        break
      case "repo":
        const path = prompt("Enter repository path or URL:")
        if (path) {
          addDocument({
            id: `repo-${Date.now()}`,
            name: path.split("/").pop() || "repository",
            type: "repo",
            status: "processing",
            uploadedAt: new Date(),
          })
        }
        break
      case "settings":
        setSettingsOpen(true)
        break
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      addDocument({
        id: `pdf-${Date.now()}`,
        name: file.name,
        type: "pdf",
        status: "processing",
        uploadedAt: new Date(),
      })
    }
    // Reset input
    e.target.value = ""
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="fixed bottom-6 right-6 z-50">
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="absolute bottom-16 right-0 flex flex-col gap-2"
            >
              {menuItems.map((item, index) => (
                <motion.div
                  key={item.action}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Button
                    variant="secondary"
                    size="sm"
                    className="gap-2 shadow-lg"
                    onClick={() => handleAction(item.action)}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </Button>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <Button
          size="icon"
          className={cn(
            "h-14 w-14 rounded-full shadow-lg transition-transform",
            isOpen && "rotate-45"
          )}
          onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? <X className="h-6 w-6" /> : <Plus className="h-6 w-6" />}
        </Button>
      </div>
    </>
  )
}
