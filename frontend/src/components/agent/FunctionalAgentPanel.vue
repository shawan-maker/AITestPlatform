<template>
  <!-- SIT-F7: Sidebar (always visible, collapsible) + Main Content -->
  <div class="functional-agent-panel">
    <!-- Sidebar: always rendered, collapsible -->
    <AgentSessionSidebar
      :title="t('page.agent.history')"
      :sessions="sessions"
      :active-id="activeSessionId"
      :history-limit="historyLimit"
      :agent-type="'functional'"
      :disabled="streaming"
      :collapsed="sidebarCollapsed"
      @new="startNewSession"
      @select="selectSession"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
    />

    <!-- Main content area -->
    <main class="functional-agent-panel__main" :class="{ 'functional-agent-panel__main--landing': composerMode }">
      <!-- Landing mode: welcome + tabs + composer (centered vertically) -->
      <template v-if="composerMode">
        <div class="functional-agent-panel__landing">
          <AgentWelcomeHeader />
          <AgentTypeTabs v-model="sharedActiveTab" />
          <AgentComposer
            agent-type="functional"
            :streaming="streaming"
            :disabled="!withProjectParams()"
            :quick-tags="quickTags"
            @send="handleComposerSend"
          />
        </div>
      </template>

      <!-- Chat mode: context bar + chat panel + composer (fixed bottom) -->
      <template v-else>
        <div class="functional-agent-panel__chat-layout">
          <AgentContextBar
            :knowledge-doc-title="sessionDetail?.knowledge_document_title"
            :input-ref-type="sessionDetail?.input_ref_type"
            :interface-method="sessionDetail?.interface_method"
            :interface-path="sessionDetail?.interface_path"
          />

          <AgentChatPanel
            :messages="messages"
            :streaming="streaming"
            :streaming-text="streamingText"
            :has-stage-progress="hasStageProgress"
            :stage-log-lines="stageLogLines"
            :quick-tags="quickTags"
            agent-type="functional"
            @send="sendMessage"
            @stop="stopStream"
            @open-case-list="handleOpenCaseList"
          >
            <template #after-messages>
              <AgentPayloadCard
                v-if="sessionDetail?.output_payload && Object.keys(sessionDetail.output_payload).length > 2 && !hasAgentResponse"
                gen-type="functional"
                :payload="sessionDetail.output_payload"
                :can-edit="canEdit"
                :saving="saving"
                :catalogs="catalogs"
                @save="saveCases"
              />
            </template>
          </AgentChatPanel>

          <!-- Composer in chat mode (compact) -->
          <AgentComposer
            agent-type="functional"
            :streaming="streaming"
            :disabled="!withProjectParams()"
            :compact="true"
            :hide-prompt-row="true"
            @send="sendMessageForComposer"
          />
        </div>
      </template>
    </main>

    <!-- Case list dialog (opened from result card click) -->
    <AgentCaseListDialog
      v-model="caseListVisible"
      :payload="caseListPayload"
      gen-type="functional"
      :catalogs="catalogs"
      @save="saveCasesFromDialog"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
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
import AgentPayloadCard from '@/components/agent/AgentPayloadCard.vue'
import AgentResultCard from '@/components/agent/AgentResultCard.vue'
import AgentCaseListDialog from '@/components/agent/AgentCaseListDialog.vue'
import AgentContextBar from '@/components/agent/AgentContextBar.vue'
import AgentWelcomeHeader from '@/components/agent/AgentWelcomeHeader.vue'
import AgentTypeTabs from '@/components/agent/AgentTypeTabs.vue'

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
const hasStageProgress = ref(false)
const creating = ref(false)
const saving = ref(false)
const catalogs = ref([])
const meta = ref(null)
const composerMode = ref(true)
const sidebarCollapsed = ref(false)
const sharedActiveTab = ref('functional')
// Legacy stage log lines (for backward compat with chat panel)
const stageLogLines = ref([])

// Case list dialog state
const caseListVisible = ref(false)
const caseListPayload = ref(null)

let abortController = null
let tempMsgId = 0

// Check if current messages contain a unified agent response
const hasAgentResponse = computed(() =>
  messages.value.some(m => m.role === 'agent')
)

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
  const raw = res.data.data ?? []

  // Merge legacy messages (role=assistant/tool/system) into unified agent responses
  const merged = []
  let currentAgent = null
  for (const msg of raw) {
    if (msg.role === 'user') {
      // Flush any pending agent block before adding user msg
      if (currentAgent) {
        currentAgent.isStreaming = false
        merged.push(currentAgent)
        currentAgent = null
      }
      merged.push({ ...msg })
    } else {
      // Start or continue an agent response block
      if (!currentAgent) {
        currentAgent = {
          id: `agent-history-${merged.length}`,
          role: 'agent',
          isStreaming: false,
          stages: [],
          finalText: '',
          payload: null,
          streamingText: '',
        }
      }

      // Classify legacy message type
      if (msg.message_type === 'custom' || msg.role === 'system') {
        const time = msg.created_at ? new Date(msg.created_at).toLocaleTimeString('zh-CN', { hour12: false }) : ''
        _addLogToAgent(currentAgent, 'default', `[${time}] ${msg.content}`)
      } else if (msg.message_type === 'tool_call' && msg.tool_name) {
        _addLogToAgent(currentAgent, 'default', `[工具] ${msg.tool_name}: ${msg.content || ''}`)
      } else if (msg.role === 'assistant' && msg.content) {
        // Text content → append to finalText
        currentAgent.finalText += (currentAgent.finalText ? '\n' : '') + msg.content
      } else if (msg.content) {
        _addLogToAgent(currentAgent, 'default', msg.content)
      }
    }
  }
  // Flush last agent block
  if (currentAgent) {
    currentAgent.isStreaming = false
    merged.push(currentAgent)
  }

  messages.value = merged
}

/** Helper: add a log line to an agent response's default stage */
function _addLogToAgent(agent, stageName, line) {
  let stage = agent.stages.find(s => s.name === stageName)
  if (!stage) {
    stage = { name: stageName, status: 'done', text: '', logs: [] }
    agent.stages.push(stage)
  }
  stage.logs.push(line)
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
  loadSessions()
}

async function selectSession(id) {
  if (streaming.value) stopStream()
  activeSessionId.value = id
  setComposerMode(false)
  await Promise.all([refreshSession(), loadMessages(), loadSessions()])
}

async function createSessionFromComposer(payload) {
  const params = withProjectParams({ project_id: payload.projectId })
  if (!params) {
    ElMessage.warning(t('common.selectProjectHint'))
    return null
  }

  creating.value = true
  try {
    const body = {
      ...params,
      requirement_text: payload.requirementText,
      knowledge_document_id: payload.knowledgeDocumentId,
      user_prompt: payload.userPrompt,
    }
    const res = await createFunctionalSession(body)
    const session = res?.data?.data
    if (!session?.id) {
      throw new Error(t('common.requestFailed'))
    }
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
  hasStageProgress.value = false
  stageLogLines.value = []
}

/** Detect which stage a text belongs to based on keywords */
function detectStageFromText(text) {
  const str = String(text)
  if (str.includes('检索') || str.includes('搜索') || str.includes('\u{1F50D}') || str.includes('search')) return 'search_requirement'
  if (str.includes('测试点') || str.includes('testpoint') || str.includes('TestPoint')) return 'generate_testpoints'
  if (str.includes('用例') || str.includes('生成') || str.includes('generate')) return 'generate_testcases'
  // Default: return last active stage or 'default'
  return 'default'
}

async function sendMessage(content) {
  if (!activeSessionId.value || streaming.value) return
  streaming.value = true
  streamingText.value = ''
  hasStageProgress.value = false
  abortController = new AbortController()

  // Add user message
  const userMsg = {
    id: `temp-${++tempMsgId}`,
    role: 'user',
    content,
    message_type: 'text',
    sequence: messages.value.length + 1,
  }
  messages.value = [...messages.value, userMsg]

  try {
    // ===== Create unified agent response object (KEY CHANGE) =====
    const agentResponse = reactive({
      id: `agent-${Date.now()}`,
      role: 'agent',
      isStreaming: true,
      stages: [],
      finalText: '',
      payload: null,
      streamingText: '',
    })

    // Push only ONE message for the entire response
    messages.value = [...messages.value, agentResponse]

    // Helper to find or create a stage (auto-marks previous running stages as done)
    const KNOWN_STAGE_ORDER = ['search_requirement', 'generate_testpoints', 'generate_testcases', 'formatting_testcases']

    const getStage = (name) => {
      let stage = agentResponse.stages.find(s => s.name === name)
      if (!stage) {
        // 新阶段 → 先把所有之前还在 running 的阶段标记为 done（保证同一时间只有一个 running）
        agentResponse.stages = agentResponse.stages.map(s =>
          s.status === 'done' ? s : { ...s, status: 'done' }
        )
        stage = { name, status: 'running', text: '', logs: [] }
        agentResponse.stages = [...agentResponse.stages, stage]
      }
      return stage
    }

    // Helper to add log line to a stage (keep max 30 per stage)
    const _addLog = (stageName, line) => {
      const stage = getStage(stageName)
      const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
      stage.logs = [...stage.logs.slice(-29), `[${time}] ${line}`]
      // Also keep legacy log for backward compat
      stageLogLines.value = [...stageLogLines.value.slice(-49), `[${time}] ${line}`]
    }

    // Reset legacy logs
    stageLogLines.value = []

    await streamFunctionalMessage(
      activeSessionId.value,
      content,
      {
        stage: (data) => {
          hasStageProgress.value = true
          if (data?.name) {
            // 新阶段开始 → 先标记所有之前的 running 阶段为 done
            agentResponse.stages = agentResponse.stages.map(s =>
              s.name === data.name || s.status === 'done' ? s : { ...s, status: 'done' }
            )
            const stage = getStage(data.name)
            stage.text = data.text || ''
            stage.status = data.status || 'running'
          }
        },
        custom: (data) => {
          hasStageProgress.value = true
          const text = String(data)
          // Auto-detect which stage this belongs to
          const stageName = detectStageFromText(text)
          _addLog(stageName, text)
        },
        messages: (data) => {
          const text = String(data)
          // 只追加到 agentResponse 的 finalText/streamingText（用于兼容和结果展示）
          agentResponse.streamingText += text
          agentResponse.finalText += text
          streamingText.value = agentResponse.streamingText
          // 注意：messages 事件（LLM 流式文本）不再注入到阶段 logs 中，
          // 阶段详情框只展示 custom/tool_call 事件的结构化日志，避免跨阶段内容混乱
        },
        tool_call: (data) => {
          hasStageProgress.value = true
          if (data?.name) {
            _addLog(data.name, `调用工具: ${data.name}`)
          } else {
            _addLog('default', `工具调用`)
          }
        },
        payload_updated: async () => {
          // 不再创建 default 阶段，静默刷新 session 即可
          await refreshSession()
          agentResponse.payload = sessionDetail.value?.output_payload || null
        },
        error: (data) => {
          const errorMsg = data?.message || t('common.requestFailed')
          ElMessage.error(errorMsg)
          // 错误信息追加到最后一个阶段，不创建新的 default 阶段
          const stages = agentResponse.stages
          if (stages.length > 0) {
            const lastStage = stages[stages.length - 1]
            const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
            lastStage.logs = [...(lastStage.logs || []), `[${time}] [错误] ${errorMsg}`]
          }
        },
        done: async () => {
          // 标记所有阶段为 done
          agentResponse.stages = agentResponse.stages.map(s => ({ ...s, status: 'done' }))
          agentResponse.isStreaming = false

          // 只刷新 session 以获取 payload，不要重新加载 messages（会丢失阶段信息）
          await refreshSession()
          if (!agentResponse.payload) {
            agentResponse.payload = sessionDetail.value?.output_payload || null
          }

          // 只刷新侧边栏列表
          await loadSessions()

          // Clear streaming text reference
          streamingText.value = ''
        },
      },
      abortController.signal,
    )
  } catch (err) {
    if (err.name !== 'AbortError') {
      const msg = err.message || t('common.requestFailed')
      ElMessage.error(msg)
      messages.value = [...messages.value, {
        id: `temp-${++tempMsgId}`,
        role: 'tool',
        message_type: 'custom',
        content: `[连接中断] ${msg}`,
        sequence: messages.value.length + 1,
      }]
      await loadMessages()
    }
  } finally {
    streaming.value = false
    streamingText.value = ''
    hasStageProgress.value = false
    stageLogLines.value = []
    abortController = null
  }
}

async function handleComposerSend(payload) {
  if (streaming.value || creating.value) return
  try {
    const session = await createSessionFromComposer(payload)
    if (!session) return
    await sendMessage(payload.content || '')
  } catch (err) {
    console.error('handleComposerSend error:', err)
    ElMessage.error(err.message || t('common.requestFailed'))
  }
}

/* SIT-F7: Composer in chat mode sends directly */
async function sendMessageForComposer(payload) {
  if (streaming.value || creating.value) return
  // Chat mode composer: if no active session, create one first
  if (!activeSessionId.value) {
    try {
      const session = await createSessionFromComposer(payload)
      if (!session) return
    } catch (err) {
      console.error('sendMessageForComposer error:', err)
      ElMessage.error(err.message || t('common.requestFailed'))
      return
    }
  }
  const content = payload.content || ''
  if (content) {
    await sendMessage(content)
  }
}

/* Handle open case list from result card */
function handleOpenCaseList(payload) {
  caseListPayload.value = payload
  caseListVisible.value = true
}

/* Save cases from case list dialog */
async function saveCasesFromDialog(saveData) {
  if (!activeSessionId.value) return
  saving.value = true
  try {
    const body = saveData.case_indexes !== undefined
      ? { case_indexes: saveData.case_indexes, catalog_id: saveData.catalog_id }
      : saveData
    await saveFunctionalSession(activeSessionId.value, body)
    ElMessage.success(t('page.agent.saved'))
    await refreshSession()
  } finally {
    saving.value = false
  }
}

/* Save payload card content (legacy embedded PayloadCard) */
async function saveCases(payload) {
  if (!activeSessionId.value) return
  saving.value = true
  try {
    const body = payload.case_indexes !== undefined
      ? { case_indexes: payload.case_indexes, catalog_id: payload.catalog_id }
      : payload
    await saveFunctionalSession(activeSessionId.value, body)
    ElMessage.success(t('page.agent.saved'))
    await refreshSession()
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
/* Row layout - Sidebar (left, always visible) + Main (right) */
.functional-agent-panel {
  display: flex;
  flex-direction: row;
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

/* Main content area */
.functional-agent-panel__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  &--landing {
    align-items: center;
    justify-content: center;
    padding: 24px;
    overflow-y: auto;
  }
}

/* Landing mode inner layout (centered vertically) */
.functional-agent-panel__landing {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 800px;
  gap: 20px;
  min-height: 0;
}

/* Chat mode layout: context bar + chat + fixed composer */
.functional-agent-panel__chat-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 16px;
}
</style>
