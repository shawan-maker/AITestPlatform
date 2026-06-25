<template>
  <div v-if="visible" class="precondition-panel">
    <div class="precondition-header" @click="collapsed = !collapsed">
      <el-icon :class="{ 'is-expanded': !collapsed }"><ArrowRight /></el-icon>
      <span class="precondition-title">{{ t('page.apiCases.preconditionCases') }}</span>
      <span class="precondition-count">{{ preconditionList.length }}</span>
      <el-button size="small" link type="primary" @click.stop="openConfigDialog">{{ t('common.configure') }}</el-button>
    </div>
    <div v-show="!collapsed" class="precondition-body">
      <el-table :key="'pre-' + refreshKey" v-if="preconditionList.length" :data="preconditionList" size="small" border>
        <el-table-column type="index" :label="t('common.index') || '序号'" :width="60" align="center" />
        <el-table-column prop="title" :label="t('page.functional.caseName') || '用例名称'" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ stripTitleSuffix(row.title) }}</template>
        </el-table-column>
        <el-table-column :label="t('page.defects.interfaceName') || '接口'" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ getCaseInterfaceName(row) }}</template>
        </el-table-column>
        <el-table-column label="Path" min-width="180">
          <template #default="{ row }">
            <el-tag v-if="getCaseMethod(row)" size="small" :type="methodType(getCaseMethod(row))" style="margin-right: 4px">{{ getCaseMethod(row) }}</el-tag>
            <span>{{ getCasePath(row) || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('page.test.execStatus') || '执行状态'" :width="90" align="center">
          <template #default="{ row }">
            <span class="exec-dot" :class="dotClass(row.exec_status)"></span>
            {{ statusLabel(row.exec_status) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions') || '操作'" :width="120" align="center">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="viewCase(row)">{{ t('common.view') || '查看' }}</el-button>
            <el-button size="small" link type="danger" @click="unlinkCase(row)">{{ t('page.apiCases.unlink') || '移除' }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else :description="t('page.apiCases.noPreconditions')" :image-size="40" />
    </div>

    <!-- 配置前置操作对话框：仅当前接口的前置用例 -->
    <el-dialog
      v-model="showConfigDialog"
      :title="t('page.apiCases.configurePreconditions') || '配置前置操作'"
      width="600px"
      :destroy-on-close="true"
      @open="onConfigDialogOpen"
    >
      <div v-loading="configLoading">
        <el-input
          v-model="configSearchKey"
          :placeholder="t('page.apiCases.searchCases') || '搜索用例名称'"
          clearable
          size="default"
          style="margin-bottom: 12px"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-table
          :data="filteredConfigCases"
          size="small"
          border
          row-key="id"
          max-height="400"
          @selection-change="onConfigSelectionChange"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column prop="title" :label="t('page.functional.caseName') || '用例名称'" min-width="180" show-overflow-tooltip />
          <el-table-column label="Path" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag v-if="getCaseMethod(row)" size="small" :type="methodType(getCaseMethod(row))" style="margin-right: 4px">{{ getCaseMethod(row) }}</el-tag>
              <span>{{ getCasePath(row) || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!configLoading && !localPreconditionCases.length" :description="t('page.apiCases.noPreconditionCasesForConfig')" :image-size="60" />
      </div>
      <template #footer>
        <el-button @click="showConfigDialog = false">{{ t('common.cancel') || '取消' }}</el-button>
        <el-button type="primary" @click="onConfigConfirm">{{ t('common.confirm') || '确定' }}</el-button>
      </template>
    </el-dialog>
  </div>
  <div v-else class="precondition-add">
    <el-button size="small" link type="primary" @click="openConfigDialog">+ {{ t('page.apiCases.addPrecondition') }}</el-button>

    <!-- 配置前置操作对话框（无关联时也会渲染） -->
    <el-dialog
      v-model="showConfigDialog"
      :title="t('page.apiCases.configurePreconditions') || '配置前置操作'"
      width="600px"
      :destroy-on-close="true"
      @open="onConfigDialogOpen"
    >
      <div v-loading="configLoading">
        <el-input
          v-model="configSearchKey"
          :placeholder="t('page.apiCases.searchCases') || '搜索用例名称'"
          clearable
          size="default"
          style="margin-bottom: 12px"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-table
          :data="filteredConfigCases"
          size="small"
          border
          row-key="id"
          max-height="400"
          @selection-change="onConfigSelectionChange"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column prop="title" :label="t('page.functional.caseName') || '用例名称'" min-width="180" show-overflow-tooltip />
          <el-table-column label="Path" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag v-if="getCaseMethod(row)" size="small" :type="methodType(getCaseMethod(row))" style="margin-right: 4px">{{ getCaseMethod(row) }}</el-tag>
              <span>{{ getCasePath(row) || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!configLoading && !localPreconditionCases.length" :description="t('page.apiCases.noPreconditionCasesForConfig')" :image-size="60" />
      </div>
      <template #footer>
        <el-button @click="showConfigDialog = false">{{ t('common.cancel') || '取消' }}</el-button>
        <el-button type="primary" @click="onConfigConfirm">{{ t('common.confirm') || '确定' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, Search } from '@element-plus/icons-vue'
import { listApiCases, batchGetApiCases, unlinkPrecondition } from '@/api/apiTest'

const { t } = useI18n()
const router = useRouter()

const props = defineProps({
  preconditionIds: { type: Array, default: () => [] },
  interfaceId: { type: Number, default: null },
  /** 当前主用例 ID，用于解绑 API 调用 */
  caseId: { type: Number, default: null },
  /** 父组件提供的前置用例完整列表（用于刷新 exec_status 等字段） */
  allPreconditionCases: { type: Array, default: () => [] },
  /** 父组件递增此值以强制刷新内部缓存 */
  refreshKey: { type: Number, default: 0 },
})

const emit = defineEmits(['update:preconditionIds'])

const collapsed = ref(false)
const showConfigDialog = ref(false)
const configLoading = ref(false)
const configSearchKey = ref('')

// Local cache of precondition case data (keyed by case id)
const caseDataMap = ref({})

// 当前接口的前置用例列表（用于配置对话框）
const localPreconditionCases = ref([])

// 配置对话框中的当前勾选
const configSelectedIds = ref(new Set())

const visible = computed(function () {
  return props.preconditionIds && props.preconditionIds.length > 0
})

const preconditionList = computed(function () {
  if (!props.preconditionIds || !props.preconditionIds.length) return []
  // 优先从父组件提供的实时数据中查找（确保 exec_status 等字段是最新的）
  var parentMap = {}
  if (props.allPreconditionCases && props.allPreconditionCases.length) {
    props.allPreconditionCases.forEach(function (c) {
      if (c && c.id) parentMap[c.id] = c
    })
  }
  var map = caseDataMap.value
  var result = props.preconditionIds
    .filter(function (id) { return parentMap[id] || map[id] })
    .map(function (id) { return parentMap[id] || map[id] })
  return result
})

const filteredConfigCases = computed(function () {
  var kw = configSearchKey.value ? configSearchKey.value.toLowerCase() : ''
  if (!kw) return localPreconditionCases.value
  return localPreconditionCases.value.filter(function (c) {
    return (c.title || '').toLowerCase().indexOf(kw) >= 0
  })
})

function stripTitleSuffix(title) {
  if (!title) return ''
  return title.replace(/[（(][^）)]*[）)]$/, '').trim() || title
}

function dotClass(status) {
  if (status === 'running') return 'dot-running'
  if (status === 'success') return 'dot-success'
  if (status === 'fail' || status === 'failed') return 'dot-failed'
  if (status === 'error') return 'dot-error'
  return 'dot-pending'
}

function statusLabel(status) {
  if (status === 'running') return '运行中'
  if (status === 'success') return t('common.success') || '成功'
  if (status === 'fail' || status === 'failed') return t('page.test.resultFail') || '失败'
  if (status === 'error') return t('common.error') || '错误'
  return '-'
}

function methodType(method) {
  var m = (method || '').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

function getCaseMethod(row) {
  if (row.interface_method) return row.interface_method
  var p = row.case_payload || {}
  return (p.method || (p.interface && p.interface.method) || '').toUpperCase()
}

function getCasePath(row) {
  if (row.interface_path) return row.interface_path
  var p = row.case_payload || {}
  return p.path || (p.interface && p.interface.url) || ''
}

function getCaseInterfaceName(row) {
  if (row.interface_name) return row.interface_name
  var p = row.case_payload || {}
  return (p.interface && (p.interface.summary || p.interface.name)) || row.title || '-'
}

// ========== 查看前置用例详情 ==========
function viewCase(row) {
  router.push('/cases/api/cases/' + row.id)
}

// ========== 移除关联（解除前置用例与主用例的关联） ==========
async function unlinkCase(row) {
  try {
    await ElMessageBox.confirm(
      t('page.apiCases.unlinkConfirm') || '确认移除该前置操作关联？前置用例本身不会被删除。',
      t('common.confirm') || '确认',
      { confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel'), type: 'warning' }
    )
  } catch { return }

  try {
    if (props.caseId) {
      await unlinkPrecondition(props.caseId, row.id)
    }
    var newIds = (props.preconditionIds || []).filter(function (id) { return id !== row.id })
    emit('update:preconditionIds', newIds)
    ElMessage.success(t('page.apiCases.unlinkSuccess') || '已移除关联')
  } catch (e) {
    ElMessage.error(e?.message || '移除关联失败')
  }
}

// ========== 配置对话框 ==========
function openConfigDialog() {
  showConfigDialog.value = true
}

async function onConfigDialogOpen() {
  configSearchKey.value = ''
  configSelectedIds.value = new Set(props.preconditionIds || [])
  configLoading.value = true
  try {
    if (!props.interfaceId) {
      localPreconditionCases.value = []
      return
    }
    var res = await listApiCases(props.interfaceId, { case_kind: 'precondition', page: 1, page_size: 200 })
    localPreconditionCases.value = res.data.data?.items ?? res.data.data ?? []
    // 等表格渲染后恢复勾选
    nextTick(function () {
      nextTick(function () {
        syncConfigSelection()
      })
    })
  } catch (e) {
    console.error('[PreconditionPanel] 加载前置用例失败:', e)
    localPreconditionCases.value = []
  } finally {
    configLoading.value = false
  }
}

var _isSyncingConfig = false

function syncConfigSelection() {
  _isSyncingConfig = true
  // 直接通过 selectedIds 计算，不依赖 el-table ref
  setTimeout(function () { _isSyncingConfig = false }, 200)
}

function onConfigSelectionChange(rows) {
  if (_isSyncingConfig) return
  var allIds = localPreconditionCases.value.map(function (c) { return c.id })
  allIds.forEach(function (id) { configSelectedIds.value.delete(id) })
  rows.forEach(function (r) { configSelectedIds.value.add(r.id) })
  configSelectedIds.value = new Set(configSelectedIds.value)
}

function onConfigConfirm() {
  var newIds = Array.from(configSelectedIds.value)
  // 确保选中用例的数据在 caseDataMap 中
  localPreconditionCases.value.forEach(function (c) {
    if (configSelectedIds.value.has(c.id)) {
      caseDataMap.value[c.id] = c
    }
  })
  caseDataMap.value = Object.assign({}, caseDataMap.value)
  emit('update:preconditionIds', newIds)
  showConfigDialog.value = false
}

// ========== 数据加载：确保 preconditionIds 对应的用例数据 ==========
watch(
  function () { return props.preconditionIds },
  function (ids) {
    if (!ids || !ids.length) return
    var missing = ids.filter(function (id) { return !caseDataMap.value[id] })
    if (missing.length) {
      loadMissingCases(missing)
    }
  },
  { immediate: true, deep: true }
)

// ========== 父组件刷新前置用例数据时（如调试运行后），同步更新缓存 ==========
watch(
  function () { return props.refreshKey },
  function () {
    var cases = props.allPreconditionCases
    if (!cases || !cases.length) return
    var updated = false
    cases.forEach(function (c) {
      if (c && c.id) {
        caseDataMap.value[c.id] = Object.assign({}, c)
        updated = true
      }
    })
    if (updated) {
      caseDataMap.value = Object.assign({}, caseDataMap.value)
    }
  }
)

async function loadMissingCases(ids) {
  try {
    var res = await batchGetApiCases(ids)
    var cases = res.data.data ?? []
    cases.forEach(function (c) {
      if (!caseDataMap.value[c.id]) {
        caseDataMap.value[c.id] = c
      }
    })
    caseDataMap.value = Object.assign({}, caseDataMap.value)
  } catch (e) {
    console.error('[PreconditionPanel] Failed to load missing cases:', e)
  }
}
</script>

<style scoped lang="scss">
.precondition-panel {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  margin-bottom: 12px;
  background: var(--el-fill-color-lighter);
}

.precondition-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  font-size: 13px;

  .el-icon {
    transition: transform 0.2s;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    &.is-expanded { transform: rotate(90deg); }
  }

  .precondition-title {
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .precondition-count {
    font-size: 11px;
    color: var(--el-text-color-placeholder);
    margin-right: auto;
  }

  &:hover {
    background: var(--el-fill-color);
  }
}

.precondition-body {
  padding: 4px 12px 8px;
}

.exec-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
  &.dot-running { background-color: var(--el-color-primary); animation: dot-pulse 1s ease-in-out infinite; }
  &.dot-success { background-color: var(--el-color-success); }
  &.dot-failed { background-color: var(--el-color-danger); }
  &.dot-error { background-color: var(--el-color-warning); }
  &.dot-pending { background-color: var(--el-text-color-placeholder); }
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.precondition-add {
  margin-bottom: 8px;
}
</style>
