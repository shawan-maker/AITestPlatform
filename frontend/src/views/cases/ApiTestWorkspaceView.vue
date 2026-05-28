<template>
  <div class="api-workspace app-card">
    <PageHeader :title="t('page.apiCases.title')">
      <template #actions>
        <el-button v-if="projectId && selectedCatalogId" @click="showImport = true">{{ t('page.apiCases.importInterfaces') }}</el-button>
        <el-button v-if="canEdit && selectedCatalogId" type="primary" @click="openCreateInterface">{{ t('page.apiCases.createInterface') }}</el-button>
      </template>
    </PageHeader>
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <SplitView v-else>
      <template #left>
        <CatalogTree v-model="selectedCatalogId" :nodes="catalogTree" />
      </template>
      <template #right>
        <div v-if="interfaces.length" class="interface-bar">
          <el-select v-model="selectedInterfaceId" style="width: 280px">
            <el-option v-for="i in interfaces" :key="i.id" :label="`${i.method} ${i.path}`" :value="i.id" />
          </el-select>
          <template v-if="selectedInterfaceId && canEdit">
            <el-button link @click="openEditInterface">{{ t('common.edit') }}</el-button>
            <el-button link type="danger" @click="removeInterface">{{ t('common.delete') }}</el-button>
            <el-button link @click="copyCurrentInterface">{{ t('common.copy') }}</el-button>
          </template>
        </div>
        <EmptyState v-else-if="selectedCatalogId" :title="t('page.apiCases.noInterface')" />
        <el-tabs v-if="selectedInterfaceId" v-model="activeTab">
          <el-tab-pane :label="t('page.apiCases.tabDebug')" name="debug">
            <el-form inline>
              <EnvironmentSelect v-model="environmentId" />
              <el-button type="primary" :loading="debugging" @click="runDebug">{{ t('page.apiCases.debugRun') }}</el-button>
              <el-button @click="saveTemplate">{{ t('common.save') }}</el-button>
              <el-button @click="fillFromDoc">{{ t('page.apiCases.fillFromDoc') }}</el-button>
            </el-form>
            <div class="editor-row">
              <div class="editor-col">
                <div class="editor-label">{{ t('page.apiCases.request') }}</div>
                <MonacoJsonEditor v-model="requestJson" :height="280" />
              </div>
              <div class="editor-col">
                <div class="editor-label">{{ t('page.apiCases.response') }}</div>
                <MonacoJsonEditor v-model="responseJson" read-only :height="220" />
              </div>
            </div>
            <div class="editor-label">{{ t('page.apiCases.assertions') }}</div>
            <MonacoJsonEditor v-model="assertionsJson" :height="160" />
          </el-tab-pane>
          <el-tab-pane :label="t('page.apiCases.tabDocDep')" name="doc-dep">
            <div class="doc-dep-toolbar">
              <el-button :loading="reanalyzing" @click="reanalyze">{{ t('page.apiCases.reanalyze') }}</el-button>
              <el-button @click="loadDocPreview">{{ t('page.apiCases.refreshDoc') }}</el-button>
            </div>
            <div class="editor-label">{{ t('page.apiCases.docPreview') }}</div>
            <MonacoJsonEditor v-if="docPreviewJson" :model-value="docPreviewJson" read-only :height="200" />
            <div class="editor-label">{{ t('page.apiCases.dependencies') }}</div>
            <MonacoJsonEditor v-if="dependencies" :model-value="depJson" read-only :height="240" />
          </el-tab-pane>
          <el-tab-pane :label="t('page.apiCases.tabCases')" name="case">
            <div class="case-toolbar">
              <el-button link type="primary" @click="router.push('/agent?tab=api')">{{ t('page.apiCases.agentGenerate') }}</el-button>
            </div>
            <h4>{{ t('page.apiCases.preconditionCases') }}</h4>
            <PaginatedTable :data="preconditionCases" :loading="casesLoading" :show-pagination="false">
              <el-table-column prop="title" :label="t('common.name')">
                <template #default="{ row }">{{ row.title || row.name }}</template>
              </el-table-column>
              <el-table-column :label="t('common.actions')" width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="router.push(`/cases/api/cases/${row.id}`)">{{ t('common.view') }}</el-button>
                </template>
              </el-table-column>
            </PaginatedTable>
            <h4 style="margin-top: 16px">{{ t('page.apiCases.mainCases') }}</h4>
            <PaginatedTable :data="mainCases" :loading="casesLoading" :show-pagination="false">
              <el-table-column prop="title" :label="t('common.name')">
                <template #default="{ row }">{{ row.title || row.name }}</template>
              </el-table-column>
              <el-table-column :label="t('common.actions')" width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="router.push(`/cases/api/cases/${row.id}`)">{{ t('common.view') }}</el-button>
                </template>
              </el-table-column>
            </PaginatedTable>
          </el-tab-pane>
        </el-tabs>
      </template>
    </SplitView>

    <ImportInterfacesWizard v-model="showImport" :catalog-id="selectedCatalogId" @imported="loadInterfaces" />
    <InterfaceFormDrawer
      v-model="showInterfaceForm"
      :catalog-id="selectedCatalogId"
      :interface-data="editingInterface"
      @saved="loadInterfaces"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  copyInterface,
  debugRunInterface,
  deleteInterface,
  fillDebugFromDoc,
  getApiCatalogTree,
  getDebugTemplate,
  getDocPreview,
  listApiCases,
  listDependencies,
  listInterfacesByCatalog,
  reanalyzeDependencies,
  saveDebugTemplate,
} from '@/api/apiTest'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SplitView from '@/components/common/SplitView.vue'
import CatalogTree from '@/components/tree/CatalogTree.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'
import ImportInterfacesWizard from '@/components/api-test/ImportInterfacesWizard.vue'
import InterfaceFormDrawer from '@/components/api-test/InterfaceFormDrawer.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()

const catalogTree = ref([])
const selectedCatalogId = ref(Number(route.query.catalogId) || null)
const interfaces = ref([])
const selectedInterfaceId = ref(Number(route.query.interfaceId) || null)
const activeTab = ref(route.query.tab || 'debug')
const environmentId = ref(null)
const requestJson = ref('{}')
const responseJson = ref('')
const assertionsJson = ref('[]')
const debugging = ref(false)
const reanalyzing = ref(false)
const dependencies = ref(null)
const docPreview = ref(null)
const preconditionCases = ref([])
const mainCases = ref([])
const casesLoading = ref(false)
const showImport = ref(false)
const showInterfaceForm = ref(false)
const editingInterface = ref(null)

const depJson = computed(() => JSON.stringify(dependencies.value ?? {}, null, 2))
const docPreviewJson = computed(() => docPreview.value ? JSON.stringify(docPreview.value, null, 2) : '')

async function loadTree() {
  const params = withProjectParams()
  if (!params) return
  const res = await getApiCatalogTree(params)
  catalogTree.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadInterfaces() {
  if (!selectedCatalogId.value) return
  const res = await listInterfacesByCatalog(selectedCatalogId.value, withProjectParams({ page: 1, page_size: 100 }))
  interfaces.value = res.data.data?.items ?? []
  if (!interfaces.value.find((i) => i.id === selectedInterfaceId.value)) {
    selectedInterfaceId.value = interfaces.value[0]?.id ?? null
  }
}

async function loadTemplate() {
  if (!selectedInterfaceId.value) return
  const res = await getDebugTemplate(selectedInterfaceId.value).catch(() => null)
  const tpl = res?.data?.data ?? {}
  requestJson.value = JSON.stringify(tpl, null, 2)
  assertionsJson.value = JSON.stringify(tpl.assertions ?? [], null, 2)
}

async function loadCases() {
  if (!selectedInterfaceId.value) return
  casesLoading.value = true
  try {
    const [preRes, mainRes] = await Promise.all([
      listApiCases(selectedInterfaceId.value, { case_kind: 'precondition' }),
      listApiCases(selectedInterfaceId.value, { case_kind: 'main' }),
    ])
    preconditionCases.value = preRes.data.data?.items ?? preRes.data.data ?? []
    mainCases.value = mainRes.data.data?.items ?? mainRes.data.data ?? []
  } finally {
    casesLoading.value = false
  }
}

async function loadDeps() {
  if (!selectedInterfaceId.value) return
  const res = await listDependencies(selectedInterfaceId.value)
  dependencies.value = res.data.data
}

async function loadDocPreview() {
  if (!selectedInterfaceId.value) return
  const res = await getDocPreview(selectedInterfaceId.value)
  docPreview.value = res.data.data
}

async function runDebug() {
  debugging.value = true
  try {
    const res = await debugRunInterface(selectedInterfaceId.value, { environment_id: environmentId.value })
    responseJson.value = JSON.stringify(res.data.data, null, 2)
  } finally {
    debugging.value = false
  }
}

async function saveTemplate() {
  let payload
  try {
    payload = JSON.parse(requestJson.value)
    payload.assertions = JSON.parse(assertionsJson.value)
  } catch {
    ElMessage.error(t('page.apiCases.invalidJson'))
    return
  }
  await saveDebugTemplate(selectedInterfaceId.value, payload)
  ElMessage.success(t('common.saved'))
}

async function fillFromDoc() {
  const res = await fillDebugFromDoc(selectedInterfaceId.value)
  const tpl = res.data.data ?? {}
  requestJson.value = JSON.stringify(tpl, null, 2)
  assertionsJson.value = JSON.stringify(tpl.assertions ?? [], null, 2)
  ElMessage.success(t('page.apiCases.filledFromDoc'))
}

async function reanalyze() {
  reanalyzing.value = true
  try {
    await reanalyzeDependencies(selectedInterfaceId.value)
    await loadDeps()
    ElMessage.success(t('common.saved'))
  } finally {
    reanalyzing.value = false
  }
}

function openCreateInterface() {
  editingInterface.value = null
  showInterfaceForm.value = true
}

function openEditInterface() {
  editingInterface.value = interfaces.value.find((i) => i.id === selectedInterfaceId.value) ?? null
  showInterfaceForm.value = true
}

async function removeInterface() {
  await ElMessageBox.confirm(t('common.deleteConfirm'), { type: 'warning' })
  await deleteInterface(selectedInterfaceId.value)
  selectedInterfaceId.value = null
  await loadInterfaces()
  ElMessage.success(t('common.deleted'))
}

async function copyCurrentInterface() {
  const res = await copyInterface(selectedInterfaceId.value)
  const copied = res.data.data
  ElMessage.success(copied?.path ? `${t('common.copy')}: ${copied.path}` : t('common.saved'))
  await loadInterfaces()
  if (copied?.id) selectedInterfaceId.value = copied.id
}

watch(selectedCatalogId, () => { loadInterfaces() })
watch(selectedInterfaceId, () => {
  loadTemplate()
  loadCases()
  loadDeps()
  loadDocPreview()
})
onMounted(async () => {
  await loadTree()
  await loadInterfaces()
  if (selectedInterfaceId.value) {
    await loadTemplate()
    await loadCases()
    await loadDeps()
    await loadDocPreview()
  }
})
</script>

<style scoped lang="scss">
.interface-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.editor-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.editor-label { font-size: 13px; margin-bottom: 4px; color: var(--el-text-color-secondary); }
.doc-dep-toolbar, .case-toolbar { margin-bottom: 12px; }
h4 { font-size: 14px; margin: 0 0 8px; }
</style>
