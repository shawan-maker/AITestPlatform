<template>
  <div v-loading="loading" class="defect-detail-view app-card">
    <PageHeader :title="defect?.title || t('page.defects.title')" />

    <div class="page-toolbar">
      <el-button @click="router.push('/test/defects')">{{ t('common.back') }}</el-button>
      <el-button v-if="canEdit" @click="startEdit">{{ t('common.edit') }}</el-button>
      <el-button v-if="canEdit" type="primary" @click="showTransition = true">{{ t('page.defects.transition') }}</el-button>
    </div>

    <template v-if="defect">
      <!-- 基本信息 -->
      <SectionPanel :title="t('page.test.tabBasic')">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ defect.id }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.status')"><DefectStatusTag :status="defect.status" /></el-descriptions-item>
          <el-descriptions-item :label="t('page.defects.severity')"><el-tag :type="severityType(defect.severity)" size="small">{{ DEFECT_SEVERITY_MAP[defect.severity] || defect.severity }}</el-tag></el-descriptions-item>
          <el-descriptions-item :label="t('page.defects.priority')">{{ DEFECT_PRIORITY_MAP[defect.priority] || defect.priority }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.defects.category')">{{ DEFECT_CATEGORY_MAP[defect.defect_category] || defect.defect_category }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.defects.assignee')">{{ defect.assignee_name || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.defects.submitter')">{{ defect.created_by_name || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.defects.submitTime')">{{ formatTime(defect.created_at) }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.defects.rootCause')" :span="2">{{ defect.root_cause || '-' }}</el-descriptions-item>
        </el-descriptions>
      </SectionPanel>

      <!-- 来源信息 -->
      <SectionPanel v-if="defect.source" :title="t('page.defects.source')">
        <el-descriptions :column="2" border>
          <el-descriptions-item :label="t('page.defects.sourceType')">{{ defect.source.source_type || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.defects.sourceCase')">{{ defect.source.case_name || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.defects.sourceRun')">{{ defect.source.run_label || '-' }}</el-descriptions-item>
        </el-descriptions>
      </SectionPanel>

      <!-- 缺陷步骤 -->
      <SectionPanel :title="t('page.defects.steps')">
        <pre style="white-space: pre-wrap; margin: 0; color: var(--el-text-color-primary)">{{ defect.steps || '-' }}</pre>
      </SectionPanel>

      <!-- 编辑区 -->
      <SectionPanel v-if="editing" :title="t('page.defects.editDefect')">
        <el-form :model="editForm" label-width="100px" style="max-width: 640px">
          <el-form-item :label="t('page.defects.title')"><el-input v-model="editForm.title" /></el-form-item>
          <el-form-item :label="t('page.defects.category')">
            <el-select v-model="editForm.defect_category" style="width: 100%">
              <el-option v-for="(label, val) in DEFECT_CATEGORY_MAP" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('page.defects.severity')">
            <el-select v-model="editForm.severity" style="width: 100%">
              <el-option v-for="(label, val) in DEFECT_SEVERITY_MAP" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('page.defects.priority')">
            <el-select v-model="editForm.priority" style="width: 100%">
              <el-option v-for="(label, val) in DEFECT_PRIORITY_MAP" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('page.defects.steps')">
            <el-input v-model="editForm.steps" type="textarea" :rows="4" />
          </el-form-item>
          <el-form-item :label="t('page.defects.rootCause')">
            <el-input v-model="editForm.root_cause" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
        <FormActionBar :saving="saving" @save="saveEdit" @cancel="editing = false" />
      </SectionPanel>

      <!-- 状态流转时间线 -->
      <SectionPanel v-if="defect.status_timeline?.length" :title="t('page.defects.statusTimeline')">
        <el-timeline>
          <el-timeline-item v-for="(item, i) in defect.status_timeline" :key="i" :timestamp="formatTime(item.at)" placement="top">
            <DefectStatusTag :status="item.status" />
            <span style="margin-left: 8px; color: var(--el-text-color-secondary)">{{ item.operator_name || '' }}</span>
          </el-timeline-item>
        </el-timeline>
      </SectionPanel>

      <!-- 评论 -->
      <SectionPanel :title="t('page.defects.comments')">
        <el-timeline v-if="defect.comments?.length">
          <el-timeline-item v-for="c in defect.comments" :key="c.id" :timestamp="formatTime(c.created_at)" placement="top">
            <div><strong>{{ c.created_by_name || '-' }}</strong></div>
            <div style="white-space: pre-wrap">{{ c.content }}</div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else :description="t('page.defects.noComments')" />
        <div v-if="canEdit" style="margin-top: 16px">
          <el-input v-model="commentText" type="textarea" :rows="3" :placeholder="t('page.defects.addComment')" />
          <div style="margin-top: 8px">
            <el-button type="primary" :loading="commentSaving" @click="addComment">{{ t('page.defects.addComment') }}</el-button>
          </div>
        </div>
      </SectionPanel>

      <!-- 历史记录 -->
      <SectionPanel v-if="defect.history?.length" :title="t('page.defects.history')">
        <el-timeline>
          <el-timeline-item v-for="h in defect.history" :key="h.id" :timestamp="formatTime(h.created_at)" placement="top">
            <span style="color: var(--el-text-color-secondary)">{{ h.operator_name || '' }}</span>
            <span v-if="h.action === 'status_change'" style="margin-left: 8px">
              {{ t('page.defects.historyStatusChange') }}: <DefectStatusTag :status="h.old_value" /> → <DefectStatusTag :status="h.new_value" />
            </span>
            <span v-else-if="h.action === 'field_update'" style="margin-left: 8px">
              {{ t('page.defects.historyFieldUpdate') }} {{ h.field_name }}: {{ h.old_value || t('page.defects.historyEmpty') }} → {{ h.new_value || t('page.defects.historyEmpty') }}
            </span>
            <span v-else-if="h.action === 'comment_added'" style="margin-left: 8px">{{ t('page.defects.historyCommentAdded') }}</span>
            <span v-else-if="h.action === 'created'" style="margin-left: 8px">{{ t('page.defects.historyCreated') }}</span>
            <span v-else style="margin-left: 8px">{{ h.action }}</span>
          </el-timeline-item>
        </el-timeline>
      </SectionPanel>
    </template>

    <!-- 状态流转对话框 -->
    <TransitionDefectDialog v-model="showTransition" :current-status="defect?.status || 'init'" @submit="doTransition" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { addDefectComment, getDefect, transitionDefect, updateDefect } from '@/api/testManagement'
import { usePermission } from '@/composables/usePermission'
import { DEFECT_SEVERITY_MAP, DEFECT_PRIORITY_MAP, DEFECT_CATEGORY_MAP } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import SectionPanel from '@/components/common/SectionPanel.vue'
import FormActionBar from '@/components/common/FormActionBar.vue'
import DefectStatusTag from '@/components/defect/DefectStatusTag.vue'
import TransitionDefectDialog from '@/components/defect/TransitionDefectDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const defectId = computed(() => Number(route.params.defectId))

const loading = ref(false)
const saving = ref(false)
const commentSaving = ref(false)
const defect = ref(null)
const editing = ref(false)
const editForm = reactive({ title: '', defect_category: 'other', severity: 'normal', priority: 'medium', steps: '', root_cause: '' })
const commentText = ref('')
const showTransition = ref(false)

function severityType(s) {
  if (s === 'critical') return 'danger'
  if (s === 'serious') return 'warning'
  return 'info'
}

function startEdit() {
  if (!defect.value) return
  Object.assign(editForm, {
    title: defect.value.title,
    defect_category: defect.value.defect_category || 'other',
    severity: defect.value.severity || 'normal',
    priority: defect.value.priority || 'medium',
    steps: defect.value.steps || '',
    root_cause: defect.value.root_cause || '',
  })
  editing.value = true
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
  } finally {
    saving.value = false
  }
}

async function doTransition(data) {
  await transitionDefect(defectId.value, data)
  ElMessage.success(t('common.saved'))
  showTransition.value = false
  await load()
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

onMounted(load)
</script>
