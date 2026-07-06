<template>
  <div class="empty-state">
    <div class="empty-state__icon">
      <el-icon :size="64" :color="iconColor"><component :is="iconComponent" /></el-icon>
    </div>
    <p class="empty-state__title">{{ title }}</p>
    <p v-if="description" class="empty-state__desc">{{ description }}</p>
    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Document, Search, Warning, Lock } from '@element-plus/icons-vue'

const props = defineProps({
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  icon: { type: String, default: 'document' },
})

const iconMap = {
  document: Document,
  search: Search,
  warning: Warning,
  lock: Lock,
}

const iconComponent = computed(() => iconMap[props.icon] || Document)
const iconColor = 'var(--text-secondary)'
</script>

<style scoped lang="scss">
.empty-state {
  text-align: center;
  padding: 48px $space-xl;
  color: $text-secondary;
}

.empty-state__icon {
  margin-bottom: $space-md;
  opacity: 0.4;
}

.empty-state__title {
  font-size: var(--font-card-title);
  font-weight: 500;
  color: $text-primary;
  margin: 0 0 $space-sm;
}

.empty-state__desc {
  margin: 0;
  font-size: var(--font-caption);
}
</style>
