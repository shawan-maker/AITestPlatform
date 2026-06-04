<template>
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
    <el-form v-if="step === 'form'" label-width="100px">
      <el-form-item :label="t('page.agent.prompt')">
        <el-input v-model="userPrompt" type="textarea" :rows="3" :placeholder="t('page.agent.promptPlaceholder')" />
      </el-form-item>
      <el-form-item :label="t('page.apiCases.selectEnv')">
        <EnvironmentSelect v-model="environmentId" />
      </el-form-item>
    </el-form>

    <div v-else v-loading="previewLoading" class="case-preview-body" :style="{ maxHeight: `${bodyMaxHeight}px` }">
      <el-alert v-if="sessionError" type="error" :title="sessionError" show-icon :closable="false" />
      <el-checkbox-group v-else v-model="selectedIndexes">
        <div v-for="(item, index) in baseCases" :key="index" class="case-row">
          <el-checkbox :label="index">{{ item.name || `Case ${index + 1}` }}</el-checkbox>
          <ul v-if="item.steps?.length">
            <li v-for="(step, si) in item.steps" :key="si">{{ step }}</li>
          </ul>
        </div>
      </el-checkbox-group>
      <el-empty v-if="!previewLoading && !baseCases.length && !sessionError" :description="t('page.agent.noPreview')" />
      <el-form-item v-if="baseCases.length" :label="t('page.apiCases.selectEnv')" style="margin-top: 16px">
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
        <el-button type="primary" :loading="confirming" :disabled="!canConfirm" @click="runConfirm">
          {{ t('common.confirm') }}
        </el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { confirmCaseGeneration, generateCasePreview } from '@/api/apiTest'
import { useContentDialog } from '@/composables/useContentDialog'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  interfaceId: { type: Number, required: true },
})

const emit = defineEmits(['update:modelValue', 'confirmed'])

const { t } = useI18n()
const { dialogWidth, dialogTop, dialogClass, bodyMaxHeight } = useContentDialog(220)

const step = ref('form')
const userPrompt = ref('')
const environmentId = ref(null)
const confirmEnvId = ref(null)
const previewLoading = ref(false)
const confirming = ref(false)
const sessionId = ref(null)
const baseCases = ref([])
const selectedIndexes = ref([])
const sessionError = ref('')

const canConfirm = computed(() => Boolean(confirmEnvId.value && selectedIndexes.value.length && sessionId.value))

watch(
  () => props.modelValue,
  (open) => {
    if (open) reset()
  },
)

function reset() {
  step.value = 'form'
  userPrompt.value = ''
  environmentId.value = null
  confirmEnvId.value = null
  previewLoading.value = false
  confirming.value = false
  sessionId.value = null
  baseCases.value = []
  selectedIndexes.value = []
  sessionError.value = ''
}

async function runPreview() {
  previewLoading.value = true
  sessionError.value = ''
  try {
    const res = await generateCasePreview(props.interfaceId, {
      user_prompt: userPrompt.value || undefined,
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
    ElMessage.success(t('page.agent.saved'))
    emit('confirmed')
    emit('update:modelValue', false)
  } finally {
    confirming.value = false
  }
}
</script>

<style scoped lang="scss">
.case-preview-body {
  overflow: auto;
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
