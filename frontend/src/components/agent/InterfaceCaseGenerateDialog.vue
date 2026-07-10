<template>
  <!-- v2-Q2/Q3: 移除user_prompt输入框，直接生成preview；confirm后5s轮询进度 -->
  <el-dialog :close-on-click-modal="false"
    :model-value="modelValue"
    :title="t('page.apiCases.generateCases')"
    width="75vw"
    top="8vh"
    class="case-generate-dialog"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @closed="reset"
  >
    <div v-if="step === 'form'" class="generate-form">
      <el-form-item :label="t('page.apiCases.selectEnv')">
        <EnvironmentSelect v-model="environmentId" />
      </el-form-item>
      <!-- v2-Q2: 不再显示user_prompt输入框，点击生成即直接调用API -->
      <p style="color: var(--el-text-color-secondary); font-size: 13px; margin: 0">
        {{ t('page.agent.caseGen.generateHint') }}
      </p>
    </div>

    <div v-else-if="step === 'preview'" class="case-preview-body">
      <!-- 生成中状态 -->
      <div v-if="previewLoading" class="generating-status">
        <el-icon class="generating-icon is-loading" :size="32" color="#409eff"><Loading /></el-icon>
        <div class="generating-text">{{ t('page.agent.caseGen.generating') }}</div>
        <div class="generating-hint">{{ t('page.agent.caseGen.generatingHint') }}</div>
      </div>
      <el-alert v-else-if="sessionError" type="error" :title="sessionError" show-icon :closable="false" />
      <template v-else>
        <!-- 轮询中显示结构化进度 -->
        <div v-if="pollingStatus === 'running'" ref="pollingStatusRef" class="structuring-status">
          <div class="structuring-header">
            <el-icon class="is-loading" color="var(--el-color-primary)"><Loading /></el-icon>
            <span class="structuring-title">{{ t('page.agent.caseGen.structuring') }}</span>
            <span class="structuring-count">({{ pollingCompleted }}/{{ pollingTotal }})</span>
          </div>
          <el-progress
            :percentage="pollingProgress"
            :stroke-width="12"
            :color="'var(--el-color-primary)'"
          />
          <div class="structuring-hint">{{ t('page.agent.caseGen.structuringHint') }}</div>
        </div>
        <div v-if="baseCases.length" class="table-toolbar">
          <div class="table-toolbar-left"></div>
          <div class="table-toolbar-right">
            <span class="env-label">{{ t('page.apiCases.selectEnv') }}：</span>
            <EnvironmentSelect v-model="confirmEnvId" style="width: 220px" />
          </div>
        </div>
        <el-table
          v-if="baseCases.length"
          :data="baseCases"
          border
          size="small"
          row-key="index"
          @selection-change="onTableSelectionChange"
          class="case-preview-table"
        >
          <el-table-column type="selection" width="40" />
          <el-table-column :label="t('page.agent.caseGen.colNo')" width="55" align="center">
            <template #default="{ $index }">{{ $index + 1 }}</template>
          </el-table-column>
          <el-table-column prop="name" :label="t('page.agent.caseGen.colName')" min-width="160" align="left">
            <template #default="{ row }">
              <el-input v-model="row.name" size="small" />
            </template>
          </el-table-column>
          <el-table-column :label="t('page.agent.caseGen.colDeps')" min-width="140" align="left">
            <template #default="{ row }">
              <el-input
                v-model="row._depsText"
                size="small"
                :placeholder="t('page.agent.caseGen.commaSep')"
                @blur="syncDepsFromText(row)"
              />
            </template>
          </el-table-column>
          <el-table-column :label="t('page.agent.caseGen.colSteps')" min-width="260" align="left">
            <template #default="{ row }">
              <el-input
                v-model="row._stepsText"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 8 }"
                size="small"
                @blur="syncStepsFromText(row)"
              />
            </template>
          </el-table-column>
          <el-table-column :label="t('page.agent.caseGen.colExpected')" min-width="240" align="left">
            <template #default="{ row }">
              <el-input
                v-model="row._expectedText"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 8 }"
                size="small"
                @blur="syncExpectedFromText(row)"
              />
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!baseCases.length && !sessionError" :description="t('page.agent.noPreview')" />
      </template>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
      <el-button v-if="step === 'form'" type="primary" :loading="previewLoading" @click="runPreview">
        {{ t('page.agent.generate') }}
      </el-button>
      <template v-else-if="pollingStatus !== 'running'">
        <el-button
          type="primary"
          :loading="confirming"
          :disabled="!canConfirm"
          @click="runConfirm"
        >
          {{ t('common.confirm') }}
        </el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import {
  confirmCaseGeneration,
  generateCasePreview,
  getGenerationStatus,
} from '@/api/apiTest'
import { useContentDialog } from '@/composables/useContentDialog'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  interfaceId: { type: Number, required: true },
})

const emit = defineEmits(['update:modelValue', 'confirmed'])

const { t, locale } = useI18n()
const { dialogWidth, dialogTop, dialogClass, bodyMaxHeight } = useContentDialog(120)

// v2-Q2: 移除 userPrompt，仅保留环境选择
const step = ref('form')
const environmentId = ref(null)
const confirmEnvId = ref(null)
const previewLoading = ref(false)
const confirming = ref(false)
const sessionId = ref(null)
const baseCases = ref([])
const selectedIndexes = ref([])
const sessionError = ref('')

// v2-Q3: 轮询状态
const pollingStatus = ref('')
const pollingProgress = ref(0)
const pollingCompleted = ref(0)
const pollingTotal = ref(0)
const pollingItems = ref([])
const pollingStage = ref('structuring')
const pollingStatusRef = ref(null)
let pollTimer = null
let previewPollTimer = null

const canConfirm = computed(() => {
  if (pollingStatus.value === 'running') return false
  return Boolean(selectedIndexes.value.length && sessionId.value)
})

function syncStepsFromText(row) {
  row.steps = (row._stepsText || '').split('\n').map(function (s) { return s.trim() }).filter(Boolean)
}

function syncExpectedFromText(row) {
  row.expected = (row._expectedText || '').split('\n').map(function (s) { return s.trim() }).filter(Boolean)
}

function syncDepsFromText(row) {
  row.dependencies = (row._depsText || '').split(/[,，]/).map(function (s) { return s.trim() }).filter(Boolean)
}

function onTableSelectionChange(rows) {
  selectedIndexes.value = rows.map(function (r) { return r.index })
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      reset()
      // 打开弹窗时直接开始生成预览，跳过手动点击"生成"步骤
      autoRunPreview()
    }
  },
)

async function autoRunPreview() {
  step.value = 'preview'
  previewLoading.value = true
  sessionError.value = ''
  try {
    const res = await generateCasePreview(props.interfaceId, {
      environment_id: environmentId.value || undefined,
      locale: locale.value,
    })
    const data = res.data.data
    sessionId.value = data.session_id
    // v3: preview 现在是异步的，需要轮询等待结果
    startPreviewPolling()
  } catch (err) {
    sessionError.value = err.message || t('common.requestFailed')
    step.value = 'form'
    previewLoading.value = false
  }
}

function reset() {
  stopPolling()
  stopPreviewPolling()
  step.value = 'form'
  environmentId.value = null
  confirmEnvId.value = null
  previewLoading.value = false
  confirming.value = false
  sessionId.value = null
  baseCases.value = []
  selectedIndexes.value = []
  sessionError.value = ''
  pollingStatus.value = ''
  pollingProgress.value = 0
  pollingCompleted.value = 0
  pollingTotal.value = 0
  pollingItems.value = []
}

async function runPreview() {
  previewLoading.value = true
  sessionError.value = ''
  try {
    const res = await generateCasePreview(props.interfaceId, {
      environment_id: environmentId.value || undefined,
      locale: locale.value,
    })
    const data = res.data.data
    sessionId.value = data.session_id
    step.value = 'preview'
    // v3: preview 现在是异步的，需要轮询等待结果
    startPreviewPolling()
  } catch (err) {
    sessionError.value = err.message || t('common.requestFailed')
    previewLoading.value = false
  }
}

async function runConfirm() {
  confirming.value = true
  // 同步编辑中的文本到数组
  baseCases.value.forEach(function (row) {
    syncStepsFromText(row)
    syncExpectedFromText(row)
    syncDepsFromText(row)
  })
  // 构建编辑后的 base cases（只发送选中行的编辑数据）
  var editedCases = baseCases.value.map(function (c) {
    return { name: c.name, steps: c.steps, expected: c.expected, dependencies: c.dependencies }
  })
  try {
    await confirmCaseGeneration(props.interfaceId, {
      session_id: sessionId.value,
      selected_indexes: selectedIndexes.value,
      environment_id: confirmEnvId.value,
      edited_base_cases: editedCases,
    })
    // v2-Q3: confirm后开始轮询generation-status
    startPolling()
  } catch (err) {
    sessionError.value = err.message || t('common.requestFailed')
    confirming.value = false
  }
}

// ==================== v2-Q3: 5s轮询逻辑 ====================

function startPolling() {
  pollingStatus.value = 'running'
  pollingStage.value = 'structuring'
  pollingCompleted.value = 0
  pollingTotal.value = selectedIndexes.value.length || baseCases.value.length

  // 自动滚动到顶部进度条
  nextTick(() => {
    const el = pollingStatusRef.value
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })

  pollTimer = setInterval(async () => {
    try {
      const res = await getGenerationStatus(props.interfaceId, sessionId.value)
      const statusData = res.data.data
      const status = statusData.status

      if (status === 'success' || status === 'failed' || status === 'cancelled') {
        stopPolling()
        pollingStatus.value = status
        if (status === 'success') {
          pollingProgress.value = 100
          pollingCompleted.value = pollingTotal.value
          const confirmResult = statusData.confirm_result
          const savedCount = confirmResult?.created_case_ids?.length || pollingTotal.value
          const hasEnv = !!confirmEnvId.value
          if (hasEnv) {
            ElMessage.success(t('page.agent.caseGen.savedAndVerifying', { count: savedCount }))
          } else {
            ElMessage.success(t('page.agent.saved'))
          }
          emit('confirmed')
          emit('update:modelValue', false)
        } else if (status === 'failed') {
          sessionError.value = statusData.error_message || t('page.agent.caseGen.execFailed')
        } else {
          sessionError.value = t('page.agent.caseGen.userCancelled')
        }
        confirming.value = false
      } else {
        // 更新进度
        const progress = statusData.progress
        if (progress) {
          pollingCompleted.value = progress.completed || 0
          pollingTotal.value = progress.total || selectedIndexes.value.length
          pollingProgress.value =
            pollingTotal.value > 0
              ? Math.round((pollingCompleted.value / pollingTotal.value) * 100)
              : 0
          pollingItems.value = progress.items || []
          if (progress.stage) pollingStage.value = progress.stage
        }
      }
    } catch {
      // 网络错误继续轮询
    }
  }, 5000) // v2: 每5秒查询一次
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// ==================== v3: 预览生成轮询 ====================

function startPreviewPolling() {
  previewPollTimer = setInterval(async () => {
    try {
      const res = await getGenerationStatus(props.interfaceId, sessionId.value)
      const statusData = res.data.data
      const status = statusData.status

      if (status === 'success') {
        stopPreviewPolling()
        previewLoading.value = false
        const cases = statusData.base_cases || []
        baseCases.value = cases.map(function (c, i) {
          return Object.assign({}, c, {
            index: i,
            _stepsText: (c.steps || []).join('\n'),
            _expectedText: (c.expected || []).join('\n'),
            _depsText: (c.dependencies || []).join(', '),
          })
        })
        selectedIndexes.value = baseCases.value.map(function (c) { return c.index })
        confirmEnvId.value = environmentId.value
        if (!baseCases.value.length) {
          sessionError.value = t('page.agent.noPreview')
        }
      } else if (status === 'failed') {
        stopPreviewPolling()
        previewLoading.value = false
        sessionError.value = statusData.error_message || t('page.agent.caseGen.previewFailed')
      }
      // status === 'running' 则继续轮询
    } catch {
      // 网络错误继续轮询
    }
  }, 5000)
}

function stopPreviewPolling() {
  if (previewPollTimer) {
    clearInterval(previewPollTimer)
    previewPollTimer = null
  }
}

onUnmounted(() => {
  stopPolling()
  stopPreviewPolling()
})
</script>

<style scoped lang="scss">
.generate-form {
  padding: 10px 0;
}

.generating-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.generating-icon {
  margin-bottom: 16px;
}

.generating-text {
  font-size: 15px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}

.generating-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.structuring-status {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border-radius: 8px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-5);
  margin-bottom: 8px;
}

.structuring-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.structuring-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.structuring-count {
  font-size: 13px;
  color: var(--el-color-primary);
  font-weight: 600;
}

.structuring-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.case-preview-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;

  .table-toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .env-label {
    font-size: 13px;
    color: var(--el-text-color-regular);
    white-space: nowrap;
  }
}

.case-preview-table {
  :deep(.el-table__cell) {
    vertical-align: top;
  }

  :deep(.cell) {
    white-space: normal;
    word-break: break-word;
    line-height: 1.5;
    text-align: left;
    padding: 8px 10px;
  }

  .steps-list {
    margin: 0;
    padding-left: 0;
    list-style: none;
    counter-reset: step-counter;
    font-size: 12px;
    line-height: 1.6;
    color: var(--el-text-color-regular);

    li {
      margin-bottom: 2px;
      counter-increment: step-counter;

      &::before {
        content: counter(step-counter) ". ";
        font-weight: 500;
      }
    }
  }

  .expected-list {
    margin: 0;
    padding-left: 0;
    list-style: none;
    font-size: 12px;
    line-height: 1.6;
    color: var(--el-text-color-regular);

    li {
      margin-bottom: 2px;
    }
  }
}
</style>

<style lang="scss">
.case-generate-dialog {
  max-width: calc(100vw - 32px);
  max-height: 84vh;
  display: flex;
  flex-direction: column;

  .el-dialog__body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding-bottom: 8px;
  }

  .el-dialog__footer {
    flex-shrink: 0;
    padding-top: 8px;
  }
}
</style>
