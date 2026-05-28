<template>
  <div class="agent-center-view app-card">
    <PageHeader :title="t('menu.agent')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <el-tabs v-else v-model="activeTab">
      <el-tab-pane :label="t('page.agent.functionalTab')" name="functional">
        <FunctionalAgentPanel
          :auto-new="route.query.new === '1'"
          :initial-requirement="functionalRequirement"
        />
      </el-tab-pane>
      <el-tab-pane :label="t('page.agent.apiTab')" name="api">
        <ApiAgentPanel
          :auto-new="route.query.new === '1'"
          :initial-interface-id="apiInterfaceId"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useProjectScope } from '@/composables/useProjectScope'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import FunctionalAgentPanel from '@/components/agent/FunctionalAgentPanel.vue'
import ApiAgentPanel from '@/components/agent/ApiAgentPanel.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { projectId } = useProjectScope()
const activeTab = ref(route.query.tab === 'api' ? 'api' : 'functional')

const functionalRequirement = computed(() => {
  const q = route.query.requirement
  return typeof q === 'string' ? q : ''
})

const apiInterfaceId = computed(() => {
  const q = Number(route.query.interface_id)
  return Number.isFinite(q) && q > 0 ? q : null
})

watch(activeTab, (tab) => {
  router.replace({ query: { ...route.query, tab } })
})
</script>
