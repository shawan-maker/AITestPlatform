<template>
  <!-- SIT-F7: Card-style payload display - clickable to open detail dialog -->
  <div
    class="payload-card"
    :class="[`payload-card--${genType}`, { 'payload-card--clickable': hasContent }]"
    @click="openDialog"
  >
    <div class="payload-card__preview">
      <div class="payload-card__icon">
        <el-icon :size="22"><Document /></el-icon>
      </div>
      <div class="payload-card__info">
        <div class="payload-card__title-row">
          <span class="payload-card__title">{{ cardTitle }}</span>
          <el-tag v-if="hasContent" size="small" type="success" effect="light" round>
            {{ caseCountText }}
          </el-tag>
          <el-tag v-else size="small" :type="statusTagType" effect="plain">
            {{ statusLabel }}
          </el-tag>
        </div>
        <div class="payload-card__subtitle">
          {{ subtitleText }}
        </div>
      </div>
      <el-icon v-if="hasContent" class="payload-card__arrow"><ArrowRight /></el-icon>
    </div>

    <!-- Quick preview (collapsed by default, shown inline for functional) -->
    <div v-if="showInlinePreview && genType === 'functional'" class="payload-card__inline-preview">
      <div v-for="(tp, i) in testPoints.slice(0, 3)" :key="i" class="payload-card__tp-mini">
        <el-icon color="#67c23a" style="margin-right:4px;"><CircleCheckFilled /></el-icon>
        <span>{{ tp.name }}</span>
        <el-tag size="small" type="info" round>{{ tp.case_count }}</el-tag>
      </div>
      <div v-if="testPoints.length > 3" class="payload-card__more">
        +{{ testPoints.length - 3 }} {{ t('page.agent.moreItems') }}
      </div>
    </div>
  </div>

  <!-- SIT-F7: Detail Dialog (clicking the card opens this) -->
  <el-dialog
    v-model="dialogVisible"
    :title="cardTitle"
    width="720px"
    destroy-on-close
    append-to-body
  >
    <div class="payload-dialog">
      <!-- Functional content -->
      <template v-if="genType === 'functional' && payload">
        <!-- Test points section -->
        <section v-if="testPoints?.length" class="payload-dialog__section">
          <h4 class="payload-dialog__heading">
            <el-icon><DataAnalysis /></el-icon>
            {{ t('page.agent.testPoints') }} ({{ testPoints.length }})
          </h4>
          <div class="payload-dialog__grid">
            <div
              v-for="(tp, i) in testPoints"
              :key="i"
              class="payload-dialog__point"
              :class="{ 'payload-dialog__point--expanded': expandedPoint === i }"
            >
              <div class="payload-dialog__point-header" @click="togglePoint(i)">
                <span>{{ tp.name }}</span>
                <el-tag size="small" type="info" round>{{ tp.case_count }}</el-tag>
                <el-icon><ArrowDown v-if="expandedPoint === i" /><ArrowRight v-else /></el-icon>
              </div>
              <div v-if="expandedPoint === i && tp.cases?.length" class="payload-dialog__point-cases">
                <div
                  v-for="(c, j) in tp.cases"
                  :key="j"
                  class="payload-dialog__case-item"
                >
                  <el-checkbox
                    :model-value="isSelectedByPoint(i, j)"
                    @change="toggleSelectByPoint(i, j)"
                    :disabled="!canEdit"
                  >
                    {{ c.case_name || c.name }}
                  </el-checkbox>
                  <span v-if="c.priority" class="priority-tag">{{ c.priority }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Cases list section -->
        <section v-if="flatCases?.length" class="payload-dialog__section">
          <h4 class="payload-dialog__heading">
            <el-icon><List /></el-icon>
            {{ t('page.agent.generatedCases') }} ({{ flatCases.length }})
          </h4>
          <div class="payload-dialog__cases-list">
            <div
              v-for="(c, i) in flatCases"
              :key="i"
              class="payload-dialog__case-row"
              :class="{ 'payload-dialog__case-row--selected': isSelectedFlat(i) }"
              @click="toggleSelectFlat(i)"
            >
              <el-checkbox
                :model-value="isSelectedFlat(i)"
                :disabled="!canEdit"
                @click.stop
              />
              <span class="case-name">{{ c.case_name || c.name }}</span>
              <span v-if="c.priority" class="priority-tag">{{ c.priority }}</span>
            </div>
          </div>
        </section>

        <!-- Actions -->
        <div v-if="canEdit && flatCases?.length" class="payload-dialog__actions">
          <el-select
            v-model="saveCatalogId"
            :placeholder="t('page.agent.selectCatalog')"
            style="flex: 1; max-width: 260px"
          >
            <el-option
              v-for="cat in catalogs"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
          <el-button
            type="primary"
            :disabled="!selectedIndexes.length || !saveCatalogId"
            :loading="saving"
            @click="handleSave"
          >
            <el-icon><Check /></el-icon> {{ t('page.agent.saveSelected') }} ({{ selectedIndexes.length }})
          </el-button>
        </div>
      </template>

      <!-- API base cases content -->
      <template v-else-if="genType === 'api_base' && payload?.base_cases">
        <section v-for="(bc, i) in payload.base_cases" :key="i" class="payload-dialog__section">
          <h4 class="payload-dialog__heading">
            <el-icon><Cpu /></el-icon>
            {{ bc.name }}
          </h4>
          <pre class="payload-dialog__code">{{ formatSteps(bc.steps) }}</pre>
        </section>

        <div v-if="canEdit" class="payload-dialog__actions">
          <el-button
            type="primary"
            :disabled="saving"
            @click="handleConfirm"
          >
            {{ t('page.agent.confirmAndRun') }}
          </el-button>
        </div>
      </template>

      <!-- Empty state -->
      <div v-else class="payload-dialog__empty">
        <el-empty :description="t('page.agent.noData')" />
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Check,
  Document,
  ArrowRight,
  ArrowDown,
  CircleCheckFilled,
  DataAnalysis,
  List,
  Cpu
} from '@element-plus/icons-vue'

const props = defineProps({
  genType: { type: String, default: 'functional' }, // 'functional' or 'api_base'
  payload: { type: Object, default: null },
  canEdit: { type: Boolean, default: true },
  saving: { type: Boolean, default: false },
  catalogs: { type: Array, default: () => [] },
})

const emit = defineEmits(['save', 'confirm'])

const { t } = useI18n()

// Dialog state
const dialogVisible = ref(false)
const expandedPoint = ref(null)

// Selection state
const selectedIndexes = ref([])
const saveCatalogId = ref(null)

// Computed properties
const hasContent = computed(() => {
  if (props.genType === 'functional') {
    return !!(props.payload?.test_points?.length || props.payload?.cases?.length)
  }
  return !!(props.payload?.base_cases?.length)
})

const cardTitle = computed(() => {
  if (props.genType === 'functional') return t('page.agent.functionalResultTitle')
  return t('page.agent.apiResultTitle')
})

const subtitleText = computed(() => {
  if (!hasContent.value) return t('page.agent.generating')
  if (props.genType === 'functional') return t('page.agent.clickToExpandCases')
  return t('page.agent.clickToViewDetails')
})

const caseCountText = computed(() => {
  if (props.genType === 'functional') {
    const total = flatCases.value.length
    return `${total} ${t('page.agent.cases')}`
  }
  const count = (props.payload?.base_cases || []).length
  return `${count} ${t('page.agent.baseCases')}`
})

const showInlinePreview = computed(() => hasContent.value && props.genType === 'functional')

// Test points (for functional type)
const testPoints = computed(() => props.payload?.test_points || [])

// Flat cases list
const flatCases = computed(() => {
  if (props.genType === 'functional') {
    return props.payload?.cases || []
  }
  return []
})

// Legacy compatibility - original cases prop
const cases = computed(() => flatCases.value)

const statusTagType = computed(() => {
  if (!props.payload) return 'info'
  return 'success'
})

const statusLabel = computed(() => {
  if (!props.payload) return t('common.unknown')
  const s = props.payload.status
  if (s === 'success') return t('page.agent.statusSuccess')
  if (s === 'failed') return t('page.agent.statusFailed')
  return t('page.agent.statusPending')
})

// Methods
function openDialog() {
  if (hasContent.value) {
    dialogVisible.value = true
  }
}

function togglePoint(i) {
  expandedPoint.value = expandedPoint.value === i ? null : i
}

function isSelected(i) {
  return selectedIndexes.value.includes(i)
}

function isSelectedFlat(i) {
  return selectedIndexes.value.includes(i)
}

function isSelectedByPoint(pointIdx, caseIdx) {
  // Map point-level selection to flat index
  let offset = 0
  for (let p = 0; p < pointIdx; p++) {
    offset += (testPoints.value[p]?.cases?.length || 1)
  }
  return selectedIndexes.value.includes(offset + caseIdx)
}

function toggleSelect(i) {
  const idx = selectedIndexes.value.indexOf(i)
  if (idx >= 0) {
    selectedIndexes.value.splice(idx, 1)
  } else {
    selectedIndexes.value.push(i)
  }
}

function toggleSelectFlat(i) {
  toggleSelect(i)
}

function toggleSelectByPoint(pointIdx, caseIdx) {
  let offset = 0
  for (let p = 0; p < pointIdx; p++) {
    offset += (testPoints.value[p]?.cases?.length || 1)
  }
  toggleSelect(offset + caseIdx)
}

function handleSave() {
  emit('save', { catalog_id: saveCatalogId.value, case_indexes: selectedIndexes.value })
}

function handleConfirm() {
  emit('confirm')
}

function formatSteps(steps) {
  if (!Array.isArray(steps)) return ''
  return steps.map((s, i) => `${i + 1}. ${s}`).join('\n')
}
</script>

<style scoped lang="scss">
/* SIT-F7: Card-style payload display (compact, clickable) */
.payload-card {
  border: 1.5px solid rgba($color-primary, 0.25);
  border-radius: 12px;
  background: var(--el-bg-color);
  margin: 16px;
  transition: all 0.2s ease;

  &--clickable {
    cursor: pointer;

    &:hover {
      border-color: $color-primary;
      box-shadow: 0 4px 16px rgba($color-primary, 0.12);
      transform: translateY(-1px);
    }

    &:active {
      transform: translateY(0);
    }
  }

  &--functional {
    border-left: 4px solid $color-primary;
  }

  &--api_base {
    border-left: 4px solid var(--el-color-warning);
  }
}

/* Preview section (always visible) */
.payload-card__preview {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
}

.payload-card__icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba($color-primary, 0.08), rgba($color-primary, 0.15));
  color: $color-primary;
  flex-shrink: 0;
}

.payload-card__info {
  flex: 1;
  min-width: 0;
}

.payload-card__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.payload-card__title {
  font-weight: 600;
  font-size: 15px;
  color: var(--el-text-color-primary);
}

.payload-card__subtitle {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.payload-card__arrow {
  color: var(--el-text-color-placeholder);
  font-size: 16px;
  flex-shrink: 0;
}

/* Inline preview (collapsed test points) */
.payload-card__inline-preview {
  padding: 0 18px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.payload-card__tp-mini {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--el-text-color-regular);

  .el-tag {
    margin-left: auto;
  }
}

.payload-card__more {
  font-size: 12px;
  color: $color-primary;
  text-align: center;
  padding: 4px 0 2px;
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
}

/* ==================== Dialog Styles ==================== */
.payload-dialog {
  max-height: 60vh;
  overflow-y: auto;
}

.payload-dialog__section {
  margin-bottom: 20px;
}

.payload-dialog__heading {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.payload-dialog__grid {
  display: grid;
  gap: 8px;
}

.payload-dialog__point {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;

  &--expanded {
    border-color: rgba($color-primary, 0.3);
  }
}

.payload-dialog__point-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--el-fill-color-lighter);
  cursor: pointer;
  font-weight: 500;
  font-size: 13.5px;
  transition: background 0.15s;

  &:hover {
    background: var(--el-fill-color-light);
  }

  > span:first-child {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .el-icon:last-child {
    font-size: 12px;
    color: var(--el-text-color-placeholder);
  }
}

.payload-dialog__point-cases {
  padding: 8px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.payload-dialog__case-item,
.payload-dialog__case-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 13px;
  transition: background 0.15s;

  &:hover {
    background: var(--el-fill-color-lighter);
  }

  .case-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .priority-tag {
    font-size: 11px;
    color: var(--el-text-color-secondary);
    background: var(--el-fill-color);
    padding: 2px 8px;
    border-radius: 4px;
  }

  &--selected {
    background: rgba($color-primary, 0.06);

    .priority-tag {
      color: $color-primary;
      font-weight: 600;
    }
  }
}

.payload-dialog__cases-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.payload-dialog__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: 20px;
}

.payload-dialog__code {
  white-space: pre-wrap;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-blank);
  padding: 14px 16px;
  border-radius: 8px;
  border: 1px dashed var(--el-border-color-lighter);
  max-height: 280px;
  overflow-y: auto;
  margin: 0;
}

.payload-dialog__empty {
  text-align: center;
  padding: 40px 0;
}
</style>
