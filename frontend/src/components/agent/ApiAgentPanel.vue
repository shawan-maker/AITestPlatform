<template>
  <div class="api-agent-panel" :class="{ 'api-agent-panel--landing': composerMode }">
    <template v-if="composerMode">
      <div class="api-agent-panel__landing">
        <div class="api-agent-panel__landing-spacer" />
        <AgentComposer
          agent-type="api"
          :streaming="streaming"
          :disabled="!withProjectParams()"
          :quick-tags="quickTags"
          @send="handleComposerSend"
        />
      </div>
    </template>

    <template v-else>
      <div class="api-agent-panel__workspace agent-layout">
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
          agent-type="api"
          @send="sendMessage"
          @stop="stopStream"
        />
        <ApiPreviewPanel
          :output-payload="sessionDetail?.output_payload"
          :catalogs="catalogs"
          :interface-id="boundInterfaceId"
          :can-edit="canEdit"
          :confirming="confirming"
          @confirm="confirmCases"
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
  confirmApiGeneration,
  createApiSession,
  getApiSession,
  getMeta,
  listApiMessages,
  listApiSessions,
  streamApiMessage,
} from '@/api/aiGeneration'
import { getApiCatalogTree } from '@/api/apiTest'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import AgentSessionSidebar from '@/components/agent/AgentSessionSidebar.vue'
import AgentChatPanel from '@/components/agent/AgentChatPanel.vue'
import AgentComposer from '@/components/agent/AgentComposer.vue'
import ApiPreviewPanel from '@/components/agent/ApiPreviewPanel.vue'

const props = defineProps({
  autoNew: { type: Boolean, default: false },
  initialInterfaceId: { type: Number, default: null },
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
const confirming = ref(false)
const catalogs = ref([])
const meta = ref(null)
const boundInterfaceId = ref(null)
const composerMode = ref(true)
let abortController = null
let tempMsgId = 0

const historyLimit = computed(() => meta.value?.history_limit ?? 10)
const quickTags = computed(() => meta.value?.api_prompt_templates ?? [])

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
  const res = await getApiCatalogTree(params)
  catalogs.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadSessions() {
  const params = withProjectParams()
  if (!params) return
  const res = await listApiSessions(params)
  sessions.value = res.data.data ?? []
}

async function refreshSession() {
  if (!activeSessionId.value) {
    sessionDetail.value = null
    return
  }
  const res = await getApiSession(activeSessionId.value)
  sessionDetail.value = res.data.data
  const payload = sessionDetail.value?.output_payload ?? {}
  boundInterfaceId.value = payload.interface_id ?? boundInterfaceId.value
}

async function loadMessages() {
  if (!activeSessionId.value) {
    messages.value = []
    return
  }
  const res = await listApiMessages(activeSessionId.value)
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
      interface_id: payload.interfaceId,
      api_doc_text: payload.apiDocText,
      user_prompt: payload.userPrompt,
    }
    const res = await createApiSession(body)
    const session = res.data.data
    if (payload.interfaceId) boundInterfaceId.value = payload.interfaceId
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

  messages.value = [...messages.value, {
    id: `temp-${++tempMsgId}`,
    role: 'user',
    content,
    message_type: 'text',
    sequence: messages.value.length + 1,
  }]

  try {
    await streamApiMessage(
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

  if (!payload.interfaceId && !payload.apiDocText) {
    ElMessage.warning(t('page.agent.apiBindingRequired'))
    return
  }

  const session = await createSessionFromComposer(payload)
  if (!session) return
  await sendMessage(payload.content)
}

async function confirmCases(payload) {
  if (!activeSessionId.value) return
  confirming.value = true
  try {
    await confirmApiGeneration({
      session_id: activeSessionId.value,
      selected_indexes: payload.selected_indexes,
      environment_id: payload.environment_id,
      catalog_id: payload.catalog_id,
      interface_id: payload.interface_id ?? boundInterfaceId.value ?? undefined,
    })
    ElMessage.success(t('page.agent.saved'))
  } finally {
    confirming.value = false
  }
}

const resolvedInterfaceId = computed(() => {
  const q = Number(route.query.interface_id)
  return props.initialInterfaceId || (Number.isFinite(q) && q > 0 ? q : null)
})

watch(
  () => props.isActive,
  (active) => {
    if (active) emit('composer-mode-change', composerMode.value)
  },
  { immediate: true },
)

watch(resolvedInterfaceId, (id) => {
  if (id) boundInterfaceId.value = id
}, { immediate: true })

onMounted(async () => {
  await Promise.all([loadMeta(), loadCatalogs(), loadSessions()])
  if (props.autoNew || route.query.new === '1' || resolvedInterfaceId.value) {
    setComposerMode(true)
  }
})
</script>

<style scoped lang="scss">
.api-agent-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;

  &--landing {
    justify-content: flex-end;
  }
}

.api-agent-panel__landing {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding-bottom: 0;
}

.api-agent-panel__landing-spacer {
  flex: 1;
  min-height: 24px;
}

.api-agent-panel__workspace {
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
