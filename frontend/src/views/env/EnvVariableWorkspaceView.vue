<template>
  <div class="env-variable-workspace app-card">
    <PageHeader :title="t('page.env.variables.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <SplitView v-else :initial-width="380" :min-width="300" :max-width="560" :drawer-title="t('page.env.variables.envSection')">
      <template #left>
        <EnvVariableSidebar
          v-model:keyword="keyword"
          :catalog-nodes="catalogTree"
          :environments="allEnvironments"
          :selection="selection"
          :selected-env-id="selectedEnvId"
          :selected-catalog-id="pendingCatalogId"
          :can-edit="canEdit"
          @select-global="selectGlobal"
          @select-catalog="onSelectCatalog"
          @select-env="selectEnv"
          @section-command="onSectionCommand"
          @catalog-command="onCatalogCommand"
          @env-command="onEnvCommand"
        />
      </template>
      <template #right>
        <EnvInlineGlobalEditor v-if="selection === 'global'" :project-id="projectId" :can-edit="canEdit" />
        <div v-else-if="selectedEnvId">
          <el-tabs v-model="detailTab">
            <el-tab-pane :label="t('page.env.variables.tabConfigs')" name="configs" lazy>
              <EnvInlineConfigEditor
                :environment-id="selectedEnvId"
                :project-id="projectId"
                :can-edit="canEdit"
                @env-updated="onEnvUpdated"
              />
            </el-tab-pane>
            <el-tab-pane :label="t('page.env.variables.tabBindings')" name="bindings" lazy>
              <EnvBindingPanel :environment-id="selectedEnvId" :can-edit="canEdit" />
            </el-tab-pane>
          </el-tabs>
        </div>
        <EmptyState v-else :title="t('page.env.variables.selectHint')" />
      </template>
    </SplitView>

    <EnvCopyDialog
      v-model="showCopy"
      :environment-id="copyEnvId"
      :default-name="copyEnvName"
      @copied="loadEnvs"
    />
    <EnvImportExportDialog
      v-model="showImportExport"
      :environment-id="importExportEnvId"
      :env-name="importExportEnvName"
      @imported="loadEnvs"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCatalog,
  createEnvironment,
  deleteCatalog,
  deleteEnvironment,
  exportEnvironment,
  getCatalogTree,
  listEnvironments,
} from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { useDownload } from '@/composables/useDownload'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SplitView from '@/components/common/SplitView.vue'
import EnvVariableSidebar from '@/components/env/EnvVariableSidebar.vue'
import EnvInlineConfigEditor from '@/components/env/EnvInlineConfigEditor.vue'
import EnvInlineGlobalEditor from '@/components/env/EnvInlineGlobalEditor.vue'
import EnvBindingPanel from '@/components/env/EnvBindingPanel.vue'
import EnvCopyDialog from '@/components/env/EnvCopyDialog.vue'
import EnvImportExportDialog from '@/components/env/EnvImportExportDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { downloadJson } = useDownload()

const catalogTree = ref([])
const allEnvironments = ref([])
const keyword = ref('')
const selection = ref('global')
const selectedEnvId = ref(null)
const pendingCatalogId = ref(null)
const detailTab = ref('configs')
const showCopy = ref(false)
const copyEnvId = ref(null)
const copyEnvName = ref('')
const showImportExport = ref(false)
const importExportEnvId = ref(null)
const importExportEnvName = ref('')

function syncRoute() {
  const q = { ...route.query }
  if (selection.value === 'global') {
    q.scope = 'global'
    delete q.environmentId
  } else if (selectedEnvId.value) {
    q.environmentId = String(selectedEnvId.value)
    delete q.scope
  }
  router.replace({ query: q })
}

function selectGlobal() {
  selection.value = 'global'
  selectedEnvId.value = null
  pendingCatalogId.value = null
  syncRoute()
}

function selectEnv(env) {
  selection.value = env.id
  selectedEnvId.value = env.id
  pendingCatalogId.value = env.catalog_id ?? null
  syncRoute()
}

function onSelectCatalog(catalogId) {
  pendingCatalogId.value = catalogId
}

async function loadTree() {
  const params = withProjectParams()
  if (!params) return
  const res = await getCatalogTree(params)
  catalogTree.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadEnvs() {
  const params = withProjectParams({ page: 1, page_size: 100 })
  if (!params) return
  const res = await listEnvironments(params)
  allEnvironments.value = res.data.data?.items ?? []
}

async function createEnv(catalogId = null) {
  const params = withProjectParams()
  if (!params) return
  const { value } = await ElMessageBox.prompt(t('page.env.variables.envName'), t('common.create'))
  if (!value?.trim()) return
  await createEnvironment(
    { env_name: value.trim(), catalog_id: catalogId ?? undefined },
    params,
  )
  ElMessage.success(t('common.saved'))
  await loadEnvs()
}

async function createCat(parentId = null) {
  const params = withProjectParams()
  if (!params) return
  const { value } = await ElMessageBox.prompt(t('page.env.variables.catalogName'), t('common.create'))
  if (!value?.trim()) return
  await createCatalog({ name: value.trim(), parent_id: parentId ?? undefined }, params)
  ElMessage.success(t('common.saved'))
  await loadTree()
}

function onSectionCommand(cmd) {
  if (cmd === 'catalog') createCat(null)
  else createEnv(null)
}

function findCatalogName(nodes, catalogId) {
  for (const node of nodes) {
    if (node.id === catalogId) return node.name
    if (node.children?.length) {
      const name = findCatalogName(node.children, catalogId)
      if (name) return name
    }
  }
  return ''
}

async function doDeleteCatalog(catalogId) {
  const name = findCatalogName(catalogTree.value, catalogId)
  await ElMessageBox.confirm(
    t('page.env.variables.confirmDeleteCatalog', { name: name || catalogId }),
    t('common.warning'),
    { type: 'warning' },
  )
  await deleteCatalog(catalogId)
  ElMessage.success(t('common.deleted'))
  if (pendingCatalogId.value === catalogId) pendingCatalogId.value = null
  await loadTree()
}

function onCatalogCommand(cmd, catalogId) {
  if (cmd === 'catalog') createCat(catalogId)
  else if (cmd === 'env') createEnv(catalogId)
  else if (cmd === 'delete') doDeleteCatalog(catalogId)
}

function openCopy(env) {
  copyEnvId.value = env.id
  copyEnvName.value = env.env_name
  showCopy.value = true
}

async function doExport(env) {
  const res = await exportEnvironment(env.id)
  downloadJson(res.data.data, `${env.env_name}.json`)
}

function doImport(env) {
  importExportEnvId.value = env.id
  importExportEnvName.value = env.env_name
  showImportExport.value = true
}

async function doDelete(env) {
  await ElMessageBox.confirm(t('common.confirmDelete'), t('common.warning'), { type: 'warning' })
  await deleteEnvironment(env.id)
  ElMessage.success(t('common.deleted'))
  if (selectedEnvId.value === env.id) selectGlobal()
  await loadEnvs()
}

function onEnvCommand(cmd, env) {
  if (cmd === 'copy') openCopy(env)
  else if (cmd === 'export') doExport(env)
  else if (cmd === 'import') doImport(env)
  else if (cmd === 'delete') doDelete(env)
}

function onEnvUpdated({ id, env_name }) {
  const env = allEnvironments.value.find((e) => e.id === id)
  if (env) env.env_name = env_name
}

function initFromRoute() {
  if (route.query.environmentId) {
    selectedEnvId.value = Number(route.query.environmentId)
    selection.value = selectedEnvId.value
  } else if (route.params.environmentId) {
    selectedEnvId.value = Number(route.params.environmentId)
    selection.value = selectedEnvId.value
  } else {
    selection.value = 'global'
    selectedEnvId.value = null
  }
}

watch(projectId, () => {
  loadTree()
  loadEnvs()
})

onMounted(() => {
  initFromRoute()
  loadTree()
  loadEnvs()
})
</script>
