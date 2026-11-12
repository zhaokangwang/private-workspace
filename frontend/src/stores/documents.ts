/** 工作台状态入口：读取、草稿、人工保存和冲突处理。只有服务端确认后才推进版本。 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  ApiError,
  getDocument,
  listDocuments,
  openDailyReport,
  saveDocument,
} from '@/api/documents'
import type { DocumentDetail, DocumentSummary } from '@/api/documents'

export const useDocumentsStore = defineStore('documents', () => {
  const current = ref<DocumentDetail | null>(null)
  const draftTitle = ref('')
  const draftBody = ref('')
  const items = ref<DocumentSummary[]>([])
  const total = ref(0)
  const page = ref(1)
  const listLoading = ref(false)
  const listError = ref('')
  const opening = ref(false)
  const openError = ref('')
  const saving = ref(false)
  const saveError = ref('')
  const conflict = ref(false)
  const latest = ref<DocumentDetail | null>(null)
  const conflictLoading = ref(false)
  const conflictError = ref('')
  let readSequence = 0
  let listSequence = 0
  let readController: AbortController | undefined
  let listController: AbortController | undefined

  const dirty = computed(
    () =>
      current.value !== null &&
      (draftTitle.value !== current.value.title || draftBody.value !== current.value.content_md),
  )
  const titleValid = computed(() => {
    const length = Array.from(draftTitle.value.trim()).length
    return length > 0 && length <= 200
  })
  const canSave = computed(
    () => dirty.value && titleValid.value && !saving.value && !opening.value && !conflict.value,
  )

  function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : '操作未完成，请重试。'
  }

  function setCurrent(document: DocumentDetail): void {
    current.value = document
    draftTitle.value = document.title
    draftBody.value = document.content_md
    saveError.value = ''
    conflict.value = false
    latest.value = null
    conflictError.value = ''
  }

  async function loadList(targetPage = page.value): Promise<void> {
    const sequence = ++listSequence
    listController?.abort()
    listController = new AbortController()
    listLoading.value = true
    listError.value = ''
    try {
      const result = await listDocuments(targetPage, listController.signal)
      if (sequence !== listSequence) return
      // 列表可能在保存前发起，不能用它的旧概要覆盖刚确认的新版本。
      const active = current.value
      items.value = result.items.map((item) =>
        active && item.id === active.id && item.version < active.version ? active : item,
      )
      total.value = result.total
      page.value = result.page
    } catch (error) {
      if (sequence === listSequence) listError.value = errorMessage(error)
    } finally {
      if (sequence === listSequence) listLoading.value = false
    }
  }

  /** 旧请求即使晚返回，也不能覆盖已经打开的另一篇日报。 */
  async function openReport(target: { id: number } | { date?: string }): Promise<boolean> {
    if (saving.value) return false
    const sequence = ++readSequence
    readController?.abort()
    readController = new AbortController()
    opening.value = true
    openError.value = ''
    try {
      const document =
        'id' in target
          ? await getDocument(target.id, readController.signal)
          : await openDailyReport(target.date, readController.signal)
      if (sequence !== readSequence) return false
      setCurrent(document)
      if (!('id' in target)) void loadList(1)
      return true
    } catch (error) {
      if (sequence === readSequence) openError.value = errorMessage(error)
      return false
    } finally {
      if (sequence === readSequence) opening.value = false
    }
  }

  /** 失败保留草稿；请求期间继续输入时，只确认本次发送的内容，后续输入仍待保存。 */
  async function save(): Promise<boolean> {
    if (!current.value || saving.value || opening.value || conflict.value) return false
    if (!dirty.value) {
      saveError.value = ''
      return true
    }
    if (!titleValid.value) {
      saveError.value = '请输入 1 到 200 个字符的标题。'
      return false
    }
    const id = current.value.id
    const title = draftTitle.value
    const content = draftBody.value
    const expectedVersion = current.value.version
    saving.value = true
    saveError.value = ''
    try {
      const saved = await saveDocument(id, {
        expected_version: expectedVersion,
        title,
        content_md: content,
      })
      if (current.value?.id !== id) return false
      current.value = saved
      if (draftTitle.value === title) draftTitle.value = saved.title
      if (draftBody.value === content) draftBody.value = saved.content_md
      items.value = items.value.map((item) => (item.id === id ? saved : item))
      latest.value = null
      return true
    } catch (error) {
      if (current.value?.id === id) {
        saveError.value = errorMessage(error)
        conflict.value = error instanceof ApiError && error.status === 409
      }
      return false
    } finally {
      saving.value = false
    }
  }

  /** 只读取对方版本用于比较，绝不在读取时覆盖本地草稿。 */
  async function readLatest(): Promise<void> {
    if (!current.value || conflictLoading.value) return
    const id = current.value.id
    conflictLoading.value = true
    conflictError.value = ''
    latest.value = null
    try {
      const document = await getDocument(id)
      if (current.value?.id === id) latest.value = document
    } catch (error) {
      if (current.value?.id === id) conflictError.value = errorMessage(error)
    } finally {
      conflictLoading.value = false
    }
  }

  /** 用户明确选择后才采用新版本；保留草稿时仍需要人工比较和再次保存。 */
  function resolveConflict(useRemote: boolean): void {
    if (!latest.value || latest.value.id !== current.value?.id) return
    if (useRemote) setCurrent(latest.value)
    else {
      current.value = latest.value
      conflict.value = false
      saveError.value = ''
    }
    items.value = items.value
      .map((item) => (item.id === current.value?.id ? current.value : item))
      .filter((item): item is DocumentSummary => item !== null)
  }

  function discard(): void {
    if (current.value) setCurrent(current.value)
  }

  function cancelReads(): void {
    ++readSequence
    ++listSequence
    readController?.abort()
    listController?.abort()
    opening.value = false
    listLoading.value = false
  }

  return {
    current,
    draftTitle,
    draftBody,
    items,
    total,
    page,
    listLoading,
    listError,
    opening,
    openError,
    saving,
    saveError,
    conflict,
    latest,
    conflictLoading,
    conflictError,
    dirty,
    titleValid,
    canSave,
    loadList,
    openReport,
    save,
    readLatest,
    resolveConflict,
    discard,
    cancelReads,
  }
})
