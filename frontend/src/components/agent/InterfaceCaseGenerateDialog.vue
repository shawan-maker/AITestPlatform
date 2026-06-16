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
        {{ t('page.apiCases.generateHint') || '将基于接口文档自动生成测试用例预览' }}
      </p>
    </div>

    <div v-else-if="step === 'preview'" class="case-preview-body">
      <!-- 生成中状态 -->
      <div v-if="previewLoading" class="generating-status">
        <el-icon class="generating-icon is-loading" :size="32" color="#409eff"><Loading /></el-icon>
        <div class="generating-text">正在分析接口文档，智能生成测试用例...</div>
        <div class="generating-hint">AI 正在理解接口参数、业务场景和边界条件，预计需要 30-120 秒，请耐心等待</div>
      </div>
      <el-alert v-else-if="sessionError" type="error" :title="sessionError" show-icon :closable="false" />
      <template v-else>
        <!-- v2-Q3: 轮询中显示进度 -->
        <div v-if="pollingStatus === 'running'" class="polling-status">
          <el-progress :percentage="pollingProgress" :stroke-width="10" :color="'var(--el-color-primary)'" />
          <span class="polling-status-text">
            正在执行预验证... ({{ pollingCompleted }}/{{ pollingTotal }})
          </span>
          <div v-if="pollingItems.length" class="polling-items">
            <div v-for="item in pollingItems" :key="item.index" class="polling-item" :class="item.status">
              <span class="polling-item-name">{{ item.name || `用例 ${item.index + 1}` }}</span>
              <el-tag v-if="item.status === 'success'" type="success" size="small">通过</el-tag>
              <el-tag v-else-if="item.status === 'warning'" type="warning" size="small">警告</el-tag>
              <el-tag v-else-if="item.status === 'error'" type="danger" size="small">失败</el-tag>
              <el-tag v-else type="info" size="small">等待中</el-tag>
              <span v-if="item.error" class="polling-item-error">{{ item.error }}</span>
            </div>
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
          <el-table-column label="编号" width="55" align="center">
            <template #default="{ $index }">{{ $index + 1 }}</template>
          </el-table-column>
          <el-table-column prop="name" label="名称" min-width="140" align="left">
            <template #default="{ row }">{{ row.name || '-' }}</template>
          </el-table-column>
          <el-table-column label="依赖" min-width="120" align="left">
            <template #default="{ row }">
              <template v-if="row.dependencies && row.dependencies.length">
                <el-tag v-for="(dep, di) in row.dependencies" :key="di" size="small" style="margin: 1px 2px">{{ dep }}</el-tag>
              </template>
              <span v-else style="color: #999">无</span>
            </template>
          </el-table-column>
          <el-table-column label="步骤" min-width="220" align="left">
            <template #default="{ row }">
              <ol v-if="row.steps && row.steps.length" class="steps-list">
                <li v-for="(s, si) in row.steps" :key="si">{{ s }}</li>
              </ol>
              <span v-else style="color: #999">-</span>
            </template>
          </el-table-column>
          <el-table-column label="预期结果" min-width="200" align="left">
            <template #default="{ row }">
              <ul v-if="row.expected && row.expected.length" class="expected-list">
                <li v-for="(e, ei) in row.expected" :key="ei">{{ e }}</li>
              </ul>
              <span v-else style="color: #999">-</span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!baseCases.length && !sessionError" :description="t('page.agent.noPreview')" />
      </template>
      <div v-if="baseCases.length && !previewLoading && pollingStatus !== 'running'" class="confirm-env-row">
        <span class="env-label">{{ t('page.apiCases.selectEnv') }}：</span>
        <EnvironmentSelect v-model="confirmEnvId" />
      </div>
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
import { computed, onUnmounted, ref, watch } from 'vue'
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

const { t } = useI18n()
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
let pollTimer = null
let previewPollTimer = null

const canConfirm = computed(() => {
  if (pollingStatus.value === 'running') return false
  return Boolean(selectedIndexes.value.length && sessionId.value)
})

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
  try {
    await confirmCaseGeneration(props.interfaceId, {
      session_id: sessionId.value,
      selected_indexes: selectedIndexes.value,
      environment_id: confirmEnvId.value,
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
  pollingCompleted.value = 0
  pollingTotal.value = selectedIndexes.value.length || baseCases.value.length

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
          // 检查预执行是否有错误
          const confirmResult = statusData.confirm_result
          const runErrors = confirmResult?.run_errors || []
          const savedCount = confirmResult?.created_case_ids?.length || pollingTotal.value
          if (runErrors.length) {
            const errorDetail = runErrors.map(function (e, i) { return (i + 1) + '. ' + e }).join('\n')
            ElMessage({
              type: 'warning',
              message: `已保存 ${savedCount} 条用例，${runErrors.length} 条预验证未通过`,
              duration: 5000,
            })
            console.warn('[预验证未通过详情]', errorDetail)
          } else {
            ElMessage.success(t('page.agent.saved'))
          }
          emit('confirmed')
          emit('update:modelValue', false)
        } else if (status === 'failed') {
          sessionError.value = statusData.error_message || '执行失败'
        } else {
          sessionError.value = '用户取消了本次生成'
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
          return Object.assign({}, c, { index: i })
        })
        selectedIndexes.value = baseCases.value.map(function (c) { return c.index })
        confirmEnvId.value = environmentId.value
        if (!baseCases.value.length) {
          sessionError.value = t('page.agent.noPreview')
        }
      } else if (status === 'failed') {
        stopPreviewPolling()
        previewLoading.value = false
        sessionError.value = statusData.error_message || '预览生成失败'
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

.case-preview-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.polling-status {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-color-primary-light-7) 100%);
  border: 1px solid var(--el-color-primary-light-5);
  margin-bottom: 8px;

  :deep(.el-progress-bar__inner) {
    background: linear-gradient(90deg, var(--el-color-primary) 0%, var(--el-color-primary-light-3) 100%);
    transition: width 0.6s ease;
  }
}

.polling-status-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-color-primary);
  display: flex;
  align-items: center;
  gap: 6px;

  &::before {
    content: '';
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--el-color-primary);
    animation: polling-pulse 1.5s ease-in-out infinite;
  }
}

@keyframes polling-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.8); }
}

.polling-items {
  max-height: 200px;
  overflow-y: auto;
  border-radius: 6px;
  background: var(--el-bg-color);
  padding: 8px;
}

.polling-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  font-size: 12px;
  border-radius: 4px;
  margin-bottom: 2px;
  transition: background-color 0.3s ease;

  &.success { background-color: var(--el-color-success-light-9); }
  &.warning { background-color: var(--el-color-warning-light-9); }
  &.error { background-color: var(--el-color-danger-light-9); }

  .polling-item-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .polling-item-error {
    color: var(--el-color-danger);
    font-size: 11px;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.confirm-env-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 12px;

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
