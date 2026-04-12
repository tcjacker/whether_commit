const BASE = import.meta.env.VITE_API_BASE ?? ''

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const json = await res.json()
      detail = json.detail ?? detail
    } catch {}
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const get = <T>(path: string) => request<T>('GET', path)
export const post = <T>(path: string, body: unknown) => request<T>('POST', path, body)
