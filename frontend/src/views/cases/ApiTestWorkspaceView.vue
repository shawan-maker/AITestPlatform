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
                <el-dropdown trigger="click" popper-class="var-file-dropdown">
                  <el-button>
                    <el-icon><Document /></el-icon> {{ t('page.apiCases.selectVarFile') }}<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item
                        v-for="env in environmentList"
                        :key="env.id"
                        :class="{ 'is-active': caseEnvId === env.id }"
                        @click="selectCaseEnvironment(env.id)"
                      >{{ env.env_name }}</el-dropdown-item>
                      <el-dropdown-item v-if="!environmentList.length" disabled>暂无变量文件</el-dropdown-item>
                      <el-dropdown-item divided @click="refreshEnvironmentList">刷新</el-dropdown-item>
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
          <div v-show="activeTab === 'interface-debug'" class="detail-panel detail-panel--flex">
            <div class="debug-header-row">
              <h3 class="detail-title">{{ currentIfaceSummary || '-' }}</h3>
              <el-dropdown trigger="click" popper-class="var-file-dropdown">
                <el-button size="default">
                  <el-icon><Document /></el-icon> {{ currentEnvName || t('page.apiCases.selectVarFile') }}<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-for="env in environmentList"
                      :key="env.id"
                      :class="{ 'is-active': debugEnvId === env.id }"
                      @click="selectDebugEnvironment(env.id)"
                    >{{ env.env_name }}</el-dropdown-item>
                    <el-dropdown-item v-if="!environmentList.length" disabled>暂无变量文件</el-dropdown-item>
                    <el-dropdown-item divided @click="refreshEnvironmentList">刷新</el-dropdown-item>
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
              <!-- Body -->
              <el-tab-pane :label="t('page.apiCases.subTabBody')" name="body">
                <div class="sub-tab-content body-editor">
                  <div class="body-type-selector">
                    <el-radio-group v-model="bodyType" size="small">
                      <el-radio value="json">JSON</el-radio>
                      <el-radio value="urlencoded">x-www-form-urlencoded</el-radio>
                      <el-radio value="form-data">multipart/form-data</el-radio>
                    </el-radio-group>
                  </div>
                  <div v-if="bodyType === 'json'" class="body-json-section">
                    <MonacoJsonEditor v-model="requestJson" :height="260" language="json" />
                  </div>
                  <div v-else-if="bodyType === 'urlencoded'" class="body-urlencoded-section">
                    <el-table :data="urlencodedRows" border size="small" empty_text="">
                      <el-table-column prop="name" label="参数名" min-width="140">
                        <template #default="{ row, $index }">
                          <el-input v-if="$index < urlencodedRows.length - 1" v-model="row.name" size="small" placeholder="" />
                          <span v-else class="add-param-link" @click="addUrlencodedRow">添加参数</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="value" label="参数值" min-width="180">
                        <template #default="{ row, $index }">
                          <el-input v-if="$index < urlencodedRows.length - 1" v-model="row.value" size="small" placeholder="" />
                          <span v-else></span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="desc" label="说明" min-width="120">
                        <template #default="{ row, $index }">
                          <el-input v-if="$index < urlencodedRows.length - 1" v-model="row.desc" size="small" placeholder="" />
                          <span v-else></span>
                        </template>
                      </el-table-column>
                      <el-table-column label="操作" width="60" align="center">
                        <template #default="{ $index }">
                          <el-button v-if="$index < urlencodedRows.length - 1" link type="danger" size="small" :icon="Close" @click="removeUrlencodedRow($index)" />
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                  <div v-else class="body-formdata-section">
                    <el-table :data="formDataRows" border size="small" empty_text="">
                      <el-table-column prop="name" label="参数名" min-width="130">
                        <template #default="{ row, $index }">
                          <el-input v-if="$index < formDataRows.length - 1" v-model="row.name" size="small" placeholder="" />
                          <span v-else class="add-param-link" @click="addFormDataRow">添加参数</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="type" label="类型" width="110">
                        <template #default="{ row, $index }">
                          <el-select v-if="$index < formDataRows.length - 1" v-model="row.type" size="small" style="width: 100%">
                            <el-option label="string" value="string" />
                            <el-option label="file" value="file" />
                          </el-select>
                          <span v-else></span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="value" label="参数值" min-width="180">
                        <template #default="{ row, $index }">
                          <template v-if="$index < formDataRows.length - 1">
                            <el-select v-if="row.type === 'file'" v-model="row.fileId" filterable clearable size="small" style="width: 100%" placeholder="选择已上传的文件">
                              <el-option v-for="item in uploadFileOptions" :key="item.id" :label="displayFileLabel(item)" :value="item.id" />
                            </el-select>
                            <el-input v-else v-model="row.value" size="small" placeholder="" />
                          </template>
                          <span v-else></span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="desc" label="说明" min-width="100">
                        <template #default="{ row, $index }">
                          <el-input v-if="$index < formDataRows.length - 1" v-model="row.desc" size="small" placeholder="" />
                          <span v-else></span>
                        </template>
                      </el-table-column>
                      <el-table-column label="操作" width="60" align="center">
                        <template #default="{ $index }">
                          <el-button v-if="$index < formDataRows.length - 1" link type="danger" size="small" :icon="Close" @click="removeFormDataRow($index)" />
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
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
                          <el-option v-for="m in assertMethods" :key="m.value" :label="m.label" :value="m.value" />
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
                  <div class="prepost-container">
                    <div class="prepost-code">
                      <MonacoJsonEditor v-model="preOpsCode" :height="260" language="python" />
                    </div>
                    <div class="prepost-template">
                      <div class="template-header">前置操作模板</div>
                      <div class="template-list">
                        <div class="template-item" @click="insertPreTemplate('env')">
                          <span class="template-name">设置临时变量</span>
                        </div>
                        <div class="template-item" @click="insertPreTemplate('global')">
                          <span class="template-name">设置环境变量</span>
                        </div>
                        <div class="template-item" @click="insertPreTemplate('sql')">
                          <span class="template-name">执行SQL</span>
                        </div>
                        <div class="template-item" @click="insertPreTemplate('get_env')">
                          <span class="template-name">获取临时变量</span>
                        </div>
                        <div class="template-item" @click="insertPreTemplate('get_global')">
                          <span class="template-name">获取环境变量</span>
                        </div>
                        <div class="template-item" @click="insertPreTemplate('request')">
                          <span class="template-name">发送请求</span>
                        </div>
                        <div class="template-item" @click="insertPreTemplate('sleep')">
                          <span class="template-name">等待</span>
                        </div>
                        <div class="template-item" @click="insertPreTemplate('call_func')">
                          <span class="template-name">执行自定义函数</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </el-tab-pane>
              <!-- PostOps (Python) -->
              <el-tab-pane :label="t('page.apiCases.subTabPostOps')" name="postops">
                <div class="sub-tab-content prepost-editor">
                  <div class="prepost-container">
                    <div class="prepost-code">
                      <MonacoJsonEditor v-model="postOpsCode" :height="260" language="python" />
                    </div>
                    <div class="prepost-template">
                      <div class="template-header">后置操作模板</div>
                      <div class="template-list">
                        <div class="template-item" @click="insertPostTemplate('body')">
                          <span class="template-name">获取响应体</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('json')">
                          <span class="template-name">获取JSON响应</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('json_res')">
                          <span class="template-name">JSONPath提取单个</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('json_all')">
                          <span class="template-name">JSONPath提取列表</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('re_res')">
                          <span class="template-name">正则提取单个</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('re_all')">
                          <span class="template-name">正则提取列表</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('assert')">
                          <span class="template-name">断言结果</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('env')">
                          <span class="template-name">设置临时变量</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('global')">
                          <span class="template-name">设置环境变量</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('delete_global')">
                          <span class="template-name">删除全局变量</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('sql')">
                          <span class="template-name">执行SQL</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('save_file')">
                          <span class="template-name">保存到文件</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('log')">
                          <span class="template-name">记录日志</span>
                        </div>
                        <div class="template-item" @click="insertPostTemplate('call_func')">
                          <span class="template-name">执行自定义函数</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </el-tab-pane>
            </el-tabs>

            <div class="response-area">
              <div class="response-area-toolbar">
                <el-tabs v-model="responseSubTab" class="response-sub-tabs">
                  <el-tab-pane name="result">
                    <template #label>
                      <span>{{ t('page.apiCases.resultInfo') }}</span>
                      <el-tag
                        v-if="responseDataInfo && responseDataInfo.status_code"
                        :type="getStatusCodeType(responseDataInfo.status_code)"
                        size="small"
                        style="margin-left: 4px; font-size: 11px;"
                      >{{ responseDataInfo.status_code }}</el-tag>
                    </template>
                  </el-tab-pane>
                  <el-tab-pane :label="t('page.apiCases.responseInfo')" name="response-info" />
                  <el-tab-pane :label="t('page.apiCases.requestInfo')" name="request-info" />
                  <el-tab-pane :label="t('page.apiCases.requestHeadersInfo')" name="request-headers-info" />
                  <el-tab-pane v-if="hasConfiguredExtracts" :label="t('page.apiCases.extractInfo')" name="extract-info" />
                  <el-tab-pane v-if="hasConfiguredAsserts" :label="t('page.apiCases.assertInfo')" name="assert-info" />
                  <el-tab-pane label="日志信息" name="log-info" />
                </el-tabs>
                <el-button link type="primary" :icon="Clock" @click="showTestRecords = true">{{ t('page.apiCases.testRecord') }}</el-button>
              </div>
              <div class="response-body">
                <!-- 响应数据 -->
                <template v-if="responseSubTab === 'result' && responseResult">
                  <div class="run-result-block" :class="responseResult.status || ''">
                    <el-icon :color="getStatusColor(responseResult.status)"><CircleCheckFilled /></el-icon>
                    <span class="result-label">{{ getStatusLabel(responseResult.status) }}</span>
                    <el-tag
                      v-if="responseDataInfo && responseDataInfo.status_code"
                      :type="getStatusCodeType(responseDataInfo.status_code)"
                      size="small"
                      style="margin-left: 8px;"
                    >{{ responseDataInfo.status_code }}</el-tag>
                    <span class="result-meta">耗时: {{ (responseResult.duration_ms || 0) }}ms &nbsp;&nbsp; 操作人: {{ responseResult.executor || '-' }}</span>
                  </div>
                  <div v-if="responseResult.error_message" class="error-message">
                    <strong>错误信息:</strong> {{ responseResult.error_message }}
                  </div>
                  <pre v-if="responseDataInfo && responseDataInfo.body" class="response-pre">{{ formatResponseBody(responseDataInfo.body) }}</pre>
                  <el-empty v-else-if="!responseResult.error_message" description="暂无响应体" :image-size="48" />
                </template>
                <!-- 响应头信息 -->
                <template v-else-if="responseSubTab === 'response-info' && responseDataInfo">
                  <div class="structured-response">
                    <table v-if="responseDataInfo.headers && Object.keys(responseDataInfo.headers).length" class="info-table">
                      <thead><tr><th>Header</th><th>Value</th></tr></thead>
                      <tbody>
                        <tr v-for="(value, key) in responseDataInfo.headers" :key="key">
                          <td style="font-weight: 500;">{{ key }}</td>
                          <td>{{ value }}</td>
                        </tr>
                      </tbody>
                    </table>
                    <el-empty v-else description="暂无响应头信息" :image-size="48" />
                  </div>
                </template>
                <!-- 请求数据 -->
                <template v-else-if="responseSubTab === 'request-info' && requestInfo">
                  <div class="structured-response">
                    <div class="info-row"><strong>请求方法:</strong> <el-tag size="small" :class="'method-tag-' + (requestInfo.method || 'GET').toLowerCase()">{{ (requestInfo.method || '-').toUpperCase() }}</el-tag></div>
                    <div class="info-row"><strong>请求URL:</strong> <code>{{ requestInfo.url || '-' }}</code></div>
                    <div class="info-row" v-if="requestInfo.params && Object.keys(requestInfo.params).length"><strong>Query参数:</strong></div>
                    <table v-if="requestInfo.params && Object.keys(requestInfo.params).length" class="info-table">
                      <tr v-for="(value, key) in requestInfo.params" :key="key">
                        <td>{{ key }}</td>
                        <td>{{ value }}</td>
                      </tr>
                    </table>
                    <div class="info-row" v-if="requestInfo.body !== undefined && requestInfo.body !== null"><strong>请求体:</strong></div>
                    <pre class="response-pre" v-if="requestInfo.body !== undefined && requestInfo.body !== null">{{ typeof requestInfo.body === 'string' ? requestInfo.body : JSON.stringify(requestInfo.body, null, 2) }}</pre>
                  </div>
                </template>
                <!-- 请求头信息 -->
                <template v-else-if="responseSubTab === 'request-headers-info' && requestInfo">
                  <div class="structured-response">
                    <table v-if="requestInfo.headers && Object.keys(requestInfo.headers).length" class="info-table">
                      <thead><tr><th>Header</th><th>Value</th></tr></thead>
                      <tbody>
                        <tr v-for="(value, key) in requestInfo.headers" :key="key">
                          <td style="font-weight: 500;">{{ key }}</td>
                          <td>{{ value }}</td>
                        </tr>
                      </tbody>
                    </table>
                    <el-empty v-else description="暂无请求头信息" :image-size="48" />
                  </div>
                </template>
                <!-- 提取信息 -->
                <template v-else-if="responseSubTab === 'extract-info' && extractInfo">
                  <table class="info-table extract-table" v-if="extractInfo.length">
                    <thead><tr><th>变量名</th><th>表达式</th><th>值</th></tr></thead>
                    <tbody>
                      <tr v-for="(item, idx) in extractInfo" :key="idx">
                        <td>{{ item.var_name || item.name }}</td>
                        <td>{{ item.extract_expr || item.expression }}</td>
                        <td>{{ item.value !== undefined ? item.value : '-' }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <el-empty v-else description="暂无提取数据" :image-size="48" />
                </template>
                <!-- 断言信息 -->
                <template v-else-if="responseSubTab === 'assert-info' && assertInfo">
                  <table class="info-table assert-table" v-if="assertInfo.length">
                    <thead><tr><th style="width:40px">结果</th><th>断言目标</th><th>比较方式</th><th>预期值</th><th>实际值</th></tr></thead>
                    <tbody>
                      <tr v-for="(item, idx) in assertInfo" :key="idx" :class="item.passed ? 'assert-passed' : 'assert-failed'">
                        <td><el-icon v-if="item.passed" color="#67C23A"><CircleCheckFilled /></el-icon><el-icon v-else color="#F56C6C"><CircleCloseFilled /></el-icon></td>
                        <td>{{ item.field || item.target }}</td>
                        <td>{{ getAssertMethodLabel(item.type || item.method) }}</td>
                        <td>{{ item.expected }}</td>
                        <td>{{ item.actual !== undefined && item.actual !== null ? item.actual : '-' }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <el-empty v-else description="暂无断言数据" :image-size="48" />
                </template>
                <!-- 日志信息 -->
                <template v-else-if="responseSubTab === 'log-info' && logData">
                  <div class="log-container">
                    <div
                      v-for="(logItem, idx) in logData"
                      :key="idx"
                      class="log-item"
                      :class="'log-' + (Array.isArray(logItem) ? logItem[0]?.toLowerCase() : logItem.level?.toLowerCase() || 'info')"
                    >
                      <span class="log-level-badge" :class="'badge-' + (Array.isArray(logItem) ? logItem[0]?.toLowerCase() : logItem.level?.toLowerCase() || 'info')">
                        {{ Array.isArray(logItem) ? logItem[0] : (logItem.level || 'INFO') }}
                      </span>
                      <span class="log-message">{{ Array.isArray(logItem) ? logItem.slice(1).join(' ') : (logItem.message || '') }}</span>
                    </div>
                  </div>
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
    <el-drawer v-model="showTestRecords" title="调试记录" direction="rtl" size="50%" :destroy-on-close="false">
      <!-- 列表视图 -->
      <div v-if="!drawerRecordDetail">
        <el-table :data="debugRecords" v-loading="debugRecordsLoading" size="small" stripe style="width: 100%">
          <el-table-column prop="triggered_by_username" label="执行人" width="100" />
          <el-table-column prop="created_at" label="执行时间" min-width="170">
            <template #default="{ row }">{{ formatRecordTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="status" label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="getStatusCodeType(row.status === 'success' ? 200 : row.status === 'fail' ? 400 : 500)" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="duration_ms" label="耗时" width="80">
            <template #default="{ row }">{{ row.duration_ms || 0 }}ms</template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewDebugRecord(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <!-- 详情视图 -->
      <div v-else class="drawer-detail-view">
        <div class="drawer-detail-header">
          <el-button link type="primary" @click="drawerRecordDetail = null">← 返回列表</el-button>
          <span class="drawer-detail-meta">
            <el-tag :type="getStatusCodeType(drawerRecordDetail.status === 'success' ? 200 : drawerRecordDetail.status === 'fail' ? 400 : 500)" size="small">{{ drawerRecordDetail.status }}</el-tag>
            {{ formatRecordTime(drawerRecordDetail.created_at) }} &nbsp; 耗时: {{ drawerRecordDetail.duration_ms || 0 }}ms
            &nbsp; 操作人: {{ drawerRecordDetail.triggered_by_username || '-' }}
          </span>
        </div>
        <div class="response-area" style="flex:1; min-height:0;">
          <div class="response-area-toolbar">
            <el-tabs v-model="drawerResponseSubTab" class="response-sub-tabs">
              <el-tab-pane name="result">
                <template #label>
                  <span>响应数据</span>
                  <el-tag v-if="drawerResponseDataInfo && drawerResponseDataInfo.status_code" :type="getStatusCodeType(drawerResponseDataInfo.status_code)" size="small" style="margin-left:4px;font-size:11px">{{ drawerResponseDataInfo.status_code }}</el-tag>
                </template>
              </el-tab-pane>
              <el-tab-pane label="响应头信息" name="response-headers" />
              <el-tab-pane label="请求数据" name="request-data" />
              <el-tab-pane label="请求头信息" name="request-headers" />
              <el-tab-pane v-if="drawerExtractInfo && drawerExtractInfo.length" label="提取信息" name="extract-info" />
              <el-tab-pane v-if="drawerAssertInfo && drawerAssertInfo.length" label="断言信息" name="assert-info" />
              <el-tab-pane label="日志信息" name="log" />
            </el-tabs>
          </div>
          <div class="response-body">
            <!-- 响应数据 -->
            <template v-if="drawerResponseSubTab === 'result'">
              <div class="run-result-block" :class="drawerRecordDetail.status || ''">
                <el-icon :color="getStatusColor(drawerRecordDetail.status)"><CircleCheckFilled /></el-icon>
                <span class="result-label">{{ getStatusLabel(drawerRecordDetail.status) }}</span>
                <el-tag v-if="drawerResponseDataInfo && drawerResponseDataInfo.status_code" :type="getStatusCodeType(drawerResponseDataInfo.status_code)" size="small" style="margin-left:8px">{{ drawerResponseDataInfo.status_code }}</el-tag>
                <span class="result-meta">耗时: {{ drawerRecordDetail.duration_ms || 0 }}ms</span>
              </div>
              <div v-if="drawerRecordDetail.error_message" class="error-message"><strong>错误信息:</strong> {{ drawerRecordDetail.error_message }}</div>
              <pre v-if="drawerResponseDataInfo && drawerResponseDataInfo.body" class="response-pre">{{ formatResponseBody(drawerResponseDataInfo.body) }}</pre>
              <el-empty v-else-if="!drawerRecordDetail.error_message" description="暂无响应体" :image-size="48" />
            </template>
            <!-- 响应头信息 -->
            <template v-else-if="drawerResponseSubTab === 'response-headers'">
              <table v-if="drawerResponseDataInfo && drawerResponseDataInfo.headers && Object.keys(drawerResponseDataInfo.headers).length" class="info-table">
                <thead><tr><th>Header</th><th>Value</th></tr></thead>
                <tbody><tr v-for="(value, key) in drawerResponseDataInfo.headers" :key="key"><td style="font-weight:500">{{ key }}</td><td>{{ value }}</td></tr></tbody>
              </table>
              <el-empty v-else description="暂无响应头信息" :image-size="48" />
            </template>
            <!-- 请求数据 -->
            <template v-else-if="drawerResponseSubTab === 'request-data'">
              <div v-if="drawerRequestInfo" class="structured-response">
                <div class="info-row"><strong>请求方法:</strong> <el-tag size="small">{{ (drawerRequestInfo.method || '-').toUpperCase() }}</el-tag></div>
                <div class="info-row"><strong>请求URL:</strong> <code>{{ drawerRequestInfo.url || '-' }}</code></div>
                <div class="info-row" v-if="drawerRequestInfo.params && Object.keys(drawerRequestInfo.params).length"><strong>Query参数:</strong></div>
                <table v-if="drawerRequestInfo.params && Object.keys(drawerRequestInfo.params).length" class="info-table">
                  <tr v-for="(value, key) in drawerRequestInfo.params" :key="key"><td>{{ key }}</td><td>{{ value }}</td></tr>
                </table>
                <div class="info-row" v-if="drawerRequestInfo.body"><strong>请求体:</strong></div>
                <pre class="response-pre" v-if="drawerRequestInfo.body">{{ typeof drawerRequestInfo.body === 'string' ? drawerRequestInfo.body : JSON.stringify(drawerRequestInfo.body, null, 2) }}</pre>
              </div>
              <el-empty v-else description="暂无请求数据" :image-size="48" />
            </template>
            <!-- 请求头信息 -->
            <template v-else-if="drawerResponseSubTab === 'request-headers'">
              <table v-if="drawerRequestInfo && drawerRequestInfo.headers && Object.keys(drawerRequestInfo.headers).length" class="info-table">
                <thead><tr><th>Header</th><th>Value</th></tr></thead>
                <tbody><tr v-for="(value, key) in drawerRequestInfo.headers" :key="key"><td style="font-weight:500">{{ key }}</td><td>{{ value }}</td></tr></tbody>
              </table>
              <el-empty v-else description="暂无请求头信息" :image-size="48" />
            </template>
            <!-- 提取信息 -->
            <template v-else-if="drawerResponseSubTab === 'extract-info'">
              <table class="info-table extract-table" v-if="drawerExtractInfo && drawerExtractInfo.length">
                <thead><tr><th>变量名</th><th>表达式</th><th>值</th></tr></thead>
                <tbody><tr v-for="(item, idx) in drawerExtractInfo" :key="idx"><td>{{ item.var_name || item.name }}</td><td>{{ item.extract_expr || item.expression }}</td><td>{{ item.value !== undefined ? item.value : '-' }}</td></tr></tbody>
              </table>
              <el-empty v-else description="暂无提取数据" :image-size="48" />
            </template>
            <!-- 断言信息 -->
            <template v-else-if="drawerResponseSubTab === 'assert-info'">
              <table class="info-table assert-table" v-if="drawerAssertInfo && drawerAssertInfo.length">
                <thead><tr><th style="width:40px">结果</th><th>断言目标</th><th>比较方式</th><th>预期值</th><th>实际值</th></tr></thead>
                <tbody>
                  <tr v-for="(item, idx) in drawerAssertInfo" :key="idx" :class="item.passed ? 'assert-passed' : 'assert-failed'">
                    <td><el-icon v-if="item.passed" color="#67C23A"><CircleCheckFilled /></el-icon><el-icon v-else color="#F56C6C"><CircleCloseFilled /></el-icon></td>
                    <td>{{ item.field || item.target }}</td>
                    <td>{{ getAssertMethodLabel(item.type || item.method) }}</td>
                    <td>{{ item.expected }}</td>
                    <td>{{ item.actual !== undefined && item.actual !== null ? item.actual : '-' }}</td>
                  </tr>
                </tbody>
              </table>
              <el-empty v-else description="暂无断言数据" :image-size="48" />
            </template>
            <!-- 日志信息 -->
            <template v-else-if="drawerResponseSubTab === 'log'">
              <div v-if="drawerLogData && drawerLogData.length" class="log-container">
                <div v-for="(logItem, idx) in drawerLogData" :key="idx" class="log-item" :class="'log-' + (Array.isArray(logItem) ? logItem[0]?.toLowerCase() : 'info')">
                  <span class="log-level-badge" :class="'badge-' + (Array.isArray(logItem) ? logItem[0]?.toLowerCase() : 'info')">{{ Array.isArray(logItem) ? logItem[0] : 'INFO' }}</span>
                  <span class="log-message">{{ Array.isArray(logItem) ? logItem.slice(1).join(' ') : '' }}</span>
                </div>
              </div>
              <el-empty v-else description="暂无日志" :image-size="48" />
            </template>
          </div>
        </div>
      </div>
    </el-drawer>
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
  CircleCheckFilled,
  CircleCloseFilled,
} from '@element-plus/icons-vue'
import {
  copyInterface,
  createApiCatalog,
  debugRunInterface,
  deleteApiCatalog,
  deleteInterface,
  fillDebugFromDoc,
  listDebugRecords,
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
import { listEnvironments as fetchEnvList, listUploadedFiles } from '@/api/environment'

const { t, locale } = useI18n()
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

// 变量文件选择相关
const environmentList = ref([])
const debugEnvId = ref(null)
const caseEnvId = ref(null)

// 文件上传相关
const bodyType = ref('json')
const uploadFileOptions = ref([])
const uploadFieldName = ref('file')
const selectedUploadId = ref(null)
const urlencodedRows = ref([{ name: '', value: '', desc: '' }])
const formDataRows = ref([{ name: '', type: 'string', value: '', fileId: null, desc: '' }])

// 调试相关
const requestJson = ref('{}')
const assertionsJson = ref('[]')  // 断言数据JSON格式（兼容旧逻辑）
const debugging = ref(false)
const debugAbortController = ref(null)

// 结果解析相关（结构化展示）
const responseResult = ref(null)
const responseDataInfo = ref(null)
const requestInfo = ref(null)
const requestHeadersInfo = ref(null)
const extractInfo = ref(null)
const assertInfo = ref(null)
const logData = ref([])
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
const debugRecords = ref([])
const debugRecordsLoading = ref(false)
const drawerRecordDetail = ref(null)
const drawerResponseSubTab = ref('result')
const drawerResponseDataInfo = ref(null)
const drawerRequestInfo = ref(null)
const drawerLogData = ref([])
const drawerExtractInfo = ref([])
const drawerAssertInfo = ref([])
const httpMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

async function loadDebugRecords() {
  if (!selectedInterfaceId.value) return
  debugRecordsLoading.value = true
  try {
    var res = await listDebugRecords(selectedInterfaceId.value, { page: 1, page_size: 50 })
    debugRecords.value = res.data.data?.items || []
  } catch (e) {
    console.error('加载调试记录失败:', e)
    debugRecords.value = []
  } finally {
    debugRecordsLoading.value = false
  }
}

function viewDebugRecord(row) {
  drawerRecordDetail.value = row
  drawerResponseSubTab.value = 'result'
  if (row.api_requests_info) {
    var data = row.api_requests_info
    var debugDetail = data._debug_detail || data
    // Populate drawer response info
    var ri = debugDetail.response_info || data.response_info || {}
    drawerResponseDataInfo.value = {
      status_code: ri.status_code || data.response_code,
      content_type: ri.content_type,
      body: ri.body || data.response_body,
      elapsed_ms: ri.elapsed_ms || data.run_time,
      headers: ri.headers || data.response_headers || {},
    }
    drawerRequestInfo.value = debugDetail.request_info || data.request_info || {
      method: data.method,
      url: data.url,
      headers: data.request_headers || {},
      params: data.params || {},
      body: data.request_body,
    }
    drawerLogData.value = debugDetail.log_data || data.log_data || []
    drawerExtractInfo.value = debugDetail.extract_info || data.extract_info || []
    drawerAssertInfo.value = debugDetail.assert_info || data.assert_info || []
  } else {
    drawerResponseDataInfo.value = null
    drawerRequestInfo.value = null
    drawerLogData.value = []
    drawerExtractInfo.value = []
    drawerAssertInfo.value = []
    drawerLogData.value = []
  }
}

function formatRecordTime(val) {
  if (!val) return '-'
  var d = new Date(val)
  if (isNaN(d.getTime())) return val
  var pad = function (n) { return n < 10 ? '0' + n : '' + n }
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds())
}

watch(showTestRecords, function (val) {
  if (val) loadDebugRecords()
})

// Body 类型切换时自动更新 Content-Type 请求头
var contentTypeMap = {
  'json': 'application/json',
  'urlencoded': 'application/x-www-form-urlencoded',
  'form-data': 'multipart/form-data',
}
watch(bodyType, function (newType) {
  var newCt = contentTypeMap[newType] || 'application/json'
  // 查找 Content-Type 行并更新
  for (var i = 0; i < headerRows.value.length; i++) {
    if (headerRows.value[i].name && headerRows.value[i].name.toLowerCase() === 'content-type') {
      headerRows.value[i].value = newCt
      return
    }
  }
  // 没有 Content-Type 行，在末尾空行前插入
  var lastIdx = headerRows.value.length - 1
  headerRows.value.splice(lastIdx, 0, { name: 'Content-Type', value: newCt, desc: '' })
})

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

const currentEnvName = computed(function () {
  if (!debugEnvId.value) return ''
  var env = environmentList.value.find(function (e) { return e.id === debugEnvId.value })
  return env ? env.env_name : ''
})

const hasConfiguredExtracts = computed(function () {
  return extractRows.value.some(function (r, i) {
    return i < extractRows.value.length - 1 && r.name && r.name.trim()
  })
})

const hasConfiguredAsserts = computed(function () {
  return assertRows.value.some(function (r, i) {
    return i < assertRows.value.length - 1 && r.target && r.target.trim()
  })
})

const assertMethods = computed(function () {
  var isZh = locale.value === 'zh-cn' || locale.value === 'zh-CN'
  return [
    { value: 'eq', label: isZh ? '相等' : 'Equals' },
    { value: 'eq_ignore_case', label: isZh ? '相等(忽略大小写)' : 'Equals (ignore case)' },
    { value: 'ne', label: isZh ? '不相等' : 'Not Equals' },
    { value: 'contains', label: isZh ? '包含' : 'Contains' },
    { value: 'not_contains', label: isZh ? '不包含' : 'Not Contains' },
    { value: 'gt', label: isZh ? '大于' : 'Greater Than' },
    { value: 'lt', label: isZh ? '小于' : 'Less Than' },
    { value: 'ge', label: isZh ? '大于等于' : 'Greater or Equal' },
    { value: 'le', label: isZh ? '小于等于' : 'Less or Equal' },
    { value: 'regex', label: isZh ? '正则匹配' : 'Regex Match' },
  ]
})

/** 将断言比较方式值映射为显示标签 */
function getAssertMethodLabel(methodValue) {
  if (!methodValue) return '-'
  var found = assertMethods.value.find(function (m) { return m.value === methodValue })
  if (found) return found.label
  // 兼容引擎返回的中英文标签（如 "相等"、"包含"）
  return methodValue
}

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

// ==================== 变量文件相关方法 ====================
async function refreshEnvironmentList() {
  if (!projectId.value) return
  try {
    var params = { project_id: projectId.value, page: 1, page_size: 100 }
    var res = await fetchEnvList(params)
    environmentList.value = res.data.data?.items ?? []
  } catch (e) {
    console.error('加载变量文件失败:', e)
  }
}

function selectDebugEnvironment(envId) {
  debugEnvId.value = envId
  environmentId.value = envId
  ElMessage.success('已选择变量文件: ' + (environmentList.value.find(e => e.id === envId)?.env_name || envId))
}

function selectCaseEnvironment(envId) {
  caseEnvId.value = envId
  ElMessage.success('已选择变量文件: ' + (environmentList.value.find(e => e.id === envId)?.env_name || envId))
}

// ==================== 文件上传相关方法 ====================
async function loadUploadFiles() {
  if (!projectId.value) return
  try {
    var res = await listUploadedFiles({ project_id: projectId.value })
    uploadFileOptions.value = res.data?.data?.items || []
  } catch (e) {
    console.error('加载上传文件列表失败:', e)
  }
}

function displayFileLabel(item) {
  if (!item) return ''
  if (item.info && Array.isArray(item.info) && item.info[0]) return item.info[0]
  const path = item.file
  if (!path) return ''
  try {
    const urlPath = path.indexOf('://') >= 0 ? new URL(path).pathname : path
    const parts = urlPath.replace(/\\/g, '/').split('/').filter(Boolean)
    const last = parts[parts.length - 1] || ''
    return decodeURIComponent(last)
  } catch {
    const parts = String(path).split(/[\\/]/)
    return decodeURIComponent(parts[parts.length - 1] || '') || parts[parts.length - 1] || ''
  }
}

// ==================== 前置/后置操作模板插入方法 ====================
function insertPreTemplate(templateType) {
  const templates = {
    'env': "\n# 设置临时变量 \ntest.save_env_variable('var_name',var_value)",
    'global': "\n# 设置环境变量 \ntest.save_global_variable('var_name',var_value)",
    'sql': "\n# 执行sql语句 \nvar_name = db.服务器名称.execute_all('sql语句')",
    'get_env': "\n# 获取临时变量 \nvar_name = test.get_env_variable('var_name', default_value)",
    'get_global': "\n# 获取环境变量 \nvar_name = test.get_global_variable('var_name', default_value)",
    'request': "\n# 发送HTTP请求 \ntest.request(method, url, **kwargs)",
    'sleep': "\n# 等待 \ntest.sleep(seconds)",
    'call_func': "\n# 执行自定义函数\nresult = global_func.方法名()\n# 如需保存结果到变量：\n# test.save_env_variable('var_name', result)",
  }
  preOpsCode.value += templates[templateType] || ''
}

function insertPostTemplate(templateType) {
  const templates = {
    'body': "\n# 获取响应体 \nvar_name = response.data",
    'json': "\n# 获取json响应 \nvar_name = response.json()",
    'json_res': "\n# jsonpath提取单个数据 \nvar_name = test.json_extract(json响应,jsonpath表达式)",
    'json_all': "\n# jsonpath提取一组数据 \nvar_name = test.json_extract_list(json响应,jsonpath表达式)",
    're_res': "\n# 正则表达式方式提取单个数据 \nvar_name = test.re_extract(响应体数据,正则表达式)",
    're_all': "\n# 正则表达式方式提取一组数据 \nvar_name = test.re_extract_list(响应体数据,正则表达式)",
    'assert': "\n# 对响应结果进行断言 \ntest.assertion('比较方式',预期结果,实际结果)",
    'env': "\n# 设置临时变量 \ntest.save_env_variable('var_name',var_value)",
    'global': "\n# 设置环境变量 \ntest.save_global_variable('var_name',var_value)",
    'delete_global': "\n# 删除全局变量 \ntest.del_global_variable('var_name')",
    'sql': "\n# 执行sql语句 \nvar_name = db.服务器名称.execute_all('sql语句')",
    'save_file': "\n# 保存到文件 \ntest.save_to_file(filename, content)",
    'log': "\n# 记录日志 \ntest.log(message)",
    'call_func': "\n# 执行自定义函数\nresult = global_func.方法名()\n# 如需保存结果到变量：\n# test.save_env_variable('var_name', result)",
  }
  postOpsCode.value += templates[templateType] || ''
}

// ==================== 结果展示辅助方法 ====================
function getStatusColor(status) {
  const s = (status || '').toLowerCase()
  if (s.indexOf('success') >= 0 || s.indexOf('pass') >= 0) return '#67C23A'
  if (s.indexOf('fail') >= 0 || s.indexOf('error') >= 0) return '#F56C6C'
  return '#E6A23C'
}

function getStatusLabel(status) {
  const s = (status || '').toLowerCase()
  if (s.indexOf('success') >= 0 || s.indexOf('pass') >= 0) return '执行成功'
  if (s.indexOf('fail') >= 0 || s.indexOf('error') >= 0) return '执行失败'
  return status || '未知状态'
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function getStatusCodeType(code) {
  if (!code) return 'info'
  var c = Number(code)
  if (c >= 200 && c < 300) return 'success'
  if (c >= 300 && c < 400) return ''
  if (c >= 400 && c < 500) return 'warning'
  if (c >= 500) return 'danger'
  return 'info'
}

function formatResponseBody(body) {
  if (!body) return ''
  if (typeof body === 'string') {
    try {
      return JSON.stringify(JSON.parse(body), null, 2)
    } catch (e) {
      return body
    }
  }
  return JSON.stringify(body, null, 2)
}

function parseDebugResponse(data) {
  // 解析后端返回的调试结果，进行结构化展示
  // 后端将 _debug_detail 字段合并到顶层：response_info, request_info, extract_info, assert_info, log_data
  responseResult.value = data || {}

  // 响应信息（包含响应头）
  if (data.response_info) {
    var ri = data.response_info
    responseDataInfo.value = {
      status_code: ri.status_code,
      content_type: ri.content_type,
      elapsed_ms: ri.elapsed_ms || data.duration_ms,
      body_size: ri.body_size,
      body: ri.body,
      headers: ri.headers || {},
    }
  } else {
    responseDataInfo.value = null
  }

  // 请求信息（包含请求头）
  if (data.request_info) {
    requestInfo.value = {
      method: data.request_info.method || debugMethod.value,
      url: data.request_info.url,
      headers: data.request_info.headers || {},
      params: data.request_info.params || data.request_info.query_params || {},
      body: data.request_info.body,
    }
  } else {
    requestInfo.value = null
  }

  // 提取信息
  extractInfo.value = data.extract_info || []

  // 断言信息
  assertInfo.value = data.assert_info || []

  // 日志信息
  logData.value = data.log_data || data.logs || []
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
function addUrlencodedRow() {
  urlencodedRows.value.push({ name: '', value: '', desc: '' })
}
function removeUrlencodedRow(idx) {
  urlencodedRows.value.splice(idx, 1)
}
function addFormDataRow() {
  formDataRows.value.push({ name: '', type: 'string', value: '', fileId: null, desc: '' })
}
function removeFormDataRow(idx) {
  formDataRows.value.splice(idx, 1)
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
function hasRealCode(code) {
  if (!code) return false
  // Remove comments and whitespace, check if anything remains
  return code.replace(/#[^\n]*/g, '').trim().length > 0
}

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
  // 根据bodyType决定如何处理body
  if (bodyType.value === 'json') {
    try { body = JSON.parse(requestJson.value) } catch (e) {}
  } else if (bodyType.value === 'urlencoded') {
    body = {}
    for (var ui = 0; ui < urlencodedRows.value.length; ui++) {
      var u = urlencodedRows.value[ui]
      if (u.name && u.name.trim()) body[u.name.trim()] = u.value || ''
    }
  } else if (bodyType.value === 'form-data') {
    body = {}
    for (var fi = 0; fi < formDataRows.value.length; fi++) {
      var f = formDataRows.value[fi]
      if (f.name && f.name.trim() && f.type !== 'file') body[f.name.trim()] = f.value || ''
    }
  }

  var payload = {
    method: debugMethod.value,
    path: debugPath.value,
    headers: headers,
    query: query,
    path_params: pathParams,
    body: body,
    body_type: bodyType.value,
    extracts: extracts,
    assertions: assertions,
    preconditions: hasRealCode(preOpsCode.value) ? [{ kind: 'python', code: preOpsCode.value }] : [],
    postconditions: hasRealCode(postOpsCode.value) ? [{ kind: 'python', code: postOpsCode.value }] : [],
  }

  // 保存 urlencoded/form-data 行数据用于恢复
  if (bodyType.value === 'urlencoded') {
    payload.urlencoded_rows = urlencodedRows.value.filter(function (r, i) {
      return i < urlencodedRows.value.length - 1 && r.name && r.name.trim()
    })
  } else if (bodyType.value === 'form-data') {
    payload.form_data_rows = formDataRows.value.filter(function (r, i) {
      return i < formDataRows.value.length - 1 && r.name && r.name.trim()
    }).map(function (r) {
      return { name: r.name, type: r.type || 'string', value: r.value || '', fileId: r.fileId || null, desc: r.desc || '' }
    })
    // form-data 文件类型行单独提取
    var files = []
    for (var ffi = 0; ffi < formDataRows.value.length; ffi++) {
      var ff = formDataRows.value[ffi]
      if (ff.name && ff.name.trim() && ff.type === 'file' && ff.fileId) {
        files.push({ field: ff.name.trim(), upload_id: ff.fileId })
      }
    }
    if (files.length) payload.files = files
  }

  return payload
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

/** 从 payload 字典填充调试表单各字段 */
function populateFormFromPayload(payload) {
  if (!payload || typeof payload !== 'object') return
  // 方法 & 路径
  if (payload.method) debugMethod.value = payload.method.toUpperCase()
  if (payload.path) debugPath.value = payload.path
  // headers → headerRows
  var headers = payload.headers || {}
  var hRows = Object.keys(headers).map(function (k) { return { name: k, value: headers[k], desc: '' } })
  hRows.push({ name: '', value: '', desc: '' })
  headerRows.value = hRows.length > 1 ? hRows : [{ name: 'Content-Type', value: 'application/json', desc: '' }]
  // query → queryParamRows
  var query = payload.query || {}
  var qRows = Object.keys(query).map(function (k) { return { name: k, value: query[k], desc: '' } })
  qRows.push({ name: '', value: '', desc: '' })
  queryParamRows.value = qRows
  // path_params → pathParamRows
  var pathParams = payload.path_params || {}
  var pRows = Object.keys(pathParams).map(function (k) { return { name: k, value: pathParams[k], desc: '' } })
  pRows.push({ name: '', value: '', desc: '' })
  pathParamRows.value = pRows
  // body → 根据 body_type 恢复到对应的编辑器
  var savedBodyType = payload.body_type || 'json'
  bodyType.value = savedBodyType
  if (savedBodyType === 'json') {
    requestJson.value = JSON.stringify(payload.body || {}, null, 2)
  } else if (savedBodyType === 'urlencoded') {
    var savedURows = payload.urlencoded_rows || []
    var uRows = savedURows.map(function (r) { return { name: r.name || '', value: r.value || '', desc: r.desc || '' } })
    uRows.push({ name: '', value: '', desc: '' })
    urlencodedRows.value = uRows
  } else if (savedBodyType === 'form-data') {
    var savedFRows = payload.form_data_rows || []
    var fRows = savedFRows.map(function (r) { return { name: r.name || '', type: r.type || 'string', value: r.value || '', fileId: r.fileId || null, desc: r.desc || '' } })
    fRows.push({ name: '', type: 'string', value: '', fileId: null, desc: '' })
    formDataRows.value = fRows
  } else {
    requestJson.value = JSON.stringify(payload.body || {}, null, 2)
  }
  // extracts → extractRows
  var extracts = payload.extracts || []
  var eRows = extracts.map(function (e) { return { name: e.name || '', expression: e.json_path || e.expression || '', desc: e.description || '' } })
  eRows.push({ name: '', expression: '', desc: '' })
  extractRows.value = eRows
  // assertions → assertRows
  var assertions = payload.assertions || []
  var aRows = assertions.map(function (a) { return { target: a.target || '', method: a.comparator || 'eq', expected: a.expected !== undefined ? a.expected : '' } })
  aRows.push({ target: '', method: 'eq', expected: '' })
  assertRows.value = aRows
  // preconditions / postconditions
  var pre = payload.preconditions || []
  if (pre.length > 0 && pre[0].code) preOpsCode.value = pre[0].code
  var post = payload.postconditions || []
  if (post.length > 0 && post[0].code) postOpsCode.value = post[0].code
  // assertionsJson (for display)
  assertionsJson.value = JSON.stringify(payload.assertions || [], null, 2)
}

async function loadTemplate() {
  if (!selectedInterfaceId.value) return
  var res = await getDebugTemplate(selectedInterfaceId.value).catch(function () { return null })
  var tpl = res && res.data ? res.data.data : {}
  // tpl 是 DebugTemplateOut: { interface_id, payload, default_file_id, updated_at }
  var payload = tpl.payload || null
  if (payload) {
    populateFormFromPayload(payload)
  } else {
    // 无已保存的模板，用接口默认值
    requestJson.value = '{}'
    assertionsJson.value = '[]'
    var iface = _getCachedIface()
    if (iface) {
      debugMethod.value = iface.method ? iface.method.toUpperCase() : 'POST'
      debugPath.value = iface.path || ''
    }
  }
  // 恢复默认文件
  if (tpl.default_file_id) selectedUploadId.value = tpl.default_file_id
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
  // 检查是否选择了变量文件
  if (!debugEnvId.value) {
    ElMessage.warning('请先选择变量文件')
    return
  }

  // multipart/form-data 必须包含至少一个 file 类型参数
  if (bodyType.value === 'form-data') {
    var hasFile = formDataRows.value.some(function (r, i) {
      return i < formDataRows.value.length - 1 && r.type === 'file' && r.name && r.name.trim() && r.fileId
    })
    if (!hasFile) {
      ElMessage.warning('multipart/form-data 需要至少一个 file 类型的参数。如无文件上传，请使用 x-www-form-urlencoded')
      return
    }
  }

  var controller = new AbortController()
  debugAbortController.value = controller
  debugging.value = true
  
  // 重置结果状态
  responseResult.value = null
  responseDataInfo.value = null
  requestInfo.value = null
  requestHeadersInfo.value = null
  extractInfo.value = null
  assertInfo.value = null
  logData.value = []
  responseSubTab.value = 'result'
  
  try {
    var payload = buildDebugPayload()
    var res = await debugRunInterface(
      selectedInterfaceId.value,
      { 
        environment_id: debugEnvId.value, 
        payload: payload,
        file_id: selectedUploadId.value || undefined,
      },
      { signal: controller.signal },
    )
    
    // 解析返回结果并结构化展示
    parseDebugResponse(res.data.data)
    
  } catch (err) {
    if (err.name === 'AbortError') {
      // 用户取消操作，不显示错误
    } else {
      console.error('调试执行失败:', err)
      
      // 尝试解析错误响应（如果后端返回了部分结果）
      if (err.response && err.response.data) {
        parseDebugResponse(err.response.data.data || err.response.data)
      }
      
      ElMessage.error(err.message || '调试执行失败')
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
  await saveDebugTemplate(selectedInterfaceId.value, {
    payload: payload,
    default_file_id: selectedUploadId.value || null,
  })
  ElMessage.success(t('common.saved'))
}

async function fillFromDoc() {
  var res = await fillDebugFromDoc(selectedInterfaceId.value)
  var tpl = res.data.data || {}
  // tpl 是 DebugTemplateOut，实际 payload 在 tpl.payload 中
  var payload = tpl.payload || tpl
  populateFormFromPayload(payload)
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
  if (catId) await applyInterfaceReorder(catId, reordered.map(function (r) { return r.id }))
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
  // 项目切换时重新加载变量文件和上传文件
  refreshEnvironmentList()
  loadUploadFiles()
})

watch(selectedCatalogId, function () {
  loadInterfaceList()
})

watch(selectedInterfaceId, function () {
  // 切换接口时清空响应区域
  responseResult.value = null
  responseDataInfo.value = null
  requestInfo.value = null
  requestHeadersInfo.value = null
  extractInfo.value = null
  assertInfo.value = null
  logData.value = []
  responseSubTab.value = 'result'

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
  // 加载变量文件列表
  refreshEnvironmentList()
  // 加载上传文件列表
  loadUploadFiles()
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

.detail-panel--flex {
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
  flex-shrink: 0;

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
  flex-shrink: 0;
}

.debug-sub-tabs {
  flex-shrink: 0;
  height: 340px;
  overflow: hidden;
  :deep(.el-tabs__header) {
    margin-bottom: 0;
    background: var(--fill-color-blank);
  }
  :deep(.el-tabs__content) {
    height: calc(100% - 40px);
    overflow: hidden;
  }
  :deep(.el-tab-pane) {
    height: 100%;
    overflow: auto;
  }
}

.sub-tab-content {
  padding: 12px 0;
  height: 100%;
  box-sizing: border-box;
  font-size: 14px;

  :deep(.el-table) {
    font-size: 14px;
  }

  :deep(.el-input__inner) {
    font-size: 14px;
  }

  :deep(.el-select .el-input__inner) {
    font-size: 14px;
  }

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
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.response-area-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  flex-shrink: 0;

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
  flex: 1;
  min-height: 80px;
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

/* Body类型选择器 */
.body-type-selector {
  margin-bottom: 10px;
}

.form-data-box {
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
  
  .tip {
    margin-bottom: 12px;
    color: #888;
    font-size: 13px;
    margin: 0 0 10px 0;
  }
}

/* 前置/后置操作 - 左右分栏布局 */
.prepost-container {
  display: flex;
  gap: 12px;
  height: 100%;
  
  .prepost-code {
    flex: 1;
    min-width: 0;
  }
  
  .prepost-template {
    width: 280px;
    flex-shrink: 0;
    border-left: 1px solid var(--el-border-color-lighter);
    padding-left: 12px;
    
    .template-header {
      font-weight: 600;
      font-size: 14px;
      color: var(--el-text-color-primary);
      margin-bottom: 6px;
      padding-bottom: 6px;
      border-bottom: 1px solid var(--el-border-color-lighter);
    }

    .template-list {
      overflow-y: auto;

      .template-item {
        padding: 6px 10px;
        margin-bottom: 2px;
        cursor: pointer;
        border-radius: 4px;
        transition: all 0.2s;

        &:hover {
          background: #ecf5ff;
          border-color: #b3d8ff;
        }

        .template-name {
          display: block;
          font-size: 14px;
          font-weight: 500;
          color: var(--el-text-color-primary);
        }
        
        code {
          display: block;
          font-family: 'Fira Code', Consolas, monospace;
          font-size: 11px;
          color: #c7254e;
          background: #f5f5f5;
          padding: 4px 6px;
          border-radius: 3px;
          word-break: break-all;
        }
      }
    }
  }
}

/* 结构化响应展示 */
.structured-response {
  .info-row {
    margin-bottom: 8px;
    font-size: 13px;
    line-height: 1.6;

    strong {
      color: var(--el-text-color-secondary);
      min-width: 100px;
      display: inline-block;
    }

    code {
      background: #f5f7fa;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: monospace;
      font-size: 12px;
      word-break: break-all;
    }
  }
}

/* 通用表格样式 — 提取信息/断言信息/响应头等 tab 共用 */
.response-body,
.structured-response,
.drawer-response-body {
  .info-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 0;
    table-layout: auto;

    th, td {
      border: 1px solid var(--el-border-color-lighter);
      padding: 6px 10px;
      font-size: 12px;
      text-align: left;
      word-break: break-all;
    }

    th {
      background: #fafafa;
      font-weight: 600;
    }
  }
}

.error-message {
  padding: 10px 14px;
  background: #fef0f0;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 13px;
  margin-top: 8px;
  
  strong {
    margin-right: 6px;
  }
}

/* 断言表格 */
.assert-table {
  tr.assert-passed {
    background: #f0f9eb;
  }
  tr.assert-failed {
    background: #fef0f0;
  }
}

/* 日志信息容器 */
.log-container {
  height: 100%;
  overflow-y: auto;
  font-family: 'Fira Code', Consolas, monospace;
  font-size: 12px;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  
  .log-item {
    padding: 4px 8px;
    margin-bottom: 2px;
    border-radius: 2px;
    line-height: 1.6;
    
    .log-level-badge {
      display: inline-block;
      padding: 1px 6px;
      border-radius: 3px;
      font-size: 11px;
      font-weight: 600;
      margin-right: 8px;
      min-width: 50px;
      text-align: center;
      
      &.badge-debug {
        background: #6a9955;
        color: #fff;
      }
      
      &.badge-info {
        background: #3794ff;
        color: #fff;
      }
      
      &.badge-warning, &.badge-warn {
        background: #cca700;
        color: #000;
      }
      
      &.badge-error {
        background: #f44747;
        color: #fff;
      }
    }
    
    .log-message {
      word-break: break-word;
    }
    
    /* 不同级别日志的背景色 */
    &.log-debug {
      background: rgba(106, 153, 85, 0.15);
    }
    
    &.log-info {
      background: rgba(55, 148, 255, 0.15);
    }
    
    &.log-warning,
    &.log-warn {
      background: rgba(204, 167, 0, 0.15);
    }
    
    &.log-error {
      background: rgba(244, 71, 71, 0.25);
      color: #f48771;
    }
  }
}

.drawer-detail-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.drawer-detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-shrink: 0;

  .drawer-detail-meta {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}

.drawer-response-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;

  :deep(.el-tabs__header) {
    margin-bottom: 0;
    flex-shrink: 0;
  }

  :deep(.el-tabs__content) {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  :deep(.el-tab-pane) {
    height: 100%;
  }
}

.drawer-response-body {
  height: 100%;
  overflow: auto;
  padding: 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  background: #fafafa;

  .log-container {
    height: 100%;
    max-height: none;
  }
}
</style>

<!-- 全局样式：变量文件下拉菜单（popper 挂载在 body，scoped 无法生效） -->
<style lang="scss">
.var-file-dropdown {
  .el-dropdown-menu__item {
    font-size: 14px;
    line-height: 22px;
    padding: 5px 16px;
  }
}
</style>
