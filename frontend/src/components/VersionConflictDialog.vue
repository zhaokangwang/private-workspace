<script setup lang="ts">
/** 比较时只读展示双方内容，必须由用户明确选择下一步。 */
import { useDocumentsStore } from '@/stores/documents'
import WorkspaceDialog from '@/components/WorkspaceDialog.vue'
defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()
const store = useDocumentsStore()
function resolve(useRemote: boolean): void {
  store.resolveConflict(useRemote)
  emit('close')
}
</script>
<template>
  <WorkspaceDialog
    :open="open"
    title="比较最新版本与当前草稿"
    :busy="store.conflictLoading"
    @close="emit('close')"
  >
    <p>其他窗口已经保存了新版本。先比较内容，再决定如何继续；这里的操作不会自动保存。</p>
    <p v-if="store.conflictLoading" class="conflict-message" role="status">正在读取最新版本…</p>
    <div v-if="store.conflictError" class="conflict-message error-message" role="alert">
      {{ store.conflictError }} <button type="button" @click="store.readLatest">重试</button>
    </div>
    <div v-if="store.latest" class="comparison">
      <label
        >服务器最新 · v{{ store.latest.version
        }}<input :value="store.latest.title" readonly aria-label="服务器最新标题" /><textarea
          :value="store.latest.content_md"
          readonly
          aria-label="服务器最新正文"
        /></label
      ><label
        >当前草稿<input :value="store.draftTitle" readonly aria-label="当前草稿标题" /><textarea
          :value="store.draftBody"
          readonly
          aria-label="当前草稿正文"
        />
      </label>
    </div>
    <p class="merge-note">
      选择“保留草稿”后，请回到编辑器手动合并需要的内容，再点击保存。可随时重新打开此窗口参考最新内容。
    </p>
    <template #actions
      ><button type="button" :disabled="store.conflictLoading" @click="emit('close')">
        返回编辑</button
      ><button
        type="button"
        :disabled="!store.latest || store.conflictLoading"
        @click="resolve(true)"
      >
        采用最新内容</button
      ><button
        type="button"
        class="primary-button"
        :disabled="!store.latest || store.conflictLoading"
        @click="resolve(false)"
      >
        保留草稿，手动合并
      </button></template
    >
  </WorkspaceDialog>
</template>
<style scoped>
.comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 20px;
}
label {
  display: grid;
  gap: 8px;
  font-size: 12px;
}
input,
textarea {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: #f8faf9;
  color: var(--color-text);
  padding: 10px;
  font: inherit;
}
textarea {
  min-height: 230px;
  resize: vertical;
  font-family: Consolas, 'Microsoft YaHei', monospace;
  line-height: 1.7;
}
.merge-note {
  font-size: 12px;
  margin-top: 16px;
}
.conflict-message {
  margin-top: 16px;
}
@media (max-width: 600px) {
  .comparison {
    grid-template-columns: 1fr;
  }
  textarea {
    min-height: 130px;
  }
}
</style>
