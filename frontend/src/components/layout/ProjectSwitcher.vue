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
    <template #footer>
      <div class="project-switcher__footer">
        <el-divider style="margin: 4px 0" />
        <div class="project-switcher__create" @click.stop="goToProjects">
          <el-icon><Plus /></el-icon>
          <span>{{ t('common.createProject') }}</span>
        </div>
      </div>
    </template>
  </el-select>
</template>

<script setup>
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import { usePermissionStore } from '@/stores/permission'

const { t } = useI18n()
const router = useRouter()
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

function goToProjects() {
  router.push('/projects')
}
</script>

<style scoped lang="scss">
.project-switcher {
  width: 220px;
}

.project-switcher__footer {
  padding: 4px 0;
}

.project-switcher__create {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 20px;
  cursor: pointer;
  font-size: 13px;
  color: var(--el-color-primary);

  &:hover {
    background-color: var(--el-fill-color-light);
  }
}
</style>
