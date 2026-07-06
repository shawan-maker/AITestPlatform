<template>
  <header class="agent-welcome-header">
    <span class="agent-welcome-header__emoji">👋</span>
    <span class="agent-welcome-header__text">
      {{ t('page.agent.welcomePrefix') }}
      <span class="agent-welcome-header__brand">{{ t('page.agent.welcomeBrand') }}</span>
    </span>
  </header>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<style scoped lang="scss">
.agent-welcome-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) 0 var(--space-lg);
  flex-shrink: 0;
}

.agent-welcome-header__emoji {
  font-size: 28px;
  line-height: 1;
}

.agent-welcome-header__text {
  font-size: var(--font-page-title);
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.agent-welcome-header__brand {
  font-weight: 700;
  background: linear-gradient(90deg, $color-ai-primary 0%, $color-ai-light 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
</style>
