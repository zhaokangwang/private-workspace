<script setup lang="ts">
/** 应用导航；当前只呈现已经实现的日报入口。 */
import { BookOpen, CalendarDays, FileText, PanelLeft } from 'lucide-vue-next'
defineProps<{ busy: boolean }>()
const emit = defineEmits<{ today: []; refresh: [] }>()
</script>
<template>
  <aside class="workspace-sidebar">
    <div class="brand">
      <span class="brand-mark"><PanelLeft :size="23" /></span>
      <div>
        <strong>私人工作站</strong>
        <p>Markdown 日报工作台</p>
      </div>
    </div>
    <p class="navigation-label">工作记录</p>
    <nav aria-label="工作站导航">
      <button class="navigation-item active" type="button" @click="emit('refresh')">
        <FileText :size="18" /><span>全部日报</span>
      </button>
      <button class="navigation-item" type="button" :disabled="busy" @click="emit('today')">
        <CalendarDays :size="18" /><span>今天的日报</span>
      </button>
    </nav>
    <div class="sidebar-bottom">
      <a href="/docs" target="_blank" rel="noopener noreferrer"
        ><BookOpen :size="17" /><span>接口文档</span></a
      >
      <div class="local-profile">
        <span class="avatar">我</span>
        <div>
          <strong>个人工作空间</strong>
          <p>本地 SQLite 存储</p>
        </div>
      </div>
    </div>
  </aside>
</template>
<style scoped>
.workspace-sidebar {
  background: #f7faf8;
  padding: 28px 18px 18px;
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 48px;
}
.brand-mark {
  display: grid;
  place-items: center;
  background: var(--color-primary);
  color: white;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  flex-shrink: 0;
}
.brand strong {
  font-size: 16px;
  letter-spacing: 0.04em;
}
.brand p {
  font-size: 10px;
  color: var(--color-muted);
  margin-top: 3px;
  white-space: nowrap;
}
.navigation-label {
  font-size: 11px;
  color: var(--color-muted);
  margin: 0 12px 12px;
  letter-spacing: 0.12em;
}
nav {
  display: grid;
  gap: 6px;
}
.navigation-item {
  display: flex;
  gap: 10px;
  padding: 12px;
  border: 0;
  background: transparent;
  text-align: left;
  font-size: 13px;
  color: var(--color-muted);
}
.navigation-item.active {
  background: #e3f1ea;
  color: #17684e;
  font-weight: 600;
}
.sidebar-bottom {
  margin-top: auto;
  padding-top: 32px;
}
.sidebar-bottom a {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  padding: 12px;
  text-decoration: none;
  color: var(--color-muted);
}
.local-profile {
  border-top: 1px solid var(--color-border);
  margin-top: 12px;
  padding: 20px 6px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #deece5;
  color: #32634e;
  display: grid;
  place-items: center;
  font-size: 12px;
}
.local-profile strong {
  font-size: 12px;
  font-weight: 500;
}
.local-profile p {
  font-size: 10px;
  color: var(--color-muted);
}
@media (max-width: 1100px) {
  .workspace-sidebar {
    padding-inline: 10px;
  }
  .brand {
    justify-content: center;
  }
  .brand > div,
  .navigation-label,
  .navigation-item span,
  .sidebar-bottom span,
  .local-profile {
    display: none;
  }
  .navigation-item {
    justify-content: center;
  }
  .sidebar-bottom a {
    justify-content: center;
  }
}
@media (max-width: 700px) {
  .workspace-sidebar {
    flex-direction: row;
    align-items: center;
    padding: 10px 14px;
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
    gap: 12px;
  }
  .brand {
    margin: 0;
  }
  nav {
    display: flex;
    margin-left: auto;
  }
  .navigation-item span {
    display: inline;
    font-size: 12px;
  }
  .sidebar-bottom {
    display: none;
  }
}
</style>
