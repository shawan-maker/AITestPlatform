<template>
  <div class="project-list-view app-card">
    <PageHeader :title="t('page.admin.projects.title')" />

    <FilterBar @search="load" @reset="resetFilters">
      <template #primary>
        <el-button type="primary" @click="openCreate">{{ t('page.admin.projects.create') }}</el-button>
        <ConfirmDelete v-if="auth.isSuperAdmin && selectedIds.length" @confirm="batchRemove">
          <el-button type="danger">{{ t('page.projectSettings.batchDelete') }}</el-button>
        </ConfirmDelete>
      </template>
      <el-input v-model="filters.name" :placeholder="t('page.admin.projects.keyword')" clearable />
      <UserFilterSelect
        v-if="auth.isSuperAdmin"
        v-model="filters.user_id"
        :placeholder="t('page.admin.projects.memberUsername')"
      />
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
      <AppTableColumn v-if="auth.isSuperAdmin" type="selection" variant="fixed" :width="48" />
      <AppTableColumn prop="name" variant="content" :label="t('page.admin.projects.name')" />
      <AppTableColumn prop="description" variant="content" :label="t('page.admin.projects.description')" />
      <AppTableColumn prop="member_count" variant="flex" :label="t('page.projectSettings.members')" />
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="240">
        <template #default="{ row }">
          <el-button link type="primary" @click="goDetail(row)">{{ t('common.view') }}</el-button>
          <el-button v-if="canManageProject(row)" link type="primary" @click="goDetail(row)">{{ t('common.edit') }}</el-button>
          <ConfirmDelete v-if="canDeleteProject(row)" @confirm="remove(row)">
            <el-button link type="danger">{{ t('common.delete') }}</el-button>
          </ConfirmDelete>
        </template>
      </AppTableColumn>
    </PaginatedTable>

    <ProjectFormDialog v-model="dialogVisible" :project="editProject" :loading="saving" @submit="save" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { batchDeleteProjects, createProject, deleteProject, listProjects } from '@/api/projects'
import { useAuthStore } from '@/stores/auth'
import { usePagination } from '@/composables/usePagination'
import { PROJECT_ROLE } from '@/utils/constants'
import { extractBlockersFromError, formatProjectBlockers } from '@/utils/project-delete-errors'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import ProjectFormDialog from '@/components/admin/ProjectFormDialog.vue'
import UserFilterSelect from '@/components/picker/UserFilterSelect.vue'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const { page, pageSize, total } = usePagination()

const filters = reactive({ name: '', user_id: null })
const items = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editProject = ref(null)
const selectedIds = ref([])

function canManageProject(row) {
  return auth.isSuperAdmin || row.my_role === PROJECT_ROLE.OWNER
}

function canDeleteProject(row) {
  return auth.isSuperAdmin || row.my_role === PROJECT_ROLE.OWNER
}

function goDetail(row) {
  router.push(`/projects/${row.id}`)
}

async function load() {
  loading.value = true
  try {
    const res = await listProjects({
      page: page.value,
      page_size: pageSize.value,
      name: filters.name || undefined,
      user_id: auth.isSuperAdmin ? (filters.user_id ?? undefined) : undefined,
    })
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.name = ''
  filters.user_id = null
  page.value = 1
  load()
}

function onSelectionChange(rows) {
  selectedIds.value = rows.map((r) => r.id)
}

function openCreate() {
  editProject.value = null
  dialogVisible.value = true
}

async function save(data) {
  saving.value = true
  try {
    const res = await createProject(data)
    ElMessage.success(t('page.admin.projects.created'))
    dialogVisible.value = false
    const created = res.data.data
    if (created?.id) {
      router.push(`/projects/${created.id}`)
    } else {
      load()
    }
  } finally {
    saving.value = false
  }
}

async function showDeleteError(error) {
  const blockers = extractBlockersFromError(error)
  const detail = formatProjectBlockers(blockers, t)
  const msg = detail ? `${t('page.projectSettings.deleteBlocked')}: ${detail}` : (error?.response?.data?.message || t('common.error'))
  await ElMessageBox.alert(msg, t('common.error'), { type: 'warning' })
}

async function remove(row) {
  try {
    await deleteProject(row.id)
    ElMessage.success(t('common.deleted'))
    load()
  } catch (error) {
    await showDeleteError(error)
  }
}

async function batchRemove() {
  try {
    const res = await batchDeleteProjects(selectedIds.value)
    const data = res.data.data
    selectedIds.value = []
    if (data?.failures?.length) {
      const lines = data.failures.map((f) => {
        const blockers = formatProjectBlockers(f.blockers, t)
        return `#${f.project_id}: ${f.message}${blockers ? ` (${blockers})` : ''}`
      })
      await ElMessageBox.alert(lines.join('\n'), t('page.projectSettings.batchDeletePartial'), { type: 'warning' })
    }
    if (data?.deleted_ids?.length) {
      ElMessage.success(t('page.projectSettings.batchDeleteDone', { count: data.deleted_ids.length }))
    }
    load()
  } catch (error) {
    await showDeleteError(error)
  }
}

onMounted(load)
</script>
