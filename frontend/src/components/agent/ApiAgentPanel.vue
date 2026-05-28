<template>
  <div class="api-agent-panel">
    <el-form label-width="120px">
      <el-form-item :label="t('page.agent.mode')">
        <el-radio-group v-model="mode">
          <el-radio value="interface">{{ t('page.agent.fromInterface') }}</el-radio>
          <el-radio value="doc">{{ t('page.agent.fromDoc') }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="mode === 'interface'" :label="t('page.apiCases.interface')">
        <el-input-number v-model="interfaceId" :min="1" />
      </el-form-item>
      <template v-else>
        <el-form-item :label="t('page.knowledge.titleCol')">
          <el-input-number v-model="documentId" :min="1" />
        </el-form-item>
        <el-form-item :label="t('page.knowledge.versionNo')">
          <el-input-number v-model="versionId" :min="1" />
        </el-form-item>
      </template>
      <el-form-item :label="t('page.agent.prompt')">
        <el-input v-model="userPrompt" type="textarea" :rows="3" :placeholder="t('page.agent.promptPlaceholder')" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="generating" :disabled="!canEdit" @click="generate">
          {{ t('page.agent.generate') }}
        </el-button>
        <el-button v-if="sessionId" type="success" :disabled="!canEdit" @click="showConfirm = true">
          {{ t('page.agent.confirmSave') }}
        </el-button>
      </el-form-item>
    </el-form>

    <div v-if="preview" class="preview-box">
      <MonacoJsonEditor :model-value="previewJson" read-only :height="320" />
    </div>

    <el-dialog v-model="showConfirm" :title="t('page.agent.confirmSave')" width="480px">
      <el-form label-width="120px">
        <el-form-item :label="t('page.functional.catalog')" required>
          <el-select v-model="confirmCatalogId" filterable style="width: 100%">
            <el-option v-for="c in flatCatalogs" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('page.apiCases.selectEnv')" required>
          <EnvironmentSelect v-model="confirmEnvId" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showConfirm = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="confirming" @click="confirm">{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  confirmApiGeneration,
  generateApiFromDoc,
  generateApiFromInterface,
  getApiSession,
} from '@/api/aiGeneration'
import { getApiCatalogTree } from '@/api/apiTest'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'

const { t } = useI18n()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()

const mode = ref('interface')
const interfaceId = ref(null)
const documentId = ref(null)
const versionId = ref(null)
const userPrompt = ref('')
const sessionId = ref(null)
const preview = ref(null)
const generating = ref(false)
const showConfirm = ref(false)
const confirming = ref(false)
const confirmCatalogId = ref(null)
const confirmEnvId = ref(null)
const catalogs = ref([])
let pollTimer = null

const previewJson = computed(() => JSON.stringify(preview.value ?? {}, null, 2))

const flatCatalogs = computed(() => {
  const out = []
  function walk(nodes) {
    nodes.forEach((n) => { out.push(n); if (n.children) walk(n.children) })
  }
  walk(catalogs.value)
  return out
})

async function loadCatalogs() {
  const params = withProjectParams()
  if (!params) return
  const res = await getApiCatalogTree(params)
  catalogs.value = res.data.data?.items ?? res.data.data ?? []
}

async function generate() {
  generating.value = true
  try {
    const base = { ...withProjectParams(), user_prompt: userPrompt.value || undefined }
    const res = mode.value === 'interface'
      ? await generateApiFromInterface({ ...base, interface_id: interfaceId.value })
      : await generateApiFromDoc({ ...base, document_id: documentId.value, version_id: versionId.value })
    sessionId.value = res.data.data?.session_id ?? res.data.data?.id
    pollSession()
  } finally {
    generating.value = false
  }
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function pollSession() {
  stopPoll()
  async function tick() {
    if (!sessionId.value) return
    const res = await getApiSession(sessionId.value)
    const data = res.data.data
    preview.value = data.preview ?? data.output_payload ?? data
    if (['ready', 'failed', 'completed'].includes(data.status)) stopPoll()
  }
  tick()
  pollTimer = setInterval(tick, 2000)
}

async function confirm() {
  if (!confirmCatalogId.value || !confirmEnvId.value) {
    ElMessage.warning(t('validation.required'))
    return
  }
  confirming.value = true
  try {
    const indexes = preview.value?.cases?.map((_, i) => i) ?? [0]
    await confirmApiGeneration({
      session_id: sessionId.value,
      selected_indexes: indexes,
      environment_id: confirmEnvId.value,
      catalog_id: confirmCatalogId.value,
      interface_id: mode.value === 'interface' ? interfaceId.value : undefined,
    })
    ElMessage.success(t('page.agent.saved'))
    showConfirm.value = false
  } finally {
    confirming.value = false
  }
}

onMounted(loadCatalogs)
onUnmounted(stopPoll)
</script>

<style scoped lang="scss">
.preview-box {
  margin-top: 16px;
}
</style>
