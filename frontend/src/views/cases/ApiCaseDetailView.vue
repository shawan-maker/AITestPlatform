<template>
  <div v-loading="loading" class="api-case-detail app-card">
    <PageHeader :title="caseDetail?.title || caseDetail?.name || t('page.apiCases.caseDetail')">
      <template #actions>
        <el-button @click="goBack">{{ t('common.back') }}</el-button>
        <EnvironmentSelect v-model="environmentId" />
        <el-button type="primary" :loading="running" @click="run">{{ t('page.apiCases.debugRun') }}</el-button>
      </template>
    </PageHeader>
    <SplitView>
      <template #left>
        <MonacoJsonEditor v-if="depJson" :model-value="depJson" read-only :height="400" />
      </template>
      <template #right>
        <div class="editor-label">{{ t('page.apiCases.request') }}</div>
        <MonacoJsonEditor v-model="casePayloadJson" :height="200" />
        <div class="editor-label">{{ t('page.apiCases.response') }}</div>
        <MonacoJsonEditor v-model="responseJson" read-only :height="180" />
        <div class="editor-label">{{ t('page.apiCases.assertions') }}</div>
        <MonacoJsonEditor v-model="assertionsJson" :height="160" />
        <AppTable :data="runRecords" class="run-records-table">
          <AppTableColumn prop="created_at" variant="flex" :label="t('common.createdAt')" />
          <AppTableColumn prop="status" variant="fixed" :label="t('common.status')" :width="100" />
        </AppTable>
      </template>
    </SplitView>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  debugRunApiCase,
  getApiCase,
  getApiCaseRunRecords,
  listDependencies,
  updateApiCase,
} from '@/api/apiTest'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import SplitView from '@/components/common/SplitView.vue'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const caseId = computed(() => Number(route.params.caseId))

const loading = ref(false)
const caseDetail = ref(null)
const dependencies = ref(null)
const environmentId = ref(null)
const casePayloadJson = ref('{}')
const responseJson = ref('')
const assertionsJson = ref('[]')
const runRecords = ref([])
const running = ref(false)

const depJson = computed(() => dependencies.value ? JSON.stringify(dependencies.value, null, 2) : '')

async function load() {
  loading.value = true
  try {
    const res = await getApiCase(caseId.value)
    caseDetail.value = res.data.data
    const payload = caseDetail.value?.case_payload ?? {}
    casePayloadJson.value = JSON.stringify(payload, null, 2)
    assertionsJson.value = JSON.stringify(payload.assertions ?? [], null, 2)
    if (caseDetail.value?.interface_id) {
      const depRes = await listDependencies(caseDetail.value.interface_id)
      dependencies.value = depRes.data.data
    }
    const recRes = await getApiCaseRunRecords(caseId.value)
    runRecords.value = recRes.data.data?.items ?? recRes.data.data ?? []
  } finally {
    loading.value = false
  }
}

async function run() {
  running.value = true
  try {
    let assertions
    let payload
    try {
      assertions = JSON.parse(assertionsJson.value)
      payload = JSON.parse(casePayloadJson.value)
    } catch {
      ElMessage.error(t('page.apiCases.invalidJson'))
      return
    }
    payload.assertions = assertions
    await updateApiCase(caseId.value, { case_payload: payload })
    const res = await debugRunApiCase(caseId.value, { environment_id: environmentId.value })
    responseJson.value = JSON.stringify(res.data.data, null, 2)
    load()
  } finally {
    running.value = false
  }
}

function goBack() {
  router.push({ path: '/cases/api', query: route.query })
}

onMounted(load)
</script>

<style scoped lang="scss">
.editor-label {
  font-size: 13px;
  margin: 8px 0 4px;
  color: var(--el-text-color-secondary);
}

.run-records-table {
  margin-top: 12px;
}
</style>
