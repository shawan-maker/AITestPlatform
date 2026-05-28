<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import en from 'element-plus/dist/locale/en.mjs'
import { useLocaleStore } from '@/stores/locale'

const localeStore = useLocaleStore()

const elementLocale = computed(() => (localeStore.locale === 'zh-CN' ? zhCn : en))
</script>
