"use client"

import { useRef, useCallback } from "react"
import { Send, Paperclip, Brain, Trash2, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Checkbox } from "@/components/ui/checkbox"
import { Slider } from "@/components/ui/slider"
import { useAppStore } from "@/lib/store"
import { STRATEGY_INFO, type ReasoningStrategy } from "@/types"
import { cn } from "@/lib/utils"

interface ChatInputProps {
  value: string
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  onSubmit: (e: React.FormEvent) => void
  isLoading: boolean
  onClear?: () => void
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  isLoading,
  onClear,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const {
    reasoningEnabled,
    setReasoningEnabled,
    reasoningConfig,
    setReasoningConfig,
    addDocument,
  } = useAppStore()

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        onSubmit(e)
      }
    },
    [onSubmit]
  )

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
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
    e.target.value = ""
  }

  const toggleStrategy = (strategy: ReasoningStrategy) => {
    const strategies = reasoningConfig.strategies.includes(strategy)
      ? reasoningConfig.strategies.filter((s) => s !== strategy)
      : [...reasoningConfig.strategies, strategy]
    setReasoningConfig({ strategies })
  }

  return (
    <div className="border-t bg-background p-4">
      <div className="mx-auto max-w-3xl">
        <form onSubmit={onSubmit} className="relative">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={handleFileUpload}
          />

          <Textarea
            ref={textareaRef}
            value={value}
            onChange={onChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything... (Shift+Enter for new line)"
            className="min-h-[60px] resize-none pr-32"
            rows={2}
            disabled={isLoading}
          />

          <div className="absolute bottom-2 right-2 flex items-center gap-1">
            {/* Attachment Button */}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
            >
              <Paperclip className="h-4 w-4" />
              <span className="sr-only">Attach file</span>
            </Button>

            {/* Reasoning Toggle with Popover */}
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant={reasoningEnabled ? "default" : "ghost"}
                  size="icon"
                  className={cn("h-8 w-8", reasoningEnabled && "bg-primary")}
                  disabled={isLoading}
                >
                  <Brain className="h-4 w-4" />
                  <span className="sr-only">Reasoning mode</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-80">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium">Reasoning Mode</h4>
                    <Button
                      variant={reasoningEnabled ? "default" : "outline"}
                      size="sm"
                      onClick={() => setReasoningEnabled(!reasoningEnabled)}
                    >
                      {reasoningEnabled ? "ON" : "OFF"}
                    </Button>
                  </div>

                  {reasoningEnabled && (
                    <>
                      <div className="space-y-2">
                        <label className="text-sm font-medium">Strategies</label>
                        <div className="grid grid-cols-2 gap-2">
                          {(Object.keys(STRATEGY_INFO) as ReasoningStrategy[]).map(
                            (strategy) => (
                              <div
                                key={strategy}
                                className="flex items-center gap-2"
                              >
                                <Checkbox
                                  id={strategy}
                                  checked={reasoningConfig.strategies.includes(
                                    strategy
                                  )}
                                  onCheckedChange={() => toggleStrategy(strategy)}
                                />
                                <label
                                  htmlFor={strategy}
                                  className="cursor-pointer text-sm"
                                >
                                  {STRATEGY_INFO[strategy].icon}{" "}
                                  {STRATEGY_INFO[strategy].name}
                                </label>
                              </div>
                            )
                          )}
                        </div>
                      </div>

                      <div className="space-y-3 pt-2">
                        <div className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span>ToT Depth</span>
                            <span className="text-muted-foreground">
                              {reasoningConfig.totDepth}
                            </span>
                          </div>
                          <Slider
                            value={[reasoningConfig.totDepth]}
                            min={1}
                            max={5}
                            step={1}
                            onValueChange={([v]) =>
                              setReasoningConfig({ totDepth: v })
                            }
                          />
                        </div>

                        <div className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span>Consistency Samples</span>
                            <span className="text-muted-foreground">
                              {reasoningConfig.consistencySamples}
                            </span>
                          </div>
                          <Slider
                            value={[reasoningConfig.consistencySamples]}
                            min={1}
                            max={7}
                            step={1}
                            onValueChange={([v]) =>
                              setReasoningConfig({ consistencySamples: v })
                            }
                          />
                        </div>
                      </div>

                      <div className="flex gap-2 pt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() =>
                            setReasoningConfig({ strategies: ["cot"] })
                          }
                        >
                          Quick
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() =>
                            setReasoningConfig({
                              strategies: ["cot", "self_reflection"],
                            })
                          }
                        >
                          Deep
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() =>
                            setReasoningConfig({
                              strategies: [
                                "cot",
                                "tot",
                                "react",
                                "self_reflection",
                                "consistency",
                              ],
                            })
                          }
                        >
                          Ensemble
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              </PopoverContent>
            </Popover>

            {/* Clear Button */}
            {onClear && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={onClear}
                disabled={isLoading}
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">Clear chat</span>
              </Button>
            )}

            {/* Send Button */}
            <Button
              type="submit"
              size="icon"
              className="h-8 w-8"
              disabled={isLoading || !value.trim()}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              <span className="sr-only">Send message</span>
            </Button>
          </div>
        </form>

        <p className="mt-2 text-center text-xs text-muted-foreground">
          Drop files here or paste URLs to add to knowledge base
        </p>
      </div>
    </div>
  )
}
