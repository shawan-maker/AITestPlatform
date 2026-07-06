<template>
  <div class="api-request-panel">
    <!-- 调试工具栏 -->
    <div class="debug-toolbar">
      <el-select v-model="method" size="default" style="width: 110px">
        <el-option v-for="m in httpMethods" :key="m" :value="m" :label="m" />
      </el-select>
      <el-input v-model="baseUrl" placeholder="$(base_url)" size="default" style="width: 220px" />
      <el-input v-model="path" size="default" style="flex: 1; min-width: 0" />
      <el-button v-if="!running" class="btn-debug-run" @click="$emit('run')">{{ t('page.apiCases.debugRun') }}</el-button>
      <el-button v-else type="danger" size="default" @click="$emit('cancel')">{{ t('common.cancel') }}</el-button>
      <el-button size="default" @click="$emit('save')">{{ t('page.apiCases.debugSave') }}</el-button>
    </div>

    <!-- 请求子Tab -->
    <el-tabs v-model="activeTab" class="debug-sub-tabs">
      <!-- Headers -->
      <el-tab-pane :label="t('page.apiCases.subTabHeaders')" name="headers">
        <ParamTable v-model="headers" :columns="headerColumns" :add-label="t('page.apiCases.addParam')" />
      </el-tab-pane>

      <!-- Params -->
      <el-tab-pane :label="t('page.apiCases.subTabParams')" name="params">
        <h4 class="param-type-label">{{ t('page.apiCases.request.queryParamLabel') }}</h4>
        <ParamTable v-model="query" :columns="paramColumns" :add-label="t('page.apiCases.addParam')" />
      </el-tab-pane>

      <!-- Body -->
      <el-tab-pane :label="t('page.apiCases.subTabBody')" name="body">
        <div class="body-editor">
          <div class="body-type-selector">
            <el-radio-group v-model="bodyType" size="default">
              <el-radio value="json">JSON</el-radio>
              <el-radio value="urlencoded">x-www-form-urlencoded</el-radio>
              <el-radio value="form-data">multipart/form-data</el-radio>
            </el-radio-group>
          </div>
          <div v-if="bodyType === 'json'" class="body-json-section">
            <MonacoJsonEditor v-model="body" height="100%" language="json" />
          </div>
          <div v-else-if="bodyType === 'urlencoded'">
            <ParamTable v-model="urlencodedRows" :columns="paramColumns" :add-label="t('page.apiCases.addParam')" />
          </div>
          <div v-else>
            <ParamTable v-model="formDataRows" :columns="formColumns" :add-label="t('page.apiCases.addParam')" />
          </div>
        </div>
      </el-tab-pane>

      <!-- Extract -->
      <el-tab-pane :label="t('page.apiCases.extractTabLabel')" name="extract">
        <ParamTable v-model="extracts" :columns="extractColumns" :add-label="t('page.apiCases.addParam')" />
      </el-tab-pane>

      <!-- Assert -->
      <el-tab-pane :label="t('page.apiCases.subTabAssert')" name="assert">
        <ParamTable v-model="assertions" :columns="assertColumns" :add-label="t('page.apiCases.addParam')" />
      </el-tab-pane>

      <!-- PreOps -->
      <el-tab-pane :label="t('page.apiCases.subTabPreOps')" name="preOps">
        <slot name="preOps">
          <div class="prepost-container">
            <div class="prepost-code">
              <MonacoJsonEditor v-model="preOpsScript" height="100%" language="python" />
            </div>
            <div class="prepost-template">
              <div class="template-header">{{ t('page.apiCases.request.preOpsTemplateHeader') }}</div>
              <div class="template-list">
                <div class="template-item" v-for="(tpl, idx) in preTemplates" :key="idx" @click="insertTemplate('pre', tpl.code)">
                  <span class="template-name">{{ tpl.label }}</span>
                </div>
              </div>
            </div>
          </div>
        </slot>
      </el-tab-pane>

      <!-- PostOps -->
      <el-tab-pane :label="t('page.apiCases.subTabPostOps')" name="postOps">
        <slot name="postOps">
          <div class="prepost-container">
            <div class="prepost-code">
              <MonacoJsonEditor v-model="postOpsScript" height="100%" language="python" />
            </div>
            <div class="prepost-template">
              <div class="template-header">{{ t('page.apiCases.request.postOpsTemplateHeader') }}</div>
              <div class="template-list">
                <div class="template-item" v-for="(tpl, idx) in postTemplates" :key="idx" @click="insertTemplate('post', tpl.code)">
                  <span class="template-name">{{ tpl.label }}</span>
                </div>
              </div>
            </div>
          </div>
        </slot>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ParamTable from './ParamTable.vue'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'

const { t } = useI18n()

const props = defineProps({
  method: { type: String, default: 'GET' },
  baseUrl: { type: String, default: '' },
  path: { type: String, default: '' },
  headers: { type: Array, default: () => [] },
  query: { type: Array, default: () => [] },
  body: { type: String, default: '' },
  bodyType: { type: String, default: 'json' },
  bodyForm: { type: Array, default: () => [] },
  urlencodedRows: { type: Array, default: () => [] },
  formDataRows: { type: Array, default: () => [] },
  extracts: { type: Array, default: () => [] },
  assertions: { type: Array, default: () => [] },
  preOpsScript: { type: String, default: '' },
  postOpsScript: { type: String, default: '' },
  running: { type: Boolean, default: false },
  defaultTab: { type: String, default: 'params' },
})

const emit = defineEmits([
  'update:method', 'update:baseUrl', 'update:path',
  'update:headers', 'update:query', 'update:body',
  'update:bodyType', 'update:bodyForm',
  'update:urlencodedRows', 'update:formDataRows',
  'update:extracts', 'update:assertions',
  'update:preOpsScript', 'update:postOpsScript',
  'run', 'cancel', 'save',
])

const httpMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

const activeTab = ref(props.defaultTab)

// 使用 computed 实现 v-model 的双向绑定
var method = computed({ get: () => props.method, set: v => emit('update:method', v) })
var baseUrl = computed({ get: () => props.baseUrl, set: v => emit('update:baseUrl', v) })
var path = computed({ get: () => props.path, set: v => emit('update:path', v) })
var headers = computed({ get: () => props.headers, set: v => emit('update:headers', v) })
var query = computed({ get: () => props.query, set: v => emit('update:query', v) })
var body = computed({ get: () => props.body, set: v => emit('update:body', v) })
var bodyType = computed({ get: () => props.bodyType, set: v => emit('update:bodyType', v) })
var bodyForm = computed({ get: () => props.bodyForm, set: v => emit('update:bodyForm', v) })
var urlencodedRows = computed({ get: () => props.urlencodedRows, set: v => emit('update:urlencodedRows', v) })
var formDataRows = computed({ get: () => props.formDataRows, set: v => emit('update:formDataRows', v) })
var extracts = computed({ get: () => props.extracts, set: v => emit('update:extracts', v) })
var assertions = computed({ get: () => props.assertions, set: v => emit('update:assertions', v) })
var preOpsScript = computed({ get: () => props.preOpsScript, set: v => emit('update:preOpsScript', v) })
var postOpsScript = computed({ get: () => props.postOpsScript, set: v => emit('update:postOpsScript', v) })

// 列定义
var headerColumns = [
  { prop: 'name', label: t('page.apiCases.paramName'), minWidth: 150 },
  { prop: 'value', label: t('page.apiCases.paramValue'), minWidth: 200 },
  { prop: 'desc', label: t('page.apiCases.fieldDesc'), minWidth: 140 },
]
var paramColumns = [
  { prop: 'name', label: t('page.apiCases.paramName'), minWidth: 150 },
  { prop: 'value', label: t('page.apiCases.paramValue'), minWidth: 200 },
  { prop: 'desc', label: t('page.apiCases.fieldDesc'), minWidth: 180 },
]
var extractColumns = [
  { prop: 'name', label: t('page.apiCases.varName'), minWidth: 150 },
  { prop: 'expression', label: t('page.apiCases.jsonPathExpr'), minWidth: 220, placeholder: '$.data.token' },
  { prop: 'desc', label: t('page.apiCases.fieldDesc'), minWidth: 140 },
]
var assertColumns = [
  { prop: 'target', label: t('page.apiCases.assertTarget'), minWidth: 160, placeholder: '$.status_code' },
  { prop: 'method', label: t('page.apiCases.compareMethod'), minWidth: 130, type: 'select', options: [
    { value: 'eq', label: t('page.apiCases.assertEqual') }, { value: 'ne', label: t('page.apiCases.assertNotEqual') },
    { value: 'contains', label: t('page.apiCases.assertContains') }, { value: 'not_contains', label: t('page.apiCases.assertNotContains') },
    { value: 'gt', label: t('page.apiCases.assertGreaterThan') }, { value: 'lt', label: t('page.apiCases.assertLessThan') },
    { value: 'regex', label: t('page.apiCases.assertRegex') },
  ]},
  { prop: 'expected', label: 'Expected', minWidth: 120 },
]

function insertTemplate(type, code) {
  if (type === 'pre') {
    var current = preOpsScript.value || ''
    emit('update:preOpsScript', current ? current + '\n' + code : code)
  } else {
    var current2 = postOpsScript.value || ''
    emit('update:postOpsScript', current2 ? current2 + '\n' + code : code)
  }
}

var preTemplates = [
  { label: t('page.apiCases.request.tplSaveEnvVar'), code: '# 保存环境（临时）变量\ntest.save_env_variable("变量名", "变量值")' },
  { label: t('page.apiCases.request.tplSaveGlobalVar'), code: '# 保存全局变量\ntest.save_global_variable("变量名", "变量值")' },
  { label: t('page.apiCases.request.tplExecSql'), code: '# 执行SQL\nresult = db.服务器名称.execute_all("SELECT * FROM table LIMIT 1")' },
  { label: t('page.apiCases.request.tplGetEnvVar'), code: '# 获取环境（临时）变量\nval = test.get_env_variable("变量名")' },
  { label: t('page.apiCases.request.tplGetGlobalVar'), code: '# 获取全局变量\nval = test.get_global_variable("变量名")' },
  { label: t('page.apiCases.request.tplSendRequest'), code: '# 发送HTTP请求\nresp = test.request("POST", "/api/path", json={"key": "value"})' },
  { label: t('page.apiCases.request.tplWait'), code: '# 等待\ntest.sleep(1)' },
  { label: t('page.apiCases.request.tplExecFunction'), code: '# 调用自定义函数\nresult = global_func.方法名()' },
]

var postTemplates = [
  { label: t('page.apiCases.request.tplGetResponseBody'), code: '# 获取响应体\nbody = response.data' },
  { label: t('page.apiCases.request.tplGetJsonResponse'), code: '# 获取JSON响应\njson_body = response.json()' },
  { label: t('page.apiCases.request.tplJsonPathSingle'), code: '# JSONPath提取单个值\nval = test.json_extract(json_body, "$.data.token")' },
  { label: t('page.apiCases.request.tplJsonPathList'), code: '# JSONPath提取列表\nvals = test.json_extract_list(json_body, "$.data[*].id")' },
  { label: t('page.apiCases.request.tplRegexSingle'), code: '# 正则提取单个\nval = test.re_extract(body, r"pattern")' },
  { label: t('page.apiCases.request.tplRegexList'), code: '# 正则提取列表\nvals = test.re_extract_list(body, r"pattern")' },
  { label: t('page.apiCases.request.tplAssertResult'), code: '# 断言\ntest.assertion("eq", expected, actual)' },
  { label: t('page.apiCases.request.tplSaveEnvVar'), code: '# 保存环境（临时）变量\ntest.save_env_variable("变量名", val)' },
  { label: t('page.apiCases.request.tplSaveGlobalVar'), code: '# 保存全局变量\ntest.save_global_variable("变量名", val)' },
  { label: t('page.apiCases.request.tplDeleteEnvVar'), code: '# 删除环境（临时）变量\ntest.del_evn_variable("变量名")' },
  { label: t('page.apiCases.request.tplDeleteGlobalVar'), code: '# 删除全局变量\ntest.del_global_variable("变量名")' },
  { label: t('page.apiCases.request.tplExecSql'), code: '# 执行SQL\nresult = db.服务器名称.execute_all("SELECT * FROM table")' },
  { label: t('page.apiCases.request.tplSaveToFile'), code: '# 保存到文件\ntest.save_to_file("data.json", body)' },
  { label: t('page.apiCases.request.tplLog'), code: '# 记录日志\ntest.log("debug message")' },
  { label: t('page.apiCases.request.tplExecFunction'), code: '# 调用自定义函数\nresult = global_func.方法名()' },
]

var formColumns = [
  { prop: 'name', label: t('page.apiCases.request.formParamName'), minWidth: 130 },
  { prop: 'type', label: t('page.apiCases.request.formType'), minWidth: 110, type: 'select', options: [
    { value: 'string', label: 'string' }, { value: 'file', label: 'file' },
  ]},
  { prop: 'value', label: t('page.apiCases.request.formParamValue'), minWidth: 180 },
  { prop: 'desc', label: t('page.apiCases.request.formDesc'), minWidth: 100 },
]
</script>

<style scoped lang="scss">
.api-request-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.debug-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.btn-debug-run {
  background-color: $color-info !important;
  border-color: $color-info !important;
  color: #fff !important;

  &:hover {
    background-color: #66b1ff !important;
    border-color: #66b1ff !important;
    color: #fff !important;
  }
}

.debug-sub-tabs {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  :deep(.el-tabs__header) {
    margin-bottom: 0;
    padding: 0 16px;
    background: var(--el-fill-color-blank);
    flex-shrink: 0;
  }

  :deep(.el-tabs__content) {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  :deep(.el-tab-pane) {
    height: 100%;
    overflow-y: auto;
    padding: 10px 16px;
  }
}

.param-type-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  margin: 0 0 8px;
}

.body-editor {
  padding: 0;
  height: calc(100% - 20px);
  display: flex;
  flex-direction: column;
}

.body-type-selector {
  margin-bottom: 10px;
  flex-shrink: 0;
}

.body-json-section {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  overflow: hidden;
  flex: 1;
  min-height: 0;
}

.prepost-container {
  display: flex;
  gap: 16px;
  height: calc(100% - 20px);
}

.prepost-code {
  flex: 1;
  min-width: 0;
  flex-shrink: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  overflow: hidden;
}

.prepost-template {
  width: 280px;
  flex-shrink: 0;
  border-left: 1px solid var(--el-border-color-lighter);
  padding-left: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .template-header {
    font-size: 14px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    border-bottom: 1px solid var(--el-border-color-lighter);
    padding-bottom: 6px;
    margin-bottom: 8px;
    flex-shrink: 0;
  }

  .template-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }

  .template-item {
    padding: 6px 10px;
    cursor: pointer;
    border-radius: 4px;
    border: 1px solid transparent;

    &:hover {
      background: rgba($color-info, 0.1);
      border-color: #b3d8ff;
    }

    .template-name {
      font-size: 14px;
      font-weight: 500;
      color: var(--el-text-color-regular);
    }
  }
}
</style>
