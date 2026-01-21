"use client"

import { Bot, Settings, Wrench, Monitor } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Switch } from "@/components/ui/switch"
import { useAppStore } from "@/lib/store"
import { AVAILABLE_MODELS } from "@/types"
import { cn } from "@/lib/utils"

export function Header() {
  const {
    selectedModel,
    setSelectedModel,
    demoMode,
    setDemoMode,
    setSettingsOpen,
    setDevToolsOpen,
    setCommandPaletteOpen,
  } = useAppStore()

  const currentModel = AVAILABLE_MODELS.find((m) => m.id === selectedModel)

  return (
    <header className="flex h-14 items-center justify-between border-b bg-background px-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Bot className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold">Agentic RAG</span>
        </div>

        <div className="ml-4 hidden items-center gap-2 text-sm text-muted-foreground sm:flex">
          <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
            <span className="text-xs">⌘</span>K
          </kbd>
          <span>for commands</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Model Selector */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <span className="hidden sm:inline">Model:</span>
              <span className="font-medium">{currentModel?.name || selectedModel}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Select Model</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {AVAILABLE_MODELS.map((model) => (
              <DropdownMenuItem
                key={model.id}
                onClick={() => setSelectedModel(model.id)}
                className={cn(
                  "flex items-center justify-between",
                  selectedModel === model.id && "bg-accent"
                )}
              >
                <span>{model.name}</span>
                <span className="text-xs text-muted-foreground">{model.size}</span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Demo Mode Toggle */}
        <div className="flex items-center gap-2 rounded-md border px-3 py-1.5">
          <Monitor className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm">Demo</span>
          <Switch
            checked={demoMode}
            onCheckedChange={setDemoMode}
            className="scale-75"
          />
        </div>

        {/* Settings Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setSettingsOpen(true)}
          className="h-9 w-9"
        >
          <Settings className="h-4 w-4" />
          <span className="sr-only">Settings</span>
        </Button>

        {/* Dev Tools Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setDevToolsOpen(true)}
          className="h-9 w-9"
        >
          <Wrench className="h-4 w-4" />
          <span className="sr-only">Developer Tools</span>
        </Button>
      </div>
    </header>
  )
}
