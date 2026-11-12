<script setup lang="ts">
/** 只提供实际生效的 Markdown 操作，名称同时用于鼠标提示和无障碍访问。 */
import {
  Heading2,
  Bold,
  Italic,
  List,
  ListTodo,
  Quote,
  Link,
  Code,
  Table2,
  Undo2,
  Redo2,
} from 'lucide-vue-next'
import type { FormatCommand } from '@/markdown/commands'
defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ format: [command: FormatCommand] }>()
const tools = [
  { command: 'heading', label: '二级标题', icon: Heading2 },
  { command: 'bold', label: '加粗', icon: Bold },
  { command: 'italic', label: '斜体', icon: Italic },
  { command: 'list', label: '无序列表', icon: List },
  { command: 'task', label: '任务列表', icon: ListTodo },
  { command: 'quote', label: '引用', icon: Quote },
  { command: 'link', label: '链接', icon: Link },
  { command: 'code', label: '代码块', icon: Code },
  { command: 'table', label: '表格', icon: Table2 },
  { command: 'undo', label: '撤销', icon: Undo2 },
  { command: 'redo', label: '重做', icon: Redo2 },
] satisfies { command: FormatCommand; label: string; icon: typeof Bold }[]
</script>
<template>
  <div class="markdown-toolbar" role="toolbar" aria-label="Markdown 格式">
    <button
      v-for="tool in tools"
      :key="tool.command"
      type="button"
      class="icon-button"
      :disabled="disabled"
      :title="tool.label"
      :aria-label="tool.label"
      @click="emit('format', tool.command)"
    >
      <component :is="tool.icon" :size="17" :stroke-width="1.7" />
    </button>
    <span class="toolbar-note">Markdown</span>
  </div>
</template>
<style scoped>
.markdown-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border-block: 1px solid var(--color-border);
  overflow-x: auto;
}
.toolbar-note {
  margin-left: auto;
  color: var(--color-muted);
  font-size: 12px;
  padding-left: 16px;
}
.icon-button {
  flex-shrink: 0;
}
</style>
