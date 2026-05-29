<template>
  <div class="page-header">
    <div class="page-header__left">
      <ProjectContextBar />
      <div class="page-header__title">
        <slot name="title">{{ title }}</slot>
      </div>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 16px 20px;
  border-radius: $radius-md;
  background: linear-gradient(
    135deg,
    var(--bg-page-header-start) 0%,
    var(--bg-page-header-end) 100%
  );
  border: 1px solid rgba($color-primary-dark, 0.45);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.65),
    0 1px 3px rgba($color-primary-dark, 0.12);
}

.page-header__left {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.page-header__title {
  font-size: 22px;
  font-weight: 600;
}

.page-header__actions {
  flex-shrink: 0;
}
</style>
