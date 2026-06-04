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
  gap: 8px;
  padding: 8px 0 16px;
  flex-shrink: 0;
}

.agent-welcome-header__emoji {
  font-size: 28px;
  line-height: 1;
}

.agent-welcome-header__text {
  font-size: 22px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.agent-welcome-header__brand {
  font-weight: 700;
  background: linear-gradient(90deg, #409eff 0%, #7c3aed 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
</style>
