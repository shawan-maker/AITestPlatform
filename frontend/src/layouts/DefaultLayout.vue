<template>
  <div class="default-layout">
    <AppSidebar v-if="!isMobile" class="default-layout__sidebar" />
    <div class="default-layout__main-wrap">
      <header v-if="isMobile" class="default-layout__mobile-bar">
        <el-button text :icon="Menu" @click="drawerOpen = true">
          {{ t('common.openMenu') }}
        </el-button>
        <span class="default-layout__mobile-title">{{ t('common.appNameShort') }}</span>
      </header>
      <main class="default-layout__main">
        <router-view />
      </main>
    </div>

    <el-drawer
      v-model="drawerOpen"
      direction="ltr"
      :size="280"
      :with-header="false"
      class="sidebar-drawer"
    >
      <AppSidebar @navigate="drawerOpen = false" />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Menu } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import { useIsMobileSidebar } from '@/composables/useMediaQuery'

const { t } = useI18n()
const isMobile = useIsMobileSidebar()
const drawerOpen = ref(false)
</script>

<style scoped lang="scss">
.default-layout {
  height: 100vh;
  display: flex;
  overflow: hidden;
}

.default-layout__sidebar {
  flex-shrink: 0;
}

.default-layout__main-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: linear-gradient(180deg, var(--bg-page-start) 0%, var(--bg-page-end) 100%);
}

.default-layout__mobile-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-bottom: 1px solid rgba($color-primary, 0.1);
  background: var(--bg-page-header-start);
  flex-shrink: 0;
}

.default-layout__mobile-title {
  font-weight: 600;
  font-size: 15px;
}

.default-layout__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  padding: 20px;

  > * {
    flex: 1;
    min-height: 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
}
</style>

<style lang="scss">
.sidebar-drawer .el-drawer__body {
  padding: 0;
}
</style>
