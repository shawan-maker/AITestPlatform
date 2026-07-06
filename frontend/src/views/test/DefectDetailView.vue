<template>
  <div v-loading="loading" ref="viewRef" class="defect-detail-view">
    <BreadcrumbNav :items="breadcrumbs" />
    <PageHeader :title="defect?.title || t('page.defects.title')" />

    <div class="page-toolbar">
      <el-button v-if="canEdit && !editing" @click="startEdit">{{ t('common.edit') }}</el-button>
      <el-button v-if="canEdit && editing" type="primary" :loading="saving" @click="saveEdit">{{ t('common.save') }}</el-button>
      <el-button v-if="canEdit && editing" @click="cancelEdit">{{ t('common.cancel') }}</el-button>
      <el-button v-if="canEdit && !editing" type="primary" @click="showTransition = true">{{ t('page.defects.transition') }}</el-button>
    </div>

    <template v-if="defect">
      <!-- ==================== Section 1: 基本信息 ==================== -->
      <section class="ui-section-panel">
        <h3 class="ui-section-panel__title collapse-toggle" @click="sections.basic = !sections.basic">
          <el-icon style="margin-right: 6px"><ArrowDown v-if="sections.basic" /><ArrowRight v-else /></el-icon>
          {{ t('page.test.tabBasic') }}
        </h3>
        <div class="ui-section-panel__divider" />
        <el-collapse-transition>
          <div v-show="sections.basic" class="ui-section-panel__body">
            <!-- 查看模式 -->
            <el-descriptions v-if="!editing" :column="2" border>
              <el-descriptions-item label="ID">{{ defect.defect_code || ('#' + defect.id) }}</el-descriptions-item>
              <el-descriptions-item :label="t('common.status')"><DefectStatusTag :status="defect.status" /></el-descriptions-item>
              <el-descriptions-item :label="t('page.defects.severity')">
                <el-tag :type="severityType(defect.severity)" size="small">{{ defectSeverityMap[defect.severity] || defect.severity }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item :label="t('page.defects.priority')">{{ defectPriorityMap[defect.priority] || defect.priority }}</el-descriptions-item>
              <el-descriptions-item :label="t('page.defects.category')">{{ defectCategoryMap[defect.defect_category] || defect.defect_category }}</el-descriptions-item>
              <el-descriptions-item :label="t('page.defects.assignee')">{{ defect.assignee_name || '-' }}</el-descriptions-item>
              <el-descriptions-item :label="t('page.defects.submitter')">{{ defect.created_by_name || '-' }}</el-descriptions-item>
              <el-descriptions-item :label="t('page.defects.submitTime')">{{ formatTime(defect.created_at) }}</el-descriptions-item>
              <el-descriptions-item :label="t('page.defects.rootCause')" :span="2">{{ defect.root_cause || '-' }}</el-descriptions-item>
              <!-- 来源信息 -->
              <template v-if="defect.source && defect.source.source_type !== 'manual' && (defect.source.case_name || defect.source.run_label)">
                <el-descriptions-item :label="t('page.defects.sourceType')">{{ sourceTypeLabel(defect.source.source_type) }}</el-descriptions-item>
                <el-descriptions-item :label="t('page.defects.sourceCase')">{{ defect.source.case_name || '-' }}</el-descriptions-item>
                <el-descriptions-item v-if="defect.source.run_label" :label="t('page.defects.sourceRun')" :span="2">{{ defect.source.run_label }}</el-descriptions-item>
              </template>
            </el-descriptions>
            <!-- 编辑模式 -->
            <el-form v-else :model="editForm" label-width="100px" class="edit-inline-form">
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="ID"><span class="readonly-field">{{ defect.defect_code || ('#' + defect.id) }}</span></el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item :label="t('common.status')"><span class="readonly-field"><DefectStatusTag :status="defect.status" /></span></el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :span="24">
                  <el-form-item :label="t('page.defects.defectTitle')"><el-input v-model="editForm.title" /></el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item :label="t('page.defects.projectSelector')">
                    <el-select v-model="editForm.project_id" filterable remote :remote-method="searchProjects" :loading="projectSearchLoading" style="width: 100%">
                      <el-option v-for="p in projectOptions" :key="p.id" :label="p.name" :value="p.id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item :label="t('page.defects.category')">
                    <el-select v-model="editForm.defect_category" style="width: 100%">
                      <el-option v-for="(label, val) in defectCategoryMap" :key="val" :label="label" :value="val" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item :label="t('page.defects.severity')">
                    <el-select v-model="editForm.severity" style="width: 100%">
                      <el-option v-for="(label, val) in defectSeverityMap" :key="val" :label="label" :value="val" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item :label="t('page.defects.priority')">
                    <el-select v-model="editForm.priority" style="width: 100%">
                      <el-option v-for="(label, val) in defectPriorityMap" :key="val" :label="label" :value="val" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item :label="t('page.defects.submitter')"><span class="readonly-field">{{ defect.created_by_name || '-' }}</span></el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item :label="t('page.defects.submitTime')"><span class="readonly-field">{{ formatTime(defect.created_at) }}</span></el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :span="24">
                  <el-form-item :label="t('page.defects.rootCause')">
                    <el-input v-model="editForm.root_cause" type="textarea" :rows="2" />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
          </div>
        </el-collapse-transition>
      </section>

      <!-- ==================== Section 2: 缺陷描述 ==================== -->
      <section class="ui-section-panel">
        <h3 class="ui-section-panel__title collapse-toggle" @click="sections.desc = !sections.desc">
          <el-icon style="margin-right: 6px"><ArrowDown v-if="sections.desc" /><ArrowRight v-else /></el-icon>
          {{ t('page.defects.description') }}
        </h3>
        <div class="ui-section-panel__divider" />
        <el-collapse-transition>
          <div v-show="sections.desc" class="ui-section-panel__body">
            <div class="desc-scrollable">
              <pre v-if="!editing" class="steps-content">{{ defect.steps || '-' }}</pre>
              <el-input v-else v-model="editForm.steps" type="textarea" :rows="8" />
            </div>
          </div>
        </el-collapse-transition>
      </section>

      <!-- ==================== Section 3: 活动 ==================== -->
      <section class="ui-section-panel">
        <h3 class="ui-section-panel__title collapse-toggle" @click="sections.activity = !sections.activity">
          <el-icon style="margin-right: 6px"><ArrowDown v-if="sections.activity" /><ArrowRight v-else /></el-icon>
          {{ t('page.defects.activity') }}
        </h3>
        <div class="ui-section-panel__divider" />
        <div v-show="sections.activity" class="ui-section-panel__body activity-section">
          <el-tabs v-model="activeActivityTab">
            <!-- Tab 1: 所有操作历史 -->
            <el-tab-pane :label="t('page.defects.allHistory')" name="history">
              <el-table v-if="defect.history?.length" :data="defect.history" size="small" border stripe>
                <el-table-column :label="t('page.defects.operator')" width="100" align="center">
                  <template #default="{ row }">{{ row.operator_name || '-' }}</template>
                </el-table-column>
                <el-table-column :label="t('page.defects.historyField')" min-width="120">
                  <template #default="{ row }">
                    <template v-if="row.action === 'created'">{{ t('page.defects.historyCreated') }}</template>
                    <template v-else-if="row.action === 'status_change'">{{ t('common.status') }}</template>
                    <template v-else-if="row.action === 'field_update'">{{ fieldLabel(row.field_name) }}</template>
                    <template v-else-if="row.action === 'comment_added'">{{ t('page.defects.addedComment') }}</template>
                    <template v-else>{{ row.action }}</template>
                  </template>
                </el-table-column>
                <el-table-column :label="t('page.defects.historyOldValue')" min-width="200">
                  <template #default="{ row }">
                    <template v-if="row.action === 'status_change'">
                      <DefectStatusTag v-if="row.old_value" :status="row.old_value" />
                      <span v-else>-</span>
                    </template>
                    <template v-else-if="row.action === 'comment_added'">-</template>
                    <template v-else>
                      <el-tooltip v-if="row.old_value" :content="translateValue(row.field_name, row.old_value)" placement="top" :show-after="300">
                        <span class="cell-truncated">{{ translateValue(row.field_name, row.old_value) }}</span>
                      </el-tooltip>
                      <span v-else>-</span>
                    </template>
                  </template>
                </el-table-column>
                <el-table-column :label="t('page.defects.historyNewValue')" min-width="200">
                  <template #default="{ row }">
                    <template v-if="row.action === 'status_change'">
                      <DefectStatusTag v-if="row.new_value" :status="row.new_value" />
                      <span v-else>-</span>
                    </template>
                    <template v-else>
                      <el-tooltip v-if="row.new_value" :content="translateValue(row.field_name, row.new_value)" placement="top" :show-after="300">
                        <span class="cell-truncated">{{ translateValue(row.field_name, row.new_value) }}</span>
                      </el-tooltip>
                      <span v-else>-</span>
                    </template>
                  </template>
                </el-table-column>
                <el-table-column :label="t('page.defects.processedAt')" width="170" align="center">
                  <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
                </el-table-column>
              </el-table>
              <el-empty v-else :description="t('page.defects.noComments')" :image-size="48" />
            </el-tab-pane>

            <!-- Tab 2: 状态流转 -->
            <el-tab-pane :label="t('page.defects.statusFlow')" name="statusFlow">
              <el-table v-if="statusTimelineWithDurations.length" :data="statusTimelineWithDurations" size="small" border stripe>
                <el-table-column :label="t('page.defects.transitionAction')" min-width="240">
                  <template #default="{ row }">
                    <template v-if="row.prev_status">
                      <DefectStatusTag :status="row.prev_status" />
                      <span style="margin: 0 6px; color: var(--el-text-color-secondary)">→</span>
                      <DefectStatusTag :status="row.status" />
                    </template>
                    <DefectStatusTag v-else :status="row.status" />
                  </template>
                </el-table-column>
                <el-table-column :label="t('page.defects.timeInState')" width="160" align="center">
                  <template #default="{ row }">
                    <template v-if="row.duration_ms != null">{{ formatDuration(row.duration_ms) }}</template>
                    <el-tag v-else type="info" size="small">{{ t('page.defects.currentState') }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column :label="t('page.defects.operator')" width="120" align="center">
                  <template #default="{ row }">{{ row.operator_name || '-' }}</template>
                </el-table-column>
                <el-table-column :label="t('page.defects.processedAt')" width="170" align="center">
                  <template #default="{ row }">{{ formatTime(row.at) }}</template>
                </el-table-column>
              </el-table>
              <el-empty v-else :description="t('page.defects.noComments')" :image-size="48" />
            </el-tab-pane>

            <!-- Tab 3: 备注 -->
            <el-tab-pane :label="t('page.defects.comments')" name="comments">
              <div v-if="defect.comments?.length" class="comments-list">
                  <div v-for="c in defect.comments" :key="c.id" class="comment-item">
                    <div class="comment-header" @click="toggleCommentExpand(c.id)">
                      <span>
                        <strong>{{ c.created_by_name || '-' }}</strong>
                        {{ t('page.defects.addedComment') }} - {{ formatTime(c.created_at) }}
                      </span>
                      <el-icon v-if="c.content && c.content.length > 100" style="margin-left: 8px; cursor: pointer">
                        <ArrowDown v-if="expandedComments[c.id]" /><ArrowRight v-else />
                      </el-icon>
                    </div>
                    <div class="comment-body" :class="{ expanded: expandedComments[c.id] || !c.content || c.content.length <= 100 }">
                      {{ c.content }}
                    </div>
                  </div>
                </div>
                <el-empty v-else :description="t('page.defects.noComments')" :image-size="48" />

                <!-- 新增备注 -->
                <div v-if="canEdit" class="comment-input-area">
                  <el-input v-model="commentText" type="textarea" :rows="3" :placeholder="t('page.defects.addCommentPlaceholder')" />
                  <div style="margin-top: 8px">
                    <el-button type="primary" :loading="commentSaving" @click="addComment">{{ t('page.defects.addComment') }}</el-button>
                  </div>
                </div>
              </el-tab-pane>
          </el-tabs>
        </div>
      </section>
    </template>

    <!-- 状态流转对话框 -->
    <TransitionDefectDialog v-model="showTransition" :current-status="defect?.status || 'init'" @submit="doTransition" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import { addDefectComment, getDefect, transitionDefect, updateDefect } from '@/api/testManagement'
import { listProjects } from '@/api/projects'
import { usePermission } from '@/composables/usePermission'
import { getDefectSeverityMap, getDefectPriorityMap, getDefectCategoryMap, getDefectStatusMap } from '@/utils/constants'
import { formatTime, formatDuration, calcStatusDurations } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import BreadcrumbNav from '@/components/common/BreadcrumbNav.vue'
import DefectStatusTag from '@/components/defect/DefectStatusTag.vue'
import TransitionDefectDialog from '@/components/defect/TransitionDefectDialog.vue'

const { t } = useI18n()
const defectSeverityMap = computed(() => getDefectSeverityMap(t))
const defectPriorityMap = computed(() => getDefectPriorityMap(t))
const defectCategoryMap = computed(() => getDefectCategoryMap(t))
const defectStatusMap = computed(() => getDefectStatusMap(t))
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const defectId = computed(() => Number(route.params.defectId))

const breadcrumbs = computed(() => [
  { label: t('menu.testDefects'), to: '/test/defects' },
  { label: t('common.breadcrumb.defectDetail') },
])

// --- State ---
const viewRef = ref(null)
const loading = ref(false)
const saving = ref(false)
const commentSaving = ref(false)
const defect = ref(null)
const editing = ref(false)
const showTransition = ref(false)
const commentText = ref('')
const activeActivityTab = ref('history')

const sections = reactive({ basic: true, desc: true, activity: true })
const expandedComments = reactive({})
function toggleCommentExpand(id) { expandedComments[id] = !expandedComments[id] }

const editForm = reactive({
  title: '',
  project_id: null,
  defect_category: 'other',
  severity: 'normal',
  priority: 'medium',
  steps: '',
  root_cause: '',
})

// Project selector
const projectOptions = ref([])
const projectSearchLoading = ref(false)

async function searchProjects(query) {
  projectSearchLoading.value = true
  try {
    const res = await listProjects({ q: query || undefined, page: 1, page_size: 50 })
    projectOptions.value = res.data.data?.items ?? []
  } finally {
    projectSearchLoading.value = false
  }
}

// Field name labels
const FIELD_LABELS = computed(() => ({
  status: t('common.status'),
  title: t('page.defects.defectTitle'),
  severity: t('page.defects.severity'),
  priority: t('page.defects.priority'),
  defect_category: t('page.defects.category'),
  root_cause: t('page.defects.rootCause'),
  steps: t('page.defects.steps'),
  assignee_id: t('page.defects.assignee'),
  project_id: t('page.defects.projectSelector'),
}))
function fieldLabel(name) {
  return FIELD_LABELS.value[name] || name || '-'
}

// Value translation: raw enum values → localized labels
const VALUE_MAPS = {
  severity: defectSeverityMap,
  priority: defectPriorityMap,
  defect_category: defectCategoryMap,
  status: defectStatusMap,
}
function translateValue(fieldName, rawValue) {
  if (!rawValue) return '-'
  var map = VALUE_MAPS[fieldName]
  if (map && map[rawValue]) return map[rawValue]
  return rawValue
}

// Source type labels
function sourceTypeLabel(type) {
  var map = { api_case: t('page.defects.sourceApiCase'), functional_case: t('page.defects.sourceFunctionalCase'), manual: t('page.defects.sourceManual') }
  return map[type] || type || '-'
}

// Status timeline
const statusTimelineWithDurations = computed(() =>
  calcStatusDurations(defect.value?.status_timeline)
)

function severityType(s) {
  if (s === 'critical') return 'danger'
  if (s === 'serious') return 'warning'
  return 'info'
}

function startEdit() {
  if (!defect.value) return
  Object.assign(editForm, {
    title: defect.value.title,
    project_id: defect.value.project_id,
    defect_category: defect.value.defect_category || 'other',
    severity: defect.value.severity || 'normal',
    priority: defect.value.priority || 'medium',
    steps: defect.value.steps || '',
    root_cause: defect.value.root_cause || '',
  })
  editing.value = true
  if (defect.value.project_id && defect.value.project_name) {
    projectOptions.value = [{ id: defect.value.project_id, name: defect.value.project_name }]
  }
}

function cancelEdit() {
  editing.value = false
}

async function load() {
  loading.value = true
  try {
    const res = await getDefect(defectId.value)
    defect.value = res.data.data
  } finally {
    loading.value = false
  }
}

async function saveEdit() {
  saving.value = true
  try {
    await updateDefect(defectId.value, editForm)
    ElMessage.success(t('common.saved'))
    editing.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message)
  } finally {
    saving.value = false
  }
}

async function doTransition(data) {
  try {
    await transitionDefect(defectId.value, { status: data.status, assignee_id: data.assignee_id, comment: data.comment })
    if (data.root_cause) {
      await updateDefect(defectId.value, { root_cause: data.root_cause })
    }
    ElMessage.success(t('common.saved'))
    showTransition.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message)
  }
}

async function addComment() {
  if (!commentText.value.trim()) return
  commentSaving.value = true
  try {
    await addDefectComment(defectId.value, { content: commentText.value })
    commentText.value = ''
    ElMessage.success(t('common.saved'))
    await load()
  } finally {
    commentSaving.value = false
  }
}

onMounted(async () => {
  // Override layout flex constraints so page can scroll naturally
  const mainEl = document.querySelector('.default-layout__main')
  if (mainEl) mainEl.style.overflow = 'auto'
  if (viewRef.value) {
    viewRef.value.style.flex = 'none'
    viewRef.value.style.minHeight = 'auto'
    viewRef.value.style.display = 'block'
  }
  await load()
  if (route.query.edit === '1') startEdit()
})

onUnmounted(() => {
  const mainEl = document.querySelector('.default-layout__main')
  if (mainEl) mainEl.style.overflow = ''
})
</script>

<style scoped lang="scss">
.defect-detail-view {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: 20px;
  width: 100%;
}

.page-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.collapse-toggle {
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  &:hover { color: var(--el-color-primary); }
}

.edit-inline-form {
  .readonly-field {
    font-size: 13px;
    color: var(--el-text-color-regular);
  }
}

.steps-content {
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.8;
  color: var(--el-text-color-primary);
}

.desc-scrollable {
  max-height: 33vh;
  overflow-y: auto;
}

.activity-section {
  padding-bottom: 8px;
  :deep(.el-tabs__header) { margin-bottom: 12px; }
}

/* Truncated cell with tooltip */
.cell-truncated {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-all;
  cursor: default;
}

.comments-list { margin-bottom: 16px; }

.comment-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  &:last-child { border-bottom: none; }
}

.comment-header {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
  cursor: pointer;
  strong { color: var(--el-text-color-primary); margin-right: 6px; }
}

.comment-body {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  max-height: 80px;
  overflow: hidden;
  transition: max-height 0.3s ease;
  &.expanded { max-height: none; }
}

.comment-input-area {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
