<template>
  <el-dialog :close-on-click-modal="false" v-model="visible" :title="t('page.env.variables.importExport')" width="520px">
    <el-tabs v-model="tab">
      <el-tab-pane :label="t('common.export')" name="export">
        <el-button @click="doExport">{{ t('common.export') }} JSON</el-button>
      </el-tab-pane>
      <el-tab-pane :label="t('common.import')" name="import">
        <el-form label-width="auto">
          <el-form-item :label="t('page.env.variables.importById')">
            <el-input-number v-model="importEnvId" :min="1" />
            <el-button style="margin-left: 8px" @click="doImportById">{{ t('common.import') }}</el-button>
          </el-form-item>
          <el-form-item :label="t('page.env.variables.importFile')">
            <input ref="fileInput" type="file" accept=".json" hidden @change="onFileImport" />
            <el-button @click="fileInput?.click()">{{ t('common.upload') }}</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { exportEnvironment, importEnvironment, importEnvironmentFile } from '@/api/environment'
import { useDownload } from '@/composables/useDownload'
import { useProjectScope } from '@/composables/useProjectScope'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  environmentId: { type: Number, required: true },
  envName: { type: String, default: 'env' },
})

const emit = defineEmits(['update:modelValue', 'imported'])
const { t } = useI18n()
const { downloadFromResponse } = useDownload()
const { withProjectParams } = useProjectScope()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const tab = ref('export')
const importEnvId = ref(null)
const fileInput = ref()

async function doExport() {
  const res = await exportEnvironment(props.environmentId)
  downloadFromResponse(res, `${props.envName}.json`)
}

async function doImportById() {
  const params = withProjectParams()
  await importEnvironment({ source_environment_id: importEnvId.value, ...params })
  ElMessage.success(t('common.saved'))
  emit('imported')
}

async function onFileImport(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  const params = withProjectParams()
  await importEnvironmentFile(fd, params)
  ElMessage.success(t('common.uploaded'))
  emit('imported')
}
</script>
