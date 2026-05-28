<template>
  <aside class="agent-session-sidebar">
    <div class="agent-session-sidebar__header">
      <span class="agent-session-sidebar__title">{{ title }}</span>
      <el-button type="primary" link :disabled="disabled" @click="$emit('new')">
        + {{ t('page.agent.newSession') }}
      </el-button>
    </div>
    <div v-if="historyLimit" class="agent-session-sidebar__hint">
      {{ t('page.agent.historyHint', { limit: historyLimit }) }}
    </div>
    <el-scrollbar class="agent-session-sidebar__list">
      <div
        v-for="item in sessions"
        :key="item.id"
        class="session-item"
        :class="{ 'session-item--active': item.id === activeId }"
        @click="$emit('select', item.id)"
      >
        <div class="session-item__title">{{ item.title || defaultTitle(item) }}</div>
        <div class="session-item__meta">
          <el-tag size="small" :type="statusType(item.status)">{{ statusLabel(item.status) }}</el-tag>
          <span class="session-item__time">{{ formatTime(item.created_at) }}</span>
        </div>
      </div>
      <EmptyState v-if="!sessions.length" :title="t('page.agent.noSessions')" />
    </el-scrollbar>
  </aside>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import EmptyState from '@/components/common/EmptyState.vue'

defineProps({
  title: { type: String, default: '' },
  sessions: { type: Array, default: () => [] },
  activeId: { type: Number, default: null },
  historyLimit: { type: Number, default: 10 },
  disabled: { type: Boolean, default: false },
})

defineEmits(['new', 'select'])

const { t } = useI18n()

function defaultTitle(item) {
  return `${t('page.agent.session')} #${item.id}`
}

function statusType(status) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return 'info'
}

function statusLabel(status) {
  const map = {
    pending: t('page.agent.statusPending'),
    running: t('page.agent.statusRunning'),
    success: t('page.agent.statusSuccess'),
    failed: t('page.agent.statusFailed'),
  }
  return map[status] || status
}

function formatTime(value) {
  if (!value) return ''
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString()
}
</script>

<style scoped lang="scss">
.agent-session-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 480px;
  border-right: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-blank);
}

.agent-session-sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.agent-session-sidebar__title {
  font-weight: 600;
  font-size: 14px;
}

.agent-session-sidebar__hint {
  padding: 4px 12px 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.agent-session-sidebar__list {
  flex: 1;
  padding: 8px;
}

.session-item {
  padding: 10px;
  margin-bottom: 6px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;

  &:hover {
    background: var(--el-fill-color-light);
  }

  &--active {
    background: rgba($color-primary, 0.08);
    border-color: rgba($color-primary, 0.25);
  }
}

.session-item__title {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.session-item__time {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}
</style>
