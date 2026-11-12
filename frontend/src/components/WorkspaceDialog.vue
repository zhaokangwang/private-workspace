<script setup lang="ts">
/** 原生 dialog 提供焦点约束和关闭后的焦点恢复。 */
import { onBeforeUnmount, ref, useId, watch } from 'vue'
const props = defineProps<{ open: boolean; title: string; busy?: boolean }>()
const emit = defineEmits<{ close: [] }>()
const element = ref<HTMLDialogElement | null>(null)
const titleId = useId()
watch(
  () => props.open,
  (open) => {
    if (open && !element.value?.open) element.value?.showModal()
    if (!open && element.value?.open) element.value.close()
  },
  { flush: 'post', immediate: true },
)
watch(element, (value) => {
  if (props.open && value && !value.open) value.showModal()
})
function cancel(): void {
  if (!props.busy) emit('close')
}
onBeforeUnmount(() => element.value?.close())
</script>
<template>
  <dialog
    ref="element"
    class="workspace-dialog"
    :aria-labelledby="titleId"
    @cancel.prevent="cancel"
  >
    <h2 :id="titleId">{{ title }}</h2>
    <div class="dialog-body"><slot /></div>
    <footer><slot name="actions" /></footer>
  </dialog>
</template>
<style scoped>
.workspace-dialog {
  width: min(740px, calc(100vw - 32px));
  max-height: calc(100dvh - 40px);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  padding: 28px;
  color: var(--color-text);
  background: white;
  box-shadow: 0 20px 80px #19352b33;
}
.workspace-dialog::backdrop {
  background: #1c332b66;
  backdrop-filter: blur(2px);
}
h2 {
  font-size: 19px;
  margin-bottom: 16px;
}
.dialog-body {
  font-size: 14px;
  color: var(--color-muted);
}
footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
}
</style>
