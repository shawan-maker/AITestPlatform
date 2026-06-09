<template>
  <aside class="app-sidebar">
    <div class="app-sidebar__header">
      <router-link to="/agent" class="app-sidebar__brand" @click="emit('navigate')">
        <img :src="logo" alt="" class="app-sidebar__logo-img" />
        <span class="app-sidebar__name">{{ t('common.appName') }}</span>
        <span class="app-sidebar__name-short">{{ t('common.appNameShort') }}</span>
      </router-link>
    </div>

    <nav class="app-sidebar__menu">
      <el-menu
        :default-active="activePath"
        :router="true"
        class="app-sidebar__menu-inner"
        @select="emit('navigate')"
      >
        <template v-for="item in menus" :key="item.path || item.titleKey">
          <el-sub-menu v-if="item.children" :index="item.titleKey">
            <template #title>
              <el-icon v-if="resolveMenuIcon(item.icon)" class="app-sidebar__menu-icon">
                <component :is="resolveMenuIcon(item.icon)" />
              </el-icon>
              <span>{{ t(item.titleKey) }}</span>
            </template>
            <el-menu-item
              v-for="child in item.children"
              :key="child.path"
              :index="child.path"
            >
              {{ t(child.titleKey) }}
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item
            v-else
            :index="item.path"
            :class="menuItemClass(item)"
          >
            <el-icon v-if="resolveMenuIcon(item.icon)" class="app-sidebar__menu-icon">
              <component :is="resolveMenuIcon(item.icon)" />
            </el-icon>
            <span>{{ t(item.titleKey) }}</span>
            <el-tag v-if="item.emphasis === 'admin'" size="small" type="info" class="menu-admin-tag">
              SA
            </el-tag>
          </el-menu-item>
        </template>
      </el-menu>
    </nav>

    <div class="app-sidebar__footer">
      <el-dropdown trigger="click" @command="onUserCommand">
        <div class="app-sidebar__user">
          <el-avatar :size="32" :src="defaultAvatar">{{ avatarText }}</el-avatar>
          <span class="app-sidebar__username">{{ auth.user?.username }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">{{ t('common.profile') }}</el-dropdown-item>
            <el-dropdown-item divided command="logout">{{ t('common.logout') }}</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <el-dropdown trigger="click" @command="onLocale">
        <el-button text class="app-sidebar__locale">
          {{ localeStore.locale === 'zh-CN' ? '中文' : 'EN' }}
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="zh-CN">中文</el-dropdown-item>
            <el-dropdown-item command="en-US">English</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import { filterMenus } from '@/router/menus'
import { useAuthStore } from '@/stores/auth'
import { useLocaleStore } from '@/stores/locale'
import { useProjectStore } from '@/stores/project'
import { usePermissionStore } from '@/stores/permission'
import { defaultAvatar, logo } from '@/utils/branding'

const emit = defineEmits(['navigate'])

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const auth = useAuthStore()
const localeStore = useLocaleStore()
const projectStore = useProjectStore()
const permissionStore = usePermissionStore()

function resolveMenuIcon(name) {
  return name ? ElementPlusIconsVue[name] : undefined
}

const menus = computed(() => filterMenus(auth.isSuperAdmin))
const activePath = computed(() => route.path)
const avatarText = computed(() => (auth.user?.username?.[0] ?? 'U').toUpperCase())

function menuItemClass(item) {
  if (item.emphasis === 'featured') return 'menu-item--featured'
  if (item.emphasis === 'admin') return 'menu-item--admin'
  return ''
}

function onLocale(cmd) {
  localeStore.setLocale(cmd)
}

async function onUserCommand(cmd) {
  if (cmd === 'profile') {
    emit('navigate')
    router.push('/profile')
    return
  }
  if (cmd === 'logout') {
    await auth.logout()
    projectStore.$reset()
    permissionStore.$reset()
    router.push('/login')
  }
}
</script>

<style scoped lang="scss">
.app-sidebar {
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  height: 100%;
  background: $bg-sidebar;
  border-right: 1px solid rgba($color-primary, 0.12);
}

.app-sidebar__header {
  flex-shrink: 0;
  padding: 20px 16px 12px;
  border-bottom: 1px solid rgba($color-primary, 0.1);
}

.app-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: inherit;
  text-decoration: none;
}

.app-sidebar__logo-img {
  width: 36px;
  height: 36px;
  object-fit: contain;
  flex-shrink: 0;
}

.app-sidebar__name {
  font-size: 17px;
  font-weight: 600;
  line-height: 1.3;
  color: $text-primary;
}

.app-sidebar__name-short {
  display: none;
  font-size: 17px;
  font-weight: 600;
}

.app-sidebar__menu {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.app-sidebar__menu-inner {
  border-right: none;
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: rgba($color-primary, 0.08);
  --el-menu-text-color: #{$text-primary};
}

:deep(.el-sub-menu__title) {
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent !important;
}

:deep(.el-sub-menu__title .app-sidebar__menu-icon) {
  flex-shrink: 0;
  width: 1em;
  height: 1em;
  font-size: 18px;
  margin: 0;
}

:deep(.el-menu-item .app-sidebar__menu-icon) {
  flex-shrink: 0;
  width: 1em;
  height: 1em;
  font-size: 18px;
  margin: 0;
}

:deep(.el-menu--inline) {
  background: $bg-sidebar-submenu !important;
}

:deep(.el-sub-menu .el-menu-item) {
  background: transparent !important;
  min-width: auto;
}

:deep(.el-sub-menu .el-menu-item.is-active) {
  background: $color-primary-light !important;
}

.app-sidebar__footer {
  flex-shrink: 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 16px 16px;
  border-top: 1px solid rgba($color-primary, 0.1);
}

.app-sidebar__locale {
  flex-shrink: 0;
  padding: 4px 8px;
}

.app-sidebar__user {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 0;
  min-width: 0;
  flex: 1;
}

.app-sidebar__username {
  font-size: var(--font-size-sidebar);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-admin-tag {
  margin-left: auto;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  font-size: var(--font-size-sidebar);
}

:deep(.el-menu-item) {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.el-menu-item.is-active) {
  background: $color-primary-light !important;
  color: $color-primary-dark !important;
  border-left: 3px solid $color-primary;
}

:deep(.el-menu-item.menu-item--featured:not(.is-active)) {
  background: linear-gradient(90deg, rgba($color-primary, 0.12), transparent);
  color: $color-primary-dark;
  font-weight: 600;
}

:deep(.el-menu-item.menu-item--admin:not(.is-active)) {
  color: $text-secondary;
}

:deep(.el-sub-menu__title:hover),
:deep(.el-menu-item:hover) {
  background: rgba($color-primary, 0.06);
}

@media (max-width: 991px) {
  .app-sidebar {
    width: 100%;
    border-right: none;
  }

  .app-sidebar__name {
    display: none;
  }

  .app-sidebar__name-short {
    display: inline;
  }
}
</style>
