<script setup lang="ts">
/** 页面组织布局与导航，保存及草稿规则集中在 documents store。 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { FilePenLine, Plus, ArrowUpRight } from 'lucide-vue-next'
import { useDocumentsStore } from '@/stores/documents'
import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
import WorkspaceSidebar from '@/components/WorkspaceSidebar.vue'
import ReportList from '@/components/ReportList.vue'
import DocumentWorkspace from '@/components/DocumentWorkspace.vue'
import WorkspaceDialog from '@/components/WorkspaceDialog.vue'
import VersionConflictDialog from '@/components/VersionConflictDialog.vue'

const store = useDocumentsStore()
const route = useRoute()
const router = useRouter()
const guard = useUnsavedChanges(store)
const compareVisible = ref(false)

async function open(target: { id: number } | { date?: string }): Promise<void> {
  if ('id' in target && target.id === store.current?.id) return
  if (!(await guard.confirm())) return
  if (await store.openReport(target)) {
    await router.replace({ query: { document: String(store.current?.id) } })
  }
}
async function compare(): Promise<void> {
  compareVisible.value = true
  await store.readLatest()
}
function shortcut(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    if (!guard.visible.value && !compareVisible.value) void store.save()
  }
}
onMounted(() => {
  void store.loadList(1)
  const id = Number(route.query.document)
  if (Number.isSafeInteger(id) && id > 0) void store.openReport({ id })
  window.addEventListener('keydown', shortcut)
})
onBeforeRouteLeave(() => guard.confirm())
onBeforeUnmount(() => {
  window.removeEventListener('keydown', shortcut)
  store.cancelReads()
})
</script>
<template>
  <main class="workspace-shell">
    <WorkspaceSidebar
      :busy="store.opening || store.saving"
      @today="open({})"
      @refresh="store.loadList(1)"
    />
    <ReportList
      :items="store.items"
      :total="store.total"
      :page="store.page"
      :selected-id="store.current?.id"
      :loading="store.listLoading"
      :error="store.listError"
      :busy="store.opening || store.saving"
      @select="open({ id: $event })"
      @today="open({})"
      @date="open({ date: $event })"
      @page="store.loadList"
      @retry="store.loadList()"
    />
    <div class="workspace-main">
      <div v-if="store.openError" class="open-error" role="alert">
        {{ store.openError }} 请从列表重新打开或重试日期入口。
      </div>
      <div v-if="store.opening" class="opening-status" role="status">正在打开日报…</div>
      <DocumentWorkspace v-if="store.current" @compare="compare" />
      <section v-else class="workspace-empty">
        <span class="empty-icon"><FilePenLine :size="37" :stroke-width="1.3" /></span>
        <p class="empty-eyebrow">我的工作记录</p>
        <h2>今天，有哪些新的进展？</h2>
        <p>
          用 Markdown 记下完成的工作、遇到的问题和明天的计划。<br />在左侧打开一篇日报，或从今天开始。
        </p>
        <button class="primary-button" type="button" :disabled="store.opening" @click="open({})">
          <Plus :size="17" />写今日日报<ArrowUpRight :size="15" /></button
        ><span class="manual-note">手动保存 · Ctrl / ⌘ + S</span>
      </section>
    </div>
    <WorkspaceDialog
      :open="guard.visible.value"
      title="当前日报尚未保存"
      :busy="store.saving"
      @close="guard.choose('cancel')"
      ><p>切换前需要处理当前修改。保存失败时，当前输入会继续保留。</p>
      <p v-if="store.saveError" class="dialog-error" role="alert">{{ store.saveError }}</p>
      <template #actions
        ><button type="button" :disabled="store.saving" @click="guard.choose('cancel')">
          继续编辑</button
        ><button type="button" :disabled="store.saving" @click="guard.choose('discard')">
          放弃修改并切换</button
        ><button
          class="primary-button"
          type="button"
          :disabled="store.saving || store.conflict"
          @click="guard.choose('save')"
        >
          {{ store.saving ? '保存中…' : '保存并切换' }}
        </button></template
      ></WorkspaceDialog
    >
    <VersionConflictDialog :open="compareVisible" @close="compareVisible = false" />
  </main>
</template>
<style scoped>
.workspace-shell {
  display: grid;
  grid-template-columns: 196px 276px minmax(0, 1fr);
  height: 100dvh;
  min-height: 620px;
}
.workspace-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: white;
}
.workspace-main > .document-workspace {
  flex: 1;
}
.open-error {
  background: #fff2ee;
  color: var(--color-error);
  padding: 14px 24px;
  font-size: 13px;
}
.opening-status {
  background: #edf7f1;
  color: var(--color-primary);
  padding: 10px 24px;
  font-size: 12px;
}
.workspace-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 40px 24px;
  text-align: center;
  background: radial-gradient(ellipse at 50% 40%, #f4faf6 0, white 65%);
}
.empty-icon {
  display: grid;
  place-items: center;
  width: 90px;
  height: 90px;
  border: 1px solid #dcebe2;
  color: #5c977b;
  background: #f0f8f3;
  border-radius: 24px;
  margin-bottom: 26px;
  box-shadow: 0 8px 20px #24583c06;
}
.empty-eyebrow {
  font-size: 11px;
  letter-spacing: 0.2em;
  color: #7d9988;
  margin-bottom: 12px;
}
h2 {
  font-size: 25px;
  font-weight: 600;
  margin-bottom: 14px;
}
.workspace-empty > p:not(.empty-eyebrow) {
  font-size: 13px;
  line-height: 2;
  color: var(--color-muted);
}
.workspace-empty > button {
  margin: 28px 0 16px;
  padding-inline: 20px;
}
.manual-note {
  font-size: 11px;
  color: #8ca394;
}
.dialog-error {
  margin-top: 12px;
  color: var(--color-error);
}
@media (max-width: 1100px) {
  .workspace-shell {
    grid-template-columns: 68px 250px minmax(0, 1fr);
  }
}
@media (max-width: 700px) {
  .workspace-shell {
    display: flex;
    flex-direction: column;
    height: auto;
    min-height: 100dvh;
  }
  .workspace-main {
    min-height: 650px;
  }
  .workspace-empty {
    min-height: 450px;
  }
}
</style>
