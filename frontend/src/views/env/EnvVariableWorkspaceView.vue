<template>
  <div class="env-variable-workspace app-card">
    <PageHeader :title="t('page.env.variables.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <SplitView v-else>
      <template #left>
        <CatalogTree v-model="selectedCatalogId" :nodes="catalogTree" />
        <el-button v-if="canEdit" size="small" style="margin-top: 8px" @click="createEnv">{{ t('page.env.variables.create') }}</el-button>
      </template>
      <template #right>
        <PaginatedTable :data="environments" :loading="loading" :show-pagination="false">
          <el-table-column prop="name" :label="t('common.name')">
            <template #default="{ row }">{{ row.name || row.env_name }}</template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="200">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push(`/env/variables/${row.id}`)">{{ t('common.view') }}</el-button>
              <el-button v-if="canEdit" link @click="openCopy(row)">{{ t('page.env.variables.copy') }}</el-button>
            </template>
          </el-table-column>
        </PaginatedTable>
      </template>
    </SplitView>

    <EnvCopyDialog
      v-model="showCopy"
      :environment-id="copyEnvId"
      :default-name="copyEnvName"
      @copied="loadEnvs"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { createEnvironment, getCatalogTree, listEnvironments } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SplitView from '@/components/common/SplitView.vue'
import CatalogTree from '@/components/tree/CatalogTree.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import EnvCopyDialog from '@/components/env/EnvCopyDialog.vue'

const { t } = useI18n()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()

const catalogTree = ref([])
const selectedCatalogId = ref(null)
const environments = ref([])
const loading = ref(false)
const showCopy = ref(false)
const copyEnvId = ref(null)
const copyEnvName = ref('')

async function loadTree() {
  const params = withProjectParams()
  if (!params) return
  const res = await getCatalogTree(params)
  catalogTree.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadEnvs() {
  const params = withProjectParams({ catalog_id: selectedCatalogId.value || undefined })
  if (!params) return
  loading.value = true
  try {
    const res = await listEnvironments(params)
    environments.value = res.data.data?.items ?? []
  } finally {
    loading.value = false
  }
}

async function createEnv() {
  const params = withProjectParams()
  await createEnvironment({ env_name: `env_${Date.now()}`, catalog_id: selectedCatalogId.value }, params)
  ElMessage.success(t('common.saved'))
  loadEnvs()
}

function openCopy(row) {
  copyEnvId.value = row.id
  copyEnvName.value = row.name || row.env_name
  showCopy.value = true
}

watch(selectedCatalogId, loadEnvs)
onMounted(() => { loadTree(); loadEnvs() })
</script>
