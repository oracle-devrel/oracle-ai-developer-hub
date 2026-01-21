"use client"

import { X } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useAppStore } from "@/lib/store"
import { AVAILABLE_MODELS, COLLECTION_INFO, type Collection } from "@/types"
import { cn } from "@/lib/utils"

export function SettingsDrawer() {
  const {
    settingsOpen,
    setSettingsOpen,
    selectedModel,
    setSelectedModel,
    selectedCollection,
    setSelectedCollection,
    reasoningEnabled,
    setReasoningEnabled,
    reasoningConfig,
    setReasoningConfig,
  } = useAppStore()

  const currentModel = AVAILABLE_MODELS.find((m) => m.id === selectedModel)

  return (
    <AnimatePresence>
      {settingsOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50"
            onClick={() => setSettingsOpen(false)}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 z-50 h-full w-full max-w-md border-l bg-background shadow-xl"
          >
            <div className="flex h-14 items-center justify-between border-b px-4">
              <h2 className="text-lg font-semibold">Settings</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSettingsOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-6 p-4">
              {/* Model Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Model</label>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="w-full justify-between">
                      <span>{currentModel?.name || selectedModel}</span>
                      <span className="text-xs text-muted-foreground">
                        {currentModel?.size}
                      </span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-full">
                    {AVAILABLE_MODELS.map((model) => (
                      <DropdownMenuItem
                        key={model.id}
                        onClick={() => setSelectedModel(model.id)}
                        className={cn(
                          selectedModel === model.id && "bg-accent"
                        )}
                      >
                        <span>{model.name}</span>
                        <span className="ml-auto text-xs text-muted-foreground">
                          {model.size}
                        </span>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* Collection Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Knowledge Base</label>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="w-full justify-start gap-2">
                      <span>{COLLECTION_INFO[selectedCollection].icon}</span>
                      <span>{COLLECTION_INFO[selectedCollection].name}</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-full">
                    {(Object.keys(COLLECTION_INFO) as Collection[]).map((key) => (
                      <DropdownMenuItem
                        key={key}
                        onClick={() => setSelectedCollection(key)}
                        className={cn(selectedCollection === key && "bg-accent")}
                      >
                        <span className="mr-2">{COLLECTION_INFO[key].icon}</span>
                        <span>{COLLECTION_INFO[key].name}</span>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* Reasoning Mode */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium">Reasoning Mode</label>
                    <p className="text-xs text-muted-foreground">
                      Enable advanced reasoning strategies
                    </p>
                  </div>
                  <Switch
                    checked={reasoningEnabled}
                    onCheckedChange={setReasoningEnabled}
                  />
                </div>

                {reasoningEnabled && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-4 rounded-lg border p-4"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm">Tree of Thoughts Depth</label>
                        <span className="text-sm text-muted-foreground">
                          {reasoningConfig.totDepth}
                        </span>
                      </div>
                      <Slider
                        value={[reasoningConfig.totDepth]}
                        min={1}
                        max={5}
                        step={1}
                        onValueChange={([value]) =>
                          setReasoningConfig({ totDepth: value })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm">Consistency Samples</label>
                        <span className="text-sm text-muted-foreground">
                          {reasoningConfig.consistencySamples}
                        </span>
                      </div>
                      <Slider
                        value={[reasoningConfig.consistencySamples]}
                        min={1}
                        max={7}
                        step={1}
                        onValueChange={([value]) =>
                          setReasoningConfig({ consistencySamples: value })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm">Reflection Turns</label>
                        <span className="text-sm text-muted-foreground">
                          {reasoningConfig.reflectionTurns}
                        </span>
                      </div>
                      <Slider
                        value={[reasoningConfig.reflectionTurns]}
                        min={1}
                        max={5}
                        step={1}
                        onValueChange={([value]) =>
                          setReasoningConfig({ reflectionTurns: value })
                        }
                      />
                    </div>
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
