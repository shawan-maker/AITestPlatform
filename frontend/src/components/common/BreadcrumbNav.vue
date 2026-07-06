<template>
  <div v-if="items.length > 1" class="breadcrumb-nav">
    <button class="breadcrumb-nav__back" @click="goBack">
      <el-icon :size="16"><ArrowLeft /></el-icon>
      <span>{{ t('common.back') }}</span>
    </button>
    <span class="breadcrumb-nav__separator">|</span>
    <nav class="breadcrumb-nav__path">
      <template v-for="(item, index) in items" :key="index">
        <span
          v-if="index < items.length - 1"
          class="breadcrumb-nav__link"
          @click="navigateTo(item)"
        >{{ item.label }}</span>
        <span v-else class="breadcrumb-nav__current">{{ item.label }}</span>
        <span v-if="index < items.length - 1" class="breadcrumb-nav__slash">/</span>
      </template>
    </nav>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ArrowLeft } from '@element-plus/icons-vue'

const props = defineProps({
  items: {
    type: Array,
    required: true,
    // items: Array<{ label: string; to?: string }>
  },
})

const router = useRouter()
const { t } = useI18n()

function goBack() {
  // Navigate to the second-to-last item's `to` path
  if (props.items.length >= 2) {
    const parent = props.items[props.items.length - 2]
    if (parent?.to) {
      router.push(parent.to)
    }
  }
}

function navigateTo(item) {
  if (item.to) {
    router.push(item.to)
  }
}
</script>

<style scoped lang="scss">
.breadcrumb-nav {
  display: flex;
  align-items: center;
  margin-bottom: var(--space-md);
  font-size: var(--font-caption);
  line-height: 1;
}

.breadcrumb-nav__back {
  display: inline-flex;
  align-items: center;
  gap: $space-xs;
  padding: 0;
  border: none;
  background: transparent;
  color: $text-secondary;
  font-size: var(--font-body, 15px);
  cursor: pointer;
  transition: color 0.15s;
  white-space: nowrap;

  &:hover {
    color: $color-primary;
  }
}

.breadcrumb-nav__separator {
  margin: 0 $space-md;
  color: $border-color;
  user-select: none;
}

.breadcrumb-nav__path {
  display: flex;
  align-items: center;
  gap: 0;
}

.breadcrumb-nav__link {
  color: $text-secondary;
  cursor: pointer;
  transition: color 0.15s;

  &:hover {
    color: $color-primary;
  }
}

.breadcrumb-nav__current {
  color: $text-primary;
  font-weight: 600;
}

.breadcrumb-nav__slash {
  margin: 0 $space-sm;
  color: $text-secondary;
  user-select: none;
}
</style>
