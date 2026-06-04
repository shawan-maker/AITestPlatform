<template>
  <div class="agent-type-tabs" role="tablist">
    <button
      v-for="tab in tabs"
      :key="tab.name"
      type="button"
      role="tab"
      class="agent-type-tabs__item"
      :class="{ 'agent-type-tabs__item--active': modelValue === tab.name }"
      :aria-selected="modelValue === tab.name"
      @click="$emit('update:modelValue', tab.name)"
    >
      <span class="agent-type-tabs__icon" :class="`agent-type-tabs__icon--${tab.name}`">
        <component :is="tab.icon" v-if="tab.icon" />
        <span v-else class="agent-type-tabs__api-badge">API</span>
      </span>
      <span>{{ tab.label }}</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChatDotRound } from '@element-plus/icons-vue'

defineProps({
  modelValue: { type: String, default: 'functional' },
})

defineEmits(['update:modelValue'])

const { t } = useI18n()

const tabs = computed(() => [
  { name: 'functional', label: t('page.agent.functionalTab'), icon: ChatDotRound },
  { name: 'api', label: t('page.agent.apiTab'), icon: null },
])
</script>

<style scoped lang="scss">
.agent-type-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  flex-shrink: 0;
}

.agent-type-tabs__item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 999px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, color 0.2s;

  &:hover {
    border-color: rgba($color-primary, 0.45);
    color: var(--el-text-color-primary);
  }

  &--active {
    border-color: rgba($color-primary, 0.55);
    background: rgba($color-primary, 0.06);
    color: var(--el-text-color-primary);
    font-weight: 500;
  }
}

.agent-type-tabs__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  font-size: 16px;
  color: var(--el-text-color-secondary);

  &--functional {
    color: $color-primary;
  }
}

.agent-type-tabs__api-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1.5px solid currentColor;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
</style>
