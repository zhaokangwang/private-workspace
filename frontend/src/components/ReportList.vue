<script setup lang="ts">
/** 日报列表只显示服务器数据；分页失败保留当前列表，允许重新尝试。 */
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight, Plus, RefreshCw, CalendarDays, FileText } from 'lucide-vue-next'
import type { DocumentSummary } from '@/api/documents'
const props = defineProps<{
  items: DocumentSummary[]
  total: number
  page: number
  selectedId?: number
  loading: boolean
  error: string
  busy: boolean
}>()
const emit = defineEmits<{
  select: [id: number]
  today: []
  date: [date: string]
  page: [page: number]
  retry: []
}>()
const reportDate = ref('')
const pages = computed(() => Math.max(1, Math.ceil(props.total / 12)))
function submitDate(): void {
  if (reportDate.value) emit('date', reportDate.value)
}
function dateLabel(date: string): string {
  return `${date.slice(5, 7)}月${date.slice(8)}日`
}
</script>
<template>
  <section class="report-list" aria-label="日报列表" :aria-busy="loading">
    <header class="list-heading">
      <div>
        <h1>
          我的日报 <span>{{ total }}</span>
        </h1>
        <p>把每天的进展记录下来</p>
      </div>
      <button
        class="icon-button"
        type="button"
        title="刷新列表"
        aria-label="刷新列表"
        :disabled="loading"
        @click="emit('retry')"
      >
        <RefreshCw :size="16" />
      </button>
    </header>
    <div class="list-actions">
      <button
        class="primary-button today-button"
        type="button"
        :disabled="busy"
        @click="emit('today')"
      >
        <Plus :size="17" />写今日日报
      </button>
      <form class="date-form" @submit.prevent="submitDate">
        <label for="report-date"><CalendarDays :size="14" />按日期打开或补写</label>
        <div>
          <input
            id="report-date"
            v-model="reportDate"
            aria-label="日报日期"
            type="date"
            required
          /><button type="submit" :disabled="busy">打开</button>
        </div>
      </form>
    </div>
    <div v-if="error" class="list-error" role="alert">
      <p>{{ error }}</p>
      <button type="button" @click="emit('retry')">重试</button>
    </div>
    <p v-if="loading && !items.length" class="list-message">正在读取日报…</p>
    <div v-else-if="!items.length && !error" class="list-empty">
      <FileText :size="30" :stroke-width="1.3" />
      <p>还没有日报</p>
      <span>从今天的第一篇开始</span>
    </div>
    <ol v-else class="report-items">
      <li v-for="(item, index) in items" :key="item.id">
        <p
          v-if="
            index === 0 ||
            items[index - 1]?.period_start.slice(0, 7) !== item.period_start.slice(0, 7)
          "
          class="month-label"
        >
          {{ item.period_start.slice(0, 4) }} 年 {{ Number(item.period_start.slice(5, 7)) }} 月
        </p>
        <button
          type="button"
          class="report-item"
          :class="{ selected: item.id === selectedId }"
          :aria-current="item.id === selectedId ? 'true' : undefined"
          :disabled="busy"
          @click="emit('select', item.id)"
        >
          <span class="report-item-top"
            ><span class="report-date">{{ dateLabel(item.period_start) }}</span
            ><span class="report-version">v{{ item.version }}</span></span
          ><strong>{{ item.title }}</strong
          ><span class="report-item-bottom"><FileText :size="12" />Markdown 日报</span>
        </button>
      </li>
    </ol>
    <footer class="pagination">
      <span>共 {{ total }} 篇</span>
      <div>
        <button
          class="icon-button"
          type="button"
          aria-label="上一页"
          :disabled="loading || page <= 1"
          @click="emit('page', page - 1)"
        >
          <ChevronLeft :size="16" /></button
        ><span>{{ page }} / {{ pages }}</span
        ><button
          class="icon-button"
          type="button"
          aria-label="下一页"
          :disabled="loading || page >= pages"
          @click="emit('page', page + 1)"
        >
          <ChevronRight :size="16" />
        </button>
      </div>
    </footer>
  </section>
</template>
<style scoped>
.report-list {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid var(--color-border);
  background: #fff;
}
.list-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 28px 20px 20px;
}
h1 {
  font-size: 19px;
  font-weight: 650;
}
h1 span {
  font-size: 11px;
  font-weight: 500;
  background: #edf3ef;
  color: var(--color-muted);
  padding: 2px 7px;
  border-radius: 12px;
  vertical-align: middle;
  margin-left: 6px;
}
.list-heading p {
  font-size: 11px;
  color: var(--color-muted);
  margin-top: 6px;
}
.list-actions {
  padding: 0 20px 18px;
  border-bottom: 1px solid var(--color-border);
}
.today-button {
  width: 100%;
  justify-content: center;
}
.date-form {
  margin-top: 18px;
}
.date-form label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--color-muted);
  margin-bottom: 7px;
}
.date-form > div {
  display: flex;
  gap: 6px;
}
input {
  min-width: 0;
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 7px;
  font-size: 12px;
  background: white;
  color: var(--color-text);
  font-family: inherit;
}
.date-form button {
  font-size: 12px;
  padding-inline: 9px;
  white-space: nowrap;
}
.report-items {
  flex: 1;
  min-height: 0;
  overflow: auto;
  list-style: none;
  padding: 0 12px 20px;
  margin: 0;
}
.month-label {
  padding: 20px 9px 9px;
  font-size: 11px;
  color: var(--color-muted);
  letter-spacing: 0.06em;
}
.report-item {
  width: 100%;
  display: grid;
  gap: 7px;
  padding: 14px 12px;
  border: 1px solid transparent;
  background: white;
  text-align: left;
  border-radius: 8px;
  margin: 4px 0;
}
.report-item:hover {
  background: #f4f8f5;
}
.report-item.selected {
  background: #edf7f1;
  border-color: #bcdccd;
}
.report-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.report-date {
  font-size: 12px;
  color: var(--color-muted);
}
.report-version {
  font-size: 10px;
  color: #6e8e7b;
}
.report-item strong {
  font-size: 13px;
  font-weight: 550;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.report-item-bottom {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--color-muted);
  font-size: 10px;
}
.pagination {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
  font-size: 11px;
  color: var(--color-muted);
}
.pagination > div {
  display: flex;
  align-items: center;
  gap: 5px;
}
.list-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 50px 10px;
  color: #91a599;
  gap: 6px;
}
.list-empty p {
  font-size: 13px;
  color: var(--color-muted);
  margin-top: 6px;
}
.list-empty span {
  font-size: 11px;
}
.list-error,
.list-message {
  margin: 14px;
  font-size: 12px;
}
.list-error {
  color: var(--color-error);
}
.list-error button {
  margin-top: 8px;
}
@media (max-width: 700px) {
  .report-list {
    max-height: 340px;
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
  }
  .list-heading {
    padding: 16px 20px;
  }
  .list-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .today-button {
    width: auto;
    flex-shrink: 0;
  }
  .date-form {
    margin: 0;
    flex: 1;
  }
  .date-form label {
    display: none;
  }
  .report-items {
    min-height: 80px;
  }
  .month-label {
    padding-top: 10px;
  }
}
</style>
