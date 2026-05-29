<template>
  <div class="project-switcher-wrap">
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
    <el-dropdown v-if="showSettings" trigger="click" @command="onCommand">
      <el-button link type="primary">{{ t('page.projectSettings.shortTitle') }}</el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="settings">{{ t('page.projectSettings.title') }}</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useProjectStore } from '@/stores/project'
import { usePermissionStore } from '@/stores/permission'

const { t } = useI18n()
const router = useRouter()
const projectStore = useProjectStore()
const permissionStore = usePermissionStore()

const showSettings = computed(() => permissionStore.isOwner && projectStore.currentProjectId)

onMounted(() => {
  if (!projectStore.projects.length) {
    projectStore.fetchProjects()
  }
})

async function onChange(id) {
  projectStore.setCurrent(id)
  await permissionStore.loadRoleForProject(id)
}

function onCommand(cmd) {
  if (cmd === 'settings' && projectStore.currentProjectId) {
    router.push(`/projects/${projectStore.currentProjectId}`)
  }
}
</script>

<style scoped lang="scss">
.project-switcher-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-switcher {
  width: 280px;
}
</style>
