<template>
  <div class="page-header">
    <div class="page-header__title">
      <slot name="title">{{ title }}</slot>
    </div>
    <ProjectContextBar />
  </div>
</template>

<script setup>
import ProjectContextBar from '@/components/layout/ProjectContextBar.vue'

defineProps({
  title: { type: String, default: '' },
})
</script>

<style scoped lang="scss">
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
  margin-bottom: var(--space-lg);
  padding: var(--space-md) var(--space-page);
  border-radius: $radius-md;
  background: $bg-page-header;
  border: 1px solid $border-color;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.page-header__title {
  font-size: var(--font-page-title);
  font-weight: 600;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
