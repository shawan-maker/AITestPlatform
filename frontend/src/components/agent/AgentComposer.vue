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
            v-model="selectedRequirementKey"
            class="agent-composer__inline-select agent-composer__inline-select--requirement"
            filterable
            clearable
            popper-class="agent-composer-select-dropdown"
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
          <el-select
            v-model="selectedInterfaceId"
            class="agent-composer__inline-select agent-composer__inline-select--interface"
            filterable
            clearable
            popper-class="agent-composer-select-dropdown"
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
  /* SIT-F7: Allow sending without selecting requirement/interface (empty conversation) */
  if (draft.value.trim()) return true
  if (props.agentType === 'functional') {
    return Boolean(selectedRequirementKey.value)
  }
  return Boolean(selectedInterfaceId.value)
})

async function loadRequirementOptions(projectId) {
  if (!projectId) {
    requirementOptions.value = []
    return
  }
  loadingOptions.value = true
  try {
    const reqRes = await listRequirements({ project_id: projectId, page: 1, page_size: 100 })
    const requirements = (reqRes.data?.data?.items ?? []).map((item) => ({
      key: `req-${item.id}`,
      label: item.title,
      type: 'requirement',
      requirementId: item.id,
      knowledgeDocumentId: null,
    }))
    requirementOptions.value = requirements
  } catch (error) {
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
  /* SIT-F7: 75% of main content area, max 1800px (landing mode) */
  width: 75%;
  max-width: 1800px; /* 加倍：从 900px 改为 1800px */
  margin: 0 auto;
  flex-shrink: 0;


  &--compact {
    max-width: none;
    width: 100%; /* 与chat panel对齐 */
    margin: 0 auto; /* 居中 */
    padding: 0 40px 24px; /* 加倍：从 20px 12px 改为 40px 24px */
    box-sizing: border-box;
  }
  
  @media (max-width: 767px) {
    width: 90%;
    max-width: none;
  }
}

.agent-composer__box {
  border: 2px solid rgba($color-primary, 0.35); /* 加粗边框：从 1px 改为 2px */
  border-radius: 24px; /* 加倍：从 12px 改为 24px */
  background: var(--el-bg-color);
  padding: 32px 36px 24px; /* 加倍：从 16px 18px 12px 改为 32px 36px 24px */
  box-shadow: 0 4px 24px rgba($color-primary, 0.06); /* 加倍：从 0 2px 12px 改为 0 4px 24px */
}

.agent-composer__prompt-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 16px; /* 加倍：从 6px 8px 改为 12px 16px */
  margin-bottom: 24px; /* 加倍：从 12px 改为 24px */
  font-size: 24px; /* 比tab字号(28px)小两号 */
  color: var(--el-text-color-primary);
  line-height: 48px; /* 调整行高以适应24px字体 */
}

.agent-composer__inline-select {
  :deep(.el-select__wrapper) {
    box-shadow: none !important;
    border: 2px solid var(--el-border-color); /* 加粗边框：从 1px 改为 2px */
    border-radius: 12px; /* 加倍：从 6px 改为 12px */
    min-height: 64px; /* 加倍：从 32px 改为 64px */
    padding: 0 16px; /* 加倍：从 0 8px 改为 0 16px */
  }

  /* 下拉框内文字字号比其它字体小一号(22px)，包括下拉查看和选中展示 */
  :deep(.el-input__wrapper) {
    font-size: 22px !important;
  }
  :deep(.el-input__inner) {
    font-size: 22px !important;
  }
  :deep(.el-select__placeholder) {
    font-size: 22px !important;
  }

  &--project {
    width: 240px; /* 缩小宽度，让提示词在同一行显示 */
  }

  &--requirement,
  &--interface {
    width: 280px; /* 缩小宽度，让提示词在同一行显示 */
  }
}

.agent-composer__textarea {
  width: 100%;
  min-height: 240px; /* 加倍：从 120px 改为 240px */
  max-height: 480px; /* 加倍：从 240px 改为 480px */
  border: none;
  outline: none;
  resize: vertical;
  font-size: 24px; /* 比tab字号(28px)小两号，统一字号 */
  line-height: 1.6; /* 调整行高以适应24px字体 */
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
  min-height: 144px; /* 加倍：从 72px 改为 144px */
  max-height: 320px; /* 加倍：从 160px 改为 320px */
  font-size: 13.5px; /* 与上方对话消息字体保持一致 */
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
  font-size: 24px; /* 比tab字号(28px)小两号，统一字号 */
  cursor: pointer;
  padding: 8px 0; /* 加倍：从 4px 0 改为 8px 0 */

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.agent-composer__actions {
  display: flex;
  align-items: center;
  gap: 20px; /* 加倍：从 10px 改为 20px */
}

.agent-composer__icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px; /* 加倍：从 32px 改为 64px */
  height: 64px; /* 加倍：从 32px 改为 64px */
  border: none;
  background: none;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  border-radius: 12px; /* 加倍：从 6px 改为 12px */
  font-size: 32px; /* 新增：增大图标字体大小 */

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
  width: 72px; /* 加倍：从 36px 改为 72px */
  height: 72px; /* 加倍：从 36px 改为 72px */
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, $color-primary, $color-primary-dark);
  color: #fff;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s;
  font-size: 36px; /* 新增：增大图标字体大小 */

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
  font-size: 22px !important;
}
.agent-composer-select-dropdown .el-select-dropdown__empty {
  font-size: 22px !important;
}
</style>
