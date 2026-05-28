<template>
  <EmptyState :title="t('page.forbidden.title')" :description="t('page.forbidden.desc')">
    <el-button type="primary" @click="router.push('/agent')">{{ t('common.backHome') }}</el-button>
  </EmptyState>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
const { t } = useI18n()
</script>
