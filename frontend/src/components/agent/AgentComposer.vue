<template>
  <div class="agent-composer" :class="{ 'agent-composer--compact': compact }">
    <div class="agent-composer__box">
      <div v-if="!hidePromptRow" class="agent-composer__prompt-row">
        <template v-if="agentType === 'functional'">
          <span>{{ t('page.agent.composeHelpWrite') }}</span>
          <el-select
            v-model="localProjectId"
            class="agent-composer__inline-select agent-composer__inline-select--project"
            filterable
            :placeholder="t('common.selectProject')"
            :loading="projectStore.loading"
            @change="onProjectChange"
          >
            <el-option
              v-for="item in projectStore.projects"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
          <span>{{ t('page.agent.composeFunctionalMiddle') }}</span>
          <el-select
            v-model="selectedRequirementKey"
            class="agent-composer__inline-select agent-composer__inline-select--requirement"
            filterable
            clearable
            :placeholder="t('page.agent.selectRequirement')"
            :loading="loadingOptions"
          >
            <el-option
              v-for="item in requirementOptions"
              :key="item.key"
              :label="item.label"
              :value="item.key"
            />
          </el-select>
        </template>
        <template v-else>
          <span>{{ t('page.agent.composeHelpWrite') }}</span>
          <el-select
            v-model="localProjectId"
            class="agent-composer__inline-select agent-composer__inline-select--project"
            filterable
            :placeholder="t('common.selectProject')"
            :loading="projectStore.loading"
            @change="onProjectChange"
          >
            <el-option
              v-for="item in projectStore.projects"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
          <span>{{ t('page.agent.composeApiMiddle') }}</span>
          <el-select
            v-model="selectedInterfaceId"
            class="agent-composer__inline-select agent-composer__inline-select--interface"
            filterable
            clearable
            :placeholder="t('page.agent.selectInterface')"
            :loading="loadingOptions"
          >
            <el-option
              v-for="item in interfaceOptions"
              :key="item.id"
              :label="item.label"
              :value="item.id"
            />
          </el-select>
        </template>
      </div>

      <textarea
        ref="textareaRef"
        v-model="draft"
        class="agent-composer__textarea"
        :placeholder="placeholderText"
        :disabled="disabled || streaming"
        @keydown="onKeydown"
      />

      <div class="agent-composer__footer">
        <button
          type="button"
          class="agent-composer__link-btn"
          :disabled="disabled || streaming"
          @click="onOptimize"
        >
          {{ t('page.agent.aiOptimize') }}
        </button>
        <div class="agent-composer__actions">
          <el-tooltip :content="t('page.agent.uploadKnowledge')" placement="top">
            <button
              type="button"
              class="agent-composer__icon-btn"
              :disabled="disabled || streaming"
              @click="onUpload"
            >
              <el-icon><Folder /></el-icon>
            </button>
          </el-tooltip>
          <button
            type="button"
            class="agent-composer__send-btn"
            :disabled="disabled || streaming || !canSend"
            @click="submit"
          >
            <el-icon v-if="streaming" class="is-loading"><Loading /></el-icon>
            <el-icon v-else><Promotion /></el-icon>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Folder, Loading, Promotion } from '@element-plus/icons-vue'
import { listInterfaces } from '@/api/apiTest'
import { getRequirement, listRequirements } from '@/api/functional'
import { listDocuments } from '@/api/knowledge'
import { useProjectStore } from '@/stores/project'
import { usePermissionStore } from '@/stores/permission'

const props = defineProps({
  agentType: { type: String, default: 'functional' },
  streaming: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  hidePromptRow: { type: Boolean, default: false },
  quickTags: { type: Array, default: () => [] },
})

const emit = defineEmits(['send', 'project-change'])

const { t } = useI18n()
const router = useRouter()
const projectStore = useProjectStore()
const permissionStore = usePermissionStore()

const draft = ref('')
const localProjectId = ref(projectStore.currentProjectId)
const selectedRequirementKey = ref('')
const selectedInterfaceId = ref(null)
const requirementOptions = ref([])
const interfaceOptions = ref([])
const loadingOptions = ref(false)
const textareaRef = ref(null)

const placeholderText = computed(() => {
  if (props.hidePromptRow) {
    return t('page.agent.chatPlaceholder')
  }
  if (props.agentType === 'functional') {
    return t('page.agent.composerPlaceholderFunctional')
  }
  return t('page.agent.composerPlaceholderApi')
})

const selectedRequirement = computed(() =>
  requirementOptions.value.find((item) => item.key === selectedRequirementKey.value) ?? null,
)

const canSend = computed(() => {
  if (props.hidePromptRow) return Boolean(draft.value.trim())
  if (!localProjectId.value) return false
  if (props.agentType === 'functional') {
    return Boolean(draft.value.trim() || selectedRequirementKey.value)
  }
  return Boolean(draft.value.trim() || selectedInterfaceId.value)
})

async function loadRequirementOptions(projectId) {
  if (!projectId) {
    requirementOptions.value = []
    return
  }
  loadingOptions.value = true
  try {
    const [reqRes, docRes] = await Promise.all([
      listRequirements({ project_id: projectId, page: 1, page_size: 100 }),
      listDocuments({
        project_id: projectId,
        doc_type: 'requirement',
        index_status: 'indexed',
        page: 1,
        page_size: 100,
      }),
    ])
    const requirements = (reqRes.data.data?.items ?? []).map((item) => ({
      key: `req-${item.id}`,
      label: item.title,
      type: 'requirement',
      requirementId: item.id,
      knowledgeDocumentId: null,
    }))
    const documents = (docRes.data.data?.items ?? []).map((item) => ({
      key: `doc-${item.id}`,
      label: item.title,
      type: 'knowledge',
      requirementId: null,
      knowledgeDocumentId: item.id,
    }))
    requirementOptions.value = [...requirements, ...documents]
  } catch {
    requirementOptions.value = []
  } finally {
    loadingOptions.value = false
  }
}

async function loadInterfaceOptions(projectId) {
  if (!projectId) {
    interfaceOptions.value = []
    return
  }
  loadingOptions.value = true
  try {
    const res = await listInterfaces({ project_id: projectId, page: 1, page_size: 200 })
    interfaceOptions.value = (res.data.data?.items ?? []).map((item) => ({
      id: item.id,
      label: `${item.method || '—'} ${item.summary || item.path || item.id}`,
    }))
  } catch {
    interfaceOptions.value = []
  } finally {
    loadingOptions.value = false
  }
}

async function onProjectChange(projectId) {
  projectStore.setCurrent(projectId)
  await permissionStore.loadRoleForProject(projectId)
  selectedRequirementKey.value = ''
  selectedInterfaceId.value = null
  if (props.agentType === 'functional') {
    await loadRequirementOptions(projectId)
  } else {
    await loadInterfaceOptions(projectId)
  }
  emit('project-change', projectId)
}

function onKeydown(event) {
  if (event.key === 'Enter' && event.altKey) {
    return
  }
  if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !event.metaKey) {
    event.preventDefault()
    submit()
  }
}

function onOptimize() {
  const tag = props.quickTags[0]
  if (tag?.placeholder) {
    draft.value = draft.value ? `${draft.value}\n${tag.placeholder}` : tag.placeholder
    textareaRef.value?.focus()
    return
  }
  ElMessage.info(t('page.agent.aiOptimizeHint'))
}

function onUpload() {
  router.push({ path: '/docs/knowledge', query: localProjectId.value ? { project_id: localProjectId.value } : {} })
}

async function submit() {
  if (props.hidePromptRow) {
    const content = draft.value.trim()
    if (!content || props.streaming || props.disabled) return
    emit('send', { content, projectId: localProjectId.value })
    draft.value = ''
    return
  }

  if (!canSend.value || props.streaming || props.disabled) return

  const content = draft.value.trim()
  const payload = {
    content: content || (props.agentType === 'functional'
      ? t('page.agent.defaultFunctionalPrompt')
      : t('page.agent.defaultApiPrompt')),
    projectId: localProjectId.value,
  }

  if (props.agentType === 'functional') {
    const selected = selectedRequirement.value
    if (selected?.type === 'knowledge') {
      payload.knowledgeDocumentId = selected.knowledgeDocumentId
      payload.userPrompt = content || undefined
    } else if (selected?.type === 'requirement') {
      try {
        const res = await getRequirement(selected.requirementId)
        const detail = res.data.data
        payload.requirementText = detail?.description?.trim() || detail?.title || content
        payload.userPrompt = content || undefined
      } catch {
        ElMessage.error(t('common.requestFailed'))
        return
      }
    } else {
      payload.requirementText = content
    }
  } else if (selectedInterfaceId.value) {
    payload.interfaceId = selectedInterfaceId.value
    payload.userPrompt = content || undefined
  } else {
    payload.apiDocText = content
  }

  emit('send', payload)
  draft.value = ''
}

watch(
  () => projectStore.currentProjectId,
  (id) => {
    if (id && id !== localProjectId.value) {
      localProjectId.value = id
    }
  },
)

watch(
  () => [props.agentType, localProjectId.value],
  async ([type, projectId]) => {
    if (!projectId) return
    if (type === 'functional') {
      await loadRequirementOptions(projectId)
    } else {
      await loadInterfaceOptions(projectId)
    }
  },
  { immediate: true },
)

onMounted(async () => {
  if (!projectStore.projects.length) {
    await projectStore.fetchProjects()
  }
  if (!localProjectId.value && projectStore.projects.length) {
    localProjectId.value = projectStore.currentProjectId || projectStore.projects[0].id
  }
})
</script>

<style scoped lang="scss">
.agent-composer {
  width: 100%;
  max-width: 920px;
  margin: 0 auto;
  flex-shrink: 0;

  &--compact {
    max-width: none;
    padding: 0 12px 12px;
  }
}

.agent-composer__box {
  border: 1px solid rgba($color-primary, 0.35);
  border-radius: 12px;
  background: var(--el-bg-color);
  padding: 16px 18px 12px;
  box-shadow: 0 2px 12px rgba($color-primary, 0.06);
}

.agent-composer__prompt-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--el-text-color-primary);
  line-height: 32px;
}

.agent-composer__inline-select {
  :deep(.el-select__wrapper) {
    box-shadow: none !important;
    border: 1px solid var(--el-border-color);
    border-radius: 6px;
    min-height: 32px;
    padding: 0 8px;
  }

  &--project {
    width: 180px;
  }

  &--requirement,
  &--interface {
    width: 200px;
  }
}

.agent-composer__textarea {
  width: 100%;
  min-height: 120px;
  max-height: 240px;
  border: none;
  outline: none;
  resize: vertical;
  font-size: 14px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  background: transparent;
  font-family: inherit;

  &::placeholder {
    color: var(--el-text-color-placeholder);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.65;
  }
}

.agent-composer--compact .agent-composer__textarea {
  min-height: 72px;
  max-height: 160px;
}

.agent-composer__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  padding-top: 8px;
}

.agent-composer__link-btn {
  border: none;
  background: none;
  color: $color-primary;
  font-size: 14px;
  cursor: pointer;
  padding: 4px 0;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.agent-composer__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-composer__icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  border-radius: 6px;

  &:hover:not(:disabled) {
    background: var(--el-fill-color-light);
    color: var(--el-text-color-primary);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.agent-composer__send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, $color-primary, $color-primary-dark);
  color: #fff;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s;

  &:hover:not(:disabled) {
    transform: scale(1.04);
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}
</style>
