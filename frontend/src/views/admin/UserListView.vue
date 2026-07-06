<template>
  <div class="user-list-view app-card">
    <PageHeader :title="t('page.admin.users.title')" />

    <FilterBar @search="load" @reset="resetFilters">
      <template #primary>
        <el-button type="primary" @click="showCreate = true">{{ t('page.admin.users.create') }}</el-button>
        <el-button v-if="selectedIds.length" type="danger" @click="batchRemove">{{ t('common.batchDelete') }} ({{ selectedIds.length }})</el-button>
      </template>
      <el-input v-model="filters.username" :placeholder="t('page.login.username')" clearable />
      <el-input v-model="filters.email" :placeholder="t('page.register.email')" clearable />
      <ProjectSearchPicker v-model="filters.project_id" :placeholder="t('page.admin.users.projectName')" />
      <el-select v-model="filters.is_active" :placeholder="t('page.admin.users.status')" clearable>
        <el-option :label="t('page.admin.users.statusActive')" :value="true" />
        <el-option :label="t('page.admin.users.statusInactive')" :value="false" />
      </el-select>
      <el-select v-model="filters.is_super_admin" :placeholder="t('page.admin.users.superAdmin')" clearable>
        <el-option :label="t('common.yes')" :value="true" />
        <el-option :label="t('common.no')" :value="false" />
      </el-select>
    </FilterBar>

    <PaginatedTable
      v-model:page="page"
      v-model:page-size="pageSize"
      :data="items"
      :loading="loading"
      :total="total"
      row-key="id"
      @page-change="load"
      @size-change="load"
      @selection-change="onSelectionChange"
    >
      <AppTableColumn type="selection" variant="fixed" :width="50" />
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
        <template #default="{ row }">{{ row.is_super_admin ? t('common.yes') : t('common.no') }}</template>
      </AppTableColumn>
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :button-labels="[t('common.view'), t('page.admin.deactivate'), t('page.admin.users.resetPassword'), t('common.delete')]">
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
import { batchDeleteUsers, createUser, deleteUser, listUsers, resetUserPassword, updateUserStatus } from '@/api/users'
import { usePagination } from '@/composables/usePagination'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import UserFormDialog from '@/components/admin/UserFormDialog.vue'
import ProjectSearchPicker from '@/components/picker/ProjectSearchPicker.vue'

const { t } = useI18n()
const router = useRouter()
const { page, pageSize, total } = usePagination()

const filters = reactive({ username: '', email: '', project_id: null, is_active: null, is_super_admin: null })
const selectedIds = ref([])
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
      project_id: filters.project_id ?? undefined,
      is_active: filters.is_active ?? undefined,
      is_super_admin: filters.is_super_admin ?? undefined,
    })
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, { username: '', email: '', project_id: null, is_active: null, is_super_admin: null })
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
  const activating = !row.is_active
  const msg = activating ? t('page.admin.users.confirmActivate') : t('page.admin.users.confirmDeactivate')
  await ElMessageBox.confirm(msg, t('common.confirm'), { type: 'warning' })
  await updateUserStatus(row.id, activating)
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

function onSelectionChange(rows) {
  selectedIds.value = rows.map(function (r) { return r.id })
}

async function batchRemove() {
  try {
    await ElMessageBox.confirm(
      t('common.batchDeleteConfirm', { count: selectedIds.value.length }),
      t('common.warning'),
      { type: 'warning' }
    )
    var res = await batchDeleteUsers(selectedIds.value)
    var data = res.data.data
    selectedIds.value = []
    if (data && data.failures && data.failures.length) {
      ElMessage.warning(t('common.batchDeletePartial'))
    } else if (data && data.deleted_ids && data.deleted_ids.length) {
      ElMessage.success(t('common.batchDeleteSuccess', { count: data.deleted_ids.length }))
    }
    load()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.message || e.message)
    }
  }
}

onMounted(load)
</script>
