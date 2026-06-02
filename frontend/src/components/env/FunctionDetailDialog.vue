<template>
  <el-dialog
    v-model="visible"
    :title="t('page.env.function.detail')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
  >
    <el-descriptions v-if="file" :column="1" border>
      <el-descriptions-item :label="t('page.env.function.fileName')">{{ file.file_name }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.env.function.bindEnvironments')">
        {{ boundLabel }}
      </el-descriptions-item>
    </el-descriptions>
    <div v-if="file" class="source-block">
      <MonacoJsonEditor v-model="file.source_code" language="python" read-only :height="editorHeight" />
    </div>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.close') }}</el-button>
      <el-button type="primary" @click="$emit('debug', file)">{{ t('page.env.function.debug') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getFunctionFile, listEnvironments } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { useHalfScreenDialog } from '@/composables/useHalfScreenDialog'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  fileId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'debug'])
const { t } = useI18n()
const { withProjectParams } = useProjectScope()
const { editorHeight, dialogWidth, dialogTop, dialogClass } = useHalfScreenDialog(200)
const file = ref(null)
const envMap = ref({})

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const boundLabel = computed(() => {
  const ids = file.value?.environment_ids ?? []
  if (!ids.length) return t('page.env.db.unbound')
  return ids.map((id) => envMap.value[id] || id).join(', ')
})

async function load() {
  if (!props.fileId) {
    file.value = null
    return
  }
  const params = withProjectParams({ page: 1, page_size: 100 })
  const [detailRes, envRes] = await Promise.all([
    getFunctionFile(props.fileId),
    params ? listEnvironments(params) : Promise.resolve({ data: { data: { items: [] } } }),
  ])
  file.value = { ...detailRes.data.data }
  const envs = envRes.data.data?.items ?? envRes.data.data ?? []
  envMap.value = Object.fromEntries(envs.map((e) => [e.id, e.env_name]))
}

watch(
  () => [visible.value, props.fileId],
  ([v]) => {
    if (v) load()
  },
)
</script>

<style scoped lang="scss">
.source-block {
  margin-top: 16px;
}
</style>
