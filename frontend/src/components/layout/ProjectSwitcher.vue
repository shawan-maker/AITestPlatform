<template>
  <el-select
    :model-value="projectStore.currentProjectId"
    :placeholder="t('common.selectProject')"
    :loading="projectStore.loading"
    filterable
    class="project-switcher"
    @change="onChange"
  >
    <el-option
      v-for="item in projectStore.projects"
      :key="item.id"
      :label="item.name"
      :value="item.id"
    />
  </el-select>
</template>

<script setup>
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useProjectStore } from '@/stores/project'
import { usePermissionStore } from '@/stores/permission'

const { t } = useI18n()
const projectStore = useProjectStore()
const permissionStore = usePermissionStore()

onMounted(() => {
  if (!projectStore.projects.length) {
    projectStore.fetchProjects()
  }
})

async function onChange(id) {
  projectStore.setCurrent(id)
  await permissionStore.loadRoleForProject(id)
}
</script>

<style scoped lang="scss">
.project-switcher {
  width: 220px;
}
</style>
