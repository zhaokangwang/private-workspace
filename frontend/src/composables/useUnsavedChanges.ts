/** 所有文档切换共用同一个确认入口；保存失败或仍有新输入时阻止离开。 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { useDocumentsStore } from '@/stores/documents'

export function useUnsavedChanges(store: ReturnType<typeof useDocumentsStore>) {
  const visible = ref(false)
  let pending: ((allowed: boolean) => void) | undefined

  function finish(allowed: boolean): void {
    visible.value = false
    pending?.(allowed)
    pending = undefined
  }

  async function choose(action: 'save' | 'discard' | 'cancel'): Promise<void> {
    if (store.saving) return
    if (action === 'save') {
      if ((await store.save()) && !store.dirty) finish(true)
      return
    }
    if (action === 'discard') store.discard()
    finish(action === 'discard')
  }

  function confirm(): Promise<boolean> {
    if (store.saving || store.opening || pending) return Promise.resolve(false)
    if (!store.dirty) return Promise.resolve(true)
    visible.value = true
    return new Promise((resolve) => {
      pending = resolve
    })
  }

  function beforeUnload(event: BeforeUnloadEvent): void {
    if (!store.dirty && !store.saving) return
    event.preventDefault()
    event.returnValue = ''
  }

  onMounted(() => window.addEventListener('beforeunload', beforeUnload))
  onBeforeUnmount(() => {
    window.removeEventListener('beforeunload', beforeUnload)
    finish(false)
  })
  return { visible, confirm, choose }
}
