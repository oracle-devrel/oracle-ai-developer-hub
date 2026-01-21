"use client"

import { useState } from "react"
import { X, RefreshCw, CheckCircle, XCircle, Loader2 } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useAppStore } from "@/lib/store"
import { healthCheck, getAgentCard, discoverAgents } from "@/lib/api-client"

interface TestResult {
  name: string
  status: "pending" | "running" | "success" | "error"
  message?: string
  data?: unknown
}

export function DevToolsDrawer() {
  const { devToolsOpen, setDevToolsOpen } = useAppStore()
  const [testResults, setTestResults] = useState<TestResult[]>([])
  const [isRunning, setIsRunning] = useState(false)

  const runTest = async (
    name: string,
    testFn: () => Promise<unknown>
  ): Promise<TestResult> => {
    try {
      const data = await testFn()
      return { name, status: "success", data }
    } catch (error) {
      return {
        name,
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      }
    }
  }

  const runAllTests = async () => {
    setIsRunning(true)
    setTestResults([
      { name: "Health Check", status: "pending" },
      { name: "Agent Card", status: "pending" },
      { name: "Agent Discovery", status: "pending" },
    ])

    const results: TestResult[] = []

    // Health Check
    setTestResults((prev) =>
      prev.map((t) => (t.name === "Health Check" ? { ...t, status: "running" } : t))
    )
    results.push(await runTest("Health Check", healthCheck))
    setTestResults((prev) =>
      prev.map((t) => (t.name === "Health Check" ? results[0] : t))
    )

    // Agent Card
    setTestResults((prev) =>
      prev.map((t) => (t.name === "Agent Card" ? { ...t, status: "running" } : t))
    )
    results.push(await runTest("Agent Card", getAgentCard))
    setTestResults((prev) =>
      prev.map((t) => (t.name === "Agent Card" ? results[1] : t))
    )

    // Agent Discovery
    setTestResults((prev) =>
      prev.map((t) => (t.name === "Agent Discovery" ? { ...t, status: "running" } : t))
    )
    results.push(await runTest("Agent Discovery", () => discoverAgents("document.query")))
    setTestResults((prev) =>
      prev.map((t) => (t.name === "Agent Discovery" ? results[2] : t))
    )

    setIsRunning(false)
  }

  const StatusIcon = ({ status }: { status: TestResult["status"] }) => {
    switch (status) {
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case "error":
        return <XCircle className="h-4 w-4 text-red-500" />
      case "running":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
      default:
        return <div className="h-4 w-4 rounded-full border-2 border-muted" />
    }
  }

  return (
    <AnimatePresence>
      {devToolsOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50"
            onClick={() => setDevToolsOpen(false)}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 z-50 h-full w-full max-w-lg border-l bg-background shadow-xl"
          >
            <div className="flex h-14 items-center justify-between border-b px-4">
              <h2 className="text-lg font-semibold">Developer Tools</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setDevToolsOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <ScrollArea className="h-[calc(100vh-3.5rem)]">
              <div className="space-y-4 p-4">
                {/* A2A Protocol Tests */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">A2A Protocol Tests</CardTitle>
                    <CardDescription>
                      Test connectivity with the FastAPI backend
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Button
                      onClick={runAllTests}
                      disabled={isRunning}
                      className="w-full gap-2"
                    >
                      {isRunning ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                      Run All Tests
                    </Button>

                    {testResults.length > 0 && (
                      <div className="space-y-2">
                        {testResults.map((result) => (
                          <div
                            key={result.name}
                            className="flex items-center justify-between rounded-lg border p-3"
                          >
                            <div className="flex items-center gap-2">
                              <StatusIcon status={result.status} />
                              <span className="text-sm font-medium">
                                {result.name}
                              </span>
                            </div>
                            <Badge
                              variant={
                                result.status === "success"
                                  ? "success"
                                  : result.status === "error"
                                  ? "destructive"
                                  : "secondary"
                              }
                            >
                              {result.status}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Connection Info */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Connection Info</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">API URL</span>
                        <code className="rounded bg-muted px-2 py-0.5">
                          {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
                        </code>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Protocol</span>
                        <code className="rounded bg-muted px-2 py-0.5">A2A v1.0</code>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Test Results Detail */}
                {testResults.some((r) => r.data) && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Response Data</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="max-h-64 overflow-auto rounded-lg bg-muted p-3 text-xs">
                        {JSON.stringify(
                          testResults.filter((r) => r.data).map((r) => ({
                            test: r.name,
                            data: r.data,
                          })),
                          null,
                          2
                        )}
                      </pre>
                    </CardContent>
                  </Card>
                )}
              </div>
            </ScrollArea>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
