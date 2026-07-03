<template>
  <!-- SIT-F7: Sidebar (always visible, collapsible) + Main Content -->
  <div class="api-agent-panel">
    <!-- Sidebar: always rendered, collapsible -->
    <AgentSessionSidebar
      :title="t('page.agent.history')"
      :sessions="sessions"
      :active-id="activeSessionId"
      :history-limit="historyLimit"
      agent-type="api"
      :disabled="streaming"
      :collapsed="sidebarCollapsed"
      @new="startNewSession"
      @select="selectSession"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
    />

    <!-- Main content area -->
    <main class="api-agent-panel__main" :class="{ 'api-agent-panel__main--landing': composerMode }">
      <!-- Landing mode: welcome + tabs + composer (centered vertically) -->
      <template v-if="composerMode">
        <div class="api-agent-panel__landing">
          <AgentWelcomeHeader />
          <AgentTypeTabs v-model="sharedActiveTab" />
          <AgentComposer
            agent-type="api"
            :streaming="streaming"
            :disabled="!withProjectParams()"
            :quick-tags="quickTags"
            @send="handleComposerSend"
          />
        </div>
      </template>

      <!-- Chat mode: tabs + context bar + chat panel + composer (fixed bottom) -->
      <template v-else>
        <div class="api-agent-panel__chat-layout">
          <AgentTypeTabs v-model="sharedActiveTab" :compact="true" />
          <AgentContextBar
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
            agent-type="api"
            @send="sendMessage"
            @stop="stopStream"
            @open-case-list="handleOpenCaseList"
          >
            <template #after-messages>
              <!-- Wrapper to align with chat message body (avatar 32px + gap 10px = 42px) -->
              <div class="pipeline-after-messages">
                <!-- Pipeline edit button (shown when base cases are ready, hidden for history) -->
                <div v-if="pipelineInterfaces.length && !streaming && !pipelineEditDone && !pipelineSummary" class="pipeline-edit-action">
                  <el-button type="primary" @click="openEditDialog">
                    {{ t('page.agent.editBaseCases') || '编辑全部' }}
                  </el-button>
                </div>

                <!-- Pipeline final summary -->
                <ApiPipelineSummary v-if="pipelineSummary" :summary="pipelineSummary" />

              <!-- Legacy single-interface payload card -->
              <AgentPayloadCard
                v-if="sessionDetail?.output_payload?.base_cases?.length && !pipelineInterfaces.length"
                gen-type="api_base"
                :payload="sessionDetail.output_payload"
                :can-edit="canEdit"
                :saving="confirming"
                @confirm="confirmCasesFromCard"
              />
              </div>
            </template>
          </AgentChatPanel>

          <!-- Composer in chat mode (compact) -->
          <AgentComposer
            agent-type="api"
            :streaming="streaming"
            :disabled="!withProjectParams()"
            :compact="true"
            :hide-prompt-row="true"
            @send="sendMessageForComposer"
          />
        </div>
      </template>
    </main>

    <!-- Keep confirm dialog at root level -->
    <ApiAgentConfirmDialog
      v-model="showConfirm"
      :catalogs="catalogs"
      :default-indexes="selectedIndexes"
      :interface-id="boundInterfaceId"
      :loading="confirming"
      @submit="onConfirmDialog"
    />

    <!-- Case list dialog for API cases -->
    <AgentCaseListDialog
      v-model="caseListVisible"
      :payload="caseListPayload"
      gen-type="api"
      :project-id="projectId"
      @save="saveCasesFromDialog"
    />

    <!-- Interface case edit dialog (multi-interface pipeline) -->
    <InterfaceCaseEditDialog
      v-model="showEditDialog"
      :interfaces="pipelineInterfaces"
      @save="onSaveEditedBaseCases"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled } from '@element-plus/icons-vue'
import {
  confirmApiGeneration,
  createApiSession,
  getApiSession,
  getMeta,
  listApiMessages,
  listApiSessions,
  streamApiMessage,
  streamSaveBaseCases,
  summarizeApiTitle,
} from '@/api/aiGeneration'
import { getApiCatalogTree } from '@/api/apiTest'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import AgentSessionSidebar from '@/components/agent/AgentSessionSidebar.vue'
import AgentChatPanel from '@/components/agent/AgentChatPanel.vue'
import AgentComposer from '@/components/agent/AgentComposer.vue'
import AgentPayloadCard from '@/components/agent/AgentPayloadCard.vue'
import AgentContextBar from '@/components/agent/AgentContextBar.vue'
import AgentWelcomeHeader from '@/components/agent/AgentWelcomeHeader.vue'
import AgentTypeTabs from '@/components/agent/AgentTypeTabs.vue'
import ApiAgentConfirmDialog from '@/components/agent/ApiAgentConfirmDialog.vue'
import AgentCaseListDialog from '@/components/agent/AgentCaseListDialog.vue'
import InterfaceCaseEditDialog from '@/components/agent/InterfaceCaseEditDialog.vue'
import ApiPipelineSummary from '@/components/agent/ApiPipelineSummary.vue'

const props = defineProps({
  autoNew: { type: Boolean, default: false },
  initialInterfaceId: { type: Number, default: null },
  isActive: { type: Boolean, default: true },
  activeTab: { type: String, default: 'api' },
})

const emit = defineEmits(['composer-mode-change', 'tab-change'])

const { t } = useI18n()
const route = useRoute()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()

const sessions = ref([])
const activeSessionId = ref(null)
const sessionDetail = ref(null)
const messages = ref([])
const streaming = ref(false)
const streamingText = ref('')
const hasStageProgress = ref(false)
// Legacy stage log lines
const stageLogLines = ref([])
const creating = ref(false)
const confirming = ref(false)
const catalogs = ref([])
const meta = ref(null)
const boundInterfaceId = ref(null)
const composerMode = ref(true)
const showConfirm = ref(false)
const selectedIndexes = ref([])
const sidebarCollapsed = ref(false)
const sharedActiveTab = ref('api')
let _runningPollTimer = null

// Case list dialog state
const caseListVisible = ref(false)
const caseListPayload = ref(null)

// Interface case edit dialog state (multi-interface pipeline)
const showEditDialog = ref(false)
const pipelineEditDone = ref(false)
const pipelineInterfaces = computed(() =>
  sessionDetail.value?.output_payload?.interfaces || []
)
const pipelineSummary = computed(() =>
  sessionDetail.value?.output_payload?.summary || null
)

let abortController = null
let tempMsgId = 0

// Check if current messages contain a unified agent response
const hasAgentResponse = computed(() =>
  messages.value.some(m => m.role === 'agent')
)

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
  const raw = res.data.data ?? []

  // Merge legacy messages (role=assistant/tool/system) into unified agent responses
  const merged = []
  let currentAgent = null
  for (const msg of raw) {
    if (msg.role === 'user') {
      if (currentAgent) {
        currentAgent.isStreaming = false
        merged.push(currentAgent)
        currentAgent = null
      }
      merged.push({ ...msg })
    } else {
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
      if (msg.message_type === 'custom' || msg.role === 'system') {
        const time = msg.created_at ? new Date(msg.created_at).toLocaleTimeString('zh-CN', { hour12: false }) : ''
        _addLogToAgent(currentAgent, 'history', `[${time}] ${msg.content}`)
      } else if (msg.message_type === 'tool_call' && msg.tool_name) {
        _addLogToAgent(currentAgent, 'history', `[工具] ${msg.tool_name}: ${msg.content || ''}`)
      } else if (msg.role === 'assistant' && msg.content) {
        currentAgent.finalText += (currentAgent.finalText ? '\n' : '') + msg.content
      } else if (msg.content) {
        _addLogToAgent(currentAgent, 'history', msg.content)
      }
    }
  }
  if (currentAgent) {
    currentAgent.isStreaming = false
    merged.push(currentAgent)
  }
  messages.value = merged
}

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

// Sync tab changes to parent
watch(sharedActiveTab, (tab) => {
  emit('tab-change', tab)
})

// Sync from parent activeTab (keeps both panels' tabs in sync)
watch(() => props.activeTab, (tab) => {
  if (tab && tab !== sharedActiveTab.value) sharedActiveTab.value = tab
})

function startNewSession() {
  if (streaming.value) stopStream()
  _stopRunningPoll()
  activeSessionId.value = null
  sessionDetail.value = null
  messages.value = []
  pipelineEditDone.value = false
  setComposerMode(true)
  loadSessions()
}

async function selectSession(id) {
  if (streaming.value) stopStream()
  _stopRunningPoll()
  activeSessionId.value = id
  setComposerMode(false)

  try {
    await Promise.all([refreshSession(), loadMessages(), loadSessions()])
  } catch (e) {
    console.error('[ApiAgentPanel] selectSession 加载失败:', e)
    ElMessage.error('加载会话失败，请稍后重试')
    return
  }

  const detail = sessionDetail.value
  // 按钮可见性：confirming 状态显示编辑按钮，running 隐藏，success 看是否有 summary
  if (detail?.status === 'running') {
    pipelineEditDone.value = true  // 运行中，隐藏按钮
  } else if (detail?.status === 'confirm') {
    pipelineEditDone.value = false // 待确认，显示按钮
  } else {
    pipelineEditDone.value = !!detail?.output_payload?.summary
  }

  // 如果 session 正在后台执行，将最后一个 agent 消息标记为 streaming 状态并启动轮询
  // loadMessages() 已从 DB 加载消息并创建了 agent 块，不需要再追加新的
  if (detail?.status === 'running') {
    // 根据 pipeline_progress 确定当前阶段的显示文本
    const progress = detail?.output_payload?.pipeline_progress
    const currentPhase = progress?.current_phase
    const phases = progress?.phases || []
    let stageText = '正在生成结构化用例和预执行...'
    if (currentPhase && phases.length) {
      const runningPhase = phases.find(p => p.status === 'running') || phases.find(p => p.id === currentPhase)
      if (runningPhase) {
        stageText = `正在${runningPhase.name}...`
      }
    }

    const lastAgentMsg = [...messages.value].reverse().find(m => m.role === 'agent')
    if (lastAgentMsg) {
      // 标记已有的最后一个 agent 块为 streaming
      lastAgentMsg.isStreaming = true
      // 追加当前运行阶段到已有的 stages 数组，保留历史阶段日志
      const existingStages = lastAgentMsg.stages || []
      lastAgentMsg.stages = [...existingStages, { name: 'running', status: 'running', text: stageText, logs: [] }]
    } else {
      // 没有历史 agent 消息（极端情况），追加一个占位提示
      messages.value = [...messages.value, {
        id: `running-hint-${Date.now()}`,
        role: 'agent',
        isStreaming: true,
        stages: [{ name: 'running', status: 'running', text: stageText, logs: [] }],
        finalText: '',
        payload: null,
        streamingText: '',
      }]
    }
    _startRunningPoll()
  }
}

function _stopRunningPoll() {
  if (_runningPollTimer) { clearInterval(_runningPollTimer); _runningPollTimer = null }
}

function _startRunningPoll() {
  _stopRunningPoll()
  _runningPollTimer = setInterval(async () => {
    try {
      const res = await getApiSession(activeSessionId.value)
      const detail = res.data.data
      if (detail && detail.status !== 'running') {
        _stopRunningPoll()
        sessionDetail.value = detail
        // 重新评估编辑按钮可见性：有 summary 说明已走过编辑阶段
        pipelineEditDone.value = !!detail.output_payload?.summary
        // 只在不在流式传输时重新加载，避免与正在进行的流式传输冲突
        if (!streaming.value) {
          await Promise.all([loadMessages(), loadSessions()])
        }
      }
    } catch (e) {
      console.error('[poll] session poll failed:', e)
    }
  }, 3000)
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
      interface_id: payload.interfaceId,
      interface_ids: payload.interfaceIds,
      api_doc_text: payload.apiDocText,
      user_prompt: payload.userPrompt,
      environment_id: payload.environmentId,
      mode: payload.mode,
    }
    const res = await createApiSession(body)
    const session = res?.data?.data
    if (!session?.id) {
      throw new Error(t('common.requestFailed'))
    }
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

// Flag to prevent concurrent state updates during cleanup
let isCleaningUp = false

function stopStream() {
  isCleaningUp = true

  abortController?.abort()
  abortController = null
  streaming.value = false
  streamingText.value = ''
  hasStageProgress.value = false
  stageLogLines.value = []

  // Reset flag after cleanup is complete
  setTimeout(() => {
    isCleaningUp = false
  }, 100)
}

/** Detect which stage a text belongs to */
function detectStageFromText(text) {
  const str = String(text)
  if (str.includes('检索') || str.includes('搜索') || str.includes('\u{1F50D}') || str.includes('search')) return 'search_api_document'
  if (str.includes('结构化') || str.includes('structure')) return 'structure_cases'
  if (str.includes('预执行') || str.includes('pre_run') || str.includes('pre-run')) return 'pre_run'
  if (str.includes('用例') || str.includes('生成') || str.includes('generate')) return 'generate_base_cases'
  return 'default'
}

async function sendMessage(content) {
  if (!activeSessionId.value || streaming.value) return
  streaming.value = true
  streamingText.value = ''
  hasStageProgress.value = false
  abortController = new AbortController()

  // Add user message
  messages.value = [...messages.value, {
    id: `temp-${++tempMsgId}`,
    role: 'user',
    content,
    message_type: 'text',
    sequence: messages.value.length + 1,
  }]

  try {
    // ===== Create unified agent response object =====
    const agentResponse = reactive({
      id: `agent-${Date.now()}`,
      role: 'agent',
      isStreaming: true,
      stages: [],
      finalText: '',
      payload: null,
      streamingText: '',
    })

    // Push only ONE message
    messages.value = [...messages.value, agentResponse]

    const getStage = (name) => {
      let stage = agentResponse.stages.find(s => s.name === name)
      if (!stage) {
        stage = { name, status: 'running', text: '', logs: [] }
        agentResponse.stages = [...agentResponse.stages, stage]
      }
      return stage
    }

    const _addLog = (stageName, line) => {
      const stage = getStage(stageName)
      const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
      stage.logs = [...stage.logs.slice(-29), `[${time}] ${line}`]
      stageLogLines.value = [...stageLogLines.value.slice(-49), `[${time}] ${line}`]
    }

    stageLogLines.value = []
    let payloadUpdatedResolve = null
    const payloadUpdatedPromise = new Promise(r => { payloadUpdatedResolve = r })

    await streamApiMessage(
      activeSessionId.value,
      content,
      {
        stage: (data) => {
          hasStageProgress.value = true
          if (data?.name) {
            // Mark previous running stages as done
            agentResponse.stages.forEach(s => {
              if (s.status === 'running' && s.name !== data.name) s.status = 'done'
            })
            const stage = getStage(data.name)
            stage.text = data.text || ''
            stage.status = data.status || 'running'
          }
        },
        custom: (data) => {
          hasStageProgress.value = true
          const text = String(data)
          const stageName = detectStageFromText(text)
          _addLog(stageName, text)
        },
        messages: (data) => {
          agentResponse.streamingText += String(data)
          agentResponse.finalText += String(data)
          streamingText.value = agentResponse.streamingText
        },
        tool_call: (data) => {
          hasStageProgress.value = true
          if (data?.name) _addLog(data.name, `调用工具: ${data.name}`)
          else _addLog('default', '工具调用')
        },
        interface_progress: (data) => {
          // Update per-interface progress in payload
          if (agentResponse.payload?.interfaces && data?.interface_index != null) {
            const iface = agentResponse.payload.interfaces[data.interface_index]
            if (iface) {
              if (data.case_count != null) iface.base_case_count = data.case_count
              if (data.structured_count != null) iface.structured_case_count = data.structured_count
              if (data.exec_results) iface.exec_results = data.exec_results
            }
          }
        },
        pipeline_progress: (data) => {
          // Update overall pipeline progress
          if (agentResponse.payload) {
            agentResponse.payload.pipeline_progress = data
          }
        },
        payload_updated: async () => {
          await refreshSession()
          agentResponse.payload = sessionDetail.value?.output_payload || null
          // Add interface summary to edit_base_cases stage
          const ifaces = agentResponse.payload?.interfaces || []
          if (ifaces.length) {
            _addLog('edit_base_cases', `已为 ${ifaces.length} 个接口生成基础用例：`)
            for (const iface of ifaces) {
              const skipped = iface.skipped ? '（已存在，跳过创建）' : ''
              _addLog('edit_base_cases', `  ${iface.method} ${iface.summary || iface.path} — ${(iface.base_cases || []).length} 条基础用例${skipped}`)
            }
          }
          if (payloadUpdatedResolve) payloadUpdatedResolve()
        },
        summary: (data) => {
          // Store summary in agentResponse
          if (agentResponse.payload) {
            agentResponse.payload.summary = data
          }
          // Add summary to last existing stage instead of creating a new one
          const lastStage = agentResponse.stages.length ? agentResponse.stages[agentResponse.stages.length - 1] : null
          const stageName = lastStage ? lastStage.name : 'default'
          _addLog(stageName, `生成完成: ${data?.total_interfaces || 0} 个接口, ${data?.total_cases || 0} 条用例`)
        },
        error: (data) => {
          const errorMsg = data?.message || t('common.requestFailed')
          ElMessage.error(errorMsg)
          _addLog('default', `[错误] ${errorMsg}`)
        },
        done: async () => {
          abortController?.abort()
          // Wait for payload_updated to complete first
          await payloadUpdatedPromise
          agentResponse.stages = agentResponse.stages.map(s => ({ ...s, status: 'done' }))
          // For pipeline sessions, don't mark as "已完成" — task continues after user edits
          const mode = sessionDetail.value?.output_payload?.mode
          const isPipeline = mode === 'from_interfaces' || mode === 'from_doc' || mode === 'from_prompt'
          if (!isPipeline) {
            agentResponse.isStreaming = false
          }
          // Don't call loadMessages() — it replaces client-side stage blocks
          await Promise.all([refreshSession(), loadSessions()])
          if (!agentResponse.payload) {
            agentResponse.payload = sessionDetail.value?.output_payload || null
          }
          streamingText.value = ''
          // AI-generate session title
          try { await summarizeApiTitle(activeSessionId.value) } catch {}
          await loadSessions()
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
    // Only cleanup if stopStream() hasn't already done it
    if (!isCleaningUp) {
      streaming.value = false
      streamingText.value = ''
      hasStageProgress.value = false
      stageLogLines.value = []
      abortController = null
    }
  }
}

/* 构建富文本消息：上下文 + 用户输入 */
function buildRichContent(payload) {
  const lines = []
  if (payload.projectName) lines.push(`📋 项目: ${payload.projectName}`)
  if (payload.mode === 'from_interfaces' && payload.interfaceNames?.length) {
    lines.push(`🔗 接口: ${payload.interfaceNames.join(', ')}`)
  } else if (payload.mode === 'from_doc') {
    lines.push('📄 模式: 从接口文档生成')
  } else if (payload.mode === 'from_prompt') {
    lines.push('📝 模式: 从输入内容解析接口')
  }
  if (payload.environmentName) lines.push(`🌐 环境: ${payload.environmentName}`)
  const text = payload.content || ''
  if (lines.length) {
    return `[context]\n${lines.join('\n')}\n[/context]\n${text}`
  }
  return text
}

async function handleComposerSend(payload) {
  if (streaming.value || creating.value) return
  // Multi-interface mode: allow sending with just a project (no interface/doc required)
  const session = await createSessionFromComposer(payload)
  if (!session) return
  await sendMessage(buildRichContent(payload))
}

/* SIT-F7: Composer in chat mode sends directly */
async function sendMessageForComposer(payload) {
  if (streaming.value || creating.value) return
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
  const content = buildRichContent(payload)
  if (content) {
    await sendMessage(content)
  }
}

/* Handle open case list */
function handleOpenCaseList(payload) {
  caseListPayload.value = payload
  caseListVisible.value = true
}

/* ========== Multi-interface pipeline helpers ========== */

function methodTagType(method) {
  const m = (method || '').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

function toggleBaseCase(ifaceIndex, caseIndex, checked) {
  const payload = sessionDetail.value?.output_payload
  if (!payload?.interfaces?.[ifaceIndex]) return
  const iface = payload.interfaces[ifaceIndex]
  const selected = iface.selected_indexes || []
  if (checked && !selected.includes(caseIndex)) {
    iface.selected_indexes = [...selected, caseIndex]
  } else if (!checked) {
    iface.selected_indexes = selected.filter(i => i !== caseIndex)
  }
}

function openEditDialog() {
  showEditDialog.value = true
}

async function onSaveEditedBaseCases(editedInterfaces) {
  if (!activeSessionId.value) return
  confirming.value = true
  pipelineEditDone.value = true
  try {
    // Get environment ID from session payload
    const envId = sessionDetail.value?.output_payload?.environment_id || null

    // Trigger Phase 4-5 via SSE stream
    abortController = new AbortController()
    streaming.value = true

    // 刷新侧边栏，将状态从"待确认"更新为"生成中"
    loadSessions()

    // Reuse the existing agent response from Phase 1-3 instead of creating a new one
    let agentResponse = messages.value.filter(m => m.role === 'agent').pop()
    if (!agentResponse) {
      agentResponse = reactive({
        id: `agent-structure-${Date.now()}`,
        role: 'agent',
        isStreaming: true,
        stages: [],
        finalText: '',
        payload: null,
        streamingText: '',
      })
      messages.value = [...messages.value, agentResponse]
    } else {
      // Mark the existing response as streaming again for Phase 4-5
      agentResponse.isStreaming = true
    }

    const getStage = (name) => {
      let stage = agentResponse.stages.find(s => s.name === name)
      if (!stage) {
        stage = { name, status: 'running', text: '', logs: [] }
        agentResponse.stages = [...agentResponse.stages, stage]
      }
      return stage
    }

    const _addLog = (stageName, line) => {
      const stage = getStage(stageName)
      const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
      stage.logs = [...stage.logs.slice(-29), `[${time}] ${line}`]
    }

    let payloadUpdatedResolve = null
    const payloadUpdatedPromise = new Promise(r => { payloadUpdatedResolve = r })

    await streamSaveBaseCases(
      activeSessionId.value,
      { environment_id: envId, interfaces: editedInterfaces },
      {
        stage: (data) => {
          if (data?.name) {
            agentResponse.stages.forEach(s => {
              if (s.status === 'running' && s.name !== data.name) s.status = 'done'
            })
            const stage = getStage(data.name)
            stage.text = data.text || ''
            stage.status = data.status || 'running'
          }
        },
        custom: (data) => {
          const text = String(data)
          const stageName = detectStageFromText(text)
          _addLog(stageName, text)
        },
        interface_progress: (data) => {
          // handled by payload_updated
        },
        payload_updated: async () => {
          await refreshSession()
          agentResponse.payload = sessionDetail.value?.output_payload || null
          if (payloadUpdatedResolve) payloadUpdatedResolve()
        },
        summary: (data) => {
          const lastStage = agentResponse.stages.length ? agentResponse.stages[agentResponse.stages.length - 1] : null
          const stageName = lastStage ? lastStage.name : 'default'
          _addLog(stageName, `生成完成: ${data?.total_interfaces || 0} 个接口, ${data?.total_cases || 0} 条用例`)
        },
        error: (data) => {
          ElMessage.error(data?.message || t('common.requestFailed'))
          _addLog('default', `[错误] ${data?.message || ''}`)
        },
        done: async () => {
          abortController?.abort()
          await payloadUpdatedPromise
          agentResponse.stages = agentResponse.stages.map(s => ({ ...s, status: 'done' }))
          agentResponse.isStreaming = false
          // Don't call loadMessages() here — it replaces client-side stage blocks
          // with backend messages that don't contain stage data, causing stages to disappear.
          await Promise.all([refreshSession(), loadSessions()])
          if (!agentResponse.payload) {
            agentResponse.payload = sessionDetail.value?.output_payload || null
          }
          try { await summarizeApiTitle(activeSessionId.value) } catch {}
          await loadSessions()
        },
      },
      abortController.signal,
    )
  } catch (err) {
    if (err.name !== 'AbortError') {
      ElMessage.error(err.message || t('common.requestFailed'))
    }
  } finally {
    confirming.value = false
    // Only cleanup if stopStream() hasn't already done it
    if (!isCleaningUp) {
      streaming.value = false
      abortController = null
    }
  }
}

/* Save from case list dialog */
async function saveCasesFromDialog(saveData) {
  // For API type, delegate to confirm logic
  showConfirm.value = true
  selectedIndexes.value = saveData.case_indexes || []
}

/* Confirm cases from embedded PayloadCard */
function confirmCasesFromCard() {
  showConfirm.value = true
}

/* Handle confirm dialog submit */
async function onConfirmDialog(payload) {
  if (!activeSessionId.value) return
  confirming.value = true
  try {
    const indexes = payload.selected_indexes?.length ? payload.selected_indexes : selectedIndexes.value
    await confirmApiGeneration({
      session_id: activeSessionId.value,
      selected_indexes: indexes,
      environment_id: payload.environment_id,
      catalog_id: payload.catalog_id,
      interface_id: payload.interface_id ?? boundInterfaceId.value ?? undefined,
    })
    ElMessage.success(t('page.agent.saved'))
    showConfirm.value = false
  } finally {
    confirming.value = false
  }
}

/* Kept for backward compatibility - delegates to dialog */
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
    if (active) {
      emit('composer-mode-change', composerMode.value)
      // 恢复：刷新 session 状态，如果有正在运行的 session，重新启动轮询
      if (activeSessionId.value) {
        refreshSession().then(() => {
          const detail = sessionDetail.value
          // 重新评估编辑按钮可见性
          if (detail?.status === 'running') {
            pipelineEditDone.value = true  // 还在运行，隐藏按钮
            // 标记最后一个 agent 块为 streaming 并显示阶段进度
            const progress = detail?.output_payload?.pipeline_progress
            const runningPhase = (progress?.phases || []).find(p => p.status === 'running')
            const stageText = runningPhase ? `正在${runningPhase.name}...` : '正在生成结构化用例和预执行...'
            const lastAgentMsg = [...messages.value].reverse().find(m => m.role === 'agent')
            if (lastAgentMsg) {
              lastAgentMsg.isStreaming = true
              const existingStages = lastAgentMsg.stages || []
              lastAgentMsg.stages = [...existingStages, { name: 'running', status: 'running', text: stageText, logs: [] }]
            }
            if (!_runningPollTimer) {
              _startRunningPoll()
            }
          } else if (detail?.status === 'confirm') {
            pipelineEditDone.value = false // 待确认，显示按钮
            if (!streaming.value) {
              loadMessages()
            }
          } else {
            pipelineEditDone.value = !!detail?.output_payload?.summary
            if (!streaming.value) {
              // session 在隐藏期间完成了，重新加载消息
              loadMessages()
            }
          }
        })
      }
    } else {
      // 暂停：中止流式传输和轮询，释放所有 HTTP 连接
      // 后端会继续生成，用户切回后会重新加载状态
      if (streaming.value) {
        stopStream()
      }
      _stopRunningPoll()
    }
  },
  { immediate: true },
)

watch(resolvedInterfaceId, (id) => {
  if (id) boundInterfaceId.value = id
}, { immediate: true })

// 切换项目时，重新加载该项目的会话列表
watch(
  () => projectId.value,
  (newId, oldId) => {
    if (newId && newId !== oldId) {
      activeSessionId.value = null
      sessionDetail.value = null
      messages.value = []
      setComposerMode(true)
      loadSessions()
    }
  },
)

onMounted(async () => {
  await Promise.all([loadMeta(), loadCatalogs(), loadSessions()])
  if (props.autoNew || route.query.new === '1' || resolvedInterfaceId.value) {
    setComposerMode(true)
  }
})

onBeforeUnmount(() => {
  // 组件卸载时，中止流式传输和轮询，防止后台继续运行导致浏览器卡死
  if (streaming.value) {
    stopStream()
  }
  _stopRunningPoll()
  console.log('[ApiAgentPanel] 组件卸载，已清理流式传输和轮询')
})
</script>

<style scoped lang="scss">
/* Row layout - Sidebar (left, always visible) + Main (right) */
.api-agent-panel {
  display: flex;
  flex-direction: row;
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

/* Main content area */
.api-agent-panel__main {
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
    min-height: 100vh;
  }
}

/* Landing mode inner layout (centered vertically) */
.api-agent-panel__landing {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 1600px;
  gap: 40px;
  min-height: 0;
}

/* Chat mode layout: context bar + chat + fixed composer */
.api-agent-panel__chat-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  width: 100%;
  max-width: 2400px;
  margin: 0 auto;
  padding: 0 16px;
}

/* Pipeline after-messages wrapper (align with chat message body) */
.pipeline-after-messages {
  margin-left: 42px; /* avatar 32px + gap 10px */
  margin-top: 12px;
}

/* Pipeline edit action */
.pipeline-edit-action {
  padding: 12px 0;
  text-align: center;
}
</style>
