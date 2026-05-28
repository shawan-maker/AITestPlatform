<template>
  <div class="env-config-editor">
    <el-tabs v-model="activeGroup">
      <el-tab-pane v-for="g in CONFIG_GROUPS" :key="g" :label="t(`configGroup.${g}`)" :name="g">
        <el-table :data="groupItems(g)" border>
          <el-table-column prop="name" :label="t('common.name')" />
          <el-table-column prop="config_type" :label="t('page.env.configType')" width="100" />
          <el-table-column prop="value" :label="t('page.env.configValue')" min-width="160">
            <template #default="{ row }">{{ row.value ?? '—' }}</template>
          </el-table-column>
          <el-table-column prop="remark" :label="t('page.env.remark')" />
          <el-table-column v-if="canEdit" :label="t('common.actions')" width="120">
            <template #default="{ row }">
              <el-button link @click="editItem(row)">{{ t('common.edit') }}</el-button>
              <ConfirmDelete @confirm="removeItem(row)">
                <el-button link type="danger">{{ t('common.delete') }}</el-button>
              </ConfirmDelete>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-if="g === 'envs' && envsTotal > envsPageSize"
          v-model:current-page="envsPage"
          :page-size="envsPageSize"
          :total="envsTotal"
          layout="prev, pager, next"
          style="margin-top: 12px"
        />
        <el-button v-if="canEdit" size="small" style="margin-top: 12px" @click="openCreate(g)">
          {{ t('common.create') }}
        </el-button>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showForm" :title="formTitle" width="480px">
      <el-form :model="form" label-width="100px">
        <el-form-item :label="t('common.name')"><el-input v-model="form.name" /></el-form-item>
        <el-form-item :label="t('page.env.configType')">
          <el-select v-model="form.config_type">
            <el-option v-for="ct in CONFIG_TYPES" :key="ct" :label="ct" :value="ct" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('page.env.configValue')"><el-input v-model="form.value" /></el-form-item>
        <el-form-item :label="t('page.env.remark')"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="saveItem">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { createConfig, deleteConfig, getConfigs, updateConfig } from '@/api/environment'
import { CONFIG_GROUPS, CONFIG_TYPES } from '@/utils/constants'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'

const props = defineProps({
  environmentId: { type: Number, required: true },
  canEdit: { type: Boolean, default: true },
})

const emit = defineEmits(['updated'])
const { t } = useI18n()

const items = ref([])
const activeGroup = ref('base')
const envsPage = ref(1)
const envsPageSize = 20
const showForm = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = reactive({
  config_group: 'base',
  name: '',
  config_type: 'scalar',
  value: '',
  remark: '',
})

const formTitle = computed(() => (editingId.value ? t('common.edit') : t('common.create')))

const envsTotal = computed(() => items.value.filter((i) => i.config_group === 'envs').length)

function groupItems(group) {
  const filtered = items.value.filter((i) => i.config_group === group)
  if (group !== 'envs') return filtered
  const start = (envsPage.value - 1) * envsPageSize
  return filtered.slice(start, start + envsPageSize)
}

async function load() {
  const res = await getConfigs(props.environmentId)
  items.value = res.data.data?.items ?? res.data.data ?? []
}

function openCreate(group) {
  editingId.value = null
  form.config_group = group
  form.name = ''
  form.config_type = 'scalar'
  form.value = ''
  form.remark = ''
  showForm.value = true
}

function editItem(row) {
  editingId.value = row.id
  form.config_group = row.config_group
  form.name = row.name
  form.config_type = row.config_type
  form.value = row.value === '***' ? '' : (row.value ?? '')
  form.remark = row.remark ?? ''
  showForm.value = true
}

async function saveItem() {
  saving.value = true
  try {
    const payload = {
      config_group: form.config_group,
      name: form.name,
      config_type: form.config_type,
      value: form.value,
      remark: form.remark || undefined,
    }
    if (editingId.value) {
      await updateConfig(editingId.value, payload)
    } else {
      await createConfig(props.environmentId, payload)
    }
    ElMessage.success(t('common.saved'))
    showForm.value = false
    await load()
    emit('updated')
  } finally {
    saving.value = false
  }
}

async function removeItem(row) {
  await deleteConfig(row.id)
  ElMessage.success(t('common.deleted'))
  await load()
  emit('updated')
}

watch(() => props.environmentId, load, { immediate: true })
</script>
