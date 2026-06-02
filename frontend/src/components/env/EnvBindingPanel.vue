<template>
  <div v-loading="loading" class="env-binding-panel">
    <SectionPanel :title="t('page.env.variables.bindDb')">
      <el-select
        v-model="draftDbIds"
        multiple
        filterable
        :disabled="!canEdit"
        style="width: 100%"
        :placeholder="t('page.env.variables.bindDbHint')"
      >
        <el-option
          v-for="db in dbOptions"
          :key="db.id"
          :label="db.connection_name"
          :value="db.id"
        />
      </el-select>
    </SectionPanel>

    <SectionPanel :title="t('page.env.variables.bindFunctions')">
      <AppTable :data="draftFunctionRows">
        <AppTableColumn prop="file_name" variant="content" :label="t('common.name')" />
        <AppTableColumn v-if="canEdit" actions variant="fixed" :label="t('common.actions')" :width="200">
          <template #default="{ $index }">
            <el-button link :disabled="$index === 0" @click="moveUp($index)">↑</el-button>
            <el-button link :disabled="$index === draftFunctionRows.length - 1" @click="moveDown($index)">↓</el-button>
            <el-button link type="danger" @click="removeFunction($index)">{{ t('common.delete') }}</el-button>
          </template>
        </AppTableColumn>
      </AppTable>
      <el-select
        v-if="canEdit"
        v-model="addFunctionId"
        filterable
        clearable
        style="width: 100%; margin-top: 12px"
        :placeholder="t('page.env.variables.addFunction')"
        @change="onAddFunction"
      >
        <el-option
          v-for="fn in availableFunctions"
          :key="fn.id"
          :label="fn.file_name"
          :value="fn.id"
        />
      </el-select>
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
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  bindDbConnections,
  bindFunctionFiles,
  getEnvironment,
  listDbConnections,
  listFunctionFiles,
} from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import SectionPanel from '@/components/common/SectionPanel.vue'
import FormActionBar from '@/components/common/FormActionBar.vue'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'

const props = defineProps({
  environmentId: { type: Number, required: true },
  canEdit: { type: Boolean, default: true },
})

const { t } = useI18n()
const { withProjectParams } = useProjectScope()
const loading = ref(false)
const saving = ref(false)
const draftDbIds = ref([])
const draftFunctionRows = ref([])
const dbOptions = ref([])
const allFunctions = ref([])
const addFunctionId = ref(null)
const snapshot = ref(null)

const availableFunctions = computed(() =>
  allFunctions.value.filter((fn) => !draftFunctionRows.value.some((r) => r.id === fn.id)),
)

function takeSnapshot() {
  snapshot.value = {
    dbIds: [...draftDbIds.value],
    functions: draftFunctionRows.value.map((f) => ({ ...f })),
  }
}

async function loadOptions() {
  const params = withProjectParams({ page: 1, page_size: 100 })
  if (!params) return
  const [dbRes, fnRes, envRes] = await Promise.all([
    listDbConnections(params),
    listFunctionFiles(params),
    getEnvironment(props.environmentId),
  ])
  dbOptions.value = dbRes.data.data?.items ?? []
  allFunctions.value = fnRes.data.data?.items ?? []
  const env = envRes.data.data
  draftDbIds.value = [...(env?.db_connection_ids ?? [])]
  const bindings = env?.function_bindings ?? []
  const fnMap = Object.fromEntries(allFunctions.value.map((f) => [f.id, f]))
  if (bindings.length) {
    draftFunctionRows.value = bindings.map((b) => fnMap[b.function_file_id]).filter(Boolean)
  } else {
    draftFunctionRows.value = (env?.function_file_ids ?? [])
      .map((id) => fnMap[id])
      .filter(Boolean)
  }
  takeSnapshot()
}

async function load() {
  loading.value = true
  try {
    await loadOptions()
  } finally {
    loading.value = false
  }
}

function onAddFunction(id) {
  if (!id) return
  const fn = allFunctions.value.find((f) => f.id === id)
  if (fn) draftFunctionRows.value.push(fn)
  addFunctionId.value = null
}

function removeFunction(idx) {
  draftFunctionRows.value.splice(idx, 1)
}

function moveUp(idx) {
  if (idx <= 0) return
  const rows = draftFunctionRows.value
  ;[rows[idx - 1], rows[idx]] = [rows[idx], rows[idx - 1]]
}

function moveDown(idx) {
  const rows = draftFunctionRows.value
  if (idx >= rows.length - 1) return
  ;[rows[idx], rows[idx + 1]] = [rows[idx + 1], rows[idx]]
}

async function saveAll() {
  saving.value = true
  try {
    await bindDbConnections(props.environmentId, { db_connection_ids: draftDbIds.value })
    await bindFunctionFiles(props.environmentId, {
      items: draftFunctionRows.value.map((fn, idx) => ({
        function_file_id: fn.id,
        sort_order: idx,
      })),
    })
    ElMessage.success(t('common.saved'))
    await load()
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  if (!snapshot.value) return
  draftDbIds.value = [...snapshot.value.dbIds]
  draftFunctionRows.value = snapshot.value.functions.map((f) => ({ ...f }))
  addFunctionId.value = null
}

watch(() => props.environmentId, load, { immediate: true })
</script>

<style scoped>
.env-binding-panel {
  max-width: 100%;
  overflow-x: hidden;
}
</style>
