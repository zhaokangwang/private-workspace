/** 检查真实后端连接，响应字段与后端健康检查模型保持一致。 */
export interface HealthResponse {
  status: 'ok'
  service: string
  version: string
}

function isHealthResponse(value: unknown): value is HealthResponse {
  return (
    typeof value === 'object' &&
    value !== null &&
    'status' in value &&
    value.status === 'ok' &&
    'service' in value &&
    typeof value.service === 'string' &&
    'version' in value &&
    typeof value.version === 'string'
  )
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/v1/health', { signal: AbortSignal.timeout(5000) })

  if (!response.ok) {
    throw new Error(`后端请求失败，状态码为 ${response.status}。`)
  }

  const payload: unknown = await response.json()
  if (!isHealthResponse(payload)) {
    throw new Error('后端响应格式不符合接口约定。')
  }

  return payload
}
