<template>
  <div class="placeholder-page">
    <PageHeader :title="pageTitle" />
    <div v-if="needsProject && !projectStore.currentProjectId" class="placeholder-page__body app-card">
      <EmptyState
        :title="t('common.noProject')"
        :description="t('common.selectProjectHint')"
      />
    </div>
    <div v-else class="placeholder-page__body app-card">
      <EmptyState :title="t('page.placeholder.title')" :description="t('page.placeholder.desc')" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useProjectStore } from '@/stores/project'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const route = useRoute()
const { t } = useI18n()
const projectStore = useProjectStore()

const needsProject = computed(() => route.meta.projectRequired === true)

const pageTitle = computed(() => {
  if (route.meta.titleKey) {
    return t(route.meta.titleKey)
  }
  return route.name?.toString() ?? ''
})
</script>

<style scoped lang="scss">
.placeholder-page__body {
  margin-top: 0;
}
</style>
