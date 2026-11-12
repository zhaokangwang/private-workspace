<script setup lang="ts">
/** HTML 由清理后的 Markdown 渲染器生成，预览修改不了原文。 */
import { computed } from 'vue'
import { renderMarkdown } from '@/markdown/render'
import 'highlight.js/styles/github.css'
const props = defineProps<{ source: string }>()
const html = computed(() => renderMarkdown(props.source))
</script>
<template>
  <article class="markdown-preview" aria-label="Markdown 预览">
    <p v-if="!source" class="preview-placeholder">在左侧写下今天的工作，预览会在这里实时呈现。</p>
    <!-- 渲染函数关闭原始 HTML 并经过 DOMPurify 清理。 -->
    <div v-else v-html="html" />
  </article>
</template>
<style scoped>
.markdown-preview {
  overflow: auto;
  padding: 28px 32px;
  overflow-wrap: anywhere;
  font-size: 14px;
  line-height: 1.9;
}
.preview-placeholder {
  color: var(--color-muted);
}
.markdown-preview :deep(h1) {
  font-size: 1.8em;
}
.markdown-preview :deep(h2) {
  font-size: 1.25em;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.5em;
}
.markdown-preview :deep(h3) {
  font-size: 1.1em;
}
.markdown-preview :deep(h1),
.markdown-preview :deep(h2),
.markdown-preview :deep(h3) {
  margin: 1.4em 0 0.7em;
  line-height: 1.5;
}
.markdown-preview :deep(div > :first-child) {
  margin-top: 0;
}
.markdown-preview :deep(p),
.markdown-preview :deep(ul),
.markdown-preview :deep(ol),
.markdown-preview :deep(pre),
.markdown-preview :deep(table),
.markdown-preview :deep(blockquote) {
  margin: 0.8em 0;
}
.markdown-preview :deep(ul),
.markdown-preview :deep(ol) {
  padding-left: 1.6em;
}
.markdown-preview :deep(.task-list-item) {
  list-style: none;
}
.markdown-preview :deep(.task-list-item-checkbox) {
  margin-right: 0.5em;
  accent-color: var(--color-primary);
}
.markdown-preview :deep(code) {
  font-family: Consolas, monospace;
  font-size: 0.9em;
  background: #f0f5f2;
  padding: 0.15em 0.35em;
  border-radius: 4px;
}
.markdown-preview :deep(pre) {
  overflow: auto;
  padding: 16px;
  background: #f5f8f6;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
.markdown-preview :deep(pre code) {
  background: transparent;
  padding: 0;
}
.markdown-preview :deep(blockquote) {
  margin-left: 0;
  padding-left: 16px;
  color: var(--color-muted);
  border-left: 3px solid #86b9a8;
}
.markdown-preview :deep(table) {
  display: block;
  max-width: 100%;
  overflow: auto;
  border-collapse: collapse;
}
.markdown-preview :deep(th),
.markdown-preview :deep(td) {
  border: 1px solid var(--color-border);
  padding: 7px 12px;
}
.markdown-preview :deep(th) {
  background: #f2f7f4;
}
.markdown-preview :deep(a) {
  color: var(--color-primary);
}
.markdown-preview :deep(img) {
  max-width: 100%;
}
</style>
