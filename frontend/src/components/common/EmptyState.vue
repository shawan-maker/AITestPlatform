<template>
  <div class="empty-state">
    <div class="empty-state__icon">📭</div>
    <p class="empty-state__title">{{ title }}</p>
    <p v-if="description" class="empty-state__desc">{{ description }}</p>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  description: { type: String, default: '' },
})
</script>

<style scoped lang="scss">
.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: $text-secondary;
}

.empty-state__icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-state__title {
  font-size: 16px;
  color: $text-primary;
  margin: 0 0 8px;
}

.empty-state__desc {
  margin: 0;
  font-size: 14px;
}
</style>
