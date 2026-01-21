export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export const REASONING_PRESETS = {
  quick: {
    name: "Quick Answer",
    strategies: ["standard"] as const,
    totDepth: 1,
    consistencySamples: 1,
    reflectionTurns: 1,
  },
  deep: {
    name: "Deep Analysis",
    strategies: ["cot", "self_reflection"] as const,
    totDepth: 3,
    consistencySamples: 3,
    reflectionTurns: 3,
  },
  ensemble: {
    name: "Full Ensemble",
    strategies: ["cot", "tot", "react", "self_reflection", "consistency"] as const,
    totDepth: 3,
    consistencySamples: 5,
    reflectionTurns: 3,
  },
}

export const KEYBOARD_SHORTCUTS = {
  commandPalette: "mod+k",
  send: "mod+enter",
  newChat: "mod+n",
  toggleReasoning: "mod+r",
  toggleDemo: "mod+d",
}
