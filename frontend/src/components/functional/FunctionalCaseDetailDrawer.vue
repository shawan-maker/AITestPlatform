<template>
  <el-drawer
    :model-value="visible"
    :title="t('page.functional.caseDetail')"
    direction="rtl"
    size="50%"
    :close-on-click-modal="false"
    @update:model-value="(v) => $emit('update:visible', v)"
    @closed="onClosed"
  >
    <div v-if="loading" class="drawer-loading">
      <el-skeleton :rows="10" animated />
    </div>

    <template v-else-if="caseDetail">
      <!-- 头部操作 -->
      <div class="drawer-header-actions">
        <el-button v-if="canEdit" type="primary" plain size="small" @click="$emit('edit', caseDetail.id)">
          {{ t('common.edit') }}
        </el-button>
        <ConfirmDelete v-if="canEdit" @confirm="handleDelete">
          <el-button type="danger" plain size="small">{{ t('common.delete') }}</el-button>
        </ConfirmDelete>
        <el-button plain size="small" @click="handleCopy">{{ t('page.functional.copy') }}</el-button>
      </div>

      <!-- 基本信息 -->
      <section class="detail-section">
        <h4 class="sec-title">{{ t('page.functional.basicInfo') }}</h4>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item :label="t('page.functional.caseName')">{{ caseDetail.case_name }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.functional.priority')">
            <PriorityTag :value="caseDetail.priority" />
          </el-descriptions-item>
          <el-descriptions-item :label="t('page.functional.type')">
            {{ caseDetail.type === 'ui' ? 'UI' : t('page.functional.typeFunctional') }}
          </el-descriptions-item>
          <el-descriptions-item :label="t('page.functional.status')">
            <StatusTag :type="statusTagType(caseDetail.status)">{{ statusText(caseDetail.status) }}</StatusTag>
          </el-descriptions-item>
          <el-descriptions-item v-if="caseDetail.dimension" :label="t('page.functional.dimension')">{{ caseDetail.dimension }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.functional.execResult')">
            <ExecResultTag :value="caseDetail.exec_result" />
          </el-descriptions-item>
          <el-descriptions-item :label="t('page.functional.jiraKey')">{{ caseDetail.jira_issue_key || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.knowledge.module')">{{ caseDetail.module_name || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.functional.source')">
            {{ caseDetail.source === 'ai' ? t('page.functional.sourceAI') : t('page.functional.sourceManual') }}
          </el-descriptions-item>
        </el-descriptions>
      </section>

      <!-- 测试点摘要 -->
      <section v-if="caseDetail.test_point" class="detail-section">
        <h4 class="sec-title">{{ t('page.functional.testPoint') }}</h4>
        <div class="tp-card">
          <p class="tp-text">{{ caseDetail.test_point }}</p>
        </div>
      </section>

      <!-- 测试步骤与预期结果 -->
      <section class="detail-section">
        <h4 class="sec-title">{{ t('page.functional.stepsAndExpected') }}</h4>
        <div class="field-block" v-if="caseDetail.preconditions">
          <label>{{ t('page.functional.preconditions') }}</label>
          <pre class="field-content">{{ caseDetail.preconditions }}</pre>
        </div>
        <div class="field-block">
          <label>{{ t('page.functional.steps') }}</label>
          <pre class="field-content">{{ caseDetail.test_steps || t('common.noData') }}</pre>
        </div>
        <div class="field-block" v-if="caseDetail.test_data">
          <label>{{ t('page.functional.testData') }}</label>
          <pre class="field-content">{{ caseDetail.test_data }}</pre>
        </div>
        <div class="field-block">
          <label>{{ t('page.functional.expectedResult') }}</label>
          <pre class="field-content">{{ caseDetail.expected_result || t('common.noData') }}</pre>
        </div>
      </section>

      <!-- 元数据 -->
      <section class="meta-info">
        <span>ID: {{ caseDetail.id }}</span>
        <span>{{ t('page.functional.catalog') }}: {{ caseDetail.catalog_name || '-' }}</span>
        <span>{{ t('page.functional.createdBy') }}: {{ caseDetail.created_by_username || '-' }}</span>
        <span>{{ t('page.functional.createdAt') }}: {{ formatTime(caseDetail.created_at) }}</span>
        <span v-if="caseDetail.updated_by_username">{{ t('page.functional.updatedBy') }}: {{ caseDetail.updated_by_username }}</span>
        <span>{{ t('page.functional.updatedAt') }}: {{ formatTime(caseDetail.updated_at) }}</span>
      </section>
    </template>

    <EmptyState v-else-if="!loading" :title="t('common.notFound')" />
  </el-drawer>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getCase, copyCase as copyCaseApi, deleteCase as deleteCaseApi } from '@/api/functional'
import { usePermission } from '@/composables/usePermission'
import EmptyState from '@/components/common/EmptyState.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import PriorityTag from '@/components/tags/PriorityTag.vue'
import ExecResultTag from '@/components/tags/ExecResultTag.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { formatDateTime } from '@/utils/format'

const props = defineProps({
  visible: Boolean,
  caseId: { type: Number, required: true },
  catalogs: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:visible', 'edit', 'copied', 'deleted'])

const { t } = useI18n()
const { canEdit } = usePermission()
const loading = ref(false)
const caseDetail = ref(null)

function formatTime(val) {
  return val ? formatDateTime(val) : '-'
}

function statusTagType(status) {
  const map = { design: 'info', ready: 'success', smoke: 'warning', regression: '', obsolete: 'danger' }
  return map[status] || 'info'
}

function statusText(status) {
  const map = { design: '设计中', ready: '就绪', smoke: '冒烟', regression: '回归', obsolete: '废弃' }
  return map[status] || status
}

async function loadDetail() {
  if (!props.caseId) return
  loading.value = true
  try {
    const res = await getCase(props.caseId)
    caseDetail.value = res.data.data
    // 调试代码：检查test_point字段类型
    console.log('[DEBUG] caseDetail:', caseDetail.value)
    console.log('[DEBUG] test_point type:', typeof caseDetail.value?.test_point)
    console.log('[DEBUG] test_point value:', caseDetail.value?.test_point)
    console.log('[DEBUG] test_point JSON:', JSON.stringify(caseDetail.value?.test_point))
    // 如果test_point是对象，显示其属性和值
    if (caseDetail.value?.test_point && typeof caseDetail.value?.test_point === 'object') {
      console.log('[DEBUG] test_point is object, keys:', Object.keys(caseDetail.value.test_point))
      console.log('[DEBUG] test_point.test_point:', caseDetail.value.test_point.test_point)
    }
  } catch (e) {
    caseDetail.value = null
  } finally {
    loading.value = false
  }
}

function onClosed() {
  caseDetail.value = null
}

async function handleCopy() {
  try {
    await copyCaseApi(props.caseId)
    ElMessage.success(t('page.functional.copied'))
    emit('copied')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message)
  }
}

async function handleDelete() {
  try {
    const res = await deleteCaseApi(props.caseId)
    const warning = res.data.data?.warning
    if (warning?.suite_names?.length) {
      ElMessage.warning(t('page.functional.deleteSuiteWarning', { suites: warning.suite_names.join(', ') }))
    } else {
      ElMessage.success(t('common.deleted'))
    }
    emit('deleted')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.message || e.message)
    }
  }
}

watch(() => props.visible, (val) => {
  if (val && props.caseId) loadDetail()
})
watch(() => props.caseId, (id) => {
  if (props.visible && id) loadDetail()
})
</script>

<style scoped lang="scss">
.drawer-header-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.detail-section {
  margin-bottom: 20px;
}

.sec-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 10px;
  padding-left: 8px;
  border-left: 3px solid var(--el-color-primary, #409eff);
}

.field-block {
  margin-bottom: 12px;

  label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: var(--el-text-color-secondary);
    margin-bottom: 4px;
  }

  .field-content {
    white-space: pre-wrap;
    word-break: break-word;
    padding: 10px 12px;
    background: var(--el-fill-color-lighter, #f5f7fa);
    border-radius: 4px;
    line-height: 1.6;
    font-size: 13.5px;
    color: var(--el-text-color-primary);
    max-height: none;
    margin: 0;
  }
}

.tp-card {
  background: var(--el-fill-color-lighter, #f5f7fa);
  padding: 10px 14px;
  border-radius: 6px;

  .tp-tag {
    margin-right: 8px;
  }

  .tp-dim {
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }

  .tp-text {
    margin: 8px 0 0;
    line-height: 1.6;
  }
}

.meta-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-extra-light);
  color: var(--el-text-color-secondary, #909399);
  font-size: 12px;
}

.drawer-loading {
  padding: 24px 16px;
}
</style>
