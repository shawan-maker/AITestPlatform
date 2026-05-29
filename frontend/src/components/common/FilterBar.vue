<template>
  <div class="filter-bar">
    <div class="filter-bar__row">
      <div v-if="$slots.primary" class="filter-bar__primary">
        <slot name="primary" />
      </div>
      <div class="filter-bar__filters">
        <slot />
      </div>
      <div class="filter-bar__actions">
        <el-button type="primary" @click="$emit('search')">{{ t('common.search') }}</el-button>
        <el-button @click="$emit('reset')">{{ t('common.resetForm') }}</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

defineEmits(['search', 'reset'])
const { t } = useI18n()
</script>

<style scoped lang="scss">
.filter-bar {
  margin-bottom: 16px;
  padding: 14px 18px;
  background: linear-gradient(
    135deg,
    var(--bg-filter-bar-start) 0%,
    var(--bg-filter-bar-end) 100%
  );
  border: 1px solid rgba($color-primary-dark, 0.35);
  border-radius: $radius-md;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
  font-size: var(--font-size-base);
}

.filter-bar__row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  flex-wrap: wrap;
}

.filter-bar__primary {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.filter-bar__filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
  flex-wrap: wrap;
}

.filter-bar__actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
  margin-left: auto;
}

.filter-bar__filters :deep(.el-input),
.filter-bar__filters :deep(.el-select) {
  flex: 1 1 220px;
  min-width: 200px;
  max-width: 360px;
}

.filter-bar__filters :deep(.el-input__wrapper),
.filter-bar__filters :deep(.el-select__wrapper) {
  font-size: var(--font-size-base);
  min-height: 36px;
}

.filter-bar__actions :deep(.el-button),
.filter-bar__primary :deep(.el-button) {
  font-size: var(--font-size-base);
}
</style>
