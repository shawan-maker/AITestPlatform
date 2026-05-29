<template>
  <div v-loading="loading" class="env-inline-global-editor">
    <SectionPanel :title="t('page.env.variables.global')">
      <ParamTable
        :can-add="canEdit"
        :add-label="t('page.env.variables.addParam')"
        @add="addRow"
      >
        <template #head>
          <th class="col-content">{{ t('common.name') }}</th>
          <th class="col-center">{{ t('page.env.paramType') }}</th>
          <th class="col-content">{{ t('page.env.configValue') }}</th>
          <th class="col-center">{{ t('page.env.encrypt') }}</th>
          <th class="col-content">{{ t('page.env.remark') }}</th>
          <th v-if="canEdit" class="col-center">{{ t('common.actions') }}</th>
        </template>
        <EnvParamRow
          v-for="(row, idx) in rows"
          :key="rowKey(row, idx)"
          :row="row"
          :can-edit="canEdit"
          :project-id="projectId"
          @update:row="(data) => updateRow(idx, data)"
          @delete="removeRow(idx)"
        />
      </ParamTable>
    </SectionPanel>

    <FormActionBar
      v-if="canEdit"
      :saving="saving"
      @save="saveAll"
      @cancel="cancelEdit"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  deleteGlobalConfig,
  listGlobalConfigs,
  replaceGlobalConfigs,
  updateGlobalConfig,
} from '@/api/environment'
import {
  buildUpdatePayload,
  createEmptyUiRow,
  toApiPayload,
  toUiRow,
} from '@/utils/envConfigUi'
import SectionPanel from '@/components/common/SectionPanel.vue'
import ParamTable from '@/components/common/ParamTable.vue'
import FormActionBar from '@/components/common/FormActionBar.vue'
import EnvParamRow from '@/components/env/EnvParamRow.vue'

const props = defineProps({
  projectId: { type: Number, required: true },
  canEdit: { type: Boolean, default: true },
})

const { t } = useI18n()
const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const deletedIds = ref([])
const snapshot = ref(null)

function rowKey(row, idx) {
  return row.id ?? `new-${idx}`
}

function cloneRows(list) {
  return list.map((r) => ({ ...r }))
}

function takeSnapshot() {
  snapshot.value = { rows: cloneRows(rows.value) }
  deletedIds.value = []
}

async function load() {
  loading.value = true
  try {
    const res = await listGlobalConfigs(props.projectId)
    const items = res.data.data?.items ?? res.data.data ?? []
    rows.value = items.map((item) => toUiRow(item))
    takeSnapshot()
  } finally {
    loading.value = false
  }
}

function addRow() {
  rows.value.push(createEmptyUiRow('envs'))
}

function updateRow(idx, data) {
  rows.value[idx] = { ...data }
}

function removeRow(idx) {
  const row = rows.value[idx]
  if (row.id && !row.isNew) deletedIds.value.push(row.id)
  rows.value.splice(idx, 1)
}

async function saveAll() {
  if (!props.canEdit) return
  saving.value = true
  try {
    for (const id of deletedIds.value) {
      await deleteGlobalConfig(id)
    }

    const existingRows = rows.value.filter((r) => r.id && !r.isNew && r.name?.trim())
    for (const row of existingRows) {
      await updateGlobalConfig(row.id, buildUpdatePayload(row))
    }

    const newRows = rows.value.filter((r) => r.isNew && r.name?.trim())
    if (newRows.length) {
      const res = await listGlobalConfigs(props.projectId)
      const current = res.data.data?.items ?? res.data.data ?? []
      const items = [
        ...current.map((i) => ({
          name: i.name,
          config_type: i.config_type,
          value: i.value === '***' ? '' : i.value,
          remark: i.remark,
        })),
        ...newRows.map((r) => toApiPayload(r)),
      ]
      await replaceGlobalConfigs(props.projectId, { items })
    }

    ElMessage.success(t('common.saved'))
    await load()
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  if (!snapshot.value) return
  rows.value = cloneRows(snapshot.value.rows)
  deletedIds.value = []
}

watch(() => props.projectId, load, { immediate: true })
</script>

<style scoped>
.env-inline-global-editor {
  max-width: 100%;
  overflow-x: hidden;
}
</style>
