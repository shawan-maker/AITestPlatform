<template>
  <!-- Lightweight result card embedded in agent message -->
  <div class="agent-result-card" @click="$emit('open-list', payload)">
    <div class="agent-result-card__icon">
      <el-icon :size="20"><Document /></el-icon>
    </div>
    <div class="agent-result-card__body">
      <div class="agent-result-card__title">{{ cardTitle }}</div>
      <div class="agent-result-card__hint">{{ t('page.agent.resultHint') }}</div>
    </div>
    <div class="agent-result-card__count">
      <el-tag size="small" type="danger" effect="light" round>{{ caseCountText }}</el-tag>
    </div>
    <el-icon class="agent-result-card__arrow"><ArrowRight /></el-icon>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Document, ArrowRight } from '@element-plus/icons-vue'

const props = defineProps({
  payload: { type: Object, default: null },
  genType: { type: String, default: 'functional' },
})

const emit = defineEmits(['open-list'])

const { t } = useI18n()

const cardTitle = computed(() => {
  if (props.genType === 'functional') return t('page.agent.functionalResultTitle')
  return t('page.agent.apiResultTitle')
})

const caseCountText = computed(() => {
  if (props.genType === 'functional') {
    const total = (props.payload?.cases || []).length
    return `${total} ${t('page.agent.cases')}`
  }
  const count = (props.payload?.base_cases || []).length
  return `${count} ${t('page.agent.baseCases')}`
})
</script>

<style scoped lang="scss">
.agent-result-card {
  margin-top: 12px;
  border: 1.5px solid #f56c6c;
  border-radius: 10px;
  padding: 14px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s ease;

  &:hover {
    border-color: #f23;
    box-shadow: 0 2px 12px rgba(245, 108, 108, 0.15);
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(0);
  }

  &__icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(245, 108, 108, 0.08);
    color: #f56c6c;
    flex-shrink: 0;
  }

  &__body {
    flex: 1;
    min-width: 0;
  }

  &__title {
    font-weight: 600;
    font-size: 14px;
    color: var(--el-text-color-primary);
  }

  &__hint {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 2px;
  }

  &__count {
    flex-shrink: 0;
  }

  &__arrow {
    color: var(--el-text-color-placeholder);
    font-size: 16px;
    flex-shrink: 0;
  }
}
</style>
