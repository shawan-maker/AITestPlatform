<template>
  <!-- v2-Q4: 接口用例详情页 - 对照设计稿实现 -->
  <div v-loading="loading" class="api-case-detail">
    <BreadcrumbNav :items="breadcrumbs" />

    <!-- 主内容区：左右分栏 -->
    <SplitView :initial-width="380" :min-width="300" :max-width="560" drawer-title="用例列表">
      <template #left>
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
              <span class="item-name">{{ stripTitleSuffix(item.title || item.name) }}</span>
              <div class="item-actions">
                <el-button text size="small" @click.stop><el-icon><Clock /></el-icon></el-button>
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
              <span class="item-name">{{ stripTitleSuffix(item.title || item.name) }}</span>
            </div>
            <el-empty v-if="!filteredMainCases.length" description="" :image-size="40" />
          </div>
        </div>
        </div>
      </template>
      <template #right>
      <!-- 右侧：调试面板 -->
      <div class="right-panel">
        <!-- 标题 + 变量文件 -->
        <div class="debug-header-row">
          <h3 class="debug-title">{{ caseDetail?.title || caseDetail?.name || '-' }}</h3>
          <el-dropdown trigger="click" popper-class="var-file-dropdown">
            <el-button size="default">
              <el-icon><Document /></el-icon> {{ currentEnvName || t('page.apiCases.selectVarFile') }}<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="env in environmentList"
                  :key="env.id"
                  :class="{ 'is-active': caseEnvId === env.id }"
                  @click="caseEnvId = env.id; currentEnvName = env.env_name"
                >{{ env.env_name }}</el-dropdown-item>
                <el-dropdown-item v-if="!environmentList.length" disabled>{{ t('page.apiCases.noVarFile') }}</el-dropdown-item>
                <el-dropdown-item divided @click="loadEnvironments">{{ t('common.refresh') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <!-- 前置操作面板（仅主用例显示） -->
        <PreconditionPanel
          v-if="isMainCase"
          :precondition-ids="preconditionIds"
          :interface-id="caseDetail?.interface_id"
          :case-id="caseDetail?.id"
          :all-precondition-cases="preconditionCases"
          :refresh-key="preconditionRefreshKey"
          @update:precondition-ids="onPreconditionIdsUpdate"
        />

        <!-- 请求面板 -->
        <ApiRequestPanel
          v-model:method="debugForm.method"
          v-model:base-url="debugForm.base_url"
          v-model:path="debugForm.path"
          v-model:headers="headersData"
          v-model:query="queryParamsData"
          v-model:body="bodyContent"
          v-model:body-type="bodyType"
          v-model:body-form="bodyForm"
          v-model:urlencoded-rows="urlencodedRows"
          v-model:form-data-rows="formDataRows"
          v-model:extracts="extractData"
          v-model:assertions="assertionsData"
          v-model:pre-ops-script="setupScriptText"
          v-model:post-ops-script="teardownScriptText"
          :running="running"
          default-tab="params"
          @run="runDebug"
          @cancel="cancelDebug"
          @save="saveDebug"
        />

        <!-- 响应面板 -->
        <ApiResponsePanel
          :result="execResult"
          :response-headers="responseHeaders"
          :request-headers="requestHeaders"
          :extract-info="extractResultData"
          :assert-info="assertResultData"
          :log-data="logData"
          :show-records="true"
          @toggle-records="showTestRecords = !showTestRecords"
        />
      </div>
      </template>
    </SplitView>

    <!-- 执行记录抽屉 -->
    <ExecRecordsDrawer v-model="showTestRecords" :records="runRecords" :loading="false" name-mode="case" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
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
  Document,
  Close,
} from '@element-plus/icons-vue'
import ApiRequestPanel from '@/components/api-test/ApiRequestPanel.vue'
import ApiResponsePanel from '@/components/api-test/ApiResponsePanel.vue'
import PreconditionPanel from '@/components/api-test/PreconditionPanel.vue'
import SplitView from '@/components/common/SplitView.vue'
import BreadcrumbNav from '@/components/common/BreadcrumbNav.vue'
import ExecRecordsDrawer from '@/components/api-test/ExecRecordsDrawer.vue'
import {
  debugRunApiCase,
  getDebugRunStatus,
  getApiCase,
  getApiCaseRunRecords,
  listApiCases,
  updateApiCase,
} from '@/api/apiTest'
import { listEnvironments } from '@/api/environment'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const caseId = computed(function () { return Number(route.params.caseId) })

const breadcrumbs = computed(() => [
  { label: t('menu.casesApi'), to: '/cases/api' },
  { label: t('common.breadcrumb.caseDetail') },
])

const loading = ref(false)
const caseDetail = ref(null)
const environmentList = ref([])
const caseEnvId = ref(null)
const currentEnvName = ref('')
const searchKeyword = ref('')
const selectedCaseId = ref(null)

/* ---- 左侧用例分区 ---- */
const preconditionCases = ref([])
const mainCases = ref([])
const batchMode = ref(false)
const expandedSections = reactive({ pre: true, main: true })
const preconditionRefreshKey = ref(0)

/* ---- 前置操作关联 ---- */
const isMainCase = computed(function () {
  return caseDetail.value && caseDetail.value.case_kind === 'main'
})
const preconditionIds = computed(function () {
  if (!caseDetail.value || !caseDetail.value.case_payload) return []
  return caseDetail.value.case_payload.precondition_ids || []
})

async function onPreconditionIdsUpdate(newIds) {
  try {
    var payload = Object.assign({}, caseDetail.value.case_payload || {})
    payload.precondition_ids = newIds
    var res = await updateApiCase(caseId.value, { case_payload: payload })
    if (res.data.data && res.data.data.case_payload) {
      caseDetail.value.case_payload = res.data.data.case_payload
    }
  } catch (err) {
    ElMessage.error(err.message || t('page.apiCases.saveFailed'))
  }
}

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
const debugPolling = ref(false)
const debugPollTimer = ref(null)

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
const bodyType = ref('json')
const bodyForm = ref([])
const urlencodedRows = ref([])
const formDataRows = ref([])
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
const responseHeaders = ref({})
const requestHeaders = ref({})
const extractResultData = ref([])
const assertResultData = ref([])
const logData = ref([])

/* ---- 方法 ---- */
function dotClass(status) {
  if (status === 'running') return 'dot-running'
  if (status === 'success') return 'dot-success'
  if (status === 'fail' || status === 'failed') return 'dot-failed'
  if (status === 'error') return 'dot-error'
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

function stripTitleSuffix(title) {
  if (!title) return ''
  return title.replace(/[（(][^）)]*[）)]$/, '').trim() || title
}

function selectCase(item) {
  selectedCaseId.value = item.id
  if (item.id !== caseId.value) {
    router.push({ path: '/cases/api/cases/' + item.id, query: route.query })
  }
}

async function loadCaseDetail() {
  // 如果用例列表已加载且当前 caseId 不在任何列表中（可能被删除），跳过请求
  var allCases = mainCases.value.concat(preconditionCases.value)
  if (allCases.length > 0) {
    var exists = allCases.some(function (c) { return c.id === caseId.value })
    if (!exists) {
      var firstCase = mainCases.value[0] || preconditionCases.value[0]
      if (firstCase) {
        router.replace({ path: '/cases/api/cases/' + firstCase.id, query: route.query })
      } else {
        caseDetail.value = null
      }
      return
    }
  }

  loading.value = true
  // 重置请求表单和响应面板（切换用例时清空上一个用例的数据）
  debugForm.method = 'POST'
  debugForm.base_url = ''
  debugForm.path = ''
  execResult.value = null
  responseHeaders.value = {}
  requestHeaders.value = {}
  extractResultData.value = []
  assertResultData.value = []
  logData.value = []
  headersData.value = []
  queryParamsData.value = []
  bodyContent.value = '{\n\n}'
  bodyType.value = 'json'
  urlencodedRows.value = []
  formDataRows.value = []
  setupScriptText.value = ''
  teardownScriptText.value = ''
  try {
    try {
      var res = await getApiCase(caseId.value)
      caseDetail.value = res.data.data
      selectedCaseId.value = caseId.value
    } catch (loadErr) {
      // 用例不存在（404）或加载失败，清空详情并退出
      caseDetail.value = null
      execResult.value = null
      responseHeaders.value = {}
      requestHeaders.value = {}
      extractResultData.value = []
      assertResultData.value = []
      logData.value = []
      return
    }

    var payload = caseDetail.value ? (caseDetail.value.case_payload || {}) : {}
    /* 填充调试表单 — 兼容 AI 嵌套格式和扁平格式 */
    var method = payload.method || (payload.interface && payload.interface.method)
    if (method) debugForm.method = method.toUpperCase()
    if (payload.base_url) debugForm.base_url = payload.base_url
    var pathVal = payload.path || (payload.interface && payload.interface.url)
    if (pathVal) debugForm.path = pathVal
    // body: 根据 Content-Type 决定 body 类型
    if (payload.body) {
      bodyContent.value = typeof payload.body === 'string' ? payload.body : JSON.stringify(payload.body, null, 2)
    } else if (payload.request) {
      var rb = payload.request.data || payload.request.json
      // 检测 Content-Type 决定 bodyType
      var ct = ''
      if (payload.headers && typeof payload.headers === 'object' && !Array.isArray(payload.headers)) {
        ct = (payload.headers['Content-Type'] || payload.headers['content-type'] || '').toLowerCase()
      }
      if (ct.indexOf('form-urlencoded') >= 0 && payload.request.data && Object.keys(payload.request.data).length) {
        bodyType.value = 'urlencoded'
        urlencodedRows.value = Object.entries(payload.request.data).map(function(e) {
          return { name: e[0], value: String(e[1]), desc: '' }
        })
      } else if (ct.indexOf('multipart') >= 0 && payload.request.files && Object.keys(payload.request.files).length) {
        bodyType.value = 'form-data'
        formDataRows.value = Object.entries(payload.request.files).map(function(e) {
          return { name: e[0], value: String(e[1]), type: 'file', desc: '' }
        })
      } else if (rb && Object.keys(rb).length) {
        bodyType.value = 'json'
        bodyContent.value = JSON.stringify(rb, null, 2)
      }
    }
    if (payload.headers) {
      if (Array.isArray(payload.headers)) headersData.value = payload.headers
      else if (typeof payload.headers === 'object') headersData.value = Object.entries(payload.headers).map(function(e){return{name:e[0],value:String(e[1]),desc:''}})
    }
    var qRaw = payload.query_params || payload.query || (payload.request && payload.request.params)
    if (qRaw) {
      if (Array.isArray(qRaw)) queryParamsData.value = qRaw
      else if (typeof qRaw === 'object' && Object.keys(qRaw).length) queryParamsData.value = Object.entries(qRaw).map(function(e){return{name:e[0],value:String(e[1]),desc:''}})
    }
    var extRaw = payload.extracts || payload.extract
    if (extRaw && Array.isArray(extRaw)) extractData.value = extRaw
    if (payload.assertions && Array.isArray(payload.assertions)) {
      assertionsData.value = payload.assertions.map(function(a) {
        if (typeof a === 'string') return { target: a, method: 'eq', expected: '' }
        return { target: a.field || a.target || a.name || '', method: a.type || a.method || 'eq', expected: a.expected !== undefined ? String(a.expected) : '' }
      })
    }
    preOpsData.value = Array.isArray(payload.preconditions) ? payload.preconditions : []
    setupScriptText.value = payload.setup_script || ''
    teardownScriptText.value = payload.teardown_script || ''

    /* 解析预执行结果（_exec_result） */
    var er = payload._exec_result
    if (er && typeof er === 'object' && Object.keys(er).length > 0) {
      // 兼容两种格式：扁平结构 {status, response_body, ...} 和嵌套结构 {state, cases: [{...}]}
      var firstCase = null
      var isSuccess = false
      if (er.cases && Array.isArray(er.cases) && er.cases.length) {
        // 嵌套格式
        firstCase = er.cases[0]
        isSuccess = er.state === 'success'
      } else if (er.status || er.response_body || er.response_code) {
        // 扁平格式：_exec_result 本身就是 case 结果
        firstCase = er
        isSuccess = er.status === 'success'
      }

      if (firstCase) {
        // 解析 response_body（可能是 JSON 字符串或普通字符串）
        var respBody = firstCase.response_body
        if (typeof respBody === 'string') {
          try { respBody = JSON.parse(respBody) } catch (e) { /* 保持原始字符串 */ }
        }

        execResult.value = {
          success: isSuccess,
          status_code: firstCase.response_code || '',
          duration_ms: firstCase.run_time || firstCase.duration_ms || 0,
          method: firstCase.method || '',
          url: firstCase.url || '',
          error_message: firstCase.status === 'error' ? (typeof firstCase.log_data === 'string' ? firstCase.log_data : '') : '',
          response_body: respBody,
          request_body: firstCase.request_body !== undefined ? firstCase.request_body : null,
        }

        // 响应头
        var rh = firstCase.response_headers
        if (rh) {
          if (typeof rh === 'string') {
            try { responseHeaders.value = JSON.parse(rh) } catch (e) { responseHeaders.value = {} }
          } else {
            responseHeaders.value = rh
          }
        }

        // 请求头
        var rqh = firstCase.request_headers
        if (rqh) {
          if (typeof rqh === 'string') {
            try { requestHeaders.value = JSON.parse(rqh) } catch (e) { requestHeaders.value = {} }
          } else {
            requestHeaders.value = rqh
          }
        }

        // 断言结果
        var assertRaw = firstCase.assert_info || firstCase.assertions
        if (assertRaw && Array.isArray(assertRaw)) {
          assertResultData.value = assertRaw.map(function (a) {
            return {
              field: a.field || a.target || '',
              method: a.type || a.method || 'eq',
              expected: a.expected !== undefined ? String(a.expected) : '',
              actual: a.actual !== undefined ? String(a.actual) : '',
              passed: a.passed !== undefined ? a.passed : (String(a.actual) === String(a.expected)),
            }
          })
        }

        // 提取结果
        var extRaw = firstCase.extract_info || firstCase.extracts
        if (extRaw && Array.isArray(extRaw)) {
          extractResultData.value = extRaw
        }

        // 日志：兼容 [["INFO", "msg"], ...] 和 [{level, message}, ...] 两种格式
        var logRaw = firstCase.log_data
        if (logRaw) {
          if (Array.isArray(logRaw)) {
            logData.value = logRaw.map(function (item) {
              if (Array.isArray(item)) {
                return { level: item[0] || 'INFO', message: item.slice(1).join(' ') }
              }
              return { level: item.level || 'INFO', message: item.message || String(item) }
            })
          } else if (typeof logRaw === 'string') {
            logData.value = logRaw.split('\n').filter(Boolean).map(function (line) {
              var match = line.match(/^\[(\w+)\]/)
              return { level: match ? match[1] : 'INFO', message: line }
            })
          }
        }
      }
    }

    /* 加载前置依赖 + 测试用例 */
    if (caseDetail.value && caseDetail.value.interface_id) {
      var iid = caseDetail.value.interface_id
      var results = await Promise.all([
        listApiCases(iid, { case_kind: 'precondition' }),
        listApiCases(iid, { case_kind: 'main' }),
      ])
      preconditionCases.value = results[0].data.data ? (results[0].data.data.items || results[0].data.data) : []
      mainCases.value = results[1].data.data ? (results[1].data.data.items || results[1].data.data) : []
    } else {
      preconditionCases.value = []
      mainCases.value = []
    }

    // 加载 run_records（如果 _exec_result 已有数据则仅作为补充）
    var recRes = await getApiCaseRunRecords(caseId.value)
    runRecords.value = recRes.data.data ? (recRes.data.data.items || recRes.data.data) : []

    // 如果 payload 中没有执行结果，从最新的执行记录中加载
    if (!execResult.value && runRecords.value.length > 0) {
      var latestRecord = runRecords.value[0]
      if (latestRecord.api_requests_info) {
        var recData = latestRecord.api_requests_info
        var recDetail = recData._debug_detail || recData
        var recRespInfo = recDetail.response_info || recData.response_info || {}
        var recReqInfo = recDetail.request_info || recData.request_info || {}
        execResult.value = {
          success: latestRecord.status === 'success',
          status_code: recRespInfo.status_code || '',
          duration_ms: latestRecord.duration_ms || recRespInfo.elapsed_ms || 0,
          method: recReqInfo.method || debugForm.method,
          url: recReqInfo.url || '',
          error_message: latestRecord.error_message || '',
          response_body: recRespInfo.body || null,
          request_body: recReqInfo.body || null,
        }
        responseHeaders.value = recRespInfo.headers || {}
        requestHeaders.value = recReqInfo.headers || {}
        extractResultData.value = recDetail.extract_info || recData.extract_info || []
        assertResultData.value = (recDetail.assert_info || recData.assert_info || []).map(function (a) {
          return {
            field: a.field || a.target || '',
            method: a.type || a.method || 'eq',
            expected: a.expected !== undefined ? String(a.expected) : '',
            actual: a.actual !== undefined ? String(a.actual) : '',
            passed: a.passed !== undefined ? a.passed : true,
          }
        })
        var recLogRaw = recDetail.log_data || recData.log_data || []
        logData.value = recLogRaw.map(function (item) {
          if (Array.isArray(item)) return { level: item[0] || 'INFO', message: item.slice(1).join(' ') }
          return { level: item.level || 'INFO', message: item.message || String(item) }
        })
      }
    }

    loadEnvironments()
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
  if (!caseEnvId.value) {
    ElMessage.warning(t('page.apiCases.selectEnvFirst'))
    return
  }
  // 先保存修改后的内容，再调试
  try {
    var payload = buildCasePayload()
    var saveRes = await updateApiCase(caseId.value, { case_payload: payload })
    if (saveRes.data.data && saveRes.data.data.case_payload) {
      caseDetail.value.case_payload = saveRes.data.data.case_payload
    }
  } catch (err) {
    ElMessage.error(t('page.apiCases.saveFailed') + ': ' + (err.message || ''))
    return
  }
  running.value = true
  // 清空上一次的结果
  execResult.value = null
  responseHeaders.value = {}
  requestHeaders.value = {}
  extractResultData.value = []
  assertResultData.value = []
  logData.value = []

  // 乐观更新：将主用例和前置操作用例状态设为 running（不可变替换，确保 Vue 响应）
  caseDetail.value = Object.assign({}, caseDetail.value, { exec_status: 'running' })
  preconditionCases.value = preconditionCases.value.map(function (c) {
    return Object.assign({}, c, { exec_status: 'running' })
  })
  preconditionRefreshKey.value++

  try {
    // 异步触发调试运行
    var triggerRes = await debugRunApiCase(caseId.value, { environment_id: caseEnvId.value })
    var recordId = triggerRes.data.data.record_id

    // 刷新执行记录列表（显示"执行中"记录）
    refreshRunRecords()

    // 轮询直到完成
    debugPolling.value = true
    var data = await pollDebugRunStatus(caseId.value, recordId)

    // 执行完成，填充结果
    var detail = data.api_requests_info || {}
    var respInfo = detail.response_info || {}
    var reqInfo = detail.request_info || {}
    execResult.value = {
      success: data.status === 'success',
      status_code: respInfo.status_code || '',
      duration_ms: data.duration_ms || 0,
      method: reqInfo.method || debugForm.method,
      url: reqInfo.url || '',
      error_message: data.error_message || '',
      response_body: respInfo.body || null,
      request_body: reqInfo.body || null,
    }
    responseHeaders.value = respInfo.headers || {}
    requestHeaders.value = reqInfo.headers || {}
    extractResultData.value = detail.extract_info || []
    assertResultData.value = (detail.assert_info || []).map(function (a) {
      return {
        field: a.field || a.target || '',
        method: a.type || a.method || 'eq',
        expected: a.expected !== undefined ? String(a.expected) : '',
        actual: a.actual !== undefined ? String(a.actual) : '',
        passed: a.passed !== undefined ? a.passed : true,
      }
    })
    var logRaw = detail.log_data || []
    logData.value = logRaw.map(function (item) {
      if (Array.isArray(item)) return { level: item[0] || 'INFO', message: item.slice(1).join(' ') }
      return { level: item.level || 'INFO', message: item.message || String(item) }
    })
    // 刷新执行记录列表和前置操作用例
    refreshRunRecords()
    refreshPreconditionCases()
  } catch (err) {
    if (err?.response?.status === 404) {
      ElMessage.warning(err?.response?.data?.message || t('page.apiCases.caseDeleted'))
      router.push({ path: '/cases/api', query: route.query })
    } else {
      ElMessage.error(err?.message || t('page.apiCases.debugExecFailed'))
      execResult.value = { success: false, status_code: '', duration_ms: 0, method: '', url: '', error_message: err?.message || t('page.apiCases.debugExecFailed') }
    }
  } finally {
    running.value = false
    debugPolling.value = false
    await refreshPreconditionCases()
    preconditionRefreshKey.value++
  }
}

async function pollDebugRunStatus(caseIdVal, recordId) {
  var maxAttempts = 300  // 最多轮询 5 分钟（每秒 1 次）
  for (var i = 0; i < maxAttempts; i++) {
    await new Promise(function (resolve) {
      debugPollTimer.value = setTimeout(resolve, 1000)
    })
    if (!debugPolling.value) {
      throw new Error(t('page.apiCases.debugCancelled'))
    }
    var res = await getDebugRunStatus(caseIdVal, recordId)
    var data = res.data.data
    if (data.status !== 'running') {
      return data
    }
  }
  throw new Error(t('page.apiCases.debugTimeout'))
}

function cancelDebug() {
  debugPolling.value = false
  if (debugPollTimer.value) {
    clearTimeout(debugPollTimer.value)
    debugPollTimer.value = null
  }
}

async function refreshRunRecords() {
  if (!caseId.value || isNaN(caseId.value)) return
  try {
    var recRes = await getApiCaseRunRecords(caseId.value)
    runRecords.value = recRes.data.data ? (recRes.data.data.items || recRes.data.data) : []
  } catch (e) { /* 忽略 */ }
}

async function refreshPreconditionCases() {
  try {
    if (caseDetail.value && caseDetail.value.interface_id) {
      var preRes = await listApiCases(caseDetail.value.interface_id, { case_kind: 'precondition' })
      preconditionCases.value = preRes.data.data ? (preRes.data.data.items || preRes.data.data) : []
    }
  } catch (e) { /* 忽略 */ }
}

function buildCasePayload() {
  // 从当前表单状态构建 case_payload
  var headers = {}
  headersData.value.forEach(function (h) {
    if (h.name && h.value) headers[h.name] = h.value
  })
  var params = {}
  queryParamsData.value.forEach(function (q) {
    if (q.name && q.value) params[q.name] = q.value
  })
  var body = null
  if (bodyType.value === 'json' && bodyContent.value) {
    try { body = JSON.parse(bodyContent.value) } catch { body = bodyContent.value }
  }
  var request = { params: params }
  if (bodyType.value === 'json') {
    request.json = body || {}
    request.data = {}
  } else if (bodyType.value === 'urlencoded') {
    request.data = {}
    urlencodedRows.value.forEach(function (r) {
      if (r.name) request.data[r.name] = r.value || ''
    })
    request.json = {}
  } else {
    request.data = {}
    request.json = {}
  }
  return {
    title: caseDetail.value ? caseDetail.value.title : '',
    method: debugForm.method,
    interface: { url: debugForm.path, method: debugForm.method },
    headers: headers,
    request: request,
    extract: extractData.value.filter(function (e) { return e.name }).map(function (e) {
      return { var_name: e.name, extract_expr: e.expression, type: 'jsonpath' }
    }),
    assertions: assertionsData.value.filter(function (a) { return a.target || a.name }).map(function (a) {
      return { field: a.target || a.name, type: a.method || 'eq', expected: a.expected }
    }),
    setup_script: setupScriptText.value || '',
    teardown_script: teardownScriptText.value || '',
  }
}

async function saveDebug() {
  try {
    var payload = buildCasePayload()
    var res = await updateApiCase(caseId.value, { case_payload: payload })
    if (res.data.data && res.data.data.case_payload) {
      caseDetail.value.case_payload = res.data.data.case_payload
    }
    ElMessage.success(t('common.saved'))
  } catch (err) {
    ElMessage.error(err.message || t('page.apiCases.saveFailed'))
  }
}

function goBack() {
  var query = { tab: 'test-cases' }
  if (caseDetail.value && caseDetail.value.interface_id) {
    query.interfaceId = caseDetail.value.interface_id
  }
  router.push({ path: '/cases/api', query: query })
}

async function loadEnvironments() {
  if (!caseDetail.value || !caseDetail.value.project_id) return
  try {
    var res = await listEnvironments({ project_id: caseDetail.value.project_id, page: 1, page_size: 100 })
    environmentList.value = res.data.data ? (res.data.data.items || res.data.data) : []
  } catch {}
}

onMounted(function () {
  loadCaseDetail()
})

watch(caseId, function (newId) {
  if (newId) loadCaseDetail()
})
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
  width: 100%;
  display: flex;
  flex-direction: column;

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
        font-size: var(--font-small);
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
    font-size: 14px;
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
      &.dot-running { background-color: var(--el-color-primary); animation: dot-pulse 1s ease-in-out infinite; }
      &.dot-success { background-color: var(--el-color-success); }
      &.dot-failed { background-color: var(--el-color-danger); }
      &.dot-error { background-color: var(--el-color-warning); }
      &.dot-pending { background-color: var(--el-text-color-placeholder); }
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
      font-size: var(--font-small);
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
.debug-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  padding: 0 16px;
  flex-shrink: 0;

  .debug-title {
    font-size: 16px;
    font-weight: 600;
    margin: 0;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
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
  background: var(--el-fill-color-lighter);
  padding: 4px 8px;
  border-radius: 3px;
  font-size: var(--font-small);
  max-height: 120px;
  overflow: auto;
  margin: 2px 0;
}

.extract-tag, .assert-tag {
  display: inline-block;
  background: rgba($color-success, 0.1);
  color: $color-success;
  padding: 1px 6px;
  border-radius: 3px;
  margin: 2px 4px 2px 0;
  font-size: var(--font-small);
}

.assert-tag {
  background: rgba($color-warning, 0.1);
  color: $color-warning;
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
  background: $bg-code-dark;
  color: $text-code-dark;
  padding: 8px 12px;
  border-radius: 4px;
  font-family: 'Fira Code', Consolas, monospace;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
