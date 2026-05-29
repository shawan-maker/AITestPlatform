<template>
  <button
    type="button"
    class="ui-tree-menu-trigger"
    :aria-label="ariaLabel"
    @click.stop
  >
    <el-icon><MoreFilled /></el-icon>
  </button>
</template>

<script setup>
import { MoreFilled } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const ariaLabel = t('common.moreActions')
</script>
