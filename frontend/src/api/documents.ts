/** 日报接口：校验响应结构，统一超时与中文错误；Markdown 原文不做隐式转换。 */
import { z } from 'zod'

const summarySchema = z.object({
  id: z.number().int().positive(),
  document_type: z.enum(['daily', 'weekly', 'monthly']),
  title: z.string(),
  period_start: z.string(),
  period_end: z.string(),
  version: z.number().int().positive(),
  created_at: z.string(),
  updated_at: z.string(),
})
const detailSchema = summarySchema.extend({
  content_md: z.string(),
  metadata: z.record(z.string(), z.unknown()),
})
const pageSchema = z.object({
  items: z.array(summarySchema),
  total: z.number().int().nonnegative(),
  page: z.number().int().positive(),
  page_size: z.number().int().positive(),
})

export type DocumentSummary = z.infer<typeof summarySchema>
export type DocumentDetail = z.infer<typeof detailSchema>
export type DocumentPage = z.infer<typeof pageSchema>
export interface SaveDocument {
  expected_version: number
  title: string
  content_md: string
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, schema: z.ZodType<T>, options: RequestInit): Promise<T> {
  const timeout = AbortSignal.timeout(15000)
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json' },
      signal,
    })
  } catch (error) {
    if (options.signal?.aborted) throw error
    throw new ApiError(0, '连接未完成，请检查后端服务后重试。当前输入已保留。')
  }
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = z.object({ detail: z.string() }).safeParse(body)
    const message = detail.success ? detail.data.detail : '请求未完成，请稍后重试。'
    throw new ApiError(response.status, message)
  }
  const parsed = schema.safeParse(body)
  if (!parsed.success) throw new ApiError(0, '接口返回格式不符合约定，请检查前后端版本。')
  return parsed.data
}

export function listDocuments(page: number, signal?: AbortSignal): Promise<DocumentPage> {
  return request(`/documents?document_type=daily&page=${page}&page_size=12`, pageSchema, { signal })
}

export function getDocument(id: number, signal?: AbortSignal): Promise<DocumentDetail> {
  return request(`/documents/${id}`, detailSchema, { signal })
}

export function openDailyReport(
  reportDate?: string,
  signal?: AbortSignal,
): Promise<DocumentDetail> {
  const body = reportDate ? { report_date: reportDate } : {}
  return request('/daily-reports/open', detailSchema, {
    method: 'POST',
    body: JSON.stringify(body),
    signal,
  })
}

export function saveDocument(id: number, body: SaveDocument): Promise<DocumentDetail> {
  return request(`/documents/${id}`, detailSchema, { method: 'PATCH', body: JSON.stringify(body) })
}
