<template>
  <div class="api-workspace app-card">
    <PageHeader :title="t('page.apiCases.title')">
      <template #actions>
        <el-button v-if="projectId && selectedCatalogId" @click="showImport = true">{{ t('page.apiCases.importInterfaces') }}</el-button>
        <el-button v-if="canEdit && selectedCatalogId" type="primary" @click="openCreateInterface">{{ t('page.apiCases.createInterface') }}</el-button>
      </template>
    </PageHeader>
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <SplitView v-else :initial-width="selectedInterfaceId ? 0 : 380" :min-width="300" :max-width="560" :drawer-title="t('page.apiCases.allInterfaces')">
      <template #left>
        <ApiCatalogSidebar
          v-model:keyword="sidebarKeyword"
          :catalog-nodes="catalogTree"
          :selected-catalog-id="selectedCatalogId"
          :selected-interface-id="selectedInterfaceId"
          :expanded-catalog-ids="expandedCatalogIds"
          :interfaces-by-catalog="interfacesByCatalog"
          :can-edit="canEdit"
          @select-root="selectRoot"
          @select-catalog="selectCatalog"
          @select-interface="selectInterfaceFromTree"
          @toggle-expand="onToggleExpand"
          @section-command="onSectionCommand"
          @catalog-command="onCatalogCommand"
          @interface-command="onInterfaceCommand"
          @load-more-interfaces="loadMoreCatalogInterfaces"
          @interface-reorder="onSidebarInterfaceReorder"
          @catalog-drop="onCatalogDrop"
        />
      </template>
      <template #right>
        <!-- 未选中接口时显示接口列表 -->
        <template v-if="!selectedInterfaceId">
          <InterfaceListPanel
            v-model:search-query="listSearch"
            :interfaces="interfaceList"
            :loading="listLoading"
            :total="listTotal"
            :page="listPage"
            :page-size="listPageSize"
            :selected-interface-id="selectedInterfaceId"
            :can-edit="canEdit"
            @search="onListSearch"
            @select="selectInterfaceFromList"
            @edit="openEditInterface"
            @copy="copyInterfaceItem"
            @delete="removeInterfaceItem"
            @page-change="onListPageChange"
            @size-change="onListSizeChange"
            @reorder="onListInterfaceReorder"
          />
        </template>

        <!-- 选中接口后展示3个Tab详情页 -->
        <div v-else class="interface-detail-view">

          <!-- ====== Tab 1: 文档预览 ====== -->
          <div v-show="activeTab === 'doc-preview'" class="detail-panel">
            <h3 class="detail-title">{{ currentIfaceSummary || '-' }}</h3>
            <section class="doc-section">
              <h4>{{ t('page.apiCases.request') }}</h4>
              <div class="request-info-bar">
                <span class="method-tag" :class="'method-' + (currentIfaceMethod || 'GET').toLowerCase()">{{ currentIfaceMethod || 'GET' }}</span>
                <span class="path-text">{{ currentIfacePath || '' }}</span>
              </div>
            </section>
            <section class="doc-section">
              <h4>{{ t('page.apiCases.requestBody') }}</h4>
              <el-table :data="requestBodyFields" border size="small" empty-text="-" row-key="__path">
                <el-table-column prop="name" :label="t('page.apiCases.fieldName')" min-width="160" />
                <el-table-column prop="path" :label="t('page.apiCases.fieldPath')" min-width="200" />
                <el-table-column prop="type" :label="t('page.apiCases.fieldType')" width="140" />
                <el-table-column prop="required" :label="t('page.apiCases.fieldRequired')" width="70" align="center">
                  <template #default="{ row }">{{ row.required ? '是' : '否' }}</template>
                </el-table-column>
                <el-table-column prop="nullable" :label="t('page.apiCases.fieldNullable')" width="70" align="center">
                  <template #default="{ row }">{{ row.nullable ? '是' : '否' }}</template>
                </el-table-column>
                <el-table-column prop="desc" :label="t('page.apiCases.fieldDesc')" min-width="180" show-overflow-tooltip />
              </el-table>
            </section>
            <section class="doc-section">
              <h4>{{ t('page.apiCases.responseParams') }}</h4>
              <el-table :data="responseBodyFields" border size="small" empty-text="-">
                <el-table-column prop="name" :label="t('page.apiCases.fieldName')" min-width="160" />
                <el-table-column prop="path" :label="t('page.apiCases.fieldPath')" min-width="200" />
                <el-table-column prop="type" :label="t('page.apiCases.fieldType')" width="140" />
                <el-table-column prop="desc" :label="t('page.apiCases.fieldDesc')" min-width="180" show-overflow-tooltip />
              </el-table>
            </section>
          </div>

          <!-- ====== Tab 2: 测试用例 ====== -->
          <div v-show="activeTab === 'test-cases'" class="detail-panel">
            <div class="case-toolbar-row">
              <div class="case-toolbar-left">
                <el-input
                  v-model="caseSearchKey"
                  :placeholder="t('page.apiCases.searchCases')"
                  clearable
                  size="default"
                  style="width: 260px"
                  :prefix-icon="Search"
                />
                <el-button :icon="Filter" circle size="default" />
              </div>
              <div class="case-toolbar-right">
                <el-dropdown trigger="click">
                  <el-button>
                    <el-icon><Document /></el-icon> {{ t('page.apiCases.selectVarFile') }}<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item>$base_url</el-dropdown-item>
                      <el-dropdown-item>$token</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-dropdown trigger="click">
                  <el-button>
                    {{ t('page.apiCases.batchOps') }}<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item>批量运行</el-dropdown-item>
                      <el-dropdown-item>批量删除</el-dropdown-item>
                      <el-dropdown-item>批量导出</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-button v-if="canEdit" type="primary" :icon="MagicStick" @click="showGenerate = true">{{ t('page.apiCases.generateCases') }}</el-button>
              </div>
            </div>

            <!-- 前置操作分组 -->
            <el-collapse v-model="preCollapseOpen" class="case-collapse">
              <el-collapse-item name="pre">
                <template #title>
                  <span class="collapse-title">{{ t('page.apiCases.preconditionCases') }}</span>
                  <el-badge :value="filteredPreconditionCases.length" type="info" class="collapse-badge" />
                </template>
                <el-table :data="filteredPreconditionCases" border size="small" row-key="id" empty_text="-" @row-click="(row) => router.push('/cases/api/cases/' + row.id)">
                  <el-table-column type="selection" width="40" />
                  <el-table-column prop="title" :label="t('page.apiCases.caseName')" min-width="200" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.title || row.name || '-' }}</template>
                  </el-table-column>
                  <el-table-column prop="updated_at" :label="t('page.apiCases.updateTime')" width="170">
                    <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
                  </el-table-column>
                  <el-table-column :label="t('page.apiCases.updateUser')" width="100">
                    <template #default>-</template>
                  </el-table-column>
                  <el-table-column :label="t('page.apiCases.runStatus')" width="90" align="center">
                    <template #default="{ row }">
                      <el-tag v-if="row.exec_status" size="small" :type="execStatusTag(row.exec_status)">{{ execStatusLabel(row.exec_status) }}</el-tag>
                      <span v-else>-</span>
                    </template>
                  </el-table-column>
                  <el-table-column :label="t('page.apiCases.syncStatus')" width="80" align="center">
                    <template #default>
                      <el-tag size="small" type="warning">未同步</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column :label="t('common.actions')" width="200" fixed="right">
                    <template #default="{ row }">
                      <el-button link type="primary" size="small" :icon="View" @click.stop="router.push('/cases/api/cases/' + row.id)" />
                      <el-button link type="primary" size="small" :icon="EditPen" @click.stop="router.push('/cases/api/cases/' + row.id)" />
                      <el-button link type="primary" size="small" :icon="CopyDocument" @click.stop="" />
                      <el-button link type="danger" size="small" :icon="Delete" @click.stop="" />
                    </template>
                  </el-table-column>
                </el-table>
              </el-collapse-item>
            </el-collapse>

            <!-- 测试用例分组 -->
            <el-collapse v-model="mainCollapseOpen" class="case-collapse">
              <el-collapse-item name="main">
                <template #title>
                  <span class="collapse-title">{{ t('page.apiCases.mainCases') }}</span>
                  <el-badge :value="filteredMainCases.length" type="info" class="collapse-badge" />
                </template>
                <el-table :data="filteredMainCases" border size="small" row-key="id" empty_text="-" @row-click="(row) => router.push('/cases/api/cases/' + row.id)">
                  <el-table-column type="selection" width="40" />
                  <el-table-column prop="title" :label="t('page.apiCases.caseName')" min-width="200" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.title || row.name || '-' }}</template>
                  </el-table-column>
                  <el-table-column prop="updated_at" :label="t('page.apiCases.updateTime')" width="170">
                    <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
                  </el-table-column>
                  <el-table-column :label="t('page.apiCases.updateUser')" width="100">
                    <template #default>-</template>
                  </el-table-column>
                  <el-table-column :label="t('page.apiCases.runStatus')" width="90" align="center">
                    <template #default="{ row }">
                      <el-tag v-if="row.exec_status" size="small" :type="execStatusTag(row.exec_status)">{{ execStatusLabel(row.exec_status) }}</el-tag>
                      <span v-else>-</span>
                    </template>
                  </el-table-column>
                  <el-table-column :label="t('page.apiCases.syncStatus')" width="80" align="center">
                    <template #default>
                      <el-tag size="small" type="warning">未同步</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column :label="t('common.actions')" width="200" fixed="right">
                    <template #default="{ row }">
                      <el-button link type="primary" size="small" :icon="View" @click.stop="router.push('/cases/api/cases/' + row.id)" />
                      <el-button link type="primary" size="small" :icon="EditPen" @click.stop="router.push('/cases/api/cases/' + row.id)" />
                      <el-button link type="primary" size="small" :icon="CopyDocument" @click.stop="" />
                      <el-button link type="danger" size="small" :icon="Delete" @click.stop="" />
                    </template>
                  </el-table-column>
                </el-table>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- ====== Tab 1: 接口调试 ====== -->
          <div v-show="activeTab === 'interface-debug'" class="detail-panel">
            <div class="debug-header-row">
              <h3 class="detail-title">{{ currentIfaceSummary || '-' }}</h3>
              <el-dropdown trigger="click" size="small">
                <el-button size="default">
                  <el-icon><Document /></el-icon> {{ t('page.apiCases.selectVarFile') }}<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item>默认环境</el-dropdown-item>
                    <el-dropdown-item>测试环境</el-dropdown-item>
                    <el-dropdown-item>预发环境</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <div class="debug-toolbar">
              <el-select v-model="debugMethod" size="default" style="width: 110px">
                <el-option v-for="m in httpMethods" :key="m" :value="m" :label="m" />
              </el-select>
              <el-input v-model="debugBaseUrl" placeholder="$(base_url)" size="default" style="width: 220px" />
              <el-input v-model="debugPath" size="default" style="flex: 1; min-width: 0" />
              <el-button v-if="!debugging" class="btn-debug-run" @click="runDebug">{{ t('page.apiCases.debugRun') }}</el-button>
              <el-button v-else type="warning" size="default" @click="cancelDebug">{{ t('common.cancel') }}</el-button>
              <el-button size="default" @click="saveTemplate">{{ t('page.apiCases.debugSave') }}</el-button>
            </div>

            <el-tabs v-model="debugSubTab" class="debug-sub-tabs">
              <!-- Headers -->
              <el-tab-pane :label="t('page.apiCases.subTabHeaders')" name="headers">
                <div class="sub-tab-content">
                  <el-table :data="headerRows" border size="small" empty_text="">
                    <el-table-column prop="name" :label="t('page.apiCases.paramName')" min-width="150">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < headerRows.length - 1" v-model="row.name" size="small" placeholder="" />
                        <span v-else class="add-param-link" @click="addHeaderRow">{{ t('page.apiCases.addParam') }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="value" :label="t('page.apiCases.paramValue')" min-width="200">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < headerRows.length - 1" v-model="row.value" size="small" placeholder="" />
                        <span v-else></span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="desc" :label="t('page.apiCases.fieldDesc')" min-width="140">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < headerRows.length - 1" v-model="row.desc" size="small" placeholder="" />
                        <span v-else></span>
                      </template>
                    </el-table-column>
                    <el-table-column :label="t('page.apiCases.operation')" width="60" align="center">
                      <template #default="{ $index }">
                        <el-button v-if="$index < headerRows.length - 1" link type="danger" size="small" :icon="Close" @click="removeHeaderRow($index)" />
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>
              <!-- Params -->
              <el-tab-pane :label="t('page.apiCases.subTabParams')" name="params">
                <div class="sub-tab-content">
                  <h4>QUERY参数</h4>
                  <el-table :data="queryParamRows" border size="small" empty_text="">
                    <el-table-column prop="name" :label="t('page.apiCases.paramName')" min-width="150">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < queryParamRows.length - 1" v-model="row.name" size="small" placeholder="" />
                        <span v-else class="add-param-link" @click="addQueryParam">{{ t('page.apiCases.addParam') }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="value" :label="t('page.apiCases.paramValue')" min-width="200">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < queryParamRows.length - 1" v-model="row.value" size="small" placeholder="" />
                        <span v-else></span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="desc" :label="t('page.apiCases.fieldDesc')" min-width="180">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < queryParamRows.length - 1" v-model="row.desc" size="small" placeholder="" />
                        <span v-else></span>
                      </template>
                    </el-table-column>
                    <el-table-column :label="t('page.apiCases.operation')" width="60" align="center">
                      <template #default="{ $index }">
                        <el-button v-if="$index < queryParamRows.length - 1" link type="danger" size="small" :icon="Close" @click="removeQueryParam($index)" />
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>
              <!-- Path -->
              <el-tab-pane :label="t('page.apiCases.subTabPath')" name="path">
                <div class="sub-tab-content">
                  <el-table :data="pathParamRows" border size="small" empty_text="">
                    <el-table-column prop="name" :label="t('page.apiCases.paramName')" min-width="150">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < pathParamRows.length - 1" v-model="row.name" size="small" placeholder="" />
                        <span v-else class="add-param-link" @click="addPathParam">{{ t('page.apiCases.addParam') }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="value" :label="t('page.apiCases.paramValue')" min-width="200">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < pathParamRows.length - 1" v-model="row.value" size="small" placeholder="" />
                        <span v-else></span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="desc" :label="t('page.apiCases.fieldDesc')" min-width="140">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < pathParamRows.length - 1" v-model="row.desc" size="small" placeholder="" />
                        <span v-else></span>
                      </template>
                    </el-table-column>
                    <el-table-column :label="t('page.apiCases.operation')" width="60" align="center">
                      <template #default="{ $index }">
                        <el-button v-if="$index < pathParamRows.length - 1" link type="danger" size="small" :icon="Close" @click="removePathParam($index)" />
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>
              <!-- Body -->
              <el-tab-pane :label="t('page.apiCases.subTabBody')" name="body">
                <div class="sub-tab-content body-editor">
                  <MonacoJsonEditor v-model="requestJson" :height="260" />
                </div>
              </el-tab-pane>
              <!-- Extract (提取) -->
              <el-tab-pane :label="t('page.apiCases.extractTabLabel')" name="extract">
                <div class="sub-tab-content">
                  <el-table :data="extractRows" border size="small" empty_text="">
                    <el-table-column prop="name" :label="t('page.apiCases.varName')" min-width="150">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < extractRows.length - 1" v-model="row.name" size="small" placeholder="" />
                        <span v-else class="add-param-link" @click="addExtractRow">{{ t('page.apiCases.addParam') }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="expression" :label="t('page.apiCases.jsonPathExpr')" min-width="220">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < extractRows.length - 1" v-model="row.expression" size="small" placeholder="$.data.token" />
                        <span v-else></span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="desc" :label="t('page.apiCases.fieldDesc')" min-width="140">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < extractRows.length - 1" v-model="row.desc" size="small" placeholder="" />
                        <span v-else></span>
                      </template>
                    </el-table-column>
                    <el-table-column :label="t('page.apiCases.operation')" width="60" align="center">
                      <template #default="{ $index }">
                        <el-button v-if="$index < extractRows.length - 1" link type="danger" size="small" :icon="Close" @click="removeExtractRow($index)" />
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>
              <!-- Assert -->
              <el-tab-pane :label="t('page.apiCases.subTabAssert')" name="assert">
                <div class="sub-tab-content">
                  <el-table :data="assertRows" border size="small" empty_text="">
                    <el-table-column prop="target" :label="t('page.apiCases.assertTarget')" min-width="160">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < assertRows.length - 1" v-model="row.target" size="small" placeholder="$.status_code" />
                        <span v-else class="add-param-link" @click="addAssertRow">{{ t('page.apiCases.addParam') }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="method" :label="t('page.apiCases.compareMethod')" min-width="130">
                      <template #default="{ row, $index }">
                        <el-select v-if="$index < assertRows.length - 1" v-model="row.method" size="small" style="width:100%">
                          <el-option label="==" value="eq" />
                          <el-option label="!=" value="neq" />
                          <el-option label="contains" value="contains" />
                          <el-option label=">" value="gt" />
                          <el-option label="<" value="lt" />
                          <el-option label="in" value="in" />
                          <el-option label="exists" value="exists" />
                        </el-select>
                        <span v-else></span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="expected" :label="t('page.apiCases.expectedValue')" min-width="140">
                      <template #default="{ row, $index }">
                        <el-input v-if="$index < assertRows.length - 1" v-model="row.expected" size="small" placeholder="" />
                        <span v-else></span>
                      </template>
                    </el-table-column>
                    <el-table-column :label="t('page.apiCases.operation')" width="60" align="center">
                      <template #default="{ $index }">
                        <el-button v-if="$index < assertRows.length - 1" link type="danger" size="small" :icon="Close" @click="removeAssertRow($index)" />
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>
              <!-- PreOps (Python) -->
              <el-tab-pane :label="t('page.apiCases.subTabPreOps')" name="preops">
                <div class="sub-tab-content prepost-editor">
                  <div class="prepost-hint">
                    <el-tag size="small" type="info">test.方法名() 调用接口测试引擎方法</el-tag>
                    <el-button text size="small" type="primary" @click="showPreMethods = !showPreMethods">{{ t('page.apiCases.predefinedMethods') }}</el-button>
                  </div>
                  <div v-if="showPreMethods" class="methods-helper">
                    <p><code>test.set_env_var(key, value)</code> — 设置环境变量</p>
                    <p><code>test.get_env_var(key)</code> — 获取环境变量</p>
                    <p><code>test.request(method, url, **kwargs)</code> — 发送HTTP请求</p>
                    <p><code>test.sleep(seconds)</code> — 等待</p>
                    <p><code>test.extract_json(response, json_path)</code> — 从响应提取JSON</p>
                  </div>
                  <MonacoJsonEditor v-model="preOpsCode" :height="220" lang="python" />
                </div>
              </el-tab-pane>
              <!-- PostOps (Python) -->
              <el-tab-pane :label="t('page.apiCases.subTabPostOps')" name="postops">
                <div class="sub-tab-content prepost-editor">
                  <div class="prepost-hint">
                    <el-tag size="small" type="info">test.方法名() 调用接口测试引擎方法</el-tag>
                    <el-button text size="small" type="primary" @click="showPostMethods = !showPostMethods">{{ t('page.apiCases.predefinedMethods') }}</el-button>
                  </div>
                  <div v-if="showPostMethods" class="methods-helper">
                    <p><code>test.set_env_var(key, value)</code> — 设置环境变量</p>
                    <p><code>test.get_env_var(key)</code> — 获取环境变量</p>
                    <p><code>test.assert_eq(actual, expected)</code> — 断言相等</p>
                    <p><code>test.save_to_file(filename, content)</code> — 保存到文件</p>
                    <p><code>test.log(message)</code> — 记录日志</p>
                  </div>
                  <MonacoJsonEditor v-model="postOpsCode" :height="220" lang="python" />
                </div>
              </el-tab-pane>
            </el-tabs>

            <div class="response-area">
              <div class="response-area-toolbar">
                <el-tabs v-model="responseSubTab" class="response-sub-tabs">
                  <el-tab-pane :label="t('page.apiCases.resultInfo')" name="result" />
                  <el-tab-pane :label="t('page.apiCases.responseInfo')" name="response-info" />
                  <el-tab-pane :label="t('page.apiCases.requestInfo')" name="request-info" />
                  <el-tab-pane :label="t('page.apiCases.extractInfo')" name="extract-info" />
                  <el-tab-pane :label="t('page.apiCases.assertInfo')" name="assert-info" />
                </el-tabs>
                <el-button link type="primary" size="small" :icon="Clock" @click="showTestRecords = true">{{ t('page.apiCases.testRecord') }}</el-button>
              </div>
              <div class="response-body">
                <template v-if="responseSubTab === 'result' && responseJson">
                  <div v-if="!debugging" class="run-result-block">
                    <el-icon color="#67C23A"><CircleCheckFilled /></el-icon>
                    <span class="result-label">执行成功</span>
                    <span class="result-meta">操作人: yexuemei &nbsp;&nbsp; 时间: {{ formatDateTime(new Date()) }}</span>
                  </div>
                  <pre class="response-pre">{{ responseJson }}</pre>
                </template>
                <el-empty v-else description="暂无数据" :image-size="48" />
              </div>
            </div>
          </div>

          <!-- 底部固定Tab导航条 -->
          <div v-if="selectedInterfaceId" class="detail-nav-tabs">
            <el-radio-group v-model="activeTab" size="default">
              <el-radio-button value="interface-debug">{{ t('page.apiCases.tabInterfaceDebug') }}</el-radio-button>
              <el-radio-button value="doc-preview">{{ t('page.apiCases.tabDocPreview') }}</el-radio-button>
              <el-radio-button value="test-cases">{{ t('page.apiCases.tabTestCases') }}</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>
    </SplitView>

    <ImportInterfacesWizard v-model="showImport" :catalog-id="selectedCatalogId" @imported="onImported" />
    <InterfaceFormDrawer
      v-model="showInterfaceForm"
      :catalog-id="interfaceFormCatalogId"
      :interface-data="editingInterface"
      @saved="onInterfaceSaved"
    />
    <InterfaceCaseGenerateDialog
      v-if="selectedInterfaceId"
      v-model="showGenerate"
      :interface-id="selectedInterfaceId"
      @confirmed="loadCases"
    />
    <CatalogMoveDialog
      v-model="showMoveDialog"
      :catalog-nodes="catalogTree"
      :exclude-catalog-id="moveCatalogId"
      :loading="moveLoading"
      @confirm="confirmMoveCatalog"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  Clock,
  Close,
  CopyDocument,
  Delete,
  Document,
  EditPen,
  Filter,
  MagicStick,
  Search,
  View,
} from '@element-plus/icons-vue'
import {
  CircleCheckFilled,
} from '@element-plus/icons-vue'
import {
  copyInterface,
  createApiCatalog,
  debugRunInterface,
  deleteApiCatalog,
  deleteInterface,
  fillDebugFromDoc,
  getApiCatalogTree,
  getDebugTemplate,
  getDocPreview,
  listApiCases,
  listDependencies,
  listInterfaces as fetchInterfaces,
  listInterfacesByCatalog,
  moveApiCatalog,
  reanalyzeDependencies,
  reorderInterfaces,
  saveDebugTemplate,
  updateApiCatalog,
} from '@/api/apiTest'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SplitView from '@/components/common/SplitView.vue'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'
import ImportInterfacesWizard from '@/components/api-test/ImportInterfacesWizard.vue'
import InterfaceFormDrawer from '@/components/api-test/InterfaceFormDrawer.vue'
import InterfaceCaseGenerateDialog from '@/components/agent/InterfaceCaseGenerateDialog.vue'
import ApiCatalogSidebar from '@/components/tree/ApiCatalogSidebar.vue'
import InterfaceListPanel from '@/components/api-test/InterfaceListPanel.vue'
import CatalogMoveDialog from '@/components/tree/CatalogMoveDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()

// ==================== 目录树 / 接口列表 ====================
const catalogTree = ref([])
const selectedCatalogId = ref(route.query.catalogId ? Number(route.query.catalogId) : null)
const selectedInterfaceId = ref(route.query.interfaceId ? Number(route.query.interfaceId) : null)
const sidebarKeyword = ref('')
const expandedCatalogIds = ref([])
const interfacesByCatalog = ref({})

const interfaceList = ref([])
const listLoading = ref(false)
const listTotal = ref(0)
const listPage = ref(1)
const listPageSize = ref(20)
const listSearch = ref('')

// ==================== 详情页3个Tab状态 ====================
const activeTab = ref('interface-debug')
const environmentId = ref(null)

// 调试相关
const requestJson = ref('{}')
const responseJson = ref('')
const assertionsJson = ref('[]')
const debugging = ref(false)
const debugAbortController = ref(null)
const debugMethod = ref('POST')
const debugBaseUrl = ref('$(base_url)')
const debugPath = ref('')
const debugSubTab = ref('params')
const responseSubTab = ref('result')
const queryParamRows = ref([{ name: '', value: '', desc: '' }])
const headerRows = ref([{ name: 'Content-Type', value: 'application/json', desc: '' }])
const pathParamRows = ref([{ name: '', value: '', desc: '' }])
const extractRows = ref([{ name: '', expression: '', desc: '' }])
const assertRows = ref([{ target: '', method: 'eq', expected: '' }])
const preOpsCode = ref('# 前置操作代码\n')
const postOpsCode = ref('# 后置操作代码\n')
const showPreMethods = ref(false)
const showPostMethods = ref(false)
const showTestRecords = ref(false)
const httpMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

// 文档预览相关
const reanalyzing = ref(false)
const dependencies = ref(null)
const docPreview = ref(null)

// 测试用例Tab相关
const preconditionCases = ref([])
const mainCases = ref([])
const casesLoading = ref(false)
const caseSearchKey = ref('')
const preCollapseOpen = ref(['pre'])
const mainCollapseOpen = ref(['main'])
const showImport = ref(false)
const showInterfaceForm = ref(false)
const showGenerate = ref(false)
const editingInterface = ref(null)
const interfaceFormCatalogId = ref(null)

// 目录管理
const showMoveDialog = ref(false)
const moveCatalogId = ref(null)
const moveLoading = ref(false)

// ==================== 计算属性 ====================
const depJson = computed(function () { return JSON.stringify(dependencies.value ?? {}, null, 2) })
const docPreviewJson = computed(function () { return docPreview.value ? JSON.stringify(docPreview.value, null, 2) : '' })

function findSelectedIface() {
  if (!selectedInterfaceId.value) return null
  var found = interfaceList.value.find(function (i) { return i.id === selectedInterfaceId.value })
  if (found) return found
  var cats = Object.values(interfacesByCatalog.value)
  for (var ci = 0; ci < cats.length; ci++) {
    var item = cats[ci].items ? cats[ci].items.find(function (i) { return i.id === selectedInterfaceId.value }) : null
    if (item) return item
  }
  return null
}

var _ifaceCache = { iface: null, id: null }
function _getCachedIface() {
  var curId = selectedInterfaceId.value
  if (_ifaceCache.id !== curId) {
    _ifaceCache.iface = findSelectedIface()
    _ifaceCache.id = curId
  }
  return _ifaceCache.iface
}
watch(selectedInterfaceId, function () { _ifaceCache.id = null })

var currentIfaceSummary = computed(function () { var f = _getCachedIface(); return f ? (f.summary || f.name || '') : '' })
var currentIfaceMethod = computed(function () { var f = _getCachedIface(); return f ? (f.method ? f.method.toUpperCase() : '') : '' })
var currentIfacePath = computed(function () { var f = _getCachedIface(); return f ? (f.path || '') : '' })

/** 从 docPreview 解析请求体字段表格 */
var requestBodyFields = computed(function () {
  if (!docPreview.value) return []
  var body = docPreview.value.request_body || []
  return flattenSchema(body, 'root')
})

/** 从 docPreview 解析返回参数字段表格 */
var responseBodyFields = computed(function () {
  if (!docPreview.value) return []
  var responses = docPreview.value.responses || []
  if (responses.length === 0) return []
  var firstResp = responses[0]
  if (typeof firstResp === 'string' || !firstResp.body) return []
  return flattenResponseSchema(firstResp.body)
})

/** 过滤后的前置操作用例 */
var filteredPreconditionCases = computed(function () {
  var kw = caseSearchKey.value.trim().toLowerCase()
  if (!kw) return preconditionCases.value
  return preconditionCases.value.filter(function (c) {
    var n = c.title || c.name || ''
    return n.toLowerCase().indexOf(kw) >= 0
  })
})

/** 过滤后的测试用例 */
var filteredMainCases = computed(function () {
  var kw = caseSearchKey.value.trim().toLowerCase()
  if (!kw) return mainCases.value
  return mainCases.value.filter(function (c) {
    var n = c.title || c.name || ''
    return n.toLowerCase().indexOf(kw) >= 0
  })
})

// ==================== 工具函数 ====================
function findCatalogNode(nodes, id) {
  for (var ni = 0; ni < nodes.length; ni++) {
    var node = nodes[ni]
    if (node.id === id) return node
    if (node.children && node.children.length) {
      var found = findCatalogNode(node.children, id)
      if (found) return found
    }
  }
  return null
}

function findCatalogName(nodes, catalogId) {
  var n = findCatalogNode(nodes, catalogId)
  return n ? n.name : String(catalogId)
}

function getSiblingList(nodes, parentId) {
  if (parentId == null) return nodes
  var p = findCatalogNode(nodes, parentId)
  return p ? (p.children || []) : []
}

/** 扁平化请求体schema为表格行 */
function flattenSchema(schema, parentPath) {
  if (!parentPath) parentPath = 'root'
  if (!schema) return []
  if (Array.isArray(schema)) {
    var result = []
    for (var ai = 0; ai < schema.length; ai++) {
      var aitem = schema[ai]
      if (typeof aitem === 'object' && aitem !== null) {
        var apath = parentPath + '[' + ai + ']'
        result.push(...flattenSchema(aitem, apath))
      }
    }
    return result
  }
  if (typeof schema !== 'object') return []
  var props = schema.properties || schema
  var requiredSet = new Set(schema.required || [])
  var rows = []
  var pkeys = Object.keys(props)
  for (var pi = 0; pi < pkeys.length; pi++) {
    var key = pkeys[pi]
    var val = props[key]
    if (typeof val !== 'object' || val === null) continue
    var fpath = parentPath === 'root' ? key : parentPath + '.' + key
    var typeStr = Array.isArray(val.type) ? val.type.join('|') : (val.type || (val.properties ? 'object' : '-'))
    var hasChildren = val.properties && Object.keys(val.properties).length > 0
    rows.push({
      __path: fpath,
      name: key,
      path: fpath,
      type: typeStr,
      required: requiredSet.has(key),
      nullable: val.nullable || false,
      desc: val.description || val.title || '',
    })
    if (hasChildren) {
      rows.push(...flattenSchema(val.properties, fpath))
    }
  }
  return rows
}

/** 扁平化响应body为表格行 - 使用字符串拼接避免SFC编译器解析反引号 */
function flattenResponseSchema(obj, parentPath) {
  if (!parentPath) parentPath = ''
  if (!obj || typeof obj !== 'object') return []
  if (Array.isArray(obj)) {
    var result = []
    for (var i = 0; i < obj.length; i++) {
      var item = obj[i]
      if (typeof item === 'object' && item !== null) {
        var pKey = parentPath + '[' + i + ']'
        result.push({ __path: pKey, name: '[' + i + ']', path: pKey, type: 'array[item]', desc: '' })
        var children = flattenResponseSchema(item, pKey)
        for (var c = 0; c < children.length; c++) result.push(children[c])
      }
    }
    return result
  }
  var rows = []
  var keys = Object.keys(obj)
  for (var k = 0; k < keys.length; k++) {
    var key = keys[k]
    var val = obj[key]
    var rpath = parentPath ? parentPath + '.' + key : key
    var typeStr = Array.isArray(val && val.type) ? val.type.join('|') : (val && val.type || typeof val)
    rows.push({
      __path: rpath,
      name: key,
      path: rpath,
      type: typeStr,
      desc: val && val.description || '',
    })
    if (val && typeof val === 'object' && (val.properties || (Array.isArray(val) && val.length))) {
      var subRows = flattenResponseSchema(val.properties || val, rpath)
      for (var s = 0; s < subRows.length; s++) rows.push(subRows[s])
    }
  }
  return rows
}

function formatTime(isoStr) {
  if (!isoStr) return '-'
  try {
    var d = new Date(isoStr)
    function pad(n) { return String(n).padStart(2, '0') }
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes())
  } catch (e) {
    return isoStr
  }
}

function formatDateTime(d) {
  try {
    function pad2(n) { return String(n).padStart(2, '0') }
    return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()) + ' ' + pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds())
  } catch (e) {
    return ''
  }
}

function methodTagType(method) {
  var m = (method || '').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

function execStatusTag(status) {
  var s = String(status).toLowerCase()
  if (s.indexOf('success') >= 0 || s.indexOf('pass') >= 0) return 'success'
  if (s.indexOf('fail') >= 0 || s.indexOf('error') >= 0) return 'danger'
  if (s.indexOf('running') >= 0 || s.indexOf('pending') >= 0) return 'warning'
  return 'info'
}

function execStatusLabel(status) {
  var s = String(status).toLowerCase()
  if (s === 'success' || s === 'pass') return '成功'
  if (s === 'fail' || s === 'error') return '失败'
  if (s === 'running') return '运行中'
  if (s === 'pending') return '待执行'
  if (s === 'ready') return '就绪'
  return status
}

// ==================== Query Params 操作 ====================
function addQueryParam() {
  queryParamRows.value.push({ name: '', value: '', desc: '' })
}
function removeQueryParam(idx) {
  queryParamRows.value.splice(idx, 1)
}

// Headers
function addHeaderRow() {
  headerRows.value.push({ name: '', value: '', desc: '' })
}
function removeHeaderRow(idx) {
  headerRows.value.splice(idx, 1)
}

// Path Params
function addPathParam() {
  pathParamRows.value.push({ name: '', value: '', desc: '' })
}
function removePathParam(idx) {
  pathParamRows.value.splice(idx, 1)
}

// Extract (提取)
function addExtractRow() {
  extractRows.value.push({ name: '', expression: '', desc: '' })
}
function removeExtractRow(idx) {
  extractRows.value.splice(idx, 1)
}

// Assert
function addAssertRow() {
  assertRows.value.push({ target: '', method: 'eq', expected: '' })
}
function removeAssertRow(idx) {
  assertRows.value.splice(idx, 1)
}

/** 构建调试请求payload（将表格数据转换为后端格式） */
function buildDebugPayload() {
  var headers = {}
  for (var hi = 0; hi < headerRows.value.length; hi++) {
    var h = headerRows.value[hi]
    if (h.name && h.name.trim()) headers[h.name.trim()] = h.value || ''
  }
  var query = {}
  for (var qi = 0; qi < queryParamRows.value.length; qi++) {
    var q = queryParamRows.value[qi]
    if (q.name && q.name.trim()) query[q.name.trim()] = q.value || ''
  }
  var pathParams = {}
  for (var pi = 0; pi < pathParamRows.value.length; pi++) {
    var p = pathParamRows.value[pi]
    if (p.name && p.name.trim()) pathParams[p.name.trim()] = p.value || ''
  }

  var extracts = []
  for (var ei = 0; ei < extractRows.value.length; ei++) {
    var e = extractRows.value[ei]
    if (e.name && e.name.trim()) {
      extracts.push({
        name: e.name.trim(),
        json_path: e.expression || '',
        expression: e.expression || '',
        description: e.desc || '',
      })
    }
  }

  var assertions = []
  for (var ai = 0; ai < assertRows.value.length; ai++) {
    var a = assertRows.value[ai]
    if (a.target && a.target.trim()) {
      assertions.push({
        target: a.target.trim(),
        comparator: a.method || 'eq',
        expected: a.expected !== undefined ? a.expected : '',
      })
    }
  }

  var body = null
  try { body = JSON.parse(requestJson.value) } catch (e) {}

  return {
    method: debugMethod.value,
    path: debugPath.value,
    headers: headers,
    query: query,
    path_params: pathParams,
    body: body,
    extracts: extracts,
    assertions: assertions,
    preconditions: [
      { kind: 'python', code: preOpsCode.value },
    ],
    postconditions: [
      { kind: 'python', code: postOpsCode.value },
    ],
  }
}

// ==================== 目录/接口列表加载 ====================
async function loadTree() {
  var params = withProjectParams()
  if (!params) return
  var res = await getApiCatalogTree(params)
  catalogTree.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadInterfaceList() {
  var params = withProjectParams()
  if (!params) return
  listLoading.value = true
  try {
    var query = {
      page: listPage.value,
      page_size: listPageSize.value,
      q: listSearch.value.trim() || undefined,
    }
    var res
    if (selectedCatalogId.value == null) {
      res = await fetchInterfaces(Object.assign({}, params, query))
    } else {
      res = await listInterfacesByCatalog(selectedCatalogId.value, query)
    }
    var data = res.data.data
    interfaceList.value = data?.items ?? []
    listTotal.value = data?.total ?? interfaceList.value.length
  } finally {
    listLoading.value = false
  }
}

async function loadCatalogInterfaces(catalogId, append) {
  if (append === undefined) append = false
  var prev = interfacesByCatalog.value[catalogId] || { items: [], page: 0, total: 0 }
  var page = append ? prev.page + 1 : 1
  if (append) {
    interfacesByCatalog.value[catalogId] = Object.assign({}, prev, { loadingMore: true })
  }
  try {
    var res = await listInterfacesByCatalog(catalogId, { page: page, page_size: 10 })
    var items = res.data.data?.items ?? []
    var total = res.data.data?.total ?? items.length
    interfacesByCatalog.value[catalogId] = {
      items: append ? prev.items.concat(items) : items,
      page: page,
      total: total,
      hasMore: page * 10 < total,
      loadingMore: false,
    }
  } catch (e) {
    if (append) {
      interfacesByCatalog.value[catalogId] = Object.assign({}, prev, { loadingMore: false })
    }
  }
}

function selectRoot() {
  selectedCatalogId.value = null
  selectedInterfaceId.value = null
  listPage.value = 1
  loadInterfaceList()
}

function selectCatalog(catalogId) {
  selectedCatalogId.value = catalogId
  selectedInterfaceId.value = null
  listPage.value = 1
  loadInterfaceList()
}

function selectInterfaceFromTree(iface, catalogId) {
  selectedCatalogId.value = catalogId
  selectedInterfaceId.value = iface.id
}

function selectInterfaceFromList(row) {
  selectedInterfaceId.value = row.id
  if (row.catalog_id != null) selectedCatalogId.value = row.catalog_id
}

function onToggleExpand(catalogId) {
  var idx = expandedCatalogIds.value.indexOf(catalogId)
  if (idx >= 0) {
    expandedCatalogIds.value = expandedCatalogIds.value.filter(function (id) { return id !== catalogId })
  } else {
    expandedCatalogIds.value = expandedCatalogIds.value.concat([catalogId])
    if (!interfacesByCatalog.value[catalogId] || !interfacesByCatalog.value[catalogId].items || !interfacesByCatalog.value[catalogId].items.length) {
      loadCatalogInterfaces(catalogId)
    }
  }
}

function loadMoreCatalogInterfaces(catalogId) {
  loadCatalogInterfaces(catalogId, true)
}

// ==================== 模板/用例/依赖/文档 加载 ====================
async function loadTemplate() {
  if (!selectedInterfaceId.value) return
  var res = await getDebugTemplate(selectedInterfaceId.value).catch(function () { return null })
  var tpl = res && res.data ? res.data.data : {}
  requestJson.value = JSON.stringify(tpl, null, 2)
  assertionsJson.value = JSON.stringify(tpl.assertions || [], null, 2)
  var iface = _getCachedIface()
  if (iface) {
    debugMethod.value = iface.method ? iface.method.toUpperCase() : 'POST'
    debugPath.value = iface.path || ''
  }
}

async function loadCases() {
  if (!selectedInterfaceId.value) return
  casesLoading.value = true
  try {
    var results = await Promise.all([
      listApiCases(selectedInterfaceId.value, { case_kind: 'precondition' }),
      listApiCases(selectedInterfaceId.value, { case_kind: 'main' }),
    ])
    preconditionCases.value = results[0].data.data?.items ?? results[0].data.data ?? []
    mainCases.value = results[1].data.data?.items ?? results[1].data.data ?? []
  } finally {
    casesLoading.value = false
  }
}

async function loadDeps() {
  if (!selectedInterfaceId.value) return
  var res = await listDependencies(selectedInterfaceId.value)
  dependencies.value = res.data.data
}

async function loadDocPreview() {
  if (!selectedInterfaceId.value) return
  var res = await getDocPreview(selectedInterfaceId.value)
  docPreview.value = res.data.data
}

// ==================== 调试操作 ====================
async function runDebug() {
  var controller = new AbortController()
  debugAbortController.value = controller
  debugging.value = true
  try {
    var payload = buildDebugPayload()
    var res = await debugRunInterface(
      selectedInterfaceId.value,
      { environment_id: environmentId.value, payload: payload },
      { signal: controller.signal },
    )
    responseJson.value = JSON.stringify(res.data.data, null, 2)
  } catch (err) {
    if (err.name === 'AbortError') {
      responseJson.value = '{"status":"cancelled","message":' + JSON.stringify(t('common.cancelled')) + '}'
    } else {
      throw err
    }
  } finally {
    debugging.value = false
    debugAbortController.value = null
  }
}

function cancelDebug() {
  if (debugAbortController.value) {
    debugAbortController.value.abort()
  }
}

async function saveTemplate() {
  var payload = buildDebugPayload()
  await saveDebugTemplate(selectedInterfaceId.value, payload)
  ElMessage.success(t('common.saved'))
}

async function fillFromDoc() {
  var res = await fillDebugFromDoc(selectedInterfaceId.value)
  var tpl = res.data.data || {}
  requestJson.value = JSON.stringify(tpl, null, 2)
  assertionsJson.value = JSON.stringify(tpl.assertions || [], null, 2)
  ElMessage.success(t('page.apiCases.filledFromDoc'))
}

async function reanalyze() {
  reanalyzing.value = true
  try {
    await reanalyzeDependencies(selectedInterfaceId.value)
    await loadDeps()
    ElMessage.success(t('common.saved'))
  } finally {
    reanalyzing.value = false
  }
}

// ==================== CRUD 操作 ====================
function openCreateInterface() {
  editingInterface.value = null
  interfaceFormCatalogId.value = selectedCatalogId.value
  showInterfaceForm.value = true
}

function openEditInterface(row) {
  editingInterface.value = row
  interfaceFormCatalogId.value = row.catalog_id != null ? row.catalog_id : selectedCatalogId.value
  showInterfaceForm.value = true
}

async function removeInterfaceItem(row) {
  var id = row && row.id ? row.id : selectedInterfaceId.value
  await ElMessageBox.confirm(t('page.apiCases.interface') + '「' + (row.summary || row.name || row.path || '') + '」？', t('common.confirmDelete'), { type: 'warning' })
  await deleteInterface(id)
  if (selectedInterfaceId.value === id) selectedInterfaceId.value = null
  await refreshAfterInterfaceChange()
  ElMessage.success(t('common.deleted'))
}

async function copyInterfaceItem(row) {
  var id = row && row.id ? row.id : selectedInterfaceId.value
  var res = await copyInterface(id)
  var copied = res.data.data
  ElMessage.success(copied && copied.path ? ('已复制: ' + copied.path) : t('common.saved'))
  await refreshAfterInterfaceChange()
  if (copied && copied.id) selectedInterfaceId.value = copied.id
}

function onInterfaceCommand(cmd, iface) {
  if (cmd === 'edit') openEditInterface(iface)
  else if (cmd === 'copy') copyInterfaceItem(iface)
  else if (cmd === 'delete') removeInterfaceItem(iface)
}

async function refreshAfterInterfaceChange() {
  await loadTree()
  await loadInterfaceList()
  for (var ei = 0; ei < expandedCatalogIds.value.length; ei++) {
    await loadCatalogInterfaces(expandedCatalogIds.value[ei])
  }
}

function onImported() {
  refreshAfterInterfaceChange()
}

function onInterfaceSaved() {
  refreshAfterInterfaceChange()
}

function onListSearch() {
  listPage.value = 1
  loadInterfaceList()
}

function onListPageChange(page) {
  listPage.value = page
  loadInterfaceList()
}

function onListSizeChange(size) {
  listPageSize.value = size
  listPage.value = 1
  loadInterfaceList()
}

async function applyInterfaceReorder(catalogId, orderedIds, targetCatalogId) {
  await reorderInterfaces({
    catalog_id: catalogId,
    ordered_ids: orderedIds,
    target_catalog_id: targetCatalogId,
  })
  await refreshAfterInterfaceChange()
}

async function onListInterfaceReorder(payload) {
  var reordered = interfaceList.value.slice(0)
  var item = reordered.splice(payload.fromIndex, 1)[0]
  reordered.splice(payload.toIndex, 0, item)
  interfaceList.value = reordered
  var catId = selectedCatalogId.value != null ? selectedCatalogId.value : item.catalog_id
  if (catId) await applyInterfaceReorder(catId,_reordered.map(function (r) { return r.id }))
}

async function onSidebarInterfaceReorder(payload) {
  var state = interfacesByCatalog.value[payload.catalogId]
  if (!state) return
  var reordered = state.items.slice(0)
  var item = reordered.splice(payload.fromIndex, 1)[0]
  reordered.splice(payload.toIndex, 0, item)
  interfacesByCatalog.value[payload.catalogId] = Object.assign({}, state, { items: reordered })
  await applyInterfaceReorder(payload.catalogId, reordered.map(function (r) { return r.id }))
}

// ==================== 目录CRUD ====================
async function createCat(parentId) {
  var params = withProjectParams()
  if (!params) return
  var result = await ElMessageBox.prompt(t('page.apiCases.catalogName'), t('page.apiCases.addCatalog'))
  var value = result.value
  if (!value || !value.trim()) return
  await createApiCatalog({ name: value.trim(), parent_id: parentId != null ? parentId : undefined }, params)
  ElMessage.success(t('common.saved'))
  await loadTree()
}

async function renameCat(catalog) {
  var result = await ElMessageBox.prompt(t('page.apiCases.catalogName'), t('page.apiCases.renameCatalog'), {
    inputValue: catalog.name,
  })
  var value = result.value
  if (!value || !value.trim() || value.trim() === catalog.name) return
  await updateApiCatalog(catalog.id, { name: value.trim() })
  ElMessage.success(t('common.saved'))
  await loadTree()
}

async function deleteCat(catalog) {
  await ElMessageBox.confirm(
    t('page.apiCases.catalogDeleteConfirm', { name: catalog.name }),
    t('common.warning'),
    { type: 'warning' },
  )
  await deleteApiCatalog(catalog.id)
  if (selectedCatalogId.value === catalog.id) selectRoot()
  ElMessage.success(t('common.deleted'))
  await loadTree()
  await loadInterfaceList()
}

async function moveCat(catalogId, parentId, sortOrder) {
  await moveApiCatalog(catalogId, {
    parent_id: parentId != null ? parentId : 0,
    sort_order: sortOrder,
  })
  await loadTree()
}

async function moveCatSibling(catalog, direction) {
  var siblings = getSiblingList(catalogTree.value, catalog.parent_id)
  var idx = siblings.findIndex(function (s) { return s.id === catalog.id })
  var targetIdx = direction === 'up' ? idx - 1 : idx + 1
  if (targetIdx < 0 || targetIdx >= siblings.length) return
  var other = siblings[targetIdx]
  await moveApiCatalog(catalog.id, { parent_id: catalog.parent_id != null ? catalog.parent_id : 0, sort_order: other.sort_order })
  await moveApiCatalog(other.id, { parent_id: other.parent_id != null ? other.parent_id : 0, sort_order: catalog.sort_order })
  await loadTree()
}

function openMoveDialog(catalog) {
  moveCatalogId.value = catalog.id
  showMoveDialog.value = true
}

async function confirmMoveCatalog(parentId) {
  if (!moveCatalogId.value) return
  moveLoading.value = true
  try {
    await moveCat(moveCatalogId.value, parentId)
    showMoveDialog.value = false
    ElMessage.success(t('common.saved'))
  } finally {
    moveLoading.value = false
  }
}

async function onCatalogDrop(dropPayload) {
  try {
    await moveCat(dropPayload.catalogId, dropPayload.targetParentId)
    ElMessage.success(t('common.saved'))
  } catch (e) {
    ElMessage.error(e && e.response && e.response.data && e.response.data.message ? e.response.data.message : (e.message || ''))
  }
}

function onSectionCommand(cmd) {
  if (cmd === 'catalog') createCat(null)
}

function onCatalogCommand(cmd, catalog) {
  if (cmd === 'child') createCat(catalog.id)
  else if (cmd === 'rename') renameCat(catalog)
  else if (cmd === 'move') openMoveDialog(catalog)
  else if (cmd === 'up') moveCatSibling(catalog, 'up')
  else if (cmd === 'down') moveCatSibling(catalog, 'down')
  else if (cmd === 'root') moveCat(catalog.id, 0)
  else if (cmd === 'delete') deleteCat(catalog)
}

function goAgentCenter() {
  router.push({
    path: '/agent',
    query: {
      tab: 'api',
      new: '1',
      interface_id: selectedInterfaceId.value || undefined,
    },
  })
}

// ==================== Watchers & Mount ====================
watch(projectId, function () {
  loadTree()
  loadInterfaceList()
})

watch(selectedCatalogId, function () {
  loadInterfaceList()
})

watch(selectedInterfaceId, function () {
  if (selectedInterfaceId.value) {
    loadTemplate()
    loadCases()
    loadDeps()
    loadDocPreview()
  }
})

onMounted(async function () {
  await loadTree()
  await loadInterfaceList()
  if (selectedInterfaceId.value) {
    await loadTemplate()
    await loadCases()
    await loadDeps()
    await loadDocPreview()
  }
})
</script>

<style scoped lang="scss">
.interface-detail-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.detail-panel {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.detail-nav-tabs {
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  padding: 12px 0;
  border-top: 1px solid var(--el-border-color-lighter);
  background: var(--bg-color);
}

.detail-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px;
}

/* 文档预览 Tab */
.doc-section {
  margin-bottom: 20px;

  h4 {
    font-size: 14px;
    font-weight: 600;
    margin: 0 0 8px;
    color: var(--el-text-color-primary);
  }
}

.request-info-bar {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 14px;
  background: #f0f9eb;
  border-radius: 4px;
  font-family: monospace;

  .method-tag {
    font-weight: 700;
    font-size: 13px;
    padding: 2px 8px;
    border-radius: 3px;
    color: #fff;

    &.method-get { background: #67c23a; }
    &.method-post { background: #409eff; }
    &.method-put, &.method-patch { background: #e6a23c; }
    &.method-delete { background: #f56c6c; }
    &.method-head, &.method-options { background: #909399; }
  }

  .path-text {
    font-size: 13px;
    color: #303133;
  }
}

/* 测试用例 Tab */
.case-toolbar-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 8px;
  flex-wrap: wrap;

  .case-toolbar-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .case-toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.case-collapse {
  border: 1px solid var(--el-border-color);
  overflow: hidden;

  :deep(.el-collapse-item__header) {
    background: #fafafa;
    font-weight: 600;
    font-size: 14px;
    padding: 0 14px;
  }

  :deep(.el-collapse-item__content) {
    padding: 10px 12px;
  }

  :deep(.el-table) {
    --el-table-border-color: var(--el-border-color-lighter);
  }
}

.collapse-title {
  margin-right: 8px;
}

.collapse-badge {
  :deep(.el-badge__content) {
    font-size: 11px;
  }
}

/* 接口调试 Tab */
.debug-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;

  .detail-title {
    margin-bottom: 0;
    flex: 1;
  }
}

.btn-debug-run {
  background-color: #409eff !important;
  border-color: #409eff !important;
  color: #fff !important;
}

.debug-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.debug-sub-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 0;
    background: var(--fill-color-blank);
  }
}

.sub-tab-content {
  padding: 12px 0;
  min-height: 120px;

  h4 {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    margin: 0 0 8px;
  }

  .empty-hint {
    color: var(--el-text-color-placeholder);
    font-size: 13px;
  }
}

.body-editor,
.assert-editor,
.prepost-editor {
  padding: 4px 0;
}

.prepost-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.methods-helper {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 8px;
  font-size: 12px;
  line-height: 1.9;

  p { margin: 2px 0; color: var(--el-text-color-regular); }
  code {
    font-family: 'Fira Code', Consolas, monospace;
    background: #e8e8e8;
    padding: 1px 6px;
    border-radius: 3px;
    color: #c7254e;
    font-size: 11.5px;
  }
}

.add-param-link {
  color: var(--el-color-primary);
  cursor: pointer;
  font-size: 13px;
}

.response-area {
  margin-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 12px;
}

.response-area-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;

  .response-sub-tabs {
    :deep(.el-tabs__header) {
      margin-bottom: 0;
    }
    :deep(.el-tabs__nav-wrap::after) {
      display: none;
    }
  }
}

.response-body {
  min-height: 100px;
  max-height: 300px;
  overflow: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  padding: 10px;
  background: #fafafa;
}

.run-result-block {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f0f9eb;
  border-radius: 4px;
  margin-bottom: 8px;
  font-size: 13px;

  .result-label {
    font-weight: 600;
    color: #67c23a;
  }

  .result-meta {
    color: var(--el-text-color-secondary);
    margin-left: auto;
  }
}

.response-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
}
</style>
