<template>
  <div v-loading="loading" class="user-detail-view app-card">
    <BreadcrumbNav :items="breadcrumbs" />
    <PageHeader :title="user?.username || t('page.admin.users.title')" />

    <el-descriptions v-if="user" :column="2" border class="user-detail-view__info">
      <el-descriptions-item label="ID">{{ user.id }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.login.username')">{{ user.username }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.register.email')">{{ user.email }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.admin.users.status')">
        <el-tag :type="user.is_active ? 'success' : 'info'">
          {{ user.is_active ? t('page.admin.users.statusActive') : t('page.admin.users.statusInactive') }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.admin.users.superAdmin')">{{ user.is_super_admin ? t('common.yes') : t('common.no') }}</el-descriptions-item>
    </el-descriptions>

    <h3 class="user-detail-view__section">{{ t('page.admin.users.relatedProjects') }}</h3>
    <AppTable :data="user?.projects ?? []">
      <AppTableColumn prop="project_name" variant="content" :label="t('page.admin.projects.name')">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/projects/${row.project_id}`)">
            {{ row.project_name }}
          </el-button>
        </template>
      </AppTableColumn>
      <AppTableColumn variant="fixed" :label="t('page.projectSettings.role')" :width="140">
        <template #default="{ row }">{{ t(`role.${PROJECT_ROLE_LABEL[row.role] || 'viewer'}`) }}</template>
      </AppTableColumn>
    </AppTable>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getUser } from '@/api/users'
import { PROJECT_ROLE_LABEL } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import BreadcrumbNav from '@/components/common/BreadcrumbNav.vue'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const userId = computed(() => Number(route.params.id))
const user = ref(null)
const loading = ref(false)

const breadcrumbs = computed(() => [
  { label: t('menu.adminUsers'), to: '/admin/users' },
  { label: t('common.breadcrumb.userDetail') },
])

async function load() {
  loading.value = true
  try {
    const res = await getUser(userId.value)
    user.value = res.data.data
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped lang="scss">
.user-detail-view__info {
  margin-bottom: 24px;
}

.user-detail-view__section {
  margin: 0 0 12px;
  font-size: 16px;
}
</style>
