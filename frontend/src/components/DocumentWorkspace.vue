<script setup lang="ts">
/** 编辑区域从 Pinia 读取同一份草稿，预览和统计均由正文派生。 */
import { computed, defineAsyncComponent, ref } from 'vue'
import {
  CalendarDays,
  Check,
  Circle,
  Columns2,
  Eye,
  FilePenLine,
  Save,
  CircleAlert,
} from 'lucide-vue-next'
import { useDocumentsStore } from '@/stores/documents'
import type MarkdownEditorComponent from '@/components/MarkdownEditor.vue'
import MarkdownPreview from '@/components/MarkdownPreview.vue'
import MarkdownToolbar from '@/components/MarkdownToolbar.vue'
import type { FormatCommand } from '@/markdown/commands'
const emit = defineEmits<{ compare: [] }>()
// 编辑器体积较大，在打开日报时再加载；列表和空页面可以更早显示。
const MarkdownEditor = defineAsyncComponent(() => import('@/components/MarkdownEditor.vue'))
const store = useDocumentsStore()
const mode = ref<'edit' | 'split' | 'preview'>('split')
const editor = ref<InstanceType<typeof MarkdownEditorComponent> | null>(null)
const wordCount = computed(() => Array.from(store.draftBody.replace(/\s/g, '')).length)
const status = computed(() => {
  if (store.saving) return '正在保存…'
  if (store.conflict) return '版本冲突，草稿已保留'
  if (store.saveError) return '保存失败，草稿已保留'
  if (store.dirty) return '有未保存的修改'
  return '已保存'
})
const updatedTime = computed(() =>
  store.current
    ? new Intl.DateTimeFormat('zh-CN', {
        timeZone: 'Asia/Shanghai',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(new Date(store.current.updated_at))
    : '',
)
const modes = [
  { key: 'edit', label: '编辑', icon: FilePenLine },
  { key: 'split', label: '分屏', icon: Columns2 },
  { key: 'preview', label: '预览', icon: Eye },
] as const
function format(command: FormatCommand): void {
  editor.value?.format(command)
}
</script>
<template>
  <section
    v-if="store.current"
    class="document-workspace"
    aria-label="日报编辑工作区"
    :aria-busy="store.opening"
  >
    <header class="document-header">
      <p class="breadcrumb">
        工作记录 <span>/</span> 我的日报 <span>/</span> {{ store.current.period_start }}
      </p>
      <div class="title-row">
        <input
          v-model="store.draftTitle"
          class="document-title"
          aria-label="日报标题"
          placeholder="请输入日报标题"
          :disabled="store.opening"
          :aria-invalid="!store.titleValid"
        /><button
          class="primary-button save-button"
          type="button"
          :disabled="!store.canSave"
          @click="store.save"
        >
          <Save :size="16" />{{ store.saving ? '保存中…' : '保存' }}<kbd>Ctrl S</kbd>
        </button>
      </div>
      <div class="document-meta">
        <span><CalendarDays :size="14" />{{ store.current.period_start }}</span
        ><span
          class="save-status"
          :class="{ pending: store.dirty, failed: store.saveError }"
          role="status"
          ><Check v-if="!store.dirty && !store.saving && !store.saveError" :size="14" /><Circle
            v-else
            :size="10"
          />{{ status }}</span
        >
        <div class="view-modes" role="group" aria-label="视图模式">
          <button
            v-for="item in modes"
            :key="item.key"
            type="button"
            :aria-pressed="mode === item.key"
            :class="{ chosen: mode === item.key }"
            @click="mode = item.key"
          >
            <component :is="item.icon" :size="14" />{{ item.label }}
          </button>
        </div>
      </div>
    </header>
    <div v-if="!store.titleValid" class="notice error-message" role="alert">
      标题需要包含 1 到 200 个字符。
    </div>
    <div v-if="store.saveError" class="notice error-message" role="alert">
      <CircleAlert :size="16" /><span>{{ store.saveError }}</span
      ><button v-if="store.conflict" type="button" @click="emit('compare')">
        读取最新版本并比较
      </button>
    </div>
    <div v-else-if="store.latest" class="notice merge-notice">
      <span>草稿已保留，请手动合并后保存。</span
      ><button type="button" @click="emit('compare')">查看参考版本</button>
    </div>
    <MarkdownToolbar :disabled="store.opening || mode === 'preview' || !editor" @format="format" />
    <div class="pane-labels" :class="mode">
      <span v-if="mode !== 'preview'">MARKDOWN 原文</span
      ><span v-if="mode !== 'edit'"><Eye :size="12" />实时预览</span>
    </div>
    <div class="document-panes" :class="mode">
      <div v-show="mode !== 'preview'" class="editor-pane">
        <p v-if="!editor" class="editor-loading" role="status">正在加载编辑器…</p>
        <MarkdownEditor
          :key="store.current.id"
          ref="editor"
          v-model="store.draftBody"
          :disabled="store.opening"
          :visible="mode !== 'preview'"
        />
      </div>
      <MarkdownPreview v-if="mode !== 'edit'" :source="store.draftBody" />
    </div>
    <footer class="document-footer">
      <span
        ><span class="markdown-badge">M↓</span>Markdown
        <span class="footer-separator">·</span> UTF-8</span
      ><span
        >{{ wordCount }} 字符 <span class="footer-separator">·</span> v{{ store.current.version }}
        <span class="footer-separator">·</span> 保存于 {{ updatedTime }}</span
      >
    </footer>
  </section>
</template>
<style scoped>
.document-workspace {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: white;
}
.document-header {
  padding: 26px 32px 19px;
}
.breadcrumb {
  color: #84988c;
  font-size: 11px;
  display: flex;
  gap: 10px;
  align-items: center;
}
.breadcrumb span {
  color: #c1cdc6;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 18px;
  margin: 21px 0 16px;
}
.document-title {
  font: inherit;
  font-size: 26px;
  font-weight: 650;
  letter-spacing: -0.03em;
  width: 100%;
  min-width: 0;
  border: 1px solid transparent;
  padding: 4px 5px;
  margin-left: -6px;
  color: var(--color-text);
  background: transparent;
  border-radius: 6px;
}
.document-title:hover {
  border-color: var(--color-border);
}
.document-title:focus {
  outline: 2px solid #91c8b3;
}
.save-button {
  flex-shrink: 0;
  font-size: 12px;
}
kbd {
  margin-left: 6px;
  opacity: 0.6;
  font-size: 9px;
  font-family: inherit;
  border: 1px solid #ffffff50;
  padding: 1px 4px;
  border-radius: 3px;
}
.document-meta {
  display: flex;
  align-items: center;
  gap: 18px;
  font-size: 11px;
  color: var(--color-muted);
  flex-wrap: wrap;
}
.document-meta > span {
  display: flex;
  align-items: center;
  gap: 6px;
}
.save-status {
  color: var(--color-primary);
}
.save-status.pending {
  color: #92702e;
}
.save-status.failed {
  color: var(--color-error);
}
.view-modes {
  display: flex;
  gap: 3px;
  margin-left: auto;
  background: #f2f6f3;
  padding: 3px;
  border-radius: 7px;
}
.view-modes button {
  display: flex;
  gap: 5px;
  align-items: center;
  padding: 4px 9px;
  font-size: 11px;
  border: 0;
  background: transparent;
  color: var(--color-muted);
}
.view-modes button.chosen {
  background: white;
  color: var(--color-primary);
  box-shadow: 0 1px 3px #1c3b2912;
}
.notice {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 25px;
  font-size: 12px;
  background: #fff6f1;
}
.notice button {
  margin-left: auto;
  flex-shrink: 0;
  font-size: 11px;
}
.merge-notice {
  background: #fff9e8;
  color: #826c37;
}
.pane-labels,
.document-panes {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}
.pane-labels.edit,
.pane-labels.preview,
.document-panes.edit,
.document-panes.preview {
  grid-template-columns: minmax(0, 1fr);
}
.pane-labels {
  font-size: 10px;
  color: #7f9287;
  background: #fbfdfb;
  border-bottom: 1px solid var(--color-border);
  letter-spacing: 0.08em;
}
.pane-labels span {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 24px;
}
.pane-labels.split span + span,
.document-panes.split > :last-child {
  border-left: 1px solid var(--color-border);
}
.document-panes {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.editor-pane {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.editor-loading {
  padding: 24px;
  font-size: 12px;
  color: var(--color-muted);
}
.document-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 24px;
  border-top: 1px solid var(--color-border);
  font-size: 10px;
  color: #7a8d82;
}
.markdown-badge {
  color: #61796c;
  font-weight: bold;
  font-size: 11px;
  margin-right: 6px;
}
.footer-separator {
  padding: 0 7px;
  color: #bdc9c1;
}
@media (max-width: 1200px) {
  .document-header {
    padding: 24px;
  }
  .document-title {
    font-size: 23px;
  }
  .document-meta {
    gap: 12px;
  }
}
@media (max-width: 700px) {
  .document-header {
    padding: 20px;
  }
  .title-row {
    gap: 8px;
  }
  .document-title {
    font-size: 21px;
  }
  kbd {
    display: none;
  }
  .view-modes {
    margin-left: 0;
  }
  .document-panes {
    min-height: 450px;
  }
  .document-panes.split {
    grid-template-columns: 1fr;
    grid-template-rows: 280px 1fr;
    overflow: auto;
  }
  .document-panes.split > :last-child {
    border-left: 0;
    border-top: 1px solid var(--color-border);
    min-height: 250px;
  }
  .pane-labels.split span + span {
    display: none;
  }
  .pane-labels.split {
    grid-template-columns: 1fr;
  }
  .notice {
    flex-wrap: wrap;
    padding-inline: 20px;
  }
}
</style>
