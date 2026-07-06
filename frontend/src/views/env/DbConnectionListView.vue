<template>
  <div class="db-list-view app-card">
    <PageHeader :title="t('page.env.db.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="reset">
        <template #primary>
          <el-button v-if="canEdit" type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
          <el-button v-if="canEdit && selectedIds.length" type="danger" @click="batchRemove">{{ t('common.batchDelete') }} ({{ selectedIds.length }})</el-button>
        </template>
        <el-input v-model="filters.keyword" :placeholder="t('page.env.db.keywordPlaceholder')" clearable />
        <el-select v-model="filters.bound" :placeholder="t('page.env.db.boundFilter')" clearable>
          <el-option :label="t('page.env.db.bound')" :value="true" />
          <el-option :label="t('page.env.db.unbound')" :value="false" />
        </el-select>
      </FilterBar>
      <PaginatedTable
        :data="items"
        :loading="loading"
        :total="total"
        v-model:page="page"
        v-model:page-size="pageSize"
        row-key="id"
        @page-change="load"
        @selection-change="onSelectionChange"
      >
        <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
        <AppTableColumn prop="connection_name" variant="content" :label="t('page.env.db.connectionName')" />
        <AppTableColumn prop="server_name" variant="fixed" :label="t('page.env.db.serverName')" :width="140" />
        <AppTableColumn prop="db_type" variant="fixed" :label="t('page.env.db.dbType')" :width="100" />
        <AppTableColumn prop="username" variant="fixed" :label="t('page.env.db.username')" :width="120" />
        <AppTableColumn prop="description" variant="content" :label="t('common.description')" />
        <AppTableColumn prop="is_bound" variant="fixed" :label="t('page.env.db.boundFilter')" :width="100">
          <template #default="{ row }">
            {{ row.is_bound ? t('page.env.db.bound') : t('page.env.db.unbound') }}
          </template>
        </AppTableColumn>
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :button-labels="[t('page.env.db.detail'), t('common.edit'), t('page.env.db.test'), t('page.env.db.testLogs'), t('common.delete')]">
          <template #default="{ row }">
            <el-button link @click="openDetail(row)">{{ t('common.detail') }}</el-button>
            <el-button v-if="canEdit" link @click="openEdit(row)">{{ t('common.edit') }}</el-button>
            <el-button
              link
              :disabled="row.db_type !== 'mysql'"
              @click="testConn(row)"
            >
              {{ t('page.env.db.test') }}
            </el-button>
            <el-button link @click="openLogs(row)">{{ t('page.env.db.testLogs') }}</el-button>
            <ConfirmDelete v-if="canEdit" @confirm="remove(row)">
              <el-button link type="danger">{{ t('common.delete') }}</el-button>
            </ConfirmDelete>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>

    <DbConnectionFormDialog v-model="showForm" :connection-id="editId" @saved="onSaved" />
    <DbConnectionDetailDialog v-model="showDetail" :connection-id="detailId" />
    <DbTestLogDrawer v-model="showLogs" :connection-id="logConnectionId" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteDbConnection, listDbConnections, testDbConnection, batchDeleteDbConnections } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import DbConnectionFormDialog from '@/components/env/DbConnectionFormDialog.vue'
import DbConnectionDetailDialog from '@/components/env/DbConnectionDetailDialog.vue'
import DbTestLogDrawer from '@/components/env/DbTestLogDrawer.vue'

const { t } = useI18n()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()
const filters = reactive({ keyword: '', bound: null })
const items = ref([])
const loading = ref(false)
const showForm = ref(false)
const editId = ref(null)
const showDetail = ref(false)
const detailId = ref(null)
const showLogs = ref(false)
const logConnectionId = ref(null)
const selectedIds = ref([])

function onSelectionChange(rows) {
  selectedIds.value = rows.map(function (r) { return r.id })
}

async function load() {
  const params = withProjectParams({
    page: page.value,
    page_size: pageSize.value,
    keyword: filters.keyword || undefined,
    bound: filters.bound ?? undefined,
  })
  if (!params) return
  loading.value = true
  try {
    const res = await listDbConnections(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function reset() {
  filters.keyword = ''
  filters.bound = null
  page.value = 1
  load()
}

function openCreate() {
  editId.value = null
  showForm.value = true
}

function openEdit(row) {
  editId.value = row.id
  showForm.value = true
}

function openDetail(row) {
  detailId.value = row.id
  showDetail.value = true
}

function openLogs(row) {
  logConnectionId.value = row.id
  showLogs.value = true
}

function onSaved() {
  ElMessage.success(t('common.saved'))
  load()
}

async function testConn(row) {
  if (row.db_type !== 'mysql') {
    ElMessage.warning(t('page.env.db.testUnsupported'))
    return
  }
  const res = await testDbConnection(row.id)
  const ok = res.data.data?.success
  if (ok) ElMessage.success(t('page.env.db.testOk'))
  else ElMessage.error(res.data.data?.message || t('common.failed'))
}

async function remove(row) {
  if (row.is_bound) {
    await ElMessageBox.confirm(t('page.env.db.deleteBoundHint'), t('common.warning'), { type: 'warning' })
  }
  await deleteDbConnection(row.id)
  ElMessage.success(t('common.deleted'))
  load()
}

async function batchRemove() {
  try {
    await ElMessageBox.confirm(
      t('common.batchDeleteConfirm', { count: selectedIds.value.length }),
      t('common.warning'),
      { type: 'warning' }
    )
    const res = await batchDeleteDbConnections(selectedIds.value)
    const data = res.data.data
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
