"use client"

import { useEffect, useCallback, useRef } from "react"
import {
  FileText,
  Globe,
  FolderGit,
  Brain,
  Monitor,
  Settings,
  Wrench,
  Upload,
  Database,
} from "lucide-react"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import { useAppStore } from "@/lib/store"
import { COLLECTION_INFO, type Collection } from "@/types"

export function CommandPalette() {
  const {
    commandPaletteOpen,
    setCommandPaletteOpen,
    setReasoningEnabled,
    reasoningEnabled,
    setDemoMode,
    demoMode,
    setSettingsOpen,
    setDevToolsOpen,
    selectedCollection,
    setSelectedCollection,
  } = useAppStore()

  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setCommandPaletteOpen(!commandPaletteOpen)
      }
    }

    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [commandPaletteOpen, setCommandPaletteOpen])

  const runCommand = useCallback(
    (command: () => void) => {
      setCommandPaletteOpen(false)
      command()
    },
    [setCommandPaletteOpen]
  )

  const handleUploadPDF = () => {
    fileInputRef.current?.click()
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) {
            // Trigger upload logic - this will be connected to the upload handler
            console.log("Upload PDF:", file.name)
          }
        }}
      />
      <CommandDialog open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
        <CommandInput placeholder="Type a command or search..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>

          <CommandGroup heading="Documents">
            <CommandItem onSelect={() => runCommand(handleUploadPDF)}>
              <FileText className="mr-2 h-4 w-4" />
              <span>Upload PDF</span>
            </CommandItem>
            <CommandItem
              onSelect={() =>
                runCommand(() => {
                  const url = prompt("Enter URL to process:")
                  if (url) console.log("Process URL:", url)
                })
              }
            >
              <Globe className="mr-2 h-4 w-4" />
              <span>Add URL to Knowledge Base</span>
            </CommandItem>
            <CommandItem
              onSelect={() =>
                runCommand(() => {
                  const path = prompt("Enter repository path or URL:")
                  if (path) console.log("Process Repo:", path)
                })
              }
            >
              <FolderGit className="mr-2 h-4 w-4" />
              <span>Process Repository</span>
            </CommandItem>
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Knowledge Base">
            {(Object.keys(COLLECTION_INFO) as Collection[]).map((key) => (
              <CommandItem
                key={key}
                onSelect={() => runCommand(() => setSelectedCollection(key))}
              >
                <Database className="mr-2 h-4 w-4" />
                <span>
                  {COLLECTION_INFO[key].icon} {COLLECTION_INFO[key].name}
                </span>
                {selectedCollection === key && (
                  <span className="ml-auto text-xs text-muted-foreground">Active</span>
                )}
              </CommandItem>
            ))}
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Modes">
            <CommandItem
              onSelect={() => runCommand(() => setReasoningEnabled(!reasoningEnabled))}
            >
              <Brain className="mr-2 h-4 w-4" />
              <span>Toggle Reasoning Mode</span>
              <span className="ml-auto text-xs text-muted-foreground">
                {reasoningEnabled ? "ON" : "OFF"}
              </span>
            </CommandItem>
            <CommandItem onSelect={() => runCommand(() => setDemoMode(!demoMode))}>
              <Monitor className="mr-2 h-4 w-4" />
              <span>Toggle Demo Mode</span>
              <span className="ml-auto text-xs text-muted-foreground">
                {demoMode ? "ON" : "OFF"}
              </span>
            </CommandItem>
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Settings">
            <CommandItem onSelect={() => runCommand(() => setSettingsOpen(true))}>
              <Settings className="mr-2 h-4 w-4" />
              <span>Open Settings</span>
            </CommandItem>
            <CommandItem onSelect={() => runCommand(() => setDevToolsOpen(true))}>
              <Wrench className="mr-2 h-4 w-4" />
              <span>Developer Tools</span>
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  )
}
