const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface UploadResponse {
  message: string
  document_id: string
  chunks_processed: number
}

export interface HealthCheckResponse {
  status: string
  timestamp: string
  components: Record<string, { status: string }>
}

export interface AgentCardResponse {
  name: string
  version: string
  description: string
  capabilities: string[]
}

export async function uploadPDF(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append("file", file)

  const response = await fetch(`${API_BASE_URL}/upload/pdf`, {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "Failed to upload PDF")
  }

  return response.json()
}

export async function processURL(url: string): Promise<UploadResponse> {
  const response = await fetch(`${API_BASE_URL}/a2a`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "document.upload",
      params: { type: "url", url },
      id: `url-${Date.now()}`,
    }),
  })

  if (!response.ok) {
    throw new Error("Failed to process URL")
  }

  const data = await response.json()
  if (data.error) {
    throw new Error(data.error.message)
  }

  return data.result
}

export async function processRepository(path: string): Promise<UploadResponse> {
  const response = await fetch(`${API_BASE_URL}/a2a`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "document.upload",
      params: { type: "repo", path },
      id: `repo-${Date.now()}`,
    }),
  })

  if (!response.ok) {
    throw new Error("Failed to process repository")
  }

  const data = await response.json()
  if (data.error) {
    throw new Error(data.error.message)
  }

  return data.result
}

export async function healthCheck(): Promise<HealthCheckResponse> {
  const response = await fetch(`${API_BASE_URL}/a2a/health`)

  if (!response.ok) {
    throw new Error("Health check failed")
  }

  return response.json()
}

export async function getAgentCard(): Promise<AgentCardResponse> {
  const response = await fetch(`${API_BASE_URL}/agent_card`)

  if (!response.ok) {
    throw new Error("Failed to get agent card")
  }

  return response.json()
}

export async function discoverAgents(capability: string) {
  const response = await fetch(`${API_BASE_URL}/a2a`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "agent.discover",
      params: { capability },
      id: `discover-${Date.now()}`,
    }),
  })

  if (!response.ok) {
    throw new Error("Failed to discover agents")
  }

  const data = await response.json()
  if (data.error) {
    throw new Error(data.error.message)
  }

  return data.result
}

export async function downloadModel(modelName: string): Promise<{ success: boolean; message: string }> {
  // This is a placeholder - in reality, this would need to communicate
  // with the backend to trigger an Ollama pull
  const response = await fetch(`${API_BASE_URL}/a2a`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "model.download",
      params: { model: modelName },
      id: `model-${Date.now()}`,
    }),
  })

  if (!response.ok) {
    throw new Error("Failed to download model")
  }

  const data = await response.json()
  if (data.error) {
    throw new Error(data.error.message)
  }

  return data.result
}

export async function a2aRequest(method: string, params: Record<string, unknown>) {
  const response = await fetch(`${API_BASE_URL}/a2a`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method,
      params,
      id: `${method}-${Date.now()}`,
    }),
  })

  if (!response.ok) {
    throw new Error(`A2A request failed: ${method}`)
  }

  const data = await response.json()
  if (data.error) {
    throw new Error(data.error.message)
  }

  return data.result
}
