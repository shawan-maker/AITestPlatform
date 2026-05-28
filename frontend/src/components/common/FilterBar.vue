<template>
  <div class="filter-bar">
    <div v-if="$slots.primary" class="filter-bar__primary">
      <slot name="primary" />
    </div>
    <slot />
    <div class="filter-bar__actions">
      <el-button type="primary" @click="$emit('search')">{{ t('common.search') }}</el-button>
      <el-button @click="$emit('reset')">{{ t('common.resetForm') }}</el-button>
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
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 14px 18px;
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: $radius-md;
  font-size: var(--font-size-base);
}

.filter-bar__primary {
  flex-shrink: 0;
}

.filter-bar__actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

:deep(.el-input),
:deep(.el-select) {
  width: 220px;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  font-size: var(--font-size-base);
}

:deep(.el-button) {
  font-size: var(--font-size-base);
}
</style>
