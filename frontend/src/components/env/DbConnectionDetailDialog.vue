<template>
  <el-dialog
    v-model="visible"
    :title="t('page.env.db.detail')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
  >
    <el-descriptions v-if="connection" :column="2" border>
      <el-descriptions-item :label="t('page.env.db.connectionName')">
        {{ connection.connection_name }}
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.env.db.serverName')">
        {{ connection.server_name }}
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.env.db.dbType')">
        {{ connection.db_type }}
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.env.db.host')">
        {{ connection.config?.host || '—' }}
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.env.db.port')">
        {{ connection.config?.port ?? '—' }}
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.env.db.username')">
        {{ connection.config?.username || '—' }}
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.env.db.password')">
        {{ connection.config?.password || '—' }}
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.env.db.databaseName')">
        {{ connection.config?.database_name || '—' }}
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.env.db.bindEnvironments')" :span="2">
        {{ boundLabel }}
      </el-descriptions-item>
      <el-descriptions-item :label="t('common.description')" :span="2">
        {{ connection.description || '—' }}
      </el-descriptions-item>
    </el-descriptions>

    <SectionPanel v-if="connection" :title="t('page.env.db.testLogs')" class="db-detail-dialog__logs">
      <DbTestLogTable :connection-id="connection.id" />
    </SectionPanel>

    <template #footer>
      <el-button @click="visible = false">{{ t('common.close') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDbConnection, listEnvironments } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { useHalfScreenDialog } from '@/composables/useContentDialog'
import SectionPanel from '@/components/common/SectionPanel.vue'
import DbTestLogTable from '@/components/env/DbTestLogTable.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  connectionId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()
const { withProjectParams } = useProjectScope()
const { dialogWidth, dialogTop, dialogClass } = useHalfScreenDialog(320)
const connection = ref(null)
const envMap = ref({})

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const boundLabel = computed(() => {
  const ids = connection.value?.environment_ids ?? []
  if (!ids.length) return t('page.env.db.unbound')
  return ids.map((id) => envMap.value[id] || id).join(', ')
})

async function load() {
  if (!props.connectionId) {
    connection.value = null
    return
  }
  const params = withProjectParams({ page: 1, page_size: 100 })
  const [detailRes, envRes] = await Promise.all([
    getDbConnection(props.connectionId),
    params ? listEnvironments(params) : Promise.resolve({ data: { data: { items: [] } } }),
  ])
  connection.value = { ...detailRes.data.data }
  const envs = envRes.data.data?.items ?? envRes.data.data ?? []
  envMap.value = Object.fromEntries(envs.map((e) => [e.id, e.env_name]))
}

watch(
  () => [visible.value, props.connectionId],
  ([v]) => {
    if (v) load()
  },
)
</script>

<style scoped lang="scss">
.db-detail-dialog__logs {
  margin-top: 20px;
}
</style>
