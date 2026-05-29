<template>
  <div v-loading="loading" class="env-variable-detail app-card">
    <PageHeader :title="env?.name || env?.env_name || t('page.env.variables.title')">
      <template #actions>
        <el-button @click="router.push('/env/variables')">{{ t('common.back') }}</el-button>
        <el-button v-if="canEdit" @click="showCopy = true">{{ t('page.env.variables.copy') }}</el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab">
      <el-tab-pane :label="t('page.env.variables.tabConfigs')" name="configs">
        <EnvConfigEditor :environment-id="envId" :can-edit="canEdit" />
      </el-tab-pane>
      <el-tab-pane :label="t('page.env.variables.tabSnapshots')" name="snapshots">
        <AppTable :data="snapshots">
          <AppTableColumn prop="name" variant="content" :label="t('common.name')" />
          <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="160">
            <template #default="{ row }">
              <el-button v-if="canEdit" link @click="activate(row)">{{ t('page.env.variables.activate') }}</el-button>
              <ConfirmDelete v-if="canEdit" @confirm="removeSnapshot(row)">
                <el-button link type="danger">{{ t('common.delete') }}</el-button>
              </ConfirmDelete>
            </template>
          </AppTableColumn>
        </AppTable>
        <el-button v-if="canEdit && snapshots.length < 3" style="margin-top: 12px" @click="createSnap">
          {{ t('page.env.variables.createSnapshot') }}
        </el-button>
        <el-alert v-else-if="snapshots.length >= 3" :title="t('page.env.variables.snapshotLimit')" type="warning" show-icon />
      </el-tab-pane>
      <el-tab-pane :label="t('page.env.variables.tabDebug')" name="debug">
        <MonacoJsonEditor v-if="testEnvJson" :model-value="testEnvJson" read-only :height="360" />
      </el-tab-pane>
      <el-tab-pane :label="t('page.env.variables.tabImportExport')" name="import">
        <el-button @click="showImportExport = true">{{ t('page.env.variables.importExport') }}</el-button>
      </el-tab-pane>
    </el-tabs>

    <EnvCopyDialog
      v-model="showCopy"
      :environment-id="envId"
      :default-name="env?.name || env?.env_name"
      @copied="load"
    />
    <EnvImportExportDialog
      v-model="showImportExport"
      :environment-id="envId"
      :env-name="env?.name || env?.env_name"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  activateSnapshot as activateSnapshotApi,
  createSnapshot,
  deleteSnapshot,
  getEnvironment,
  getTestEnvData,
  listSnapshots,
} from '@/api/environment'
import { usePermission } from '@/composables/usePermission'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import EnvConfigEditor from '@/components/env/EnvConfigEditor.vue'
import EnvCopyDialog from '@/components/env/EnvCopyDialog.vue'
import EnvImportExportDialog from '@/components/env/EnvImportExportDialog.vue'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const envId = computed(() => Number(route.params.environmentId))

const loading = ref(false)
const env = ref(null)
const snapshots = ref([])
const testEnvJson = ref('')
const activeTab = ref('configs')
const showCopy = ref(false)
const showImportExport = ref(false)

async function load() {
  loading.value = true
  try {
    const [envRes, snapRes, testRes] = await Promise.all([
      getEnvironment(envId.value),
      listSnapshots(envId.value),
      getTestEnvData(envId.value).catch(() => null),
    ])
    env.value = envRes.data.data
    snapshots.value = snapRes.data.data?.items ?? snapRes.data.data ?? []
    testEnvJson.value = testRes?.data?.data ? JSON.stringify(testRes.data.data, null, 2) : ''
  } finally {
    loading.value = false
  }
}

async function createSnap() {
  await createSnapshot(envId.value, { name: `snap_${Date.now()}` })
  ElMessage.success(t('common.saved'))
  load()
}

async function activate(row) {
  await activateSnapshotApi(row.id)
  ElMessage.success(t('common.saved'))
}

async function removeSnapshot(row) {
  await deleteSnapshot(row.id)
  ElMessage.success(t('common.deleted'))
  load()
}

onMounted(load)
</script>
