<template>
  <div class="requirement-view-only app-card">
    <PageHeader :title="t('page.requirements.title')">
      <template #actions>
        <el-button @click="router.back()">{{ t('common.back') }}</el-button>
      </template>
    </PageHeader>

    <div v-if="loading" class="loading-wrapper">
      <el-skeleton :rows="8" animated />
    </div>

    <template v-else-if="detail">
      <!-- 基本信息区 -->
      <section class="detail-section">
        <h3 class="section-title">{{ t('page.requirements.basicInfo') }}</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item :label="t('page.requirements.title')">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.knowledge.module')">{{ detail.module_name || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.requirements.source')">
            <StatusTag :type="detail.source_type === 'knowledge' ? 'primary' : 'info'">
              {{ detail.source_type === 'knowledge' ? t('page.requirements.sourceKnowledge') : t('page.requirements.sourceManual') }}
            </StatusTag>
          </el-descriptions-item>
          <el-descriptions-item :label="t('page.requirements.priority')">
            <PriorityTag :value="detail.priority" />
          </el-descriptions-item>
          <el-descriptions-item :label="t('page.requirements.status')">
            <el-tag size="small" :type="detail.status === 'confirmed' ? 'success' : 'warning'">
              {{ detail.status === 'confirmed' ? t('page.requirements.confirmed') : t('page.requirements.pending') }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="t('page.requirements.docNo')">{{ detail.doc_no || '-' }}</el-descriptions-item>
        </el-descriptions>
      </section>

      <!-- 需求描述 -->
      <section class="detail-section">
        <h3 class="section-title">{{ t('page.requirements.description') }}</h3>
        <div class="description-content">
          <pre v-if="detail.description" class="desc-text" :class="{ 'desc-overflow': !expanded }">{{ detail.description }}</pre>
          <EmptyState v-else :title="t('common.noData')" :description="''" />
          <el-link v-if="detail.description && needExpandToggle" type="primary" @click="expanded = !expanded">
            {{ expanded ? t('common.collapse') : t('common.expand') }}
          </el-link>
        </div>
      </section>

      <!-- 来源文档信息（知识库来源时展示） -->
      <section v-if="detail.source_type === 'knowledge' && detail.source_document_id" class="detail-section">
        <h3 class="section-title">{{ t('page.requirements.sourceDoc') }}</h3>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item :label="t('page.requirements.versionLabel')">{{ detail.source_version_label || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.requirements.indexedAt')">{{ formatTime(detail.indexed_at) }}</el-descriptions-item>
        </el-descriptions>
      </section>

      <!-- 关联用例 -->
      <section class="detail-section">
        <h3 class="section-title">
          {{ t('page.requirementDetail.linkedCases') }} ({{ detail.linked_case_count }})
        </h3>
        <template v-if="detail.linked_case_count > 0">
          <el-button type="primary" link @click="showLinkedCases = true">{{ t('page.requirementDetail.viewCases') }}</el-button>
        </template>
        <span v-else class="text-muted">{{ t('page.requirementDetail.noLinkedCases') }}</span>
      </section>

      <!-- 创建/更新信息 -->
      <section class="detail-section meta-info">
        <span>{{ t('page.requirements.createdBy') }}: {{ detail.created_by_username || '-' }}</span>
        <span>{{ t('page.requirements.createdAt') }}: {{ formatTime(detail.created_at) }}</span>
        <span v-if="detail.updated_by_username">{{ t('page.requirements.updatedBy') }}: {{ detail.updated_by_username }}</span>
        <span>{{ t('page.requirements.updatedAt') }}: {{ formatTime(detail.updated_at) }}</span>
      </section>

      <!-- 关联用例 Drawer -->
      <el-dialog v-model="showLinkedCases" :title="t('page.requirementDetail.linkedCases')" width="640px" destroy-on-close>
        <LinkedCasesList :requirement-id="detailId" />
      </el-dialog>
    </template>

    <EmptyState v-else-if="!loading" :title="t('common.notFound')" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getRequirement } from '@/api/functional'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import PriorityTag from '@/components/tags/PriorityTag.vue'
import LinkedCasesList from '@/components/functional/LinkedCasesList.vue'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const detailId = computed(() => parseInt(route.params.requirementId))
const loading = ref(true)
const detail = ref(null)
const expanded = ref(false)
const showLinkedCases = ref(false)

// 当描述超过 10 行时显示展开按钮
const MAX_LINES = 10
const needExpandToggle = computed(() => {
  if (!detail.value?.description) return false
  return detail.value.description.split('\n').length > MAX_LINES
})

function formatTime(val) {
  return val ? formatDateTime(val) : '-'
}

onMounted(async () => {
  try {
    const res = await getRequirement(detailId.value)
    detail.value = res.data.data
  } catch (e) {
    // 404 handled by EmptyState
  } finally {
    loading.value = false
  }
})
</script>

<style scoped lang="scss">
.detail-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #1F2937);
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 3px solid var(--color-primary, #8ECAE6);
}

.description-content {
  background: var(--bg-card, #fff);
  padding: 16px;
  border-radius: var(--radius-sm, 8px);
  border: 1px solid var(--border-color, #E5E7EB);
}

.desc-text {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  line-height: 1.7;
  font-family: inherit;
  color: var(--text-primary, #1F2937);
}

.desc-overflow {
  max-height: calc(1.7em * 10 + 32px); /* 10行 */
  overflow-y: hidden;
  mask-image: linear-gradient(to bottom, black 60%, transparent 100%);
}

.meta-info {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  color: var(--text-secondary, #6B7280);
  font-size: 13px;

  span::after {
    content: '|';
    margin-left: 12px;
    color: var(--border-color, #E5E7EB);
  }

  span:last-child::after {
    content: none;
  }
}

.text-muted {
  color: var(--text-secondary, #6B7280);
  font-size: 13px;
}

.loading-wrapper {
  padding: 24px;
}
</style>
