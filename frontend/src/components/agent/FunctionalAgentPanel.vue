<template>
  <div class="functional-agent-panel" :class="{ 'functional-agent-panel--landing': composerMode }">
    <template v-if="composerMode">
      <div class="functional-agent-panel__landing">
        <div class="functional-agent-panel__landing-spacer" />
        <AgentComposer
          agent-type="functional"
          :streaming="streaming"
          :disabled="!withProjectParams()"
          :quick-tags="quickTags"
          @send="handleComposerSend"
        />
      </div>
    </template>

    <template v-else>
      <div class="functional-agent-panel__workspace agent-layout">
        <AgentSessionSidebar
          :title="t('page.agent.history')"
          :sessions="sessions"
          :active-id="activeSessionId"
          :history-limit="historyLimit"
          @new="startNewSession"
          @select="selectSession"
        />
        <AgentChatPanel
          :messages="messages"
          :streaming="streaming"
          :streaming-text="streamingText"
          :quick-tags="quickTags"
          agent-type="functional"
          @send="sendMessage"
          @stop="stopStream"
        />
        <FunctionalPreviewPanel
          :output-payload="sessionDetail?.output_payload"
          :catalogs="catalogs"
          :can-edit="canEdit"
          :saving="saving"
          @save="saveCases"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  createFunctionalSession,
  getFunctionalSession,
  getMeta,
  listFunctionalMessages,
  listFunctionalSessions,
  saveFunctionalSession,
  streamFunctionalMessage,
} from '@/api/aiGeneration'
import { getCaseCatalogTree } from '@/api/functional'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import AgentSessionSidebar from '@/components/agent/AgentSessionSidebar.vue'
import AgentChatPanel from '@/components/agent/AgentChatPanel.vue'
import AgentComposer from '@/components/agent/AgentComposer.vue'
import FunctionalPreviewPanel from '@/components/agent/FunctionalPreviewPanel.vue'

const props = defineProps({
  autoNew: { type: Boolean, default: false },
  initialRequirement: { type: String, default: '' },
  isActive: { type: Boolean, default: true },
})

const emit = defineEmits(['composer-mode-change'])

const { t } = useI18n()
const route = useRoute()
const { withProjectParams } = useProjectScope()
const { canEdit } = usePermission()

const sessions = ref([])
const activeSessionId = ref(null)
const sessionDetail = ref(null)
const messages = ref([])
const streaming = ref(false)
const streamingText = ref('')
const creating = ref(false)
const saving = ref(false)
const catalogs = ref([])
const meta = ref(null)
const composerMode = ref(true)
let abortController = null
let tempMsgId = 0

const historyLimit = computed(() => meta.value?.history_limit ?? 10)
const quickTags = computed(() => meta.value?.functional_prompt_templates ?? [])

async function loadMeta() {
  try {
    const res = await getMeta()
    meta.value = res.data.data
  } catch {
    meta.value = null
  }
}

async function loadCatalogs() {
  const params = withProjectParams()
  if (!params) return
  const res = await getCaseCatalogTree(params)
  catalogs.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadSessions() {
  const params = withProjectParams()
  if (!params) return
  const res = await listFunctionalSessions(params)
  sessions.value = res.data.data ?? []
}

async function refreshSession() {
  if (!activeSessionId.value) {
    sessionDetail.value = null
    return
  }
  const res = await getFunctionalSession(activeSessionId.value)
  sessionDetail.value = res.data.data
}

async function loadMessages() {
  if (!activeSessionId.value) {
    messages.value = []
    return
  }
  const res = await listFunctionalMessages(activeSessionId.value)
  messages.value = res.data.data ?? []
}

function setComposerMode(value) {
  composerMode.value = value
  emit('composer-mode-change', value)
}

function startNewSession() {
  if (streaming.value) stopStream()
  activeSessionId.value = null
  sessionDetail.value = null
  messages.value = []
  setComposerMode(true)
}

async function selectSession(id) {
  if (streaming.value) stopStream()
  activeSessionId.value = id
  setComposerMode(false)
  await Promise.all([refreshSession(), loadMessages()])
}

async function createSessionFromComposer(payload) {
  const params = withProjectParams({ project_id: payload.projectId })
  if (!params) return null

  creating.value = true
  try {
    const body = {
      ...params,
      requirement_text: payload.requirementText,
      knowledge_document_id: payload.knowledgeDocumentId,
      user_prompt: payload.userPrompt,
    }
    const res = await createFunctionalSession(body)
    const session = res.data.data
    await loadSessions()
    activeSessionId.value = session.id
    setComposerMode(false)
    await Promise.all([refreshSession(), loadMessages()])
    return session
  } finally {
    creating.value = false
  }
}

function stopStream() {
  abortController?.abort()
  abortController = null
  streaming.value = false
  streamingText.value = ''
}

async function sendMessage(content) {
  if (!activeSessionId.value || streaming.value) return
  streaming.value = true
  streamingText.value = ''
  abortController = new AbortController()

  const userMsg = {
    id: `temp-${++tempMsgId}`,
    role: 'user',
    content,
    message_type: 'text',
    sequence: messages.value.length + 1,
  }
  messages.value = [...messages.value, userMsg]

  try {
    await streamFunctionalMessage(
      activeSessionId.value,
      content,
      {
        custom: (data) => {
          messages.value = [...messages.value, {
            id: `temp-${++tempMsgId}`,
            role: 'tool',
            message_type: 'custom',
            content: String(data),
            sequence: messages.value.length + 1,
          }]
        },
        messages: (data) => {
          streamingText.value += String(data)
        },
        tool_call: (data) => {
          messages.value = [...messages.value, {
            id: `temp-${++tempMsgId}`,
            role: 'tool',
            message_type: 'tool_call',
            tool_name: data?.name,
            content: JSON.stringify(data?.content ?? data),
            sequence: messages.value.length + 1,
          }]
        },
        payload_updated: async () => {
          await refreshSession()
        },
        error: (data) => {
          ElMessage.error(data?.message || t('common.requestFailed'))
        },
        done: async () => {
          if (streamingText.value) {
            messages.value = [...messages.value, {
              id: `temp-${++tempMsgId}`,
              role: 'assistant',
              message_type: 'text',
              content: streamingText.value,
              sequence: messages.value.length + 1,
            }]
            streamingText.value = ''
          }
          await Promise.all([refreshSession(), loadMessages(), loadSessions()])
        },
      },
      abortController.signal,
    )
  } catch (err) {
    if (err.name !== 'AbortError') {
      ElMessage.error(err.message || t('common.requestFailed'))
      await loadMessages()
    }
  } finally {
    streaming.value = false
    streamingText.value = ''
    abortController = null
  }
}

async function handleComposerSend(payload) {
  if (streaming.value || creating.value) return

  if (!payload.requirementText && !payload.knowledgeDocumentId) {
    ElMessage.warning(t('page.agent.requirementRequired'))
    return
  }

  const session = await createSessionFromComposer(payload)
  if (!session) return
  await sendMessage(payload.content)
}

async function saveCases(payload) {
  if (!activeSessionId.value) return
  saving.value = true
  try {
    await saveFunctionalSession(activeSessionId.value, payload)
    ElMessage.success(t('page.agent.saved'))
  } finally {
    saving.value = false
  }
}

watch(
  () => props.isActive,
  (active) => {
    if (active) emit('composer-mode-change', composerMode.value)
  },
  { immediate: true },
)

watch(
  () => route.query.requirement,
  (val) => {
    if (typeof val === 'string' && val && props.autoNew) {
      setComposerMode(true)
    }
  },
  { immediate: true },
)

onMounted(async () => {
  await Promise.all([loadMeta(), loadCatalogs(), loadSessions()])
  if (props.autoNew || route.query.new === '1') {
    setComposerMode(true)
  }
})
</script>

<style scoped lang="scss">
.functional-agent-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;

  &--landing {
    justify-content: flex-end;
  }
}

.functional-agent-panel__landing {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding-bottom: 0;
}

.functional-agent-panel__landing-spacer {
  flex: 1;
  min-height: 24px;
}

.functional-agent-panel__workspace {
  flex: 1;
  min-height: 0;
}

.agent-layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1.1fr) minmax(0, 0.9fr);
  min-height: 0;
  height: 100%;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-bg-color);
}
</style>
