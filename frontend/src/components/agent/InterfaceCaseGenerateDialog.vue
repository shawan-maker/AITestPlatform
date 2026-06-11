<template>
  <!-- v2-Q2/Q3: 移除user_prompt输入框，直接生成preview；confirm后5s轮询进度 -->
  <el-dialog
    :model-value="modelValue"
    :title="t('page.apiCases.generateCases')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
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

    <div v-else-if="step === 'preview'" v-loading="previewLoading" class="case-preview-body" :style="{ maxHeight: `${bodyMaxHeight}px` }">
      <el-alert v-if="sessionError" type="error" :title="sessionError" show-icon :closable="false" />
      <template v-else>
        <!-- v2-Q3: 轮询中显示进度 -->
        <div v-if="pollingStatus === 'running'" class="polling-status">
          <el-progress :percentage="pollingProgress" :stroke-width="8" />
          <span style="font-size: 12px; color: var(--el-text-color-secondary)">
            正在执行预验证... ({{ pollingCompleted }}/{{ pollingTotal }})
          </span>
        </div>
        <el-checkbox-group v-model="selectedIndexes">
          <div v-for="(item, index) in baseCases" :key="index" class="case-row">
            <el-checkbox :label="index">{{ item.name || `Case ${index + 1}` }}</el-checkbox>
            <ul v-if="item.steps?.length">
              <li v-for="(step, si) in item.steps" :key="si">{{ step }}</li>
            </ul>
          </div>
        </el-checkbox-group>
        <el-empty v-if="!previewLoading && !baseCases.length && !sessionError" :description="t('page.agent.noPreview')" />
      </template>
      <el-form-item v-if="baseCases.length && step === 'preview'" :label="t('page.apiCases.selectEnv')" style="margin-top: 16px">
        <EnvironmentSelect v-model="confirmEnvId" />
      </el-form-item>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
      <el-button v-if="step === 'form'" type="primary" :loading="previewLoading" @click="runPreview">
        {{ t('page.agent.generate') }}
      </el-button>
      <template v-else>
        <el-button @click="step = 'form'">{{ t('common.back') }}</el-button>
        <el-button
          type="primary"
          :loading="confirming || pollingStatus === 'running'"
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
const { dialogWidth, dialogTop, dialogClass, bodyMaxHeight } = useContentDialog(220)

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
let pollTimer = null

const canConfirm = computed(() => {
  if (pollingStatus.value === 'running') return false
  return Boolean(confirmEnvId.value && selectedIndexes.value.length && sessionId.value)
})

watch(
  () => props.modelValue,
  (open) => {
    if (open) reset()
  },
)

function reset() {
  stopPolling()
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
}

async function runPreview() {
  previewLoading.value = true
  sessionError.value = ''
  try {
    // v2-Q2: 不再传user_prompt参数
    const res = await generateCasePreview(props.interfaceId, {
      environment_id: environmentId.value || undefined,
    })
    const data = res.data.data
    sessionId.value = data.session_id
    baseCases.value = data.base_cases ?? []
    selectedIndexes.value = baseCases.value.map((_, i) => i)
    confirmEnvId.value = environmentId.value
    step.value = 'preview'
    if (!baseCases.value.length) {
      sessionError.value = t('page.agent.noPreview')
    }
  } catch (err) {
    sessionError.value = err.message || t('common.requestFailed')
  } finally {
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
  pollingTotal.value = baseCases.value.length

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
          ElMessage.success(t('page.agent.saved'))
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
          pollingTotal.value = progress.total || baseCases.value.length
          pollingProgress.value =
            pollingTotal.value > 0
              ? Math.round((pollingCompleted.value / pollingTotal.value) * 100)
              : 0
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

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped lang="scss">
.generate-form {
  padding: 10px 0;
}

.case-preview-body {
  overflow: auto;
}

.polling-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 8px;
}

.case-row {
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 13px;

  ul {
    margin: 4px 0 0;
    padding-left: 24px;
    color: var(--el-text-color-secondary);
  }
}
</style>
