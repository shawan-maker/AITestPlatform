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

      <!-- Chat mode: tabs + context bar + chat panel + composer (fixed bottom) -->
      <template v-else>
        <div class="functional-agent-panel__chat-layout">
          <AgentTypeTabs v-model="sharedActiveTab" :compact="true" />
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
                v-if="sessionDetail?.output_payload && hasPayloadData && !hasAgentResponse"
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
      :project-id="projectId"
      @save="saveCasesFromDialog"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
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
  summarizeFunctionalTitle,
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
  activeTab: { type: String, default: 'functional' },
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
const creating = ref(false)
const saving = ref(false)
const catalogs = ref([])
const meta = ref(null)
const composerMode = ref(true)
const sidebarCollapsed = ref(false)
const sharedActiveTab = ref('functional')
let _runningPollTimer = null
// Legacy stage log lines (for backward compat with chat panel)
const stageLogLines = ref([])

// Case list dialog state
const caseListVisible = ref(false)
const caseListPayload = ref(null)

let abortController = null
let tempMsgId = 0

// Check if current messages contain a completed agent response (not streaming)
const hasAgentResponse = computed(() => {
  const result = messages.value.some(m => m.role === 'agent' && !m.isStreaming)
  console.log('[DEBUG] hasAgentResponse computed:', result, 'messages count:', messages.value.length)
  return result
})

// Check if sessionDetail has valid payload data
const hasPayloadData = computed(() => {
  const payload = sessionDetail.value?.output_payload
  if (!payload) return false
  // Check if payload has test_points or cases with data
  const testPoints = payload.test_points || []
  const cases = payload.cases || []
  return testPoints.length > 0 || cases.length > 0
})

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
    // [FIX-问题4] 跳过 system 角色消息（知识库文档上下文等），避免在新对话中显示为假历史
    if (msg.role === 'system') continue

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
        _addLogToAgent(currentAgent, 'history', `[${time}] ${msg.content}`)
      } else if (msg.message_type === 'tool_call' && msg.tool_name) {
        _addLogToAgent(currentAgent, 'history', `[工具] ${msg.tool_name}: ${msg.content || ''}`)
      } else if (msg.role === 'assistant' && msg.content) {
        // Text content → append to finalText
        currentAgent.finalText += (currentAgent.finalText ? '\n' : '') + msg.content
      } else if (msg.content) {
        _addLogToAgent(currentAgent, 'history', msg.content)
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
  setComposerMode(true)
  loadSessions()
}

async function selectSession(id) {
  if (streaming.value) stopStream()
  _stopRunningPoll()
  activeSessionId.value = id
  setComposerMode(false)
  await Promise.all([refreshSession(), loadMessages(), loadSessions()])
  // 如果 session 仍在后台执行中，启动轮询
  if (sessionDetail.value?.status === 'running') _startRunningPoll()
}

function _stopRunningPoll() {
  if (_runningPollTimer) { clearInterval(_runningPollTimer); _runningPollTimer = null }
}

function _startRunningPoll() {
  _stopRunningPoll()
  _runningPollTimer = setInterval(async () => {
    try {
      const res = await getFunctionalSession(activeSessionId.value)
      const detail = res.data.data
      if (detail && detail.status !== 'running') {
        _stopRunningPoll()
        sessionDetail.value = detail
        await Promise.all([loadMessages(), loadSessions()])
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
      requirement_text: payload.requirementText,
      knowledge_document_id: payload.knowledgeDocumentId,
      user_prompt: payload.userPrompt,
    }
    console.log('[DEBUG-SESSION] 创建新会话, body:', JSON.stringify(body).substring(0, 200))
    const res = await createFunctionalSession(body)
    const session = res?.data?.data
    console.log('[DEBUG-SESSION] 新会话创建成功, sessionId:', session?.id)
    if (!session?.id) {
      throw new Error(t('common.requestFailed'))
    }
    await loadSessions()
    activeSessionId.value = session.id
    console.log('[DEBUG-SESSION] activeSessionId 已设置为:', activeSessionId.value)
    setComposerMode(false)

    // 加载消息前确认 messages 已清空
    console.log('[DEBUG-SESSION] loadMessages 前, 当前 messages 数量:', messages.value.length)
    await Promise.all([refreshSession(), loadMessages()])
    console.log('[DEBUG-SESSION] loadMessages 后, messages 数量:', messages.value.length,
      ', message ids:', messages.value.map(m => m.id || m.role).join(', '))
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

// Promise to track payload_updated completion
let payloadUpdatedPromise = null
let payloadUpdatedResolve = null

/** Detect which stage a text belongs to based on keywords */
function detectStageFromText(text) {
  const str = String(text)
  // "[TRANSITIONAL]" marks transitional log between search_requirement and generate_testcases
  if (str.includes('[TRANSITIONAL]')) return 'transitional'
  // "✅ [阶段1完成]" marks search_requirement as done
  if (str.includes('✅ [阶段1完成]') || str.includes('阶段1完成')) return 'search_requirement_done'
  if (str.includes('检索') || str.includes('搜索') || str.includes('\u{1F50D}') || str.includes('search')) return 'search_requirement'
  // "✅ 测试用例的卡片生成成功" is the final marker — mark generate_testcases as truly done
  if (str.includes('✅ 测试用例的卡片生成成功') || str.includes('卡片生成成功')) return 'generate_testcases_done'
  // All testpoint/testcase related logs belong to generate_testcases stage
  if (str.includes('测试点') || str.includes('testpoint') || str.includes('TestPoint') || str.includes('用例') || str.includes('生成') || str.includes('generate')) return 'generate_testcases'
  // Default: return last active stage or 'default'
  return 'default'
}

async function sendMessage(content) {
  if (!activeSessionId.value || streaming.value) return
  streaming.value = true
  streamingText.value = ''
  hasStageProgress.value = false
  abortController = new AbortController()
  
  // Initialize payload_updated tracking Promise
  payloadUpdatedPromise = new Promise((resolve) => {
    payloadUpdatedResolve = resolve
  })
  console.log('[SSE-EVENT] payloadUpdatedPromise initialized')

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
    const KNOWN_STAGE_ORDER = ['search_requirement', 'generate_testcases']

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
      const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
      // "[TRANSITIONAL]" logs: 写入检索需求文档阶段的logs中显示，生成完成后清理
      if (stageName === 'transitional') {
        const stage = getStage('search_requirement')
        stage.logs = [...stage.logs.slice(-29), `[${time}] ${line}`]
        return
      }
      // "generate_testcases_done" means the testcases stage is truly complete
      // Map it to the existing "generate_testcases" stage and mark as done
      // "search_requirement_done" means the search stage is truly complete
      let actualStageName = stageName
      if (stageName === 'generate_testcases_done') {
        actualStageName = 'generate_testcases'
      }
      if (stageName === 'search_requirement_done') {
        actualStageName = 'search_requirement'
      }
      const stage = getStage(actualStageName)
      stage.logs = [...stage.logs.slice(-29), `[${time}] ${line}`]
      // If this is the completion marker, mark the stage as done
      if (stageName === 'generate_testcases_done' || stageName === 'search_requirement_done') {
        stage.status = 'done'
        // 问题2修复：在检索需求文档阶段完成后，添加等待状态提示
        if (stageName === 'search_requirement_done') {
          // 添加一个提示，让用户知道程序还在处理
          stage.logs = [...stage.logs, `[${time}] 检索需求文档阶段完成，正在准备生成测试用例，请稍候...`]
        }
      }
    }

    // Reset legacy logs
    stageLogLines.value = []

    await streamFunctionalMessage(
      activeSessionId.value,
      content,
      {
        stage: (data) => {
          console.log('[SSE-EVENT] stage event received:', data)
          hasStageProgress.value = true
          if (data?.name) {
            console.log(`[SSE-EVENT] Stage "${data.name}" status: ${data.status}`)
            // 新阶段开始 → 先标记所有之前的 running 阶段为 done
            agentResponse.stages = agentResponse.stages.map(s =>
              s.name === data.name || s.status === 'done' ? s : { ...s, status: 'done' }
            )
            const stage = getStage(data.name)
            stage.text = data.text || ''
            stage.status = data.status || 'running'
            console.log(`[SSE-EVENT] Stage "${data.name}" updated, text: ${data.text}`)
          } else {
            console.warn('[SSE-EVENT] stage event received but no name provided')
          }
        },
        custom: (data) => {
          console.log('[SSE-EVENT] custom event received:', data)
          hasStageProgress.value = true
          const text = String(data)
          console.log(`[SSE-EVENT] custom text: ${text.substring(0, 100)}...`)
          
          // Auto-detect which stage this belongs to
          const stageName = detectStageFromText(text)
          console.log(`[SSE-EVENT] custom event detected stage: ${stageName}`)
          _addLog(stageName, text)
          
          // 问题2修复：在"检索需求文档"阶段完成后，添加等待状态提示
          if (text.includes('✅ [阶段1完成]') || text.includes('阶段1完成')) {
            console.log('[SSE-EVENT] ✅ 检索需求文档阶段完成，等待生成测试用例...')
          }
          
          // 检测测试用例生成完成
          if (text.includes('✅ [阶段2完成]') || text.includes('阶段2完成') || text.includes('测试用例生成成功')) {
            console.log('[SSE-EVENT] ✅ 测试用例生成完成！')
          }
        },
        messages: (data) => {
          const text = String(data)
          // 过滤掉 [TRANSITIONAL] 过渡日志文本，避免出现在最终回复中
          if (text.includes('[TRANSITIONAL]')) {
            console.log('[SSE-EVENT] messages: filtered out TRANSITIONAL text')
            return
          }
          console.log(`[SSE-EVENT] messages: received ${text.length} chars`)
          
          // 只追加到 agentResponse 的 finalText/streamingText（用于兼容和结果展示）
          agentResponse.streamingText += text
          agentResponse.finalText += text
          streamingText.value = agentResponse.streamingText
          // 注意：messages 事件（LLM 流式文本）不再注入到阶段 logs 中，
          // 阶段详情框只展示 custom/tool_call 事件的结构化日志，避免跨阶段内容混乱
        },
        tool_call: (data) => {
          console.log('[SSE-EVENT] tool_call event received:', data)
          hasStageProgress.value = true
          if (data?.name) {
            console.log(`[SSE-EVENT] Tool called: ${data.name}`)
            _addLog(data.name, `调用工具: ${data.name}`)
          } else {
            console.warn('[SSE-EVENT] tool_call event but no name provided')
            _addLog('default', `工具调用`)
          }
        },
        payload_updated: async () => {
          console.log('[SSE-EVENT] 🚀 payload_updated event received at', new Date().toLocaleTimeString())
          console.log('[SSE-EVENT] payload_updated: activeSessionId:', activeSessionId.value)
          console.log('[SSE-EVENT] payload_updated: agentResponse.isStreaming before:', agentResponse.isStreaming)
          
          // 不再创建 default 阶段，静默刷新 session 即可
          console.log('[SSE-EVENT] payload_updated: calling refreshSession...')
          await refreshSession()
          console.log('[SSE-EVENT] payload_updated: after refreshSession')
          console.log('[SSE-EVENT] payload_updated: sessionDetail.output_payload:', sessionDetail.value?.output_payload ? 'EXISTS' : 'NULL')
          
          agentResponse.payload = sessionDetail.value?.output_payload || null
          console.log('[SSE-EVENT] payload_updated: agentResponse.payload set, has payload:', !!agentResponse.payload)
          
          // 卡片已出现，现在标记 generate_testcases 阶段完成并打印成功日志
          const stage = agentResponse.stages.find(s => s.name === 'generate_testcases')
          if (stage && stage.status !== 'done') {
            console.log('[SSE-EVENT] payload_updated: marking generate_testcases stage as done')
            stage.status = 'done'
            const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
            stage.logs = [...(stage.logs || []), `[${time}] ✅ 测试用例的卡片生成成功`]
          } else {
            console.log('[SSE-EVENT] payload_updated: generate_testcases stage not found or already done')
          }
          
          // 等待 DOM 更新，确保卡片渲染
          console.log('[SSE-EVENT] payload_updated: waiting for nextTick...')
          await nextTick()
          console.log('[SSE-EVENT] payload_updated: nextTick completed')
          
          // ⚠️ 不在这里设置 isStreaming = false，留给 done 事件统一处理
          console.log('[SSE-EVENT] payload_updated: ✅ payload_updated completed, waiting for done event...')
          console.log('[SSE-EVENT] payload_updated: agentResponse.isStreaming remains:', agentResponse.isStreaming)
          
          // ✅ 标记 payload_updated 完成
          if (payloadUpdatedResolve) {
            payloadUpdatedResolve()
            console.log('[SSE-EVENT] payload_updated: ✅ Promise resolved')
          }
        },
        error: (data) => {
          console.error('[SSE-EVENT] ❌ error event received:', data)
          const errorMsg = data?.message || t('common.requestFailed')
          console.error('[SSE-EVENT] error message:', errorMsg)
          ElMessage.error(errorMsg)
          // 错误信息追加到最后一个阶段，不创建新的 default 阶段
          const stages = agentResponse.stages
          if (stages.length > 0) {
            const lastStage = stages[stages.length - 1]
            const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
            console.error('[SSE-EVENT] error: adding error log to stage:', lastStage.name)
            lastStage.logs = [...(lastStage.logs || []), `[${time}] [错误] ${errorMsg}`]
          } else {
            console.error('[SSE-EVENT] error: no stages available to add error log')
          }
        },
        done: async () => {
          console.log('[SSE-EVENT] 🏁 done event received at', new Date().toLocaleTimeString())
          console.log('[SSE-EVENT] done: activeSessionId:', activeSessionId.value)
          console.log('[SSE-EVENT] done: agentResponse.isStreaming before:', agentResponse.isStreaming)
          console.log('[SSE-EVENT] done: has abortController:', !!abortController)
          
          // 强制停止 SSE 流，避免持续返回内容
          if (abortController) {
            console.log('[SSE-EVENT] done: aborting controller...')
            abortController.abort()
            console.log('[SSE-EVENT] done: controller aborted')
          }
          
          // ⚠️ 关键：等待 payload_updated 完成，确保卡片已渲染
          console.log('[SSE-EVENT] done: ⏳ Waiting for payload_updated to complete...')
          if (payloadUpdatedPromise) {
            await payloadUpdatedPromise
            console.log('[SSE-EVENT] done: ✅ payload_updated completed, now safe to set isStreaming = false')
          } else {
            console.log('[SSE-EVENT] done: ⚠️ No payloadUpdatedPromise, proceeding anyway')
          }
          
          // 标记所有阶段为 done（但保留 generate_testcases 留给 payload_updated 处理）
          console.log('[SSE-EVENT] done: marking stages as done...')
          agentResponse.stages = agentResponse.stages.map(s =>
            s.name === 'generate_testcases' ? s : { ...s, status: 'done' }
          )
          console.log('[SSE-EVENT] done: stages updated')
          
          // 等待 DOM 更新后再标记完成，确保卡片已渲染
          console.log('[SSE-EVENT] done: waiting for nextTick...')
          await nextTick()
          console.log('[SSE-EVENT] done: nextTick completed')
          
          agentResponse.isStreaming = false
          console.log('[SSE-EVENT] done: ✅ isStreaming set to false')
          
          // 清理过渡日志（从所有阶段的logs中移除[TRANSITIONAL]标记的行），生成测试用例完成后不再显示
          console.log('[SSE-EVENT] done: cleaning TRANSITIONAL logs...')
          agentResponse.stages.forEach(s => {
            const before = (s.logs || []).length
            s.logs = (s.logs || []).filter(line => !line.includes('[TRANSITIONAL]'))
            const after = s.logs.length
            if (before !== after) {
              console.log(`[SSE-EVENT] done: cleaned ${before - after} TRANSITIONAL logs from stage ${s.name}`)
            }
          })
          console.log('[SSE-EVENT] done: TRANSITIONAL logs cleaned')

          // 只刷新 session 以获取 payload，不要重新加载 messages（会丢失阶段信息）
          console.log('[SSE-EVENT] done: refreshing session...')
          await refreshSession()
          console.log('[SSE-EVENT] done: session refreshed, has payload:', !!sessionDetail.value?.output_payload)
          
          if (!agentResponse.payload) {
            console.log('[SSE-EVENT] done: setting payload from sessionDetail')
            agentResponse.payload = sessionDetail.value?.output_payload || null
          } else {
            console.log('[SSE-EVENT] done: payload already set')
          }

          // 只刷新侧边栏列表
          console.log('[SSE-EVENT] done: loading sessions...')
          await loadSessions()
          console.log('[SSE-EVENT] done: sessions loaded')

          // 生成会话标题（AI 总结）
          try {
            console.log('[SSE-EVENT] done: Calling summarizeFunctionalTitle with sessionId:', activeSessionId.value)
            const titleResult = await summarizeFunctionalTitle(activeSessionId.value)
            console.log('[SSE-EVENT] done: summarizeFunctionalTitle completed, result:', titleResult)
            await loadSessions() // 刷新侧边栏显示新标题
            console.log('[SSE-EVENT] done: sessions reloaded after title generation')
          } catch (err) {
            console.error('[SSE-EVENT] done: ❌ summarizeFunctionalTitle failed:', err)
            console.error('[SSE-EVENT] done: Error details:', err.response?.data || err.message)
            // 标题生成失败不影响主流程
          }

          // Clear streaming text reference
          streamingText.value = ''
          console.log('[SSE-EVENT] done: ✅ All done, streamingText cleared')
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

/* 构建富文本消息：上下文 + 用户输入 */
function buildRichContent(payload) {
  const lines = []
  if (payload.projectName) lines.push(`📋 项目: ${payload.projectName}`)
  if (payload.documentName) lines.push(`📄 需求文档: ${payload.documentName}`)
  const text = payload.content || ''
  if (lines.length) {
    return `[context]\n${lines.join('\n')}\n[/context]\n${text}`
  }
  return text
}

async function handleComposerSend(payload) {
  if (streaming.value || creating.value) return
  try {
    const session = await createSessionFromComposer(payload)
    if (!session) return
    await sendMessage(buildRichContent(payload))
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
  const content = buildRichContent(payload)
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

// 切换项目时，重新加载该项目的会话列表
watch(
  () => projectId.value,
  (newId, oldId) => {
    if (newId && newId !== oldId) {
      // 重置当前会话状态
      activeSessionId.value = null
      sessionDetail.value = null
      messages.value = []
      setComposerMode(true)
      // 重新加载新项目的会话
      loadSessions()
    }
  },
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
  min-height: 100vh; /* 让内容在屏幕正中间 */
  height: auto;
  overflow: hidden;
}

/* Main content area */
.functional-agent-panel__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-size: 1.2rem; /* 增大字体：从默认约 1rem 改为 1.2rem */

  &--landing {
    align-items: center;
    justify-content: center;
    padding: 48px; /* 加倍：从 24px 改为 48px */
    overflow-y: auto;
    min-height: 100vh; /* 让landing内容在屏幕正中间 */
  }
}

/* Landing mode inner layout (centered vertically) */
.functional-agent-panel__landing {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 1600px; /* 加倍：从 800px 改为 1600px */
  gap: 40px; /* 加倍：从 20px 改为 40px */
  min-height: 0;
  font-size: 1.3rem; /* 增大字体 */
}

/* Chat mode layout: context bar + chat + fixed composer */
.functional-agent-panel__chat-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  width: 100%;
  max-width: 2400px; /* 加倍：从 1200px 改为 2400px */
  margin: 0 auto;
  padding: 0 32px; /* 加倍：从 16px 改为 32px */
  font-size: 1.2rem; /* 增大字体 */
}
</style>
