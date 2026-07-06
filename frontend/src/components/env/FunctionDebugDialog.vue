<template>
  <el-dialog :close-on-click-modal="false"
    v-model="visible"
    :title="t('page.env.function.debug')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
  >
    <el-form label-width="auto">
      <el-form-item :label="t('page.env.function.method')">
        <el-select v-model="selectedMethod" filterable style="width: 100%" @change="onMethodChange">
          <el-option v-for="m in methods" :key="m.name" :label="m.name" :value="m.name" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="needsEnvironment" :label="t('page.env.function.selectEnvironment')">
        <el-select v-model="environmentId" filterable clearable style="width: 100%">
          <el-option v-for="env in envOptions" :key="env.id" :label="env.env_name" :value="env.id" />
        </el-select>
      </el-form-item>
      <el-form-item v-for="p in methodParams" :key="p" :label="p">
        <el-input v-model="paramValues[p]" :placeholder="t('page.env.function.paramHint')" />
      </el-form-item>
    </el-form>
    <div v-if="result" class="debug-result">
      <div class="debug-section">
        <div class="debug-section__label">result</div>
        <pre>{{ formatSectionValue(result.result) }}</pre>
      </div>
      <div class="debug-section">
        <div class="debug-section__label">print_out</div>
        <pre>{{ formatSectionValue(result.print_out, true) }}</pre>
      </div>
      <div class="debug-section">
        <div class="debug-section__label">error</div>
        <pre :class="{ 'is-error': !!result.error }">{{ formatSectionValue(result.error, true) }}</pre>
      </div>
    </div>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="running" @click="runDebug">{{ t('page.apiCases.debugRun') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { debugFunctionFile, listEnvironments } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { useContentDialog } from '@/composables/useContentDialog'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  file: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()
const { dialogWidth, dialogTop, dialogClass } = useContentDialog()
const { withProjectParams } = useProjectScope()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const methods = ref([])
const selectedMethod = ref('')
const paramValues = reactive({})
const result = ref(null)
const running = ref(false)
const environmentId = ref(null)
const envOptions = ref([])

const VAR_PATTERN = /\$([a-zA-Z_][a-zA-Z0-9_]*)/

const sourceHasVar = computed(() => {
  const src = props.file?.source_code ?? ''
  return VAR_PATTERN.test(src)
})

const paramsHaveVar = computed(() =>
  Object.values(paramValues).some((v) => typeof v === 'string' && v.startsWith('$') && v.length > 1),
)

const needsEnvironment = computed(() => sourceHasVar.value || paramsHaveVar.value)

const methodParams = computed(() => {
  const m = methods.value.find((item) => item.name === selectedMethod.value)
  return m?.params ?? []
})

function parseMethods(source) {
  if (!source) return []
  const found = []
  const re = /^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)/gm
  let match
  while ((match = re.exec(source)) !== null) {
    const params = match[2]
      .split(',')
      .map((p) => p.trim().split('=')[0].trim())
      .filter((p) => p && p !== 'self')
    found.push({ name: match[1], params })
  }
  return found
}

function parseParamInput(raw) {
  if (raw == null || raw === '') return raw
  const text = String(raw).trim()
  if (text.startsWith('$') && text.length > 1) return text
  try {
    return JSON.parse(text)
  } catch {
    if (/^-?\d+$/.test(text)) return Number.parseInt(text, 10)
    if (/^-?\d+\.\d+$/.test(text)) return Number.parseFloat(text)
    if (text === 'true') return true
    if (text === 'false') return false
    if (text === 'null') return null
    return text
  }
}

function formatSectionValue(value, plainText = false) {
  if (value == null || value === '') return '—'
  if (plainText || typeof value === 'string') return String(value)
  return JSON.stringify(value, null, 2)
}

function onMethodChange() {
  Object.keys(paramValues).forEach((k) => delete paramValues[k])
  methodParams.value.forEach((p) => {
    paramValues[p] = ''
  })
}

async function loadEnvironments() {
  const params = withProjectParams({ page: 1, page_size: 100 })
  if (!params) return
  const res = await listEnvironments(params)
  envOptions.value = res.data.data?.items ?? res.data.data ?? []
}

watch(
  () => props.file,
  (f) => {
    methods.value = parseMethods(f?.source_code ?? '')
    selectedMethod.value = methods.value[0]?.name ?? ''
    onMethodChange()
    result.value = null
    environmentId.value = null
  },
  { immediate: true },
)

watch(visible, (v) => {
  if (v) loadEnvironments()
})

async function runDebug() {
  if (!props.file?.id || !selectedMethod.value) return
  if (needsEnvironment.value && !environmentId.value) {
    ElMessage.warning(t('page.env.function.envRequired'))
    return
  }
  running.value = true
  try {
    const parsedParams = {}
    for (const [key, value] of Object.entries(paramValues)) {
      parsedParams[key] = parseParamInput(value)
    }
    const payload = {
      method_name: selectedMethod.value,
      params: parsedParams,
    }
    if (environmentId.value) payload.environment_id = environmentId.value
    const res = await debugFunctionFile(props.file.id, payload)
    result.value = res.data.data
    if (result.value?.success) ElMessage.success(t('page.env.function.debugOk'))
    else ElMessage.error(result.value?.error || t('common.failed'))
  } finally {
    running.value = false
  }
}
</script>

<style scoped lang="scss">
.debug-result {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 320px;
  overflow: auto;
}

.debug-section {
  padding: 10px 12px;
  background: var(--el-fill-color-light);
  border-radius: 4px;

  &__label {
    margin-bottom: 6px;
    font-size: 12px;
    font-weight: 600;
    color: var(--el-text-color-secondary);
    text-transform: lowercase;
  }

  pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
    font-family: var(--el-font-family-monospace, monospace);
    font-size: 13px;

    &.is-error {
      color: var(--el-color-danger);
    }
  }
}
</style>
