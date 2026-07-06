<template>
  <div class="agent-composer" :class="{ 'agent-composer--compact': compact }">
    <div v-if="!hidePromptRow" class="agent-composer__prompt-row">
      <template v-if="agentType === 'functional'">
        <span>{{ t('page.agent.composeHelpWrite') }}</span>
        <el-select
          v-model="localProjectId"
          class="agent-composer__inline-select agent-composer__inline-select--project"
          filterable
          popper-class="agent-composer-select-dropdown"
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
          v-model="selectedDocumentKey"
          class="agent-composer__inline-select agent-composer__inline-select--document"
          filterable
          clearable
          popper-class="agent-composer-select-dropdown"
          :placeholder="t('page.agent.selectDocument')"
          :loading="loadingOptions"
        >
          <el-option
            v-for="item in documentOptions"
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
          popper-class="agent-composer-select-dropdown"
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
        <InterfaceMultiSelect
          ref="interfaceSelectRef"
          v-model="selectedInterfaceIds"
          :project-id="localProjectId"
        />
      </template>
    </div>

    <div v-if="!hidePromptRow && agentType === 'api'" class="agent-composer__env-row">
      <span class="agent-composer__env-label">{{ t('page.agent.envLabel') }}</span>
      <EnvironmentSelect
        ref="envSelectRef"
        v-model="selectedEnvironmentId"
        :placeholder="t('page.agent.selectEnvironment')"
        class="agent-composer__env-select"
      />
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
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Folder, Loading, Promotion } from '@element-plus/icons-vue'
import { listDocuments } from '@/api/knowledge'
import { useProjectStore } from '@/stores/project'
import { usePermissionStore } from '@/stores/permission'
import InterfaceMultiSelect from './InterfaceMultiSelect.vue'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'

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
const selectedDocumentKey = ref('')
const selectedInterfaceIds = ref([])
const selectedEnvironmentId = ref(null)
const interfaceSelectRef = ref(null)
const envSelectRef = ref(null)
const documentOptions = ref([])
const loadingOptions = ref(false)
const textareaRef = ref(null)

const placeholderText = computed(() => {
  if (props.hidePromptRow) {
    return t('page.agent.chatPlaceholder')
  }
  if (props.agentType === 'functional') {
    return t('page.agent.composePlaceholderFunctional')
  }
  return t('page.agent.composePlaceholderApi')
})

const selectedDocument = computed(() =>
  documentOptions.value.find((item) => item.key === selectedDocumentKey.value) ?? null,
)

const canSend = computed(() => {
  if (props.hidePromptRow) return Boolean(draft.value.trim())
  if (!localProjectId.value) return false
  // project selected is enough to send (interfaces and textarea are both optional)
  return true
})

async function loadDocumentOptions(projectId) {
  if (!projectId) {
    documentOptions.value = []
    return
  }
  loadingOptions.value = true
  try {
    const res = await listDocuments({ project_id: projectId, doc_type: 'requirement', page: 1, page_size: 100 })
    const documents = (res.data.data?.items ?? []).map((item) => ({
      key: `doc-${item.id}`,
      label: item.title,
      type: 'document',
      documentId: item.id,
    }))
    documentOptions.value = documents
  } catch (error) {
    documentOptions.value = []
  } finally {
    loadingOptions.value = false
  }
}

async function onProjectChange(projectId) {
  projectStore.setCurrent(projectId)
  await permissionStore.loadRoleForProject(projectId)
  selectedDocumentKey.value = ''
  selectedInterfaceIds.value = []
  selectedEnvironmentId.value = null
  if (props.agentType === 'functional') {
    await loadDocumentOptions(projectId)
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
  // 获取项目名称
  const projectName = projectStore.projects.find(p => p.id === localProjectId.value)?.name || ''

  const payload = {
    content: content || (props.agentType === 'functional'
      ? t('page.agent.defaultFunctionalPrompt')
      : t('page.agent.defaultApiPrompt')),
    projectId: localProjectId.value,
    projectName,
  }

  if (props.agentType === 'functional') {
    const selected = selectedDocument.value
    if (selected?.type === 'document') {
      payload.knowledgeDocumentId = selected.documentId
      payload.documentName = selected.label || ''
      payload.userPrompt = content || undefined
    } else {
      payload.userPrompt = content || undefined
    }
  } else {
    // API agent: multi-interface mode
    payload.interfaceIds = selectedInterfaceIds.value.length ? selectedInterfaceIds.value : undefined
    payload.environmentId = selectedEnvironmentId.value || undefined
    payload.userPrompt = content || undefined
    // mode: 'from_interfaces' if interfaces selected, 'from_prompt' otherwise
    payload.mode = selectedInterfaceIds.value.length ? 'from_interfaces' : 'from_prompt'
    // 获取接口名称列表
    const ifaceList = interfaceSelectRef.value?.selectedList || []
    payload.interfaceNames = ifaceList.map(i => `${i.method} ${i.summary || i.path}`)
    // 获取环境名称
    const envList = envSelectRef.value?.environments || []
    const envObj = envList.find(e => e.id === selectedEnvironmentId.value)
    payload.environmentName = envObj?.env_name || envObj?.name || ''
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
      await loadDocumentOptions(projectId)
    }
    // API agent: InterfaceMultiSelect loads its own data
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
  /* SIT-F7: 75% of main content area, max 1800px (landing mode) */
  width: 75%;
  max-width: 1800px;
  margin: 0 auto;
  flex-shrink: 0;

  /* 外部边框：完整边框，加粗+主题色 */
  border: 2px solid rgba($color-primary, 0.35);
  border-radius: 10px;
  padding: 20px 20px; /* 内边距让内容与边框有间距 */
  background: var(--el-bg-color);
  box-shadow: 0 2px 12px rgba($color-primary, 0.06);

  &--compact {
    max-width: none;
    width: 100%; /* 与chat panel对齐 */
    margin: 0 auto; /* 居中 */
    padding: 0 20px 12px; /* compact mode padding */
    box-sizing: border-box;
  }

  @media (max-width: 767px) {
    width: 90%;
    max-width: none;
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
  gap: 12px 16px;
  margin-bottom: 24px;
  padding-bottom: 24px;
  font-size: var(--font-card-title);
  color: var(--el-text-color-primary);
  line-height: 24px;
  border-bottom: 1px solid var(--el-border-color-lighter, #ebeef5);
}

.agent-composer__env-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter, #ebeef5);
  font-size: var(--font-card-title);
  color: var(--el-text-color-primary);
}

.agent-composer__env-label {
  white-space: nowrap;
  flex-shrink: 0;
}

.agent-composer__env-select {
  width: 320px;

  :deep(.el-select__wrapper) {
    box-shadow: none !important;
    border: 1px solid var(--el-border-color);
    border-radius: 6px;
    min-height: 24px;
    padding: 0 8px;
  }
}

.agent-composer__inline-select {
  :deep(.el-select__wrapper) {
    box-shadow: none !important;
    border: 1px solid var(--el-border-color);
    border-radius: 6px;
    min-height: 32px;
    padding: 0 8px;
  }

  /* 下拉框内文字字号比其它字体小一号 */
  :deep(.el-input__wrapper) {
    font-size: var(--font-size-base) !important;
  }
  :deep(.el-input__inner) {
    font-size: var(--font-size-base) !important;
  }
  :deep(.el-select__placeholder) {
    font-size: var(--font-size-base) !important;
  }

  &--project {
    width: 240px; /* 缩小宽度，让提示词在同一行显示 */
  }

  &--document,
  &--interface {
    width: 280px; /* 缩小宽度，让提示词在同一行显示 */
  }
}

.agent-composer__textarea {
  width: 100%;
  min-height: 120px; /* 高度减半：从 240px 改为 120px */
  max-height: 240px; /* 高度减半：从 480px 改为 240px */
  border: none;
  outline: none;
  resize: vertical;
  font-size: var(--font-size-base);
  line-height: 1.6; /* 调整行高以适应字体 */
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

/* Compact 模式下缩小图标和按钮 */
.agent-composer--compact {
  .agent-composer__link-btn {
    font-size: 13.5px; /* 与输入框字体保持一致 */
    padding: 4px 0;
  }

  .agent-composer__icon-btn {
    width: 28px;
    height: 28px;
    font-size: 14px;
    border-radius: 6px;
  }

  .agent-composer__send-btn {
    width: 32px;
    height: 32px;
    font-size: 16px;
  }

  .agent-composer__footer {
    margin-top: 8px; /* 从 16px 减半 */
    padding-top: 8px; /* 从 16px 减半 */
  }

  .agent-composer__actions {
    gap: 10px; /* 从 20px 减半 */
  }
}

.agent-composer__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px; /* 加倍：从 8px 改为 16px */
  padding-top: 16px; /* 加倍：从 8px 改为 16px */
}

.agent-composer__link-btn {
  border: none;
  background: none;
  color: $color-primary;
  font-size: var(--font-size-base);
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
  font-size: 18px;

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
  font-size: 20px;

  &:hover:not(:disabled) {
    transform: scale(1.04);
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}
</style>

<!-- 非 scoped 样式：修复 el-select-dropdown 字号（Teleport 到 body 导致 scoped 样式失效） -->
<style>
.agent-composer-select-dropdown .el-select-dropdown__item {
  font-size: var(--font-size-base) !important;
}
.agent-composer-select-dropdown .el-select-dropdown__empty {
  font-size: var(--font-size-base) !important;
}
</style>
