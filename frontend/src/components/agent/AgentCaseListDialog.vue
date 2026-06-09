<template>
  <el-dialog
    v-model="visible"
    :title="t('page.agent.caseListTitle')"
    width="95%"
    top="3vh"
    destroy-on-close
    append-to-body
  >
    <!-- Toolbar: tabs + save button -->
    <div class="case-list-toolbar">
      <div class="case-list-tabs">
        <el-radio-group v-model="activeTab" size="small" @change="onTabChange">
          <el-radio-button value="all">{{ t('page.agent.tabAll') }}</el-radio-button>
          <el-radio-button value="功能">{{ t('page.agent.tabFunction') }}</el-radio-button>
          <el-radio-button value="安全">{{ t('page.agent.tabSecurity') }}</el-radio-button>
          <el-radio-button value="兼容">{{ t('page.agent.tabCompat') }}</el-radio-button>
          <el-radio-button value="易用">{{ t('page.agent.tabUsability') }}</el-radio-button>
          <el-radio-button value="性能">{{ t('page.agent.tabPerformance') }}</el-radio-button>
        </el-radio-group>
      </div>
      <el-button type="primary" @click="showSaveDialog = true">
        <el-icon><Plus /></el-icon> {{ t('page.agent.saveToCatalog') }}
      </el-button>
    </div>

    <!-- Case table -->
    <el-table
      :data="pagedCases"
      stripe
      highlight-current-row
      @selection-change="onSelectionChange"
      max-height="55vh"
      class="case-table"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column type="index" :label="t('common.index')" width="60" />
      <el-table-column prop="case_name" :label="t('page.functional.caseName')" min-width="150" show-overflow-tooltip />
      <el-table-column prop="type" :label="t('page.functional.type')" width="90">
        <template #default="{ row }">
          <el-tag size="small" type="primary" effect="light">{{ row.type || row.case_type || '功能' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="priority" :label="t('page.functional.priority')" width="70">
        <template #default="{ row }">
          <el-tag size="small" type="warning" effect="light">{{ row.priority || 'L1' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="preconditions" :label="t('page.functional.preconditions')" min-width="140" show-overflow-tooltip />
      <el-table-column prop="test_steps" :label="t('page.functional.steps')" min-width="180" show-overflow-tooltip />
      <el-table-column prop="expected_result" :label="t('page.functional.expectedResult')" min-width="160" show-overflow-tooltip />
      <el-table-column :label="t('common.actions')" width="80" fixed="right">
        <template #default="{ row, $index }">
          <el-link type="primary" @click="openEditor(row, getRealIndex($index))">编辑</el-link>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div class="case-list-pagination">
      <span>{{ t('page.agent.totalCount', { count: filteredCases.length }) }}</span>
      <el-pagination
        small
        layout="prev, pager, next"
        :total="filteredCases.length"
        :page-size="pageSize"
        v-model:current-page="currentPage"
      />
    </div>

    <!-- ===== Edit Drawer ===== -->
    <el-drawer
      v-model="editorVisible"
      :title="t('page.agent.editCase')"
      direction="rtl"
      size="50%"
      append-to-body
    >
      <el-form v-if="editingCase" :model="editingCase" label-position="top" size="large">
        <el-form-item :label="t('page.functional.caseName')">
          <el-input v-model="editingCase.case_name" :placeholder="t('page.functional.caseNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('page.functional.priority')">
          <el-select v-model="editingCase.priority" style="width: 100%">
            <el-option label="P0" value="P0" />
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('page.functional.type')">
          <el-select v-model="editingCase.type" style="width: 100%">
            <el-option :label="t('page.functional.typeFunctional')" value="功能" />
            <el-option label="安全" value="安全" />
            <el-option label="兼容" value="兼容" />
            <el-option label="易用" value="易用" />
            <el-option label="性能" value="性能" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('page.functional.testPoint')">
          <el-input v-model="editingCase.test_point" :placeholder="t('page.functional.testPoint')" />
        </el-form-item>
        <el-form-item :label="`* ${t('page.functional.preconditions')}`">
          <el-input
            v-model="editingCase.preconditions"
            type="textarea"
            :rows="3"
            :placeholder="t('page.functional.preconditionsPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('page.functional.testData')">
          <el-input
            v-model="editingCase.test_data"
            type="textarea"
            :rows="2"
            :placeholder="t('page.functional.testDataPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="`* ${t('page.functional.steps')}`">
          <el-input
            v-model="editingCase.test_steps"
            type="textarea"
            :rows="5"
            placeholder="1. ...&#10;2. ..."
          />
        </el-form-item>
        <el-form-item :label="`* ${t('page.functional.expectedResult')}`">
          <el-input
            v-model="editingCase.expected_result"
            type="textarea"
            :rows="4"
            :placeholder="t('page.functional.expectedResultPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <div class="editor-hint">{{ t('page.agent.aiGeneratedHint') }}</div>
      <template #footer>
        <el-button @click="editorVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveEditedCase">{{ t('common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- ===== Save to Catalog Dialog ===== -->
    <el-dialog
      v-model="showSaveDialog"
      :title="t('page.agent.saveToCatalog')"
      width="500px"
      append-to-body
    >
      <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px;">
        {{ t('page.agent.saveToHint') }}
        <el-link type="primary">{{ t('page.agent.goToView') }} 🔗</el-link>
      </el-alert>
      <p class="save-hint-text">
        {{ t('page.agent.selectedCount', { count: selectedCases.length }) }}
      </p>
      <el-form :label-width="100">
        <el-form-item :label="t('page.agent.project')">
          <el-select
            v-model="saveForm.projectId"
            :placeholder="t('page.agent.selectProject')"
            style="width: 100%"
            @change="onProjectChange"
          >
            <el-option
              v-for="pv in projectVersions"
              :key="pv.id"
              :label="pv.name"
              :value="pv.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('page.agent.catalog')">
          <el-select
            v-model="saveForm.catalogId"
            :placeholder="saveForm.projectId ? t('page.agent.selectCatalog') : t('page.agent.selectProjectFirst')"
            style="width: 100%"
            :disabled="!saveForm.projectId || catalogsLoading"
          >
            <el-option
              v-for="cat in catalogs"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button
          type="primary"
          :disabled="!saveForm.catalogId || selectedCases.length === 0"
          :loading="saving"
          @click="confirmSave"
        >{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { listProjects } from '@/api/projects'
import { getCaseCatalogTree } from '@/api/functional'
import { getApiCatalogTree } from '@/api/apiTest'

const props = defineProps({
  payload: { type: Object, default: null },
  genType: { type: String, default: 'functional' },
  projectId: { type: [Number, String], default: null }, // 当前项目ID，用于默认选中
})

const emit = defineEmits(['save'])

const { t } = useI18n()

// Dialog visibility (controlled by parent via v-model)
const visible = defineModel({ type: Boolean, default: false })

// Tab filtering
const activeTab = ref('all')
const currentPage = ref(1)
const pageSize = 10

// Selection
const selectedCases = ref([])

// Editor drawer
const editorVisible = ref(false)
const editingCase = ref(null)
const editingIndex = ref(-1)

// Save dialog
const showSaveDialog = ref(false)
const saving = ref(false)
const saveForm = ref({
  projectId: null, // 改为 projectId，语义更清晰
  catalogId: null,
})
const projectVersions = ref([]) // 实际是项目列表
const catalogs = ref([]) // 本地维护目录列表，不再从prop传入
const catalogsLoading = ref(false)

// Computed: all cases from payload
const allCases = computed(() => {
  if (!props.payload) return []
  return props.payload.cases || props.payload.test_points?.flatMap(tp => tp.cases || []) || []
})

// Computed: filtered by tab
const filteredCases = computed(() => {
  const cases = allCases.value
  if (activeTab.value === 'all') return cases
  // Filter by type matching the tab name
  return cases.filter(c => {
    const ct = (c.type || c.case_type || '功能').trim()
    return ct.includes(activeTab.value) || activeTab.value === 'all'
  })
})

// Computed: paged cases
const pagedCases = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredCases.value.slice(start, start + pageSize)
})

function onSelectionChange(rows) {
  selectedCases.value = rows
}

function onTabChange() {
  currentPage.value = 1
}

function getRealIndex(pageIdx) {
  return (currentPage.value - 1) * pageSize + pageIdx
}

function openEditor(caseRow, realIndex) {
  editingCase.value = { ...caseRow }
  // 调试：查看test_data原始类型和值
  console.log('[DEBUG] openEditor: test_data =', caseRow.test_data, ', typeof =', typeof caseRow.test_data)
  // 修复：test_data为对象时JSON序列化，无数据时为空字符串
  if (editingCase.value.test_data !== undefined && editingCase.value.test_data !== null) {
    if (typeof editingCase.value.test_data === 'object') {
      try {
        editingCase.value.test_data = JSON.stringify(editingCase.value.test_data, null, 2)
        console.log('[DEBUG] openEditor: stringified test_data =', editingCase.value.test_data)
      } catch (e) {
        console.error('[DEBUG] openEditor: JSON.stringify test_data failed', e)
        editingCase.value.test_data = ''
      }
    }
  } else {
    editingCase.value.test_data = ''
  }
  editingIndex.value = realIndex
  editorVisible.value = true
}

function saveEditedCase() {
  if (editingIndex.value >= 0 && editingCase.value) {
    // Update local case data in payload
    const cases = allCases.value
    if (cases[editingIndex.value]) {
      Object.assign(cases[editingIndex.value], editingCase.value)
    }
  }
  editorVisible.value = false
  ElMessage.success(t('common.saved'))
}

async function confirmSave() {
  if (!saveForm.value.catalogId || !selectedCases.value.length) return
  saving.value = true
  try {
    // 后端只需要 catalog_id 和 case_indexes，不需要 project_id
    emit('save', {
      catalog_id: saveForm.value.catalogId,
      case_indexes: selectedCases.value.map((c, i) => {
        const idx = allCases.value.indexOf(c)
        return idx >= 0 ? idx : i
      }),
    })
    showSaveDialog.value = false
    // 不在子组件中显示提示，由父组件统一显示
  } finally {
    saving.value = false
  }
}

// 将目录树扁平化为带路径的列表
function flattenCatalogs(tree, parentPath = '') {
  console.log('[DEBUG] flattenCatalogs 开始, parentPath:', parentPath, 'tree长度:', tree?.length)
  const result = []
  function walk(nodes, path) {
    for (const node of nodes) {
      const currentPath = path ? `${path}/${node.name}` : node.name
      console.log('[DEBUG] walk 处理节点:', node.name, '当前路径:', currentPath)
      result.push({
        id: node.id,
        name: currentPath
      })
      if (node.children?.length) {
        walk(node.children, currentPath)
      }
    }
  }
  walk(tree, parentPath)
  console.log('[DEBUG] flattenCatalogs 完成, 结果数量:', result.length, '结果示例:', result.slice(0, 3))
  return result
}

// 项目切换时，重新加载该项目的目录列表
async function onProjectChange(projectId) {
  console.log('[DEBUG] onProjectChange: projectId =', projectId)
  // 重置目录选择
  saveForm.value.catalogId = null
  catalogs.value = []
  
  if (!projectId) return
  
  catalogsLoading.value = true
  try {
    let res
    if (props.genType === 'api') {
      res = await getApiCatalogTree({ project_id: projectId })
    } else {
      res = await getCaseCatalogTree({ project_id: projectId })
    }
    const rawTree = res.data.data?.items ?? res.data.data ?? []
    // 扁平化目录树，显示完整路径
    catalogs.value = flattenCatalogs(rawTree)
    console.log('[DEBUG] onProjectChange: loaded and flattened catalogs =', catalogs.value)
  } catch (e) {
    console.error('[DEBUG] onProjectChange: failed to load catalogs', e)
    catalogs.value = []
  } finally {
    catalogsLoading.value = false
  }
}

// 监听保存对话框打开，加载项目列表
watch(() => showSaveDialog.value, async (visible) => {
  if (visible) {
    // 设置默认选中的项目（使用当前项目）
    if (!saveForm.value.projectId && props.projectId) {
      saveForm.value.projectId = props.projectId
      // 加载默认项目的目录
      await onProjectChange(props.projectId)
    }
    // 加载项目列表（只加载一次）
    if (projectVersions.value.length === 0) {
      console.log('[DEBUG] showSaveDialog opened, loading project list...')
      try {
        const res = await listProjects()
        projectVersions.value = res.data.data?.items ?? res.data.data ?? []
        console.log('[DEBUG] Loaded project list:', projectVersions.value)
      } catch (e) {
        console.error('[DEBUG] Failed to load project list:', e)
      }
    }
  } else {
    // 关闭对话框时重置表单
    saveForm.value.projectId = null
    saveForm.value.catalogId = null
    catalogs.value = []
  }
})
</script>

<style scoped lang="scss">
.case-list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.case-list-tabs {
  flex: 1;
}

.case-list-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.editor-hint {
  margin-top: 16px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.save-hint-text {
  margin-bottom: 16px;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.case-table {
  width: 100%;
}
</style>
