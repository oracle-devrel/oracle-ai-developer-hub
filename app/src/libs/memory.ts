// KV API wrappers for conversation state
export interface KvValue { [key: string]: any }

const API_BASE = '/api/memory'; // If a different base/proxy is used, adjust here.

export async function setKv(
  conversationId: string,
  key: string,
  value: KvValue,
  ttlSeconds?: number
): Promise<void> {
  const url = `${API_BASE}/kv/${encodeURIComponent(conversationId)}/${encodeURIComponent(key)}${
    ttlSeconds ? `?ttlSeconds=${ttlSeconds}` : ''
  }`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(value),
  });
  if (!response.ok) {
    throw new Error(`Failed to set KV (${response.status}): ${await safeText(response)}`);
  }
}

export async function getKv(
  conversationId: string,
  key: string
): Promise<KvValue | null> {
  const url = `${API_BASE}/kv/${encodeURIComponent(conversationId)}/${encodeURIComponent(key)}`;
  const response = await fetch(url);
  if (!response.ok) {
    return null; // 404 or other errors treated as missing
  }
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function deleteKv(conversationId: string, key: string): Promise<void> {
  const url = `${API_BASE}/kv/${encodeURIComponent(conversationId)}/${encodeURIComponent(key)}`;
  const response = await fetch(url, { method: 'DELETE' });
  if (!response.ok) {
    throw new Error(`Failed to delete KV (${response.status}): ${await safeText(response)}`);
  }
}

async function safeText(resp: Response): Promise<string> {
  try { return await resp.text(); } catch { return ''; }
}
