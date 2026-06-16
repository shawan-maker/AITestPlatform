<template>
  <!-- v2-Q4: 接口用例详情页 - 对照设计稿实现 -->
  <div v-loading="loading" class="api-case-detail">
    <!-- 顶部工具栏 -->
    <div class="detail-header">
      <div class="header-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <span class="header-title">{{ t('page.apiCases.caseDetail') }}</span>
        <span v-if="caseDetail?.title || caseDetail?.name" class="case-name">
          {{ caseDetail.title || caseDetail.name }}
        </span>
        <el-dropdown trigger="click">
          <el-button size="small">
            {{ t('page.apiCases.batchOps') }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>{{ t('page.apiCases.actionCreate') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchKeyword"
          :placeholder="t('page.apiCases.searchCases')"
          clearable
          size="small"
          style="width: 260px"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button text size="small"><el-icon><Setting /></el-icon></el-button>
        <el-dropdown trigger="click">
          <el-button size="small">
            {{ t('page.apiCases.globalVars') }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>var_a</el-dropdown-item>
              <el-dropdown-item>var_b</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 主内容区：左右分栏 -->
    <div class="detail-body">
      <!-- 左侧：前置依赖 + 测试用例列表 -->
      <div class="left-panel">
        <div class="panel-search">
          <el-input
            v-model="searchKeyword"
            :placeholder="t('page.apiCases.searchCases')"
            clearable
            size="small"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>

        <!-- 前置依赖 -->
        <div class="case-section">
          <div class="section-header" @click="toggleSection('pre')">
            <el-icon :class="{ 'is-expanded': expandedSections.pre }"><ArrowRight /></el-icon>
            <span class="section-label">{{ t('page.apiCases.preconditionCases') }}</span>
            <span class="section-count">{{ filteredPreconditions.length }}</span>
          </div>
          <div v-show="expandedSections.pre" class="section-body">
            <div
              v-for="(item, idx) in filteredPreconditions"
              :key="'pre-' + item.id"
              class="case-item"
              :class="{ active: selectedCaseId === item.id }"
              @click="selectCase(item)"
            >
              <span class="item-status-dot" :class="dotClass(item.exec_status)"></span>
              <span class="item-name">{{ item.title || item.name }}</span>
              <div class="item-actions">
                <el-button text size="small" @click.stop><el-icon><Clock /></el-icon></el-button>
                <el-button text size="small" @click.stop><el-icon><CopyDocument /></el-icon></el-button>
                <el-button text size="small" @click.stop="deleteCase(item)"><el-icon><Delete /></el-icon></el-button>
              </div>
            </div>
            <el-empty v-if="!filteredPreconditions.length" description="" :image-size="40" />
          </div>
        </div>

        <!-- 测试用例 -->
        <div class="case-section">
          <div class="section-header" @click="toggleSection('main')">
            <el-icon :class="{ 'is-expanded': expandedSections.main }"><ArrowRight /></el-icon>
            <span class="section-label">{{ t('page.apiCases.mainCases') }}</span>
            <span class="section-count">{{ filteredMainCases.length }}</span>
            <el-tag v-if="batchMode" size="small" type="danger" class="batch-tag">{{ t('page.apiCases.batchOps') }}</el-tag>
          </div>
          <div v-show="expandedSections.main" class="section-body">
            <div
              v-for="(item, idx) in filteredMainCases"
              :key="'main-' + item.id"
              class="case-item"
              :class="{ active: selectedCaseId === item.id }"
              @click="selectCase(item)"
            >
              <span class="item-status-dot" :class="dotClass(item.exec_status)"></span>
              <span class="item-name">{{ item.title || item.name }}</span>
              <span class="item-time">{{ formatTime(item.updated_at) }}</span>
            </div>
            <el-empty v-if="!filteredMainCases.length" description="" :image-size="40" />
          </div>
        </div>
      </div>

      <!-- 分隔线 -->
      <div class="panel-divider"></div>

      <!-- 右侧：调试面板 -->
      <div class="right-panel">
        <!-- 请求配置行 -->
        <div class="request-config-bar">
          <el-select v-model="debugForm.method" size="default" style="width: 100px">
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
            <el-option label="PATCH" value="PATCH" />
          </el-select>
          <el-input v-model="debugForm.base_url" placeholder="${base_url}" size="default" style="flex: 1" />
          <el-input v-model="debugForm.path" placeholder="/path" size="default" style="flex: 2" />
          <el-button v-if="!running" type="primary" @click="runDebug">{{ t('page.apiCases.debugRun') }}</el-button>
          <el-button v-else type="warning" @click="cancelDebug">{{ t('common.cancel') }}</el-button>
          <el-button @click="saveDebug">{{ t('page.apiCases.debugSave') }}</el-button>
        </div>

        <!-- 子Tab导航 -->
        <div class="sub-tabs-nav">
          <div
            v-for="tab in subTabs"
            :key="tab.key"
            class="sub-tab-item"
            :class="{ active: activeSubTab === tab.key }"
            @click="activeSubTab = tab.key"
          >{{ t(tab.label) }}</div>
        </div>

        <!-- 子Tab内容 -->
        <div class="sub-tab-content">
          <!-- Headers Tab -->
          <div v-show="activeSubTab === 'headers'" class="tab-pane">
            <AppTable :data="headersData" size="small" border>
              <AppTableColumn prop="name" :label="t('page.apiCases.paramName')" min-width="140" />
              <AppTableColumn prop="value" :label="t('page.apiCases.paramValue')" min-width="200" />
              <AppTableColumn prop="desc" :label="t('page.apiCases.fieldDesc')" min-width="160" />
              <AppTableColumn label="" width="60" align="center">
                <template #default>
                  <el-button text type="danger" size="small"><el-icon><Delete /></el-icon></el-button>
                </template>
              </AppTableColumn>
            </AppTable>
            <el-button text size="small" class="add-row-btn" @click="addRow('headers')">+ {{ t('page.apiCases.addParam') }}</el-button>
          </div>

          <!-- Params Tab -->
          <div v-show="activeSubTab === 'params'" class="tab-pane">
            <div class="param-type-label">QUERY参数</div>
            <AppTable :data="queryParamsData" size="small" border>
              <AppTableColumn prop="name" :label="t('page.apiCases.paramName')" min-width="140" />
              <AppTableColumn prop="value" :label="t('page.apiCases.paramValue')" min-width="200" />
              <AppTableColumn prop="desc" :label="t('page.apiCases.fieldDesc')" min-width="160" />
              <AppTableColumn label="" width="80" align="center">
                <template #default><span class="op-link">{{ t('common.action') }}</span></template>
              </AppTableColumn>
            </AppTable>
            <el-button text size="small" class="add-row-btn" @click="addRow('query')">+ {{ t('page.apiCases.addParam') }}</el-button>
          </div>

          <!-- Path Tab -->
          <div v-show="activeSubTab === 'path'" class="tab-pane">
            <AppTable :data="pathParamsData" size="small" border>
              <AppTableColumn prop="name" :label="t('page.apiCases.paramName')" min-width="140" />
              <AppTableColumn prop="value" :label="t('page.apiCases.paramValue')" min-width="200" />
              <AppTableColumn prop="desc" :label="t('page.apiCases.fieldDesc')" min-width="160" />
              <AppTableColumn label="" width="80" align="center">
                <template #default><span class="op-link">{{ t('common.action') }}</span></template>
              </AppTableColumn>
            </AppTable>
            <el-button text size="small" class="add-row-btn" @click="addRow('path')">+ {{ t('page.apiCases.addParam') }}</el-button>
          </div>

          <!-- Body Tab -->
          <div v-show="activeSubTab === 'body'" class="tab-pane body-tab">
            <MonacoJsonEditor v-model="bodyContent" :height="280" lang="json" />
          </div>

          <!-- 抽取 Tab -->
          <div v-show="activeSubTab === 'extract'" class="tab-pane">
            <AppTable :data="extractData" size="small" border>
              <AppTableColumn prop="name" :label="t('page.apiCases.paramName')" min-width="140" />
              <AppTableColumn prop="expression" :label="t('page.apiCases.fieldPath')" min-width="220" />
              <AppTableColumn prop="desc" :label="t('page.apiCases.fieldDesc')" min-width="160" />
              <AppTableColumn label="" width="60" align="center">
                <template #default>
                  <el-button text type="danger" size="small"><el-icon><Delete /></el-icon></el-button>
                </template>
              </AppTableColumn>
            </AppTable>
            <el-button text size="small" class="add-row-btn" @click="addRow('extract')">+ {{ t('page.apiCases.addParam') }}</el-button>
          </div>

          <!-- 断言 Tab -->
          <div v-show="activeSubTab === 'assert'" class="tab-pane">
            <AppTable :data="assertionsData" size="small" border>
              <AppTableColumn prop="name" :label="t('page.apiCases.paramName')" min-width="140" />
              <AppTableColumn prop="expression" :label="t('page.apiCases.fieldPath')" min-width="220" />
              <AppTableColumn prop="expected" label="Expected" min-width="120" />
              <AppTableColumn label="" width="60" align="center">
                <template #default>
                  <el-button text type="danger" size="small"><el-icon><Delete /></el-icon></el-button>
                </template>
              </AppTableColumn>
            </AppTable>
            <el-button text size="small" class="add-row-btn" @click="addRow('assert')">+ {{ t('page.apiCases.addParam') }}</el-button>
          </div>

          <!-- 前置操作 Tab -->
          <div v-show="activeSubTab === 'preOps'" class="tab-pane">
            <div v-if="preOpsData.length" class="pre-ops-list">
              <div v-for="(op, idx) in preOpsData" :key="idx" class="pre-op-item">
                <div class="pre-op-header">
                  <el-tag size="small" :type="methodTagType(op.method)">{{ (op.method || 'GET').toUpperCase() }}</el-tag>
                  <span class="pre-op-title">{{ op.title || op.path || `前置操作 ${idx + 1}` }}</span>
                </div>
                <div class="pre-op-detail" v-if="op.path">
                  <span class="detail-label">路径:</span> {{ op.path }}
                </div>
                <div class="pre-op-detail" v-if="op.headers && Object.keys(op.headers).length">
                  <span class="detail-label">Headers:</span> {{ JSON.stringify(op.headers) }}
                </div>
                <div class="pre-op-detail" v-if="op.query && Object.keys(op.query).length">
                  <span class="detail-label">Query:</span> {{ JSON.stringify(op.query) }}
                </div>
                <div class="pre-op-detail" v-if="op.body">
                  <span class="detail-label">Body:</span>
                  <pre class="pre-op-body">{{ typeof op.body === 'string' ? op.body : JSON.stringify(op.body, null, 2) }}</pre>
                </div>
                <div class="pre-op-detail" v-if="op.extracts && op.extracts.length">
                  <span class="detail-label">提取:</span>
                  <span v-for="(ext, ei) in op.extracts" :key="ei" class="extract-tag">{{ ext.var_name || ext.name }}: {{ ext.extract_expr || ext.expression }}</span>
                </div>
                <div class="pre-op-detail" v-if="op.assertions && op.assertions.length">
                  <span class="detail-label">断言:</span>
                  <span v-for="(ast, ai) in op.assertions" :key="ai" class="assert-tag">{{ ast.field || ast.target }} {{ ast.type || 'eq' }} {{ ast.expected }}</span>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无前置操作" :image-size="60" />
          </div>

          <!-- 后置操作 Tab -->
          <div v-show="activeSubTab === 'postOps'" class="tab-pane">
            <div v-if="setupScriptText || teardownScriptText" class="scripts-container">
              <div v-if="setupScriptText" class="script-block">
                <h4>Setup Script (前置脚本)</h4>
                <pre class="script-content">{{ setupScriptText }}</pre>
              </div>
              <div v-if="teardownScriptText" class="script-block">
                <h4>Teardown Script (后置脚本)</h4>
                <pre class="script-content">{{ teardownScriptText }}</pre>
              </div>
            </div>
            <el-empty v-else description="暂无后置操作" :image-size="60" />
          </div>
        </div>

        <!-- 底部响应区 -->
        <div class="response-section">
          <!-- 响应Tab导航 -->
          <div class="resp-tabs-nav">
            <div
              v-for="rtab in respTabs"
              :key="rtab.key"
              class="resp-tab-item"
              :class="{ active: activeRespTab === rtab.key }"
              @click="activeRespTab = rtab.key"
            >{{ t(rtab.label) }}</div>
            <div class="resp-tab-spacer"></div>
            <el-button text size="small" @click="showTestRecords = !showTestRecords">
              <el-icon><Timer /></el-icon> {{ t('page.apiCases.testRecord') }}
            </el-button>
          </div>

          <!-- 响应内容 -->
          <div class="resp-content">
            <!-- 返回结果 -->
            <div v-show="activeRespTab === 'result'" class="resp-pane">
              <div v-if="execResult" class="result-bar">
                <span class="status-badge" :class="execResult.success ? 'success' : 'failed'">
                  {{ execResult.success ? t('common.success') : t('common.failed') }}
                </span>
                <span class="result-meta">
                  {{ t('page.apiCases.resultInfo') }}:
                  <span class="meta-user">{{ execResult.operator || '-' }}</span>
                  {{ t('page.apiCases.updateTime') }}: {{ execResult.time || '-' }}
                </span>
              </div>
              <MonacoJsonEditor
                v-if="activeRespTab === 'result'"
                :model-value="responseResultText"
                read-only
                :height="180"
                lang="plaintext"
              />
            </div>
            <!-- 返回信息 -->
            <div v-show="activeRespTab === 'responseInfo'" class="resp-pane">
              <MonacoJsonEditor
                :model-value="responseInfoJson"
                read-only
                :height="200"
                lang="json"
              />
            </div>
            <!-- 请求信息 -->
            <div v-show="activeRespTab === 'requestInfo'" class="resp-pane">
              <MonacoJsonEditor
                :model-value="requestInfoJson"
                read-only
                :height="200"
                lang="json"
              />
            </div>
            <!-- 抽取信息 -->
            <div v-show="activeRespTab === 'extractInfo'" class="resp-pane">
              <MonacoJsonEditor
                :model-value="extractInfoJson"
                read-only
                :height="200"
                lang="json"
              />
            </div>
            <!-- 断言信息 -->
            <div v-show="activeRespTab === 'assertInfo'" class="resp-pane">
              <MonacoJsonEditor
                :model-value="assertInfoJson"
                read-only
                :height="200"
                lang="json"
              />
            </div>
            <!-- 测试记录 -->
            <div v-if="showTestRecords && runRecords.length" class="test-records-panel">
              <AppTable :data="runRecords" size="small" border max-height="200">
                <AppTableColumn prop="created_at" variant="flex" :label="t('common.createdAt')" />
                <AppTableColumn prop="status" variant="fixed" :label="t('common.status')" :width="100" />
              </AppTable>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  ArrowDown,
  ArrowRight,
  Search,
  Setting,
  Clock,
  CopyDocument,
  Delete as DeleteIcon,
  Timer,
} from '@element-plus/icons-vue'
import {
  debugRunApiCase,
  getApiCase,
  getApiCaseRunRecords,
  listApiCases,
} from '@/api/apiTest'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const caseId = computed(function () { return Number(route.params.caseId) })

const loading = ref(false)
const caseDetail = ref(null)
const searchKeyword = ref('')
const selectedCaseId = ref(null)

/* ---- 左侧用例分区 ---- */
const preconditionCases = ref([])
const mainCases = ref([])
const batchMode = ref(false)
const expandedSections = reactive({ pre: true, main: true })

function toggleSection(key) {
  expandedSections[key] = !expandedSections[key]
}

const filteredPreconditions = computed(function () {
  var kw = searchKeyword.value.trim().toLowerCase()
  if (!kw) return preconditionCases.value
  return preconditionCases.value.filter(function (it) {
    return (it.title || it.name || '').toLowerCase().indexOf(kw) >= 0
  })
})

const filteredMainCases = computed(function () {
  var kw = searchKeyword.value.trim().toLowerCase()
  if (!kw) return mainCases.value
  return mainCases.value.filter(function (it) {
    return (it.title || it.name || '').toLowerCase().indexOf(kw) >= 0
  })
})

/* ---- 调试表单 ---- */
const debugForm = reactive({
  method: 'POST',
  base_url: '${base_url}',
  path: '',
})
const running = ref(false)
const debugAbortController = ref(null)

/* ---- 子Tab ---- */
var subTabs = [
  { key: 'headers', label: 'page.apiCases.subTabHeaders' },
  { key: 'params', label: 'page.apiCases.subTabParams' },
  { key: 'path', label: 'page.apiCases.subTabPath' },
  { key: 'body', label: 'page.apiCases.subTabBody' },
  { key: 'extract', label: 'page.apiCases.subTabExtract' },
  { key: 'assert', label: 'page.apiCases.subTabAssert' },
  { key: 'preOps', label: 'page.apiCases.subTabPreOps' },
  { key: 'postOps', label: 'page.apiCases.subTabPostOps' },
]
const activeSubTab = ref('params')

/* ---- 各Tab数据 ---- */
const headersData = ref([])
const queryParamsData = ref([])
const pathParamsData = ref([])
const extractData = ref([])
const assertionsData = ref([])
const bodyContent = ref('{\n\n}')
const preOpsData = ref([])
const setupScriptText = ref('')
const teardownScriptText = ref('')

function methodTagType(method) {
  var m = (method || '').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

/* ---- 响应区 ---- */
var respTabs = [
  { key: 'result', label: 'page.apiCases.testRecord' },
  { key: 'responseInfo', label: 'page.apiCases.responseInfo' },
  { key: 'requestInfo', label: 'page.apiCases.requestInfo' },
  { key: 'extractInfo', label: 'page.apiCases.extractInfo' },
  { key: 'assertInfo', label: 'page.apiCases.assertInfo' },
]
const activeRespTab = ref('result')
const showTestRecords = ref(false)
const responseResultText = ref('')
const responseInfoJson = ref('{}')
const requestInfoJson = ref('{}')
const extractInfoJson = ref('{}')
const assertInfoJson = ref('[]')
const execResult = ref(null)
const runRecords = ref([])

/* ---- 方法 ---- */
function dotClass(status) {
  if (status === 'success') return 'dot-success'
  if (status === 'failed') return 'dot-failed'
  return 'dot-pending'
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  try {
    var d = new Date(isoStr)
    var pad = function (n) { return String(n).padStart(2, '0') }
    return pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes())
  } catch (e) {
    return isoStr
  }
}

function selectCase(item) {
  selectedCaseId.value = item.id
  if (item.id !== caseId.value) {
    router.push({ path: '/cases/api/cases/' + item.id, query: route.query })
  }
}

async function loadCaseDetail() {
  loading.value = true
  try {
    var res = await getApiCase(caseId.value)
    caseDetail.value = res.data.data
    selectedCaseId.value = caseId.value

    var payload = caseDetail.value ? (caseDetail.value.case_payload || {}) : {}
    /* 填充调试表单 */
    if (payload.method) debugForm.method = payload.method
    if (payload.base_url) debugForm.base_url = payload.base_url
    if (payload.path) debugForm.path = payload.path
    if (payload.body) bodyContent.value = typeof payload.body === 'string' ? payload.body : JSON.stringify(payload.body, null, 2)
    if (payload.headers) headersData.value = Array.isArray(payload.headers) ? payload.headers : []
    if (payload.query_params) queryParamsData.value = Array.isArray(payload.query_params) ? payload.query_params : []
    if (payload.path_params) pathParamsData.value = Array.isArray(payload.path_params) ? payload.path_params : []
    if (payload.extracts) extractData.value = Array.isArray(payload.extracts) ? payload.extracts : []
    if (payload.assertions) assertionsData.value = Array.isArray(payload.assertions) ? payload.assertions : []
    // 前置操作和后置脚本
    preOpsData.value = Array.isArray(payload.preconditions) ? payload.preconditions : []
    setupScriptText.value = payload.setup_script || ''
    teardownScriptText.value = payload.teardown_script || ''

    /* 加载前置依赖 + 测试用例 */
    if (caseDetail.value && caseDetail.value.interface_id) {
      var iid = caseDetail.value.interface_id
      var results = await Promise.all([
        listApiCases(iid, { case_kind: 'precondition' }),
        listApiCases(iid, { case_kind: 'main' }),
      ])
      preconditionCases.value = results[0].data.data ? (results[0].data.data.items || results[0].data.data) : []
      mainCases.value = results[1].data.data ? (results[1].data.data.items || results[1].data.data) : []
    }

    var recRes = await getApiCaseRunRecords(caseId.value)
    runRecords.value = recRes.data.data ? (recRes.data.data.items || recRes.data.data) : []
  } finally {
    loading.value = false
  }
}

function addRow(type) {
  var row = { name: '', value: '', desc: '' }
  switch (type) {
    case 'headers': headersData.value.push(row); break
    case 'query': queryParamsData.value.push(row); break
    case 'path': pathParamsData.value.push(row); break
    case 'extract': extractData.value.push({ name: '', expression: '', desc: '' }); break
    case 'assert': assertionsData.value.push({ name: '', expression: '', expected: '' }); break
  }
}

function deleteCase(item) {
  ElMessageBox.confirm(t('confirm.delete'), t('common.confirmTitle'), { type: 'warning' }).then(function () {
    ElMessage.info(t('common.deleted'))
  }).catch(function () {})
}

async function runDebug() {
  running.value = true
  var controller = new AbortController()
  debugAbortController.value = controller
  try {
    var res = await debugRunApiCase(
      caseId.value,
      { environment_id: null },
      { signal: controller.signal }
    )
    var data = res.data.data
    execResult.value = { success: true, operator: data.executor || '-', time: formatTime(new Date().toISOString()) }
    responseResultText.value = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
    responseInfoJson.value = JSON.stringify(data.response_info || {}, null, 2)
    requestInfoJson.value = JSON.stringify(data.request_info || {}, null, 2)
    extractInfoJson.value = JSON.stringify(data.extract_info || [], null, 2)
    assertInfoJson.value = JSON.stringify(data.assert_info || [], null, 2)
  } catch (err) {
    if (err.name === 'AbortError') {
      execResult.value = { success: false, operator: '-', time: formatTime(new Date().toISOString()), cancelled: true }
      responseResultText.value = '调试已取消'
    } else if (err?.response?.status === 404) {
      ElMessage.warning(err?.response?.data?.message || '用例已被删除，请返回列表')
      router.push({ path: '/cases/api', query: route.query })
    } else {
      throw err
    }
  } finally {
    running.value = false
    debugAbortController.value = null
  }
}

function cancelDebug() {
  if (debugAbortController.value) {
    debugAbortController.value.abort()
  }
}

function saveDebug() {
  ElMessage.success(t('common.saved'))
}

function goBack() {
  router.push({ path: '/cases/api', query: route.query })
}

onMounted(loadCaseDetail)
</script>

<style scoped lang="scss">
.api-case-detail {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 84px);
  background-color: var(--el-bg-color);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;

  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;

    .header-title {
      font-size: 15px;
      font-weight: 600;
    }

    .case-name {
      font-size: 13px;
      color: var(--el-text-color-primary);
      max-width: 240px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.detail-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ====== 左侧用例列表 ====== */
.left-panel {
  width: 300px;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color-lighter);
  overflow-y: auto;

  .panel-search {
    padding: 12px;
    border-bottom: 1px solid var(--el-border-color-extra-light);
  }

  .case-section {
    border-bottom: 1px solid var(--el-border-color-extra-light);

    .section-header {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 10px 14px;
      cursor: pointer;
      user-select: none;
      font-size: 13px;

      .el-icon {
        transition: transform 0.2s;
        font-size: 12px;
        color: var(--el-text-color-secondary);
        &.is-expanded { transform: rotate(90deg); }
      }

      .section-label {
        font-weight: 600;
        color: var(--el-text-color-primary);
      }

      .section-count {
        font-size: 11px;
        color: var(--el-text-color-placeholder);
        margin-left: auto;
      }

      .batch-tag {
        margin-left: 4px;
        transform: scale(0.85);
      }

      &:hover {
        background-color: var(--el-fill-color-lighter);
      }
    }

    .section-body {
      padding-bottom: 6px;
    }
  }

  .case-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px 7px 22px;
    cursor: pointer;
    font-size: 13px;
    transition: background 0.15s;

    &:hover {
      background-color: var(--el-fill-color-light);
    }

    &.active {
      background-color: var(--el-color-primary-light-9);
      .item-name { color: var(--el-color-primary); font-weight: 500; }
    }

    .item-status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
      &.dot-success { background-color: var(--el-color-success); }
      &.dot-failed { background-color: var(--el-color-danger); }
      &.dot-pending { background-color: var(--el-color-warning); }
    }

    .item-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      min-width: 0;
      flex: 1;
    }

    .item-actions {
      display: flex;
      gap: 2px;
      opacity: 0;
      transition: opacity 0.15s;
      flex-shrink: 0;
    }

    .item-time {
      font-size: 11px;
      color: var(--el-text-color-placeholder);
      margin-left: auto;
      flex-shrink: 0;
    }

    &:hover .item-actions { opacity: 1; }
  }
}

.panel-divider {
  width: 1px;
  background-color: var(--el-border-color-lighter);
  flex-shrink: 0;
}

/* ====== 右侧调试面板 ====== */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.request-config-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}

/* 子Tab导航 */
.sub-tabs-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
  overflow-x: auto;

  .sub-tab-item {
    padding: 8px 14px;
    font-size: 13px;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    color: var(--el-text-color-regular);
    transition: all 0.2s;

    &:hover { color: var(--el-color-primary); }

    &.active {
      color: var(--el-color-primary);
      border-bottom-color: var(--el-color-primary);
      font-weight: 500;
    }
  }
}

/* 子Tab内容 */
.sub-tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;

  .tab-pane {
    height: 100%;
  }

  .param-type-label {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-bottom: 8px;
    font-weight: 500;
  }

  .add-row-btn {
    margin-top: 8px;
  }

  .body-tab {
    height: 100%;
  }
}

/* ====== 底部响应区 ====== */
.response-section {
  border-top: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
  max-height: 320px;
  display: flex;
  flex-direction: column;
}

.resp-tabs-nav {
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;

  .resp-tab-item {
    padding: 8px 14px;
    font-size: 13px;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    color: var(--el-text-color-secondary);

    &:hover { color: var(--el-color-primary); }

    &.active {
      color: var(--el-color-primary);
      border-bottom-color: var(--el-color-primary);
      font-weight: 600;
    }
  }

  .resp-tab-spacer {
    flex: 1;
  }
}

.resp-content {
  overflow-y: auto;
  padding: 8px 16px 12px;

  .resp-pane {
    height: 100%;
  }
}

.result-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  margin-bottom: 8px;
  border-radius: 6px;
  background-color: var(--el-fill-color-lighter);

  .status-badge {
    font-size: 12px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 4px;

    &.success { background-color: var(--el-color-success-light-9); color: var(--el-color-success); }
    &.failed { background-color: var(--el-color-danger-light-9); color: var(--el-color-danger); }
  }

  .result-meta {
    font-size: 12px;
    color: var(--el-text-color-secondary);

    .meta-user { color: var(--el-text-color-primary); }
  }
}

.op-link {
  color: var(--el-color-primary);
  cursor: pointer;
  font-size: 12px;
}
/* 前置操作 */
.pre-ops-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pre-op-item {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 12px;
}

.pre-op-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-weight: 600;
}

.pre-op-detail {
  color: var(--el-text-color-regular);
  line-height: 1.6;
  word-break: break-all;

  .detail-label {
    color: var(--el-text-color-secondary);
    margin-right: 4px;
  }
}

.pre-op-body {
  background: #f5f7fa;
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 11px;
  max-height: 120px;
  overflow: auto;
  margin: 2px 0;
}

.extract-tag, .assert-tag {
  display: inline-block;
  background: #f0f9eb;
  color: #67c23a;
  padding: 1px 6px;
  border-radius: 3px;
  margin: 2px 4px 2px 0;
  font-size: 11px;
}

.assert-tag {
  background: #fdf6ec;
  color: #e6a23c;
}

/* 后置脚本 */
.scripts-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.script-block h4 {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--el-text-color-primary);
}

.script-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 8px 12px;
  border-radius: 4px;
  font-family: 'Fira Code', Consolas, monospace;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
