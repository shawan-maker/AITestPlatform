<template>
  <el-dialog v-model="visible" :title="t('page.env.function.debug')" width="640px">
    <el-form label-width="100px">
      <el-form-item :label="t('page.env.function.method')">
        <el-select v-model="selectedMethod" filterable style="width: 100%">
          <el-option v-for="m in methods" :key="m" :label="m" :value="m" />
        </el-select>
      </el-form-item>
      <el-form-item v-for="p in varParams" :key="p" :label="p">
        <el-input v-model="paramValues[p]" :placeholder="t('page.env.function.varPlaceholder')" />
      </el-form-item>
    </el-form>
    <div v-if="result" class="debug-result">
      <pre>{{ JSON.stringify(result, null, 2) }}</pre>
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
import { validateFunctionFile } from '@/api/environment'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  file: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const methods = ref([])
const selectedMethod = ref('')
const paramValues = reactive({})
const result = ref(null)
const running = ref(false)

const varParams = computed(() => {
  const src = props.file?.source_code ?? ''
  const matches = src.match(/\$([a-zA-Z_][a-zA-Z0-9_]*)/g) ?? []
  return [...new Set(matches.map((m) => m.slice(1)))]
})

function parseMethods(source) {
  if (!source) return []
  const found = new Set()
  const re = /^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/gm
  let m
  while ((m = re.exec(source)) !== null) {
    found.add(m[1])
  }
  return [...found]
}

watch(
  () => props.file,
  (f) => {
    methods.value = parseMethods(f?.source_code ?? '')
    selectedMethod.value = methods.value[0] ?? ''
    result.value = null
    Object.keys(paramValues).forEach((k) => delete paramValues[k])
  },
  { immediate: true },
)

watch(varParams, (params) => {
  params.forEach((p) => {
    if (!(p in paramValues)) paramValues[p] = ''
  })
}, { immediate: true })

async function runDebug() {
  if (!props.file) return
  running.value = true
  try {
    const res = await validateFunctionFile({
      file_name: props.file.file_name ?? props.file.name,
      source_code: props.file.source_code ?? '',
    })
    result.value = {
      valid: res.data.data?.valid ?? true,
      method: selectedMethod.value,
      params: { ...paramValues },
      note: t('page.env.function.debugNote'),
    }
    ElMessage.success(t('page.env.function.valid'))
  } finally {
    running.value = false
  }
}
</script>

<style scoped lang="scss">
.debug-result {
  margin-top: 12px;
  padding: 12px;
  background: var(--el-fill-color-light);
  max-height: 200px;
  overflow: auto;
}
</style>
