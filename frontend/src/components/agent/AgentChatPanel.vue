<template>
  <div class="agent-chat-panel">
    <el-scrollbar ref="scrollRef" class="agent-chat-panel__messages">
      <div v-for="msg in messages" :key="msg.id || `${msg.role}-${msg.sequence}`"
           class="chat-msg" :class="`chat-msg--${msg.role}`">
        <!-- ===== 用户消息 ===== -->
        <template v-if="msg.role === 'user'">
          <div class="chat-msg__avatar">
            <el-icon :size="18" color="#909399"><User /></el-icon>
          </div>
          <div class="chat-msg__body">
            <div class="chat-msg__meta">
              <span class="chat-msg__role-name">{{ roleLabel('user') }}</span>
            </div>
            <div class="chat-msg__bubble chat-msg__bubble--user">
              <div class="chat-msg__text">{{ msg.content }}</div>
            </div>
          </div>
        </template>

        <!-- ===== 统一的智能体回复（分阶段展示）===== -->
        <template v-else-if="msg.role === 'agent'">
          <div class="chat-msg__avatar chat-msg__avatar--agent">
            <el-icon :size="20"><ChatDotRound /></el-icon>
          </div>
          <div class="chat-msg__body">
            <div class="chat-msg__meta">
              <span class="chat-msg__role-name">{{ t('page.agent.roleAgent') }}</span>
              <el-tag v-if="msg.isStreaming" size="small" type="primary" effect="light" round>
                {{ msg.stages.some(s => s.status !== 'done') ? t('page.agent.executing') : t('page.agent.thinking') }}
              </el-tag>
              <el-tag v-else size="small" type="success" effect="light" round>{{ t('page.agent.completed') }}</el-tag>
            </div>

            <!-- 阶段列表：每个阶段独立区块（过滤掉default阶段，history阶段会显示） -->
            <div v-if="msg.stages?.filter(s => s.name !== 'default').length" class="agent-stages">
              <div
                v-for="(stage, idx) in msg.stages.filter(s => s.name !== 'default')"
                :key="stage.name || idx"
                class="agent-stage-block"
                :class="{ 'is-done': stage.status === 'done' }"
              >
                <!-- 阶段标题行：图标 + 名称 + 状态 + 折叠箭头 -->
                <div class="agent-stage-block__header" @click="toggleStageExpand(stage)">
                  <!-- 状态图标：完成=绿勾，进行中=旋转 -->
                  <span class="agent-stage-block__status-icon">
                    <el-icon v-if="stage.status === 'done'" color="#67c23a"><CircleCheckFilled /></el-icon>
                    <el-icon v-else color="#409eff" class="is-loading"><Loading /></el-icon>
                  </span>

                  <!-- 阶段名称 -->
                  <span class="agent-stage-block__name">{{ getStageLabel(stage.name) }}</span>

                  <!-- 完成标签 -->
                  <el-tag v-if="stage.status === 'done'" size="small" type="success" effect="plain" round>
                    {{ t('page.agent.completed') }}
                  </el-tag>

                  <!-- 展开/折叠箭头 -->
                  <span class="agent-stage-block__arrow" :class="{ 'is-collapsed': stage._collapsed }">
                    <el-icon><ArrowUp /></el-icon>
                  </span>
                </div>

                <!-- 灰底详情框（展示阶段详细内容，可拖拽调整高度） -->
                <transition name="stage-detail">
                  <div
                    v-show="stage._collapsed !== true"
                    class="agent-stage-block__detail"
                    :ref="el => setStageDetailRef(el, idx)"
                  >
                    <div class="agent-stage-block__terminal" :style="{ maxHeight: stage._height ? stage._height + 'px' : undefined }">
                      <!-- 阶段文本描述 -->
                      <div v-if="stage.text" class="agent-stage-block__stage-text">{{ stage.text }}</div>
                      <!-- 日志行 -->
                      <template v-if="stage.logs?.length">
                        <div v-for="(line, i) in visibleLogs(stage.logs)" :key="i"
                             class="agent-stage-block__log-line">{{ line }}</div>
                      </template>
                      <div v-else-if="stage.status === 'running'"
                           class="agent-stage-block__log-line agent-stage-block__log-line--empty">
                        {{ t('page.agent.thinking') }}...
                      </div>
                    </div>
                    <!-- 拖拽手柄 -->
                    <div
                      class="agent-stage-block__drag-handle"
                      @mousedown.prevent="onDragStart($event, idx)"
                    />
                  </div>
                </transition>
              </div>
            </div>

            <!-- 最终文本内容（所有阶段完成后显示）- 已整合到各阶段详情框中 -->
            <div v-if="msg.finalText && !msg.isStreaming && !msg.stages?.some(s => s.logs?.length)" class="agent-final-text">{{ msg.finalText }}</div>

            <!-- 流式文本（正在输出时实时显示 - 仅当无阶段进度时显示） -->
            <div v-if="msg.isStreaming && msg.streamingText && !msg.stages?.length" class="agent-final-text agent-final-text--streaming">
              {{ msg.streamingText }}
            </div>

            <!-- 完成后的结果卡片 -->
            <AgentResultCard
              v-if="msg.payload && !msg.isStreaming && hasPayloadContent(msg.payload)"
              :payload="msg.payload"
              :gen-type="genType"
              @open-list="$emit('open-case-list', $event)"
            />
          </div>
        </template>

        <!-- ===== 兼容历史消息（role=assistant/tool/system）===== -->
        <template v-else>
          <div class="chat-msg__avatar">
            <el-icon v-if="msg.role === 'assistant'" :size="20" color="#6366f1"><ChatDotRound /></el-icon>
            <el-icon v-else :size="16" color="#e6a23c"><Cpu /></el-icon>
          </div>
          <div class="chat-msg__body">
            <div class="chat-msg__meta">
              <span class="chat-msg__role-name">{{ roleLabel(msg.role) }}</span>
              <span v-if="msg.role === 'tool' && msg.tool_name" class="chat-msg__stage">
                <el-tag size="small" type="warning" effect="light" round>{{ msg.tool_name }}</el-tag>
              </span>
            </div>
            <div class="chat-msg__bubble" :class="{ 'chat-msg__bubble--user': msg.role === 'user' }">
              <template v-if="msg.message_type === 'tool_call'">
                <div class="chat-msg__tool-header">
                  <el-icon><Setting /></el-icon>
                  <span>{{ msg.tool_name || t('page.agent.executing') }}</span>
                  <el-icon class="is-loading" v-if="!msg.content"><Loading /></el-icon>
                </div>
                <pre v-if="msg.content" class="chat-msg__tool-content">{{ msg.content }}</pre>
              </template>
              <template v-else-if="msg.message_type === 'custom'">
                <div class="chat-msg__stage-item">
                  <el-icon color="#67c23a" style="margin-right:4px;"><CircleCheckFilled /></el-icon>
                  <span>{{ msg.content }}</span>
                </div>
              </template>
              <template v-else>
                <div class="chat-msg__text" :class="{ 'chat-msg__text--long': isLongContent(msg.content) }">
                  {{ msg.content }}
                </div>
              </template>
            </div>
          </div>
        </template>
      </div>

      <!-- Legacy streaming text indicator (backward compat) -->
      <div v-if="showLegacyStreaming" class="chat-msg chat-msg--assistant">
        <div class="chat-msg__avatar">
          <el-icon :size="20" color="#6366f1"><ChatDotRound /></el-icon>
        </div>
        <div class="chat-msg__body">
          <div class="chat-msg__meta">
            <span class="chat-msg__role-name">{{ roleLabel('assistant') }}</span>
          </div>
          <div class="chat-msg__bubble chat-msg__bubble--streaming">
            <div class="chat-msg__text chat-msg__text--streaming">{{ streamingText }}</div>
          </div>
        </div>
      </div>

      <!-- Thinking indicator -->
      <div v-if="showThinkingIndicator" class="chat-msg chat-msg--assistant">
        <div class="chat-msg__avatar">
          <el-icon :size="20" color="#6366f1"><ChatDotRound /></el-icon>
        </div>
        <div class="chat-msg__body">
          <div class="chat-msg__bubble chat-msg__bubble--thinking">
            <el-icon class="is-loading"><Loading /></el-icon>
            {{ t('page.agent.thinking') }}
          </div>
        </div>
      </div>
    </el-scrollbar>

    <!-- Slot for embedded PayloadCard after messages (legacy) -->
    <slot name="after-messages" />
  </div>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch, onUpdated } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Loading,
  ChatDotRound,
  User,
  Cpu,
  Setting,
  CircleCheckFilled,
  ArrowUp,
} from '@element-plus/icons-vue'
import AgentResultCard from './AgentResultCard.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  streaming: { type: Boolean, default: false },
  streamingText: { type: String, default: '' },
  hasStageProgress: { type: Boolean, default: false },
  stageLogLines: { type: Array, default: () => [] },
  quickTags: { type: Array, default: () => [] },
  agentType: { type: String, default: 'functional' },
})

const emit = defineEmits(['send', 'stop', 'open-case-list'])

const { t } = useI18n()
const scrollRef = ref(null)
const genType = computed(() => props.agentType)

// Stage detail DOM refs for drag-resize
const stageDetailRefsMap = reactive(new Map())

function setStageDetailRef(el, idx) {
  if (el) {
    stageDetailRefsMap.set(idx, el)
  }
}

// ===== Stage display helpers =====

const STAGE_LABEL_MAP = {
  search_requirement: () => t('page.agent.stageSearch'),
  generate_testcases: () => t('page.agent.stageTestcases'),
  history: () => t('page.agent.stageHistory'),
}

function getStageLabel(name) {
  const fn = STAGE_LABEL_MAP[name]
  return fn ? fn() : t('page.agent.stageDefault')
}

function toggleStageExpand(stage) {
  // Toggle _collapsed; default is expanded (undefined/false → show)
  stage._collapsed = !!stage._collapsed
}

// Control visible log lines per stage (max 50 shown in terminal)
function visibleLogs(logs) {
  if (!logs?.length) return []
  return logs.slice(-50)
}

// ===== Drag-to-resize for terminal panels =====

let dragState = null

function onDragStart(e, stageIdx) {
  const el = stageDetailRefsMap.get(stageIdx)
  if (!el) return

  const rect = el.getBoundingClientRect()
  dragState = {
    startY: e.clientY,
    startHeight: rect.height,
    stageIdx,
    el,
  }

  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
  document.body.style.cursor = 'ns-resize'
  document.body.style.userSelect = 'none'
  e.preventDefault()
}

function onDragMove(e) {
  if (!dragState) return
  const delta = e.clientY - dragState.startY
  const newHeight = Math.max(80, Math.min(400, dragState.startHeight + delta))

  // Find the stage and update its custom height
  const agentMsg = props.messages.find(m => m.role === 'agent')
  if (agentMsg?.stages?.[dragState.stageIdx]) {
    agentMsg.stages[dragState.stageIdx]._height = newHeight
  }

  // Update DOM directly during drag for smoothness
  const terminal = dragState.el.querySelector('.agent-stage-block__terminal')
  if (terminal) terminal.style.maxHeight = `${newHeight}px`
}

function onDragEnd() {
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  dragState = null
}

// ===== Misc helpers =====

const showLegacyStreaming = computed(() =>
  props.streaming && !!props.streamingText && !props.messages.some(m => m.role === 'agent')
)

const showThinkingIndicator = computed(() =>
  props.streaming && !props.streamingText && !props.hasStageProgress && !props.messages.some(m => m.role === 'agent')
)

function roleLabel(role) {
  const map = {
    user: t('page.agent.roleUser'),
    assistant: t('page.agent.roleAssistant'),
    tool: t('page.agent.roleTool'),
    system: t('page.agent.roleSystem'),
    agent: t('page.agent.roleAgent'),
  }
  return map[role] || role
}

function isLongContent(content) {
  return content && content.length > 200
}

// Check if payload has meaningful content
function hasPayloadContent(payload) {
  if (!payload) return false
  if (genType.value === 'api_base') {
    return !!(payload?.base_cases?.length)
  }
  return !!(payload?.test_points?.length || payload?.cases?.length)
}

// 自动滚动阶段日志terminal到底部（当有新日志时）
function scrollStageTerminalToBottom() {
  const terminals = document.querySelectorAll('.agent-stage-block__terminal')
  terminals.forEach(el => {
    el.scrollTop = el.scrollHeight
  })
}

// 监听消息变化，自动滚动聊天窗口和阶段日志到底部
watch(
  () => [props.messages.length, props.streamingText, props.streaming, props.stageLogLines.length],
  async () => {
    await nextTick()
    const wrap = scrollRef.value?.wrapRef
    if (wrap) wrap.scrollTop = wrap.scrollHeight
    scrollStageTerminalToBottom()
  },
  { deep: true },
)
</script>

<style scoped lang="scss">
.agent-chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--el-bg-color);
}

.agent-chat-panel__messages {
  flex: 1;
  min-height: 0;
  padding: 16px 25px;
}

/* Message row layout */
.chat-msg {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
  align-items: flex-start;

  &--user {
    flex-direction: row-reverse;

    .chat-msg__body {
      align-items: end;
    }
    .chat-msg__meta {
      justify-content: flex-end;
    }
  }

  &--assistant,
  &--tool,
  &--agent {
    /* Agent messages aligned to left */
  }
}

/* Avatar */
.chat-msg__avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--el-fill-color-lighter);

  .chat-msg--user & {
    background: rgba($color-primary, 0.08);
  }

  .chat-msg--assistant & {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    :deep(.el-icon) { color: #fff !important; }
  }

  &--agent {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    :deep(.el-icon) { color: #fff !important; }
  }

  .chat-msg--tool & { background: #fef3c7; }
}

/* Message body */
.chat-msg__body {
  max-width: calc(100% - 48px);
  min-width: 0;
  width: 100%; /* 固定宽度，避免流式响应时宽度变化 */
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* Role meta */
.chat-msg__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 2px;
}

.chat-msg__role-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
}

/* Bubbles */
.chat-msg__bubble {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13.5px;
  line-height: 1.65;
  word-break: break-word;
  width: 100%; /* 固定气泡宽度，避免内容少时宽度过小 */

  /* 确保背景和边框显示 - 使用 CSS 变量并提供 fallback */
  background: var(--el-fill-color-lighter, #f5f7fa);
  border: 1px solid var(--el-border-color-lighter, #e4e7ed);
  border-top-left-radius: 4px;

  /* 调试：临时添加红色边框以确认样式是否应用 */
  /* border: 2px solid red !important; */

  &--user {
    width: auto; /* 用户消息宽度自适应 */
    background: linear-gradient(135deg, var(--color-primary, #409eff), var(--color-primary-dark, #337ecc));
    border-color: transparent;
    color: #fff;
    border-top-right-radius: 4px;
  }

  &--streaming {
    border-style: dashed;
  }

  &--thinking {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--el-text-color-secondary, #909399);
  }
}

/* Text content */
.chat-msg__text {
  white-space: pre-wrap;

  &--long {
    max-height: 72px;
    overflow-y: auto;
    padding-right: 4px;
    color: var(--el-text-regular);
    &::-webkit-scrollbar { width: 4px; }
    &::-webkit-scrollbar-thumb { background: var(--el-border-color); border-radius: 2px; }
  }

  &--streaming {
    animation: fadeIn 0.3s ease;
  }
}

@keyframes fadeIn {
  from { opacity: 0.6; }
  to { opacity: 1; }
}

/* Tool call */
.chat-msg__tool-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 12px;
  color: var(--el-color-warning);
  margin-bottom: 6px;
}
.chat-msg__tool-content {
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
  max-height: 120px;
  overflow-y: auto;
  margin: 0;
  background: var(--el-fill-color-blank);
  padding: 8px;
  border-radius: 6px;
  border: 1px dashed var(--el-border-color-lighter);
}

.chat-msg__stage-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-primary);
}

/* ==================== Agent Stages (分阶段展示) ==================== */
.agent-stages {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 6px;
}

/* Each stage as a standalone block */
.agent-stage-block {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  background: var(--el-bg-color);
  overflow: hidden;
  transition: border-color 0.25s ease;

  &:hover {
    border-color: var(--el-border-color);
  }

  &.is-done {
    border-left: 3px solid #67c23a;

    .agent-stage-block__header {
      opacity: 0.85;
    }
  }
}

/* Stage header row */
.agent-stage-block__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;

  &:hover {
    background: var(--el-fill-color-extra-light);
  }

  /* Status icon (spinner / green check) */
  .agent-stage-block__status-icon {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
  }

  /* Stage name */
  .agent-stage-block__name {
    font-size: 13.5px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    flex: 1;
    line-height: 1.4;
  }

  /* Collapse/expand arrow */
  .agent-stage-block__arrow {
    display: inline-flex;
    align-items: center;
    transition: transform 0.25s ease;
    color: var(--el-text-color-placeholder);

    &.is-collapsed {
      transform: rotate(180deg);
    }
  }
}

/* Detail panel (gray bg terminal) */
.agent-stage-block__detail {
  position: relative;
  overflow: hidden;

  /* Slide transition */
  .stage-detail-enter-active,
  .stage-detail-leave-active {
    transition: all 0.25s ease;
  }
  .stage-detail-enter-from,
  .stage-detail-leave-to {
    opacity: 0;
    max-height: 0;
    padding-top: 0;
    padding-bottom: 0;
  }
}

/* Terminal inside detail */
.agent-stage-block__terminal {
  margin: 0 10px 0;
  background: #f7f8fa;
  border-radius: 6px;
  padding: 10px 14px;
  max-height: 140px; /* default height before user drags */
  overflow-y: auto;
  font-family: 'Cascadia Code', Consolas, 'SF Mono', Monaco, monospace;
  font-size: 11.5px;
  line-height: 1.65;
  color: #606266;
  transition: max-height 0.15s ease;

  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-thumb { background: #dcdfe6; border-radius: 2px; }
}

/* Stage text description inside terminal */
.agent-stage-block__stage-text {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.agent-stage-block__log-line {
  white-space: pre-wrap;
  word-break: break-all;
  padding-bottom: 2px;

  &:not(:last-child) { margin-bottom: 2px; }

  &--empty {
    font-style: italic;
    color: #c0c4cc;
  }
}

/* Drag handle at bottom of terminal */
.agent-stage-block__drag-handle {
  height: 8px;
  margin: 0 10px 6px;
  cursor: ns-resize;
  position: relative;
  border-top: 1px solid var(--el-border-color-lighter);
  transition: background 0.15s;

  &::after {
    content: '';
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 28px;
    height: 3px;
    border-radius: 2px;
    background: var(--el-border-color);
    transition: background 0.15s;
  }

  &:hover {
    background: rgba($color-primary, 0.04);

    &::after {
      background: $color-primary;
    }
  }
}

/* Final text content */
.agent-final-text {
  margin-top: 12px;
  padding: 12px 16px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  font-size: 13.5px;
  line-height: 1.7;
  white-space: pre-wrap;
  color: var(--el-text-color-primary);

  &--streaming {
    animation: fadeIn 0.3s ease;
  }
}
</style>
