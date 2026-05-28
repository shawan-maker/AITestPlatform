<template>
  <div class="user-list-view app-card">
    <PageHeader :title="t('page.admin.users.title')" />

    <FilterBar @search="load" @reset="resetFilters">
      <template #primary>
        <el-button type="primary" @click="showCreate = true">{{ t('page.admin.users.create') }}</el-button>
      </template>
      <el-input v-model="filters.username" :placeholder="t('page.login.username')" clearable />
      <el-input v-model="filters.email" :placeholder="t('page.register.email')" clearable />
      <el-input v-model="filters.project_name" :placeholder="t('page.admin.users.projectName')" clearable />
      <el-select v-model="filters.is_active" :placeholder="t('page.admin.users.status')" clearable>
        <el-option :label="t('page.admin.users.statusActive')" :value="true" />
        <el-option :label="t('page.admin.users.statusInactive')" :value="false" />
      </el-select>
    </FilterBar>

    <PaginatedTable
      v-model:page="page"
      v-model:page-size="pageSize"
      :data="items"
      :loading="loading"
      :total="total"
      @page-change="load"
      @size-change="load"
    >
      <AppTableColumn prop="username" variant="content" :label="t('page.login.username')" />
      <AppTableColumn prop="email" variant="content" :label="t('page.register.email')" />
      <AppTableColumn variant="fixed" :label="t('page.admin.users.status')" :width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? t('page.admin.users.statusActive') : t('page.admin.users.statusInactive') }}
          </el-tag>
        </template>
      </AppTableColumn>
      <AppTableColumn variant="fixed" :label="t('page.admin.users.superAdmin')" :width="100">
        <template #default="{ row }">{{ row.is_super_admin ? 'Yes' : 'No' }}</template>
      </AppTableColumn>
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="320">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/admin/users/${row.id}`)">{{ t('common.view') }}</el-button>
          <el-button link @click="toggleStatus(row)">
            {{ row.is_active ? t('page.admin.users.deactivate') : t('page.admin.users.activate') }}
          </el-button>
          <el-button link @click="resetPassword(row)">{{ t('page.admin.users.resetPassword') }}</el-button>
          <ConfirmDelete @confirm="remove(row)">
            <el-button link type="danger">{{ t('common.delete') }}</el-button>
          </ConfirmDelete>
        </template>
      </AppTableColumn>
    </PaginatedTable>

    <UserFormDialog v-model="showCreate" :loading="creating" @submit="create" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createUser, deleteUser, listUsers, resetUserPassword, updateUserStatus } from '@/api/users'
import { usePagination } from '@/composables/usePagination'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import UserFormDialog from '@/components/admin/UserFormDialog.vue'

const { t } = useI18n()
const router = useRouter()
const { page, pageSize, total } = usePagination()

const filters = reactive({ username: '', email: '', project_name: '', is_active: null })
const items = ref([])
const loading = ref(false)
const showCreate = ref(false)
const creating = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await listUsers({
      page: page.value,
      page_size: pageSize.value,
      username: filters.username || undefined,
      email: filters.email || undefined,
      project_name: filters.project_name || undefined,
      is_active: filters.is_active ?? undefined,
    })
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, { username: '', email: '', project_name: '', is_active: null })
  page.value = 1
  load()
}

async function create(data) {
  creating.value = true
  try {
    await createUser(data)
    ElMessage.success(t('page.admin.users.created'))
    showCreate.value = false
    load()
  } finally {
    creating.value = false
  }
}

async function toggleStatus(row) {
  await updateUserStatus(row.id, !row.is_active)
  ElMessage.success(t('common.saved'))
  load()
}

async function resetPassword(row) {
  const { value } = await ElMessageBox.prompt(t('page.admin.users.newPasswordHint'), t('page.admin.users.resetPassword'), {
    inputType: 'password',
  })
  await resetUserPassword(row.id, value)
  ElMessage.success(t('page.admin.users.passwordReset'))
}

async function remove(row) {
  await deleteUser(row.id)
  ElMessage.success(t('common.deleted'))
  load()
}

onMounted(load)
</script>
