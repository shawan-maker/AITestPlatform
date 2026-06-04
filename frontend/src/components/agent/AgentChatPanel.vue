<template>
  <div class="agent-chat-panel">
    <el-scrollbar ref="scrollRef" class="agent-chat-panel__messages">
      <div v-for="msg in messages" :key="msg.id || `${msg.role}-${msg.sequence}`" class="chat-msg" :class="`chat-msg--${msg.role}`">
        <div class="chat-msg__label">{{ roleLabel(msg.role) }}</div>
        <div class="chat-msg__bubble">
          <template v-if="msg.message_type === 'tool_call'">
            <span class="chat-msg__tool">{{ msg.tool_name || 'tool' }}</span>
            {{ msg.content }}
          </template>
          <template v-else-if="msg.message_type === 'custom'">
            <em>{{ msg.content }}</em>
          </template>
          <template v-else>{{ msg.content }}</template>
        </div>
      </div>
      <div v-if="streamingText" class="chat-msg chat-msg--assistant">
        <div class="chat-msg__label">{{ roleLabel('assistant') }}</div>
        <div class="chat-msg__bubble chat-msg__bubble--streaming">{{ streamingText }}</div>
      </div>
      <div v-if="streaming && !streamingText" class="chat-msg chat-msg--assistant">
        <div class="chat-msg__bubble">
          <el-icon class="is-loading"><Loading /></el-icon>
          {{ t('page.agent.thinking') }}
        </div>
      </div>
    </el-scrollbar>

    <AgentComposer
      compact
      hide-prompt-row
      :agent-type="agentType"
      :streaming="streaming"
      :quick-tags="quickTags"
      @send="onComposerSend"
    />
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading } from '@element-plus/icons-vue'
import AgentComposer from '@/components/agent/AgentComposer.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  streaming: { type: Boolean, default: false },
  streamingText: { type: String, default: '' },
  quickTags: { type: Array, default: () => [] },
  agentType: { type: String, default: 'functional' },
})

const emit = defineEmits(['send', 'stop'])

const { t } = useI18n()
const scrollRef = ref(null)

function roleLabel(role) {
  const map = {
    user: t('page.agent.roleUser'),
    assistant: t('page.agent.roleAssistant'),
    tool: t('page.agent.roleTool'),
    system: t('page.agent.roleSystem'),
  }
  return map[role] || role
}

function onComposerSend(payload) {
  if (props.streaming) return
  emit('send', payload.content)
}

watch(
  () => [props.messages.length, props.streamingText, props.streaming],
  async () => {
    await nextTick()
    const wrap = scrollRef.value?.wrapRef
    if (wrap) wrap.scrollTop = wrap.scrollHeight
  },
)
</script>

<style scoped lang="scss">
.agent-chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  border-right: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
}

.agent-chat-panel__messages {
  flex: 1;
  min-height: 0;
  padding: 12px;
}

.chat-msg {
  margin-bottom: 12px;

  &--user .chat-msg__bubble {
    background: rgba($color-primary, 0.1);
    margin-left: 24px;
  }

  &--assistant .chat-msg__bubble,
  &--tool .chat-msg__bubble {
    background: var(--el-fill-color-light);
    margin-right: 24px;
  }

  &--tool .chat-msg__tool {
    color: var(--el-color-warning);
    font-weight: 600;
    margin-right: 6px;
  }
}

.chat-msg__label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}

.chat-msg__bubble {
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;

  &--streaming {
    border: 1px dashed var(--el-border-color);
  }
}
</style>
