<template>
  <div class="filter-bar">
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
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: $radius-md;
}

.filter-bar__actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}
</style>
