import { createApp, defineComponent, h } from 'vue'
import { createPinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import { useDocumentsStore } from '@/stores/documents'
import { useUnsavedChanges } from '@/composables/useUnsavedChanges'

function mountGuard() {
  const pinia = createPinia()
  const store = useDocumentsStore(pinia)
  store.current = {
    id: 1,
    version: 1,
    title: '日报',
    content_md: '原文',
    document_type: 'daily',
    period_start: '2026-11-12',
    period_end: '2026-11-12',
    metadata: {},
    created_at: '2026-11-12T00:00:00Z',
    updated_at: '2026-11-12T00:00:00Z',
  }
  store.discard()
  store.draftBody = '草稿'
  let guard: ReturnType<typeof useUnsavedChanges> | undefined
  const app = createApp(
    defineComponent({
      setup() {
        guard = useUnsavedChanges(store)
        return () => h('div')
      },
    }),
  )
  const host = document.createElement('div')
  app.use(pinia).mount(host)
  if (!guard) throw new Error('未能挂载切换保护')
  return { app, guard, store }
}
describe('未保存切换保护', () => {
  it('保存失败继续保留草稿、弹窗和当前日报', async () => {
    const { app, guard, store } = mountGuard()
    vi.spyOn(store, 'save').mockResolvedValue(false)
    const choice = guard.confirm()
    await guard.choose('save')
    expect(guard.visible.value).toBe(true)
    expect(store.draftBody).toBe('草稿')
    await guard.choose('cancel')
    expect(await choice).toBe(false)
    app.unmount()
  })
  it('明确放弃才重置草稿，重复切换不产生第二个待处理弹窗', async () => {
    const { app, guard, store } = mountGuard()
    const choice = guard.confirm()
    expect(await guard.confirm()).toBe(false)
    await guard.choose('discard')
    expect(await choice).toBe(true)
    expect(store.dirty).toBe(false)
    app.unmount()
  })
  it('页面卸载提示只在待保存时生效，卸载组件后清理监听', async () => {
    const { app, guard, store } = mountGuard()
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    const pending = guard.confirm()
    store.saving = true
    await guard.choose('discard')
    expect(store.dirty).toBe(true)
    app.unmount()
    expect(await pending).toBe(false)
    const clean = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(clean)
    expect(clean.defaultPrevented).toBe(false)
  })
})
