<template>
  <aside
    class="agent-session-sidebar"
    :class="{ 'agent-session-sidebar--collapsed': collapsed }"
    :style="!collapsed ? { width: sidebarWidthPx } : {}"
    ref="sidebarRef"
  >
    <!-- Collapsed: icon-only narrow bar -->
    <template v-if="collapsed">
      <div class="agent-session-sidebar__collapsed-header">
        <button class="agent-session-sidebar__toggle-btn" @click="$emit('toggle')" :title="t('page.agent.expandSidebar')">
          <el-icon><DArrowRight /></el-icon>
        </button>
      </div>
      <div class="agent-session-sidebar__collapsed-icons">
        <button class="agent-session-sidebar__collapsed-icon-btn" :title="t('page.agent.newSession')" :disabled="disabled" @click="$emit('new')">
          <el-icon><Plus /></el-icon>
        </button>
        <button class="agent-session-sidebar__collapsed-icon-btn" :title="t('page.agent.history')">
          <el-icon><Clock /></el-icon>
        </button>
      </div>
    </template>

    <!-- Expanded: full sidebar -->
    <template v-else>
      <!-- Toggle button (collapse) -->
      <button class="agent-session-sidebar__toggle-btn agent-session-sidebar__toggle-btn--collapse" @click="$emit('toggle')" :title="t('page.agent.collapseSidebar')">
        <el-icon><DArrowLeft /></el-icon>
      </button>

      <div class="agent-session-sidebar__header">
        <span class="agent-session-sidebar__title">{{ title }}</span>
        <el-button type="primary" link :disabled="disabled" @click="$emit('new')">
          + {{ t('page.agent.newSession') }}
        </el-button>
      </div>
      <!-- SIT-F7: Search box -->
      <div class="agent-session-sidebar__search">
        <el-input
          v-model="searchQuery"
          :placeholder="t('page.agent.searchSessions')"
          :prefix-icon="Search"
          clearable
          size="small"
        />
      </div>
      <div v-if="historyLimit && !searchQuery" class="agent-session-sidebar__hint">
        {{ t('page.agent.historyHint', { limit: historyLimit }) }}
      </div>
      <!-- Drag handle -->
      <div class="agent-session-sidebar__drag-handle" @mousedown="onDragStart" />
      <el-scrollbar class="agent-session-sidebar__list">
        <div
          v-for="item in filteredSessions"
          :key="item.id"
          class="session-item"
          :class="{ 'session-item--active': item.id === activeId }"
          @click="$emit('select', item.id)"
        >
          <div class="session-item__body">
            <div class="session-item__title">{{ item.title || defaultTitle(item) }}</div>
            <div class="session-item__meta">
              <el-tag size="small" :type="statusType(item.status)">{{ statusLabel(item.status) }}</el-tag>
              <span class="session-item__time">{{ formatTime(item.created_at) }}</span>
            </div>
          </div>
          <!-- SIT-F7: Three-dot menu -->
          <el-dropdown trigger="click" @command="(cmd) => onMenuCommand(cmd, item)">
            <span class="session-item__menu-btn" @click.stop>
              <el-icon><MoreFilled /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">
                  <el-icon><Edit /></el-icon> {{ t('page.agent.editTitle') }}
                </el-dropdown-item>
                <el-dropdown-item command="delete" :disabled="item.status === 'running'">
                  <el-icon><Delete /></el-icon> {{ t('page.agent.deleteSession') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <EmptyState v-if="!filteredSessions.length" :title="t('page.agent.noSessions')" />
      </el-scrollbar>
    </template>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Delete, Edit, MoreFilled, Search, DArrowLeft, DArrowRight, Plus, Clock } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { renameFunctionalSession, deleteFunctionalSession, renameApiSession, deleteApiSession } from '@/api/aiGeneration'

const props = defineProps({
  title: { type: String, default: '' },
  sessions: { type: Array, default: () => [] },
  activeId: { type: Number, default: null },
  historyLimit: { type: Number, default: 10 },
  disabled: { type: Boolean, default: false },
  agentType: { type: String, default: 'functional' }, // 'functional' or 'api'
  collapsed: { type: Boolean, default: false },
})

const emit = defineEmits(['new', 'select', 'toggle'])

const { t } = useI18n()

// SIT-F7: Search
const searchQuery = ref('')
const filteredSessions = computed(() => {
  if (!searchQuery.value.trim()) return props.sessions
  const q = searchQuery.value.trim().toLowerCase()
  return props.sessions.filter((s) => (s.title || '').toLowerCase().includes(q))
})

// SIT-F7: Resizable sidebar width
const STORAGE_KEY = 'agent_sidebar_width'
const DEFAULT_WIDTH = 220
const MIN_WIDTH = 160
const MAX_WIDTH = 360
const sidebarWidth = ref(DEFAULT_WIDTH)
const sidebarWidthPx = computed(() => `${sidebarWidth.value}px`)
const sidebarRef = ref(null)
let isDragging = false
let dragStartX = 0
let dragStartWidth = 0

function onDragStart(e) {
  isDragging = true
  dragStartX = e.clientX
  dragStartWidth = sidebarWidth.value
  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onDragMove(e) {
  if (!isDragging) return
  const delta = e.clientX - dragStartX
  const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, dragStartWidth + delta))
  sidebarWidth.value = newWidth
}

function onDragEnd() {
  isDragging = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  try { localStorage.setItem(STORAGE_KEY, String(sidebarWidth.value)) } catch {}
}

onMounted(() => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const w = parseInt(saved, 10)
      if (w >= MIN_WIDTH && w <= MAX_WIDTH) sidebarWidth.value = w
    }
  } catch {}
})

// SIT-F7: Menu commands
async function onMenuCommand(command, item) {
  if (command === 'edit') {
    try {
      const { value } = await ElMessageBox.prompt(t('page.agent.editTitle'), '', {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        inputValue: item.title || '',
        inputPattern: /^.{1,200}$/,
        inputErrorMessage: t('validation.required'),
      })
      if (!value || !value.trim()) return
      const renameFn = props.agentType === 'functional' ? renameFunctionalSession : renameApiSession
      await renameFn(item.id, value.trim())
      ElMessage.success(t('page.agent.renameSuccess'))
      emit('select', item.id) // refresh list
    } catch (e) {
      if (e !== 'cancel') ElMessage.error(e?.message || t('common.requestFailed'))
    }
  } else if (command === 'delete') {
    if (item.status === 'running') {
      ElMessage.warning(t('page.agent.deleteRunningHint'))
      return
    }
    try {
      await ElMessageBox.confirm(
        t('page.agent.deleteConfirm', { title: item.title || defaultTitle(item) }),
        t('common.confirmTitle'),
        { confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel'), type: 'warning' },
      )
      const deleteFn = props.agentType === 'functional' ? deleteFunctionalSession : deleteApiSession
      await deleteFn(item.id)
      ElMessage.success(t('page.agent.deleteSuccess'))
      if (item.id === props.activeId) emit('new') // back to landing if deleted current
      else emit('select', props.activeId) // refresh list
    } catch (e) {
      if (e !== 'cancel') ElMessage.error(e?.message || t('common.requestFailed'))
    }
  }
}

function defaultTitle(item) {
  return `${t('page.agent.session')} #${item.id}`
}

function statusType(status) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  if (status === 'confirm') return 'primary'
  return 'info'
}

function statusLabel(status) {
  const map = {
    pending: t('page.agent.statusPending'),
    running: t('page.agent.statusRunning'),
    confirm: t('page.agent.statusConfirming'),
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
  flex-shrink: 0;
  transition: width 0.2s ease;
  position: relative;

  &--collapsed {
    width: 48px !important;
    min-width: 48px;
    border-right: 1px solid var(--el-border-color-lighter);
    align-items: center;
  }

  @media (max-width: 767px) {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 1001;
    background: var(--el-bg-color);
    transform: translateX(-100%);
    box-shadow: 4px 0 16px rgba(0, 0, 0, 0.12);

    &--open {
      transform: translateX(0);
    }
  }
}

/* Toggle collapse/expand button */
.agent-session-sidebar__toggle-btn {
  position: absolute;
  top: 8px;
  right: -12px;
  z-index: 10;
  width: 24px;
  height: 24px;
  border: 1px solid var(--el-border-color);
  border-radius: 50%;
  background: var(--el-bg-color);
  color: var(--el-text-color-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  font-size: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.15s;

  &:hover {
    background: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary);
    color: var(--el-color-primary);
  }

  &--collapse {
    right: -12px;
  }

  .agent-session-sidebar--collapsed & {
    position: relative;
    top: auto;
    right: auto;
    width: 32px;
    height: 32px;
    margin: 8px auto 0;
    border: none;
    background: transparent;
    box-shadow: none;

    &:hover {
      background: var(--el-fill-color-light);
      color: var(--el-color-primary);
    }
  }
}

/* Collapsed header */
.agent-session-sidebar__collapsed-header {
  flex-shrink: 0;
  padding: 8px 0;
  width: 100%;
  display: flex;
  justify-content: center;
}

/* Collapsed icon buttons area */
.agent-session-sidebar__collapsed-icons {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  width: 100%;
}

.agent-session-sidebar__collapsed-icon-btn {
  width: 36px;
  height: 36px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-blank);
  color: var(--el-text-color-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  transition: all 0.15s;

  &:hover:not(:disabled) {
    background: rgba($color-primary, 0.08);
    border-color: rgba($color-primary, 0.3);
    color: $color-primary;
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
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

// SIT-F7: Search box
.agent-session-sidebar__search {
  padding: 8px 12px 4px;
}

// SIT-F7: Drag handle
.agent-session-sidebar__drag-handle {
  position: absolute;
  top: 0;
  right: -3px;
  bottom: 0;
  width: 6px;
  cursor: col-resize;
  z-index: 2;
  opacity: 0;
  transition: opacity 0.15s;

  &:hover {
    opacity: 1;
    background: $color-primary;
  }

  @media (max-width: 991px) {
    display: none;
  }
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
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 10px;
  margin-bottom: 6px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;

  &:hover {
    background: var(--el-fill-color-light);

    .session-item__menu-btn {
      opacity: 1;
    }
  }

  &--active {
    background: rgba($color-primary, 0.08);
    border-color: rgba($color-primary, 0.25);
  }
}

.session-item__body {
  flex: 1;
  min-width: 0;
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

// SIT-F7: Menu button
.session-item__menu-btn {
  opacity: 0;
  transition: opacity 0.15s;
  padding: 2px;
  border-radius: 4px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  font-size: 14px;
  flex-shrink: 0;
  margin-left: 4px;
  margin-top: 2px;

  &:hover {
    color: var(--el-text-color-primary);
    background: var(--el-fill-color-light);
  }
}
</style>
