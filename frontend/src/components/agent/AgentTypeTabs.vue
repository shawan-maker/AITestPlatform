<template>
  <div class="agent-type-tabs" :class="{ 'agent-type-tabs--compact': compact }" role="tablist">
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
  compact: { type: Boolean, default: false },
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
  gap: 20px; /* 加倍：从 10px 改为 20px */
  flex-shrink: 0;

  &--compact {
    gap: 8px;
    margin-bottom: 8px;

    .agent-type-tabs__item {
      padding: 4px 12px;
      font-size: 13px;
      gap: 6px;
      border-width: 1.5px;
    }

    .agent-type-tabs__icon {
      width: 20px;
      height: 20px;
      font-size: 14px;
    }

    .agent-type-tabs__api-badge {
      width: 20px;
      height: 20px;
      font-size: 9px;
      border-width: 1.5px;
    }
  }
}

.agent-type-tabs__item {
  display: inline-flex;
  align-items: center;
  gap: 16px; /* 加倍：从 8px 改为 16px */
  padding: 16px 32px; /* 加倍：从 8px 16px 改为 16px 32px */
  border: 2px solid var(--el-border-color); /* 加粗边框：从 1px 改为 2px */
  border-radius: 999px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  font-size: 28px; /* 加倍：从 14px 改为 28px */
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
  width: 44px; /* 加倍：从 22px 改为 44px */
  height: 44px; /* 加倍：从 22px 改为 44px */
  font-size: 32px; /* 加倍：从 16px 改为 32px */
  color: var(--el-text-color-secondary);

  &--functional {
    color: $color-primary;
  }
}

.agent-type-tabs__api-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px; /* 加倍：从 22px 改为 44px */
  height: 44px; /* 加倍：从 22px 改为 44px */
  border-radius: 50%;
  border: 3px solid currentColor; /* 加粗边框：从 1.5px 改为 3px */
  font-size: 16px; /* 加倍：从 8px 改为 16px */
  font-weight: 700;
  letter-spacing: -0.02em;
}
</style>
