<template>
  <div class="project-detail-view">
    <BreadcrumbNav :items="breadcrumbs" />
    <ProjectWorkspaceView mode="admin" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import BreadcrumbNav from '@/components/common/BreadcrumbNav.vue'
import ProjectWorkspaceView from '@/views/project/ProjectWorkspaceView.vue'

const { t } = useI18n()

const breadcrumbs = computed(() => [
  { label: t('menu.adminProjects'), to: '/admin/projects' },
  { label: t('common.breadcrumb.projectDetail') },
])
</script>
