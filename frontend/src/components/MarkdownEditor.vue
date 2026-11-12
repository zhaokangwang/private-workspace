<script setup lang="ts">
/** CodeMirror 负责选区、行号与撤销；父组件中的草稿是保存时的权威内容。 */
import { onBeforeUnmount, onMounted, ref, watch, nextTick } from 'vue'
import { minimalSetup } from 'codemirror'
import { markdown } from '@codemirror/lang-markdown'
import { Compartment, EditorState } from '@codemirror/state'
import {
  EditorView,
  highlightActiveLine,
  highlightActiveLineGutter,
  keymap,
  lineNumbers,
} from '@codemirror/view'
import { indentWithTab } from '@codemirror/commands'
import { applyFormat } from '@/markdown/commands'
import type { FormatCommand } from '@/markdown/commands'

const props = defineProps<{ modelValue: string; disabled: boolean; visible: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const host = ref<HTMLDivElement | null>(null)
const editable = new Compartment()
let view: EditorView | undefined

onMounted(() => {
  if (!host.value) return
  view = new EditorView({
    parent: host.value,
    state: EditorState.create({
      doc: props.modelValue,
      extensions: [
        minimalSetup,
        lineNumbers(),
        highlightActiveLine(),
        highlightActiveLineGutter(),
        markdown(),
        EditorView.lineWrapping,
        keymap.of([indentWithTab]),
        editable.of(EditorState.readOnly.of(props.disabled)),
        EditorView.contentAttributes.of({ 'aria-label': 'Markdown 正文', spellcheck: 'false' }),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) emit('update:modelValue', update.state.doc.toString())
        }),
        EditorView.theme({
          '&': { height: '100%', fontSize: '14px' },
          '.cm-scroller': {
            overflow: 'auto',
            fontFamily: 'Consolas, "Microsoft YaHei", monospace',
            lineHeight: '1.9',
          },
          '.cm-content': { padding: '24px 16px', minHeight: '100%' },
          '.cm-gutters': {
            background: '#fafcfb',
            borderRight: '1px solid #edf1ef',
            color: '#9aa9a2',
          },
          '.cm-activeLine, .cm-activeLineGutter': { background: '#eff6f3' },
          '&.cm-focused': { outline: 'none' },
        }),
      ],
    }),
  })
})
watch(
  () => props.modelValue,
  (value) => {
    if (view && value !== view.state.doc.toString()) {
      view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value } })
    }
  },
)
watch(
  () => props.disabled,
  (value) => view?.dispatch({ effects: editable.reconfigure(EditorState.readOnly.of(value)) }),
)
watch(
  () => props.visible,
  async () => {
    await nextTick()
    view?.requestMeasure()
  },
)
onBeforeUnmount(() => view?.destroy())
defineExpose({
  format(command: FormatCommand): void {
    if (view && !props.disabled) applyFormat(view, command)
  },
})
</script>

<template><div ref="host" class="markdown-editor" /></template>
<style scoped>
.markdown-editor {
  min-width: 0;
  height: 100%;
  overflow: hidden;
}
</style>
