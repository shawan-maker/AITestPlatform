<template>
  <div class="project-list-view app-card">
    <PageHeader :title="t('page.admin.projects.title')" />

    <FilterBar @search="load" @reset="resetFilters">
      <template #primary>
        <el-button type="primary" @click="openCreate">{{ t('page.admin.projects.create') }}</el-button>
      </template>
      <el-input v-model="filters.name" :placeholder="t('page.admin.projects.keyword')" clearable />
      <el-input v-model="filters.username" :placeholder="t('page.admin.projects.memberUsername')" clearable />
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
      <AppTableColumn prop="name" variant="content" :label="t('page.admin.projects.name')" />
      <AppTableColumn prop="description" variant="content" :label="t('page.admin.projects.description')" />
      <AppTableColumn prop="member_count" variant="flex" :label="t('page.projectSettings.members')" />
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="240">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/admin/projects/${row.id}`)">{{ t('common.view') }}</el-button>
          <el-button link type="primary" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <ConfirmDelete @confirm="remove(row)">
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
import { ElMessage } from 'element-plus'
import { createProject, deleteProject, listProjects, updateProject } from '@/api/projects'
import { usePagination } from '@/composables/usePagination'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import ProjectFormDialog from '@/components/admin/ProjectFormDialog.vue'

const { t } = useI18n()
const router = useRouter()
const { page, pageSize, total } = usePagination()

const filters = reactive({ name: '', username: '' })
const items = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editProject = ref(null)

async function load() {
  loading.value = true
  try {
    const res = await listProjects({
      page: page.value,
      page_size: pageSize.value,
      name: filters.name || undefined,
      username: filters.username || undefined,
    })
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.name = ''
  filters.username = ''
  page.value = 1
  load()
}

function openCreate() {
  editProject.value = null
  dialogVisible.value = true
}

function openEdit(row) {
  editProject.value = row
  dialogVisible.value = true
}

async function save(data) {
  saving.value = true
  try {
    if (editProject.value?.id) {
      await updateProject(editProject.value.id, data)
      ElMessage.success(t('common.saved'))
    } else {
      await createProject(data)
      ElMessage.success(t('page.admin.projects.created'))
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await deleteProject(row.id)
  ElMessage.success(t('common.deleted'))
  load()
}

onMounted(load)
</script>
