<template>
  <div class="agent-center-view">
    <EmptyState
      v-if="!projectId && !projectStore.loading"
      :title="t('common.noProject')"
      :description="t('common.selectProjectHint')"
    />
    <template v-else>
      <div class="agent-center-view__header">
        <AgentWelcomeHeader v-if="showLandingHeader" />
        <AgentTypeTabs v-model="activeTab" />
      </div>
      <div class="agent-center-view__body">
        <FunctionalAgentPanel
          v-show="activeTab === 'functional'"
          :is-active="activeTab === 'functional'"
          :auto-new="route.query.new === '1'"
          :initial-requirement="functionalRequirement"
          @composer-mode-change="onComposerModeChange"
        />
        <ApiAgentPanel
          v-show="activeTab === 'api'"
          :is-active="activeTab === 'api'"
          :auto-new="route.query.new === '1'"
          :initial-interface-id="apiInterfaceId"
          @composer-mode-change="onComposerModeChange"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useProjectScope } from '@/composables/useProjectScope'
import { useProjectStore } from '@/stores/project'
import EmptyState from '@/components/common/EmptyState.vue'
import AgentWelcomeHeader from '@/components/agent/AgentWelcomeHeader.vue'
import AgentTypeTabs from '@/components/agent/AgentTypeTabs.vue'
import FunctionalAgentPanel from '@/components/agent/FunctionalAgentPanel.vue'
import ApiAgentPanel from '@/components/agent/ApiAgentPanel.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { projectId } = useProjectScope()
const projectStore = useProjectStore()
const activeTab = ref(route.query.tab === 'api' ? 'api' : 'functional')
const composerMode = ref(true)

const showLandingHeader = computed(() => composerMode.value)

const functionalRequirement = computed(() => {
  const q = route.query.requirement
  return typeof q === 'string' ? q : ''
})

const apiInterfaceId = computed(() => {
  const q = Number(route.query.interface_id)
  return Number.isFinite(q) && q > 0 ? q : null
})

function onComposerModeChange(value) {
  if (value !== composerMode.value) {
    composerMode.value = value
  }
}

watch(activeTab, (tab) => {
  router.replace({ query: { ...route.query, tab } })
})

watch(
  () => projectId.value,
  async (id) => {
    if (id && !projectStore.projects.length) {
      await projectStore.fetchProjects()
    }
  },
  { immediate: true },
)
</script>

<style scoped lang="scss">
.agent-center-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  width: 100%;
  padding: 0;
  background: transparent;
  box-shadow: none;
}

.agent-center-view__header {
  flex-shrink: 0;
  padding: 0 4px;
}

.agent-center-view__body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
