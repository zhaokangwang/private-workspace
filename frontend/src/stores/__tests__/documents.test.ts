/** 回归并发读取、保存中的后续输入、失败及冲突规则，不连接真实数据库。 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as api from '@/api/documents'
import type { DocumentDetail } from '@/api/documents'
import { useDocumentsStore } from '@/stores/documents'

function document(id = 1, version = 1, content = '已保存的正文'): DocumentDetail {
  return {
    id,
    version,
    title: `日报 ${id}`,
    content_md: content,
    document_type: 'daily',
    period_start: '2026-11-12',
    period_end: '2026-11-12',
    metadata: {},
    created_at: '2026-11-12T01:00:00Z',
    updated_at: '2026-11-12T01:00:00Z',
  }
}
function deferred<T>() {
  let resolve: (value: T) => void = () => {
    throw new Error('Promise 尚未初始化')
  }
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}
beforeEach(() => {
  vi.restoreAllMocks()
  setActivePinia(createPinia())
})

describe('日报保存', () => {
  async function openedStore() {
    vi.spyOn(api, 'getDocument').mockResolvedValue(document())
    const store = useDocumentsStore()
    await store.openReport({ id: 1 })
    return store
  }
  it('没有修改时不生成无意义的新版本，空白标题不可提交', async () => {
    const store = await openedStore()
    const save = vi.spyOn(api, 'saveDocument')
    expect(await store.save()).toBe(true)
    expect(save).not.toHaveBeenCalled()
    store.draftTitle = '  '
    expect(await store.save()).toBe(false)
    expect(save).not.toHaveBeenCalled()
  })
  it('网络保存失败保留标题、正文和预期版本', async () => {
    const store = await openedStore()
    vi.spyOn(api, 'saveDocument').mockRejectedValue(new api.ApiError(0, '网络失败'))
    store.draftTitle = '我的草稿'
    store.draftBody = '尚未保存'
    expect(await store.save()).toBe(false)
    expect(store.draftBody).toBe('尚未保存')
    expect(store.draftTitle).toBe('我的草稿')
    expect(store.current?.version).toBe(1)
    expect(store.dirty).toBe(true)
  })
  it('保存期间的后续输入仍然待保存，并阻止切换', async () => {
    const store = await openedStore()
    const response = deferred<DocumentDetail>()
    vi.spyOn(api, 'saveDocument').mockReturnValue(response.promise)
    store.draftBody = '本次提交'
    const saving = store.save()
    expect(await store.openReport({ id: 2 })).toBe(false)
    store.draftBody = '提交后继续输入'
    response.resolve(document(1, 2, '本次提交'))
    expect(await saving).toBe(true)
    expect(store.draftBody).toBe('提交后继续输入')
    expect(store.current?.version).toBe(2)
    expect(store.dirty).toBe(true)
  })
  it('保留本地草稿并读取冲突版本，经明确合并后才用新版本提交', async () => {
    const store = await openedStore()
    const save = vi
      .spyOn(api, 'saveDocument')
      .mockRejectedValueOnce(new api.ApiError(409, '版本冲突'))
    store.draftBody = '本地内容'
    expect(await store.save()).toBe(false)
    vi.spyOn(api, 'getDocument').mockResolvedValue(document(1, 2, '远端内容'))
    await store.readLatest()
    expect(store.draftBody).toBe('本地内容')
    expect(store.current?.version).toBe(1)
    expect(store.canSave).toBe(false)
    store.resolveConflict(false)
    expect(store.draftBody).toBe('本地内容')
    expect(store.current?.version).toBe(2)
    expect(save).toHaveBeenCalledTimes(1)
    store.draftBody = '合并后的内容'
    save.mockResolvedValueOnce(document(1, 3, '合并后的内容'))
    await store.save()
    expect(save).toHaveBeenLastCalledWith(1, {
      expected_version: 2,
      title: '日报 1',
      content_md: '合并后的内容',
    })
    expect(store.dirty).toBe(false)
  })
  it('采用远端内容必须明确选择，不会再提交本地草稿', async () => {
    const store = await openedStore()
    store.draftBody = '本地内容'
    vi.spyOn(api, 'getDocument').mockResolvedValue(document(1, 2, '远端内容'))
    await store.readLatest()
    store.resolveConflict(true)
    expect(store.draftBody).toBe('远端内容')
    expect(store.dirty).toBe(false)
    expect(store.latest).toBeNull()
  })
  it('保存失败后还原为已保存内容，可清除错误且不额外生成版本', async () => {
    const store = await openedStore()
    const save = vi.spyOn(api, 'saveDocument').mockRejectedValue(new api.ApiError(0, '网络失败'))
    store.draftBody = '未提交内容'
    await store.save()
    store.draftBody = '已保存的正文'
    expect(await store.save()).toBe(true)
    expect(store.saveError).toBe('')
    expect(save).toHaveBeenCalledTimes(1)
  })
  it('列表在保存前发起但较晚返回时，仍显示刚保存的新版本', async () => {
    const store = await openedStore()
    const response = deferred<api.DocumentPage>()
    vi.spyOn(api, 'listDocuments').mockReturnValue(response.promise)
    vi.spyOn(api, 'saveDocument').mockResolvedValue(document(1, 2, '新正文'))
    const listing = store.loadList()
    store.draftBody = '新正文'
    await store.save()
    response.resolve({ items: [document()], total: 1, page: 1, page_size: 12 })
    await listing
    expect(store.items[0]?.version).toBe(2)
  })
})

describe('异步请求顺序', () => {
  it('较早打开的日报晚返回，也不能覆盖新选择', async () => {
    const old = deferred<DocumentDetail>()
    vi.spyOn(api, 'getDocument').mockReturnValueOnce(old.promise).mockResolvedValueOnce(document(2))
    const store = useDocumentsStore()
    const first = store.openReport({ id: 1 })
    await store.openReport({ id: 2 })
    old.resolve(document(1))
    expect(await first).toBe(false)
    expect(store.current?.id).toBe(2)
  })
  it('失败的读取保留原报告，过期列表也不覆盖新分页', async () => {
    vi.spyOn(api, 'getDocument')
      .mockResolvedValueOnce(document())
      .mockRejectedValueOnce(new api.ApiError(404, '不存在'))
    const store = useDocumentsStore()
    await store.openReport({ id: 1 })
    expect(await store.openReport({ id: 2 })).toBe(false)
    expect(store.current?.id).toBe(1)
    const old = deferred<api.DocumentPage>()
    vi.spyOn(api, 'listDocuments')
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce({ items: [document(2)], total: 13, page: 2, page_size: 12 })
    const first = store.loadList(1)
    await store.loadList(2)
    old.resolve({ items: [document(1)], total: 13, page: 1, page_size: 12 })
    await first
    expect(store.page).toBe(2)
    expect(store.items[0]?.id).toBe(2)
  })
})
