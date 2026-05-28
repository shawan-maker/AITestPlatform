<template>
  <div class="functional-agent-panel">
    <el-form label-width="100px">
      <el-form-item v-if="metaTags.length" :label="t('page.agent.quickTags')">
        <el-space wrap>
          <el-tag
            v-for="tag in metaTags"
            :key="tag"
            class="quick-tag"
            @click="appendTag(tag)"
          >{{ tag }}</el-tag>
        </el-space>
      </el-form-item>
      <el-form-item :label="t('page.agent.prompt')">
        <el-input v-model="prompt" type="textarea" :rows="4" :placeholder="metaPlaceholder || t('page.agent.promptPlaceholder')" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="generating" :disabled="!canEdit" @click="generate">{{ t('page.agent.generate') }}</el-button>
        <el-button v-if="sessionId" type="success" :disabled="!canEdit" @click="showSave = true">{{ t('page.agent.save') }}</el-button>
        <el-button link @click="router.push('/docs/knowledge')">{{ t('page.agent.uploadKnowledge') }}</el-button>
      </el-form-item>
    </el-form>
    <div v-if="preview" class="preview-box">
      <MonacoJsonEditor :model-value="previewJson" read-only :height="360" />
    </div>
    <el-dialog v-model="showSave" :title="t('page.agent.saveDialog')" width="400px">
      <el-form-item :label="t('page.functional.catalog')">
        <el-select v-model="saveCatalogId" filterable style="width: 100%">
          <el-option v-for="c in flatCatalogs" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <template #footer>
        <el-button @click="showSave = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="save">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { generateFunctional, getFunctionalSession, getMeta, saveFunctionalSession } from '@/api/aiGeneration'
import { getCaseCatalogTree } from '@/api/functional'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePolling } from '@/composables/usePolling'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'

const { t } = useI18n()
const router = useRouter()
const { withProjectParams } = useProjectScope()
const { canEdit } = usePermission()

const prompt = ref('')
const sessionId = ref(null)
const preview = ref(null)
const generating = ref(false)
const showSave = ref(false)
const saveCatalogId = ref(null)
const catalogs = ref([])
const meta = ref(null)

const metaTags = computed(() => meta.value?.functional?.quick_tags ?? meta.value?.quick_tags ?? [])
const metaPlaceholder = computed(() => meta.value?.functional?.user_prompt_placeholder ?? meta.value?.user_prompt_placeholder ?? '')
const previewJson = computed(() => JSON.stringify(preview.value ?? {}, null, 2))

const flatCatalogs = computed(() => {
  const out = []
  function walk(nodes) {
    nodes.forEach((n) => { out.push(n); if (n.children) walk(n.children) })
  }
  walk(catalogs.value)
  return out
})

function appendTag(tag) {
  prompt.value = prompt.value ? `${prompt.value}\n${tag}` : tag
}

async function loadCatalogs() {
  const params = withProjectParams()
  if (!params) return
  const res = await getCaseCatalogTree(params)
  catalogs.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadMeta() {
  try {
    const res = await getMeta()
    meta.value = res.data.data
  } catch {
    meta.value = null
  }
}

async function generate() {
  const params = withProjectParams()
  generating.value = true
  try {
    const res = await generateFunctional({ ...params, user_prompt: prompt.value })
    sessionId.value = res.data.data?.session_id ?? res.data.data?.id
    pollSession()
  } finally {
    generating.value = false
  }
}

function pollSession() {
  const polling = usePolling(async () => {
    const res = await getFunctionalSession(sessionId.value)
    const data = res.data.data
    preview.value = data.preview ?? data
    if (['ready', 'failed', 'completed'].includes(data.status)) polling.stop()
  }, { interval: 2000, until: () => false })
  polling.start()
}

async function save() {
  await saveFunctionalSession(sessionId.value, { catalog_id: saveCatalogId.value })
  ElMessage.success(t('page.agent.saved'))
  showSave.value = false
}

onMounted(() => {
  loadCatalogs()
  loadMeta()
})
</script>

<style scoped lang="scss">
.preview-box { margin-top: 16px; }
.quick-tag { cursor: pointer; }
</style>
