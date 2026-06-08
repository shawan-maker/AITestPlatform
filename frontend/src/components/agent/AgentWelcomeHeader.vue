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
  gap: 16px; /* 加倍：从 8px 改为 16px */
  padding: 16px 0 32px; /* 加倍：从 8px 0 16px 改为 16px 0 32px */
  flex-shrink: 0;
}

.agent-welcome-header__emoji {
  font-size: 56px; /* 加倍：从 28px 改为 56px */
  line-height: 1;
}

.agent-welcome-header__text {
  font-size: 44px; /* 加倍：从 22px 改为 44px */
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
