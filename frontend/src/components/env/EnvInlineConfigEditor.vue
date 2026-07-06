<template>
  <div v-loading="loading" class="env-inline-config-editor">
    <SectionPanel :title="t('page.env.variables.basicInfo')">
      <div class="basic-info-stack">
        <div class="basic-info-field">
          <label class="basic-info-label">{{ t('page.env.variables.envName') }}</label>
          <el-input
            v-model="envName"
            class="basic-info-input"
            :disabled="!canEdit"
          />
        </div>
        <div class="basic-info-field">
          <label class="basic-info-label">base_url</label>
          <el-input
            v-model="baseUrl"
            class="basic-info-input"
            :disabled="!canEdit"
            placeholder="http://127.0.0.1"
          />
        </div>
      </div>
    </SectionPanel>

    <SectionPanel :title="t('configGroup.headers')">
      <ParamTable
        :can-add="canEdit"
        :add-label="t('page.env.variables.addParam')"
        @add="addHeaderRow"
      >
        <template #head>
          <th class="col-content">{{ t('common.name') }}</th>
          <th class="col-content">{{ t('page.env.configValue') }}</th>
          <th class="col-content">{{ t('page.env.remark') }}</th>
          <th v-if="canEdit" class="col-center">{{ t('common.actions') }}</th>
        </template>
        <EnvParamRow
          v-for="(row, idx) in headerRows"
          :key="rowKey(row, idx, 'h')"
          :row="row"
          :can-edit="canEdit"
          :project-id="projectId"
          :show-type="false"
          :show-encrypt="false"
          @update:row="(data) => updateHeaderRow(idx, data)"
          @delete="removeHeaderRow(idx)"
        />
      </ParamTable>
    </SectionPanel>

    <SectionPanel :title="t('configGroup.envs')">
      <ParamTable
        :can-add="canEdit"
        :add-label="t('page.env.variables.addParam')"
        @add="addEnvRow"
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
          v-for="(row, idx) in envRows"
          :key="rowKey(row, idx, 'e')"
          :row="row"
          :can-edit="canEdit"
          :project-id="projectId"
          @update:row="(data) => updateEnvRow(idx, data)"
          @delete="removeEnvRow(idx)"
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
  createConfig,
  deleteConfig,
  getConfigs,
  getEnvironment,
  updateConfig,
  updateEnvironment,
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
  environmentId: { type: Number, required: true },
  projectId: { type: Number, required: true },
  canEdit: { type: Boolean, default: true },
})

const emit = defineEmits(['env-updated'])

const { t } = useI18n()
const loading = ref(false)
const saving = ref(false)
const envName = ref('')
const baseUrl = ref('http://127.0.0.1')
const baseUrlConfigId = ref(null)
const headerRows = ref([])
const envRows = ref([])
const deletedHeaderIds = ref([])
const deletedEnvIds = ref([])
const snapshot = ref(null)

function rowKey(row, idx, prefix) {
  return `${prefix}-${row.id ?? idx}`
}

function cloneRows(rows) {
  return rows.map((r) => ({ ...r }))
}

function takeSnapshot() {
  snapshot.value = {
    envName: envName.value,
    baseUrl: baseUrl.value,
    baseUrlConfigId: baseUrlConfigId.value,
    headerRows: cloneRows(headerRows.value),
    envRows: cloneRows(envRows.value),
  }
  deletedHeaderIds.value = []
  deletedEnvIds.value = []
}

async function load() {
  loading.value = true
  try {
    const [envRes, cfgRes] = await Promise.all([
      getEnvironment(props.environmentId),
      getConfigs(props.environmentId),
    ])
    envName.value = envRes.data.data?.env_name ?? ''
    const configs = cfgRes.data.data?.items ?? cfgRes.data.data ?? []
    const baseCfg = configs.find((c) => c.config_group === 'base' && c.name === 'base_url')
    baseUrl.value = baseCfg?.value ?? 'http://127.0.0.1'
    baseUrlConfigId.value = baseCfg?.id ?? null
    headerRows.value = configs
      .filter((c) => c.config_group === 'headers')
      .map((c) => toUiRow(c, { headersOnly: true }))
    envRows.value = configs
      .filter((c) => c.config_group === 'envs')
      .map((c) => toUiRow(c))
    takeSnapshot()
  } finally {
    loading.value = false
  }
}

function addHeaderRow() {
  headerRows.value.push(createEmptyUiRow('headers'))
}

function addEnvRow() {
  envRows.value.push(createEmptyUiRow('envs'))
}

function updateHeaderRow(idx, data) {
  headerRows.value[idx] = { ...data }
}

function updateEnvRow(idx, data) {
  envRows.value[idx] = { ...data }
}

function removeHeaderRow(idx) {
  const row = headerRows.value[idx]
  if (row.id && !row.isNew) deletedHeaderIds.value.push(row.id)
  headerRows.value.splice(idx, 1)
}

function removeEnvRow(idx) {
  const row = envRows.value[idx]
  if (row.id && !row.isNew) deletedEnvIds.value.push(row.id)
  envRows.value.splice(idx, 1)
}

async function persistRows(rows, group) {
  const headersOnly = group === 'headers'
  for (const row of rows) {
    if (!row.name?.trim()) continue
    const payload = {
      config_group: group,
      ...toApiPayload(row, { headersOnly }),
    }
    if (row.id && !row.isNew) {
      await updateConfig(row.id, buildUpdatePayload(row, { headersOnly }))
    } else {
      await createConfig(props.environmentId, payload)
    }
  }
}

async function saveAll() {
  if (!props.canEdit) return
  saving.value = true
  try {
    const trimmedName = envName.value.trim()
    if (!trimmedName) {
      ElMessage.warning(t('validation.required'))
      return
    }
    if (trimmedName !== snapshot.value?.envName) {
      await updateEnvironment(props.environmentId, { env_name: trimmedName })
      emit('env-updated', { id: props.environmentId, env_name: trimmedName })
    }

    const urlValue = baseUrl.value.trim() || 'http://127.0.0.1'
    if (baseUrlConfigId.value) {
      await updateConfig(baseUrlConfigId.value, { value: urlValue })
    } else {
      const res = await createConfig(props.environmentId, {
        config_group: 'base',
        name: 'base_url',
        config_type: 'scalar',
        value: urlValue,
      })
      baseUrlConfigId.value = res.data.data?.id
    }

    for (const id of deletedHeaderIds.value) await deleteConfig(id)
    for (const id of deletedEnvIds.value) await deleteConfig(id)
    await persistRows(headerRows.value, 'headers')
    await persistRows(envRows.value, 'envs')

    ElMessage.success(t('common.saved'))
    await load()
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  const s = snapshot.value
  if (!s) return
  envName.value = s.envName
  baseUrl.value = s.baseUrl
  baseUrlConfigId.value = s.baseUrlConfigId
  headerRows.value = cloneRows(s.headerRows)
  envRows.value = cloneRows(s.envRows)
  deletedHeaderIds.value = []
  deletedEnvIds.value = []
}

watch(() => props.environmentId, load, { immediate: true })
</script>

<style scoped>
.env-inline-config-editor {
  max-width: 100%;
  overflow-x: hidden;
}

/* 基础信息：上下两行，与下方表格同宽对齐 */
.basic-info-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.basic-info-field {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 12px 16px;
  align-items: center;
  width: 100%;
}

.basic-info-label {
  margin: 0;
  padding-right: 8px;
  font-size: var(--font-size-base);
  color: var(--text-primary);
  text-align: right;
  white-space: nowrap;
}

.basic-info-input {
  width: 100%;
  min-width: 0;
}
</style>
